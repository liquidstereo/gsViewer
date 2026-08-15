import argparse
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path

from PySide6.QtWidgets import QApplication

from configs.settings import (
    LOGS_DIR, SAVE_EXT, SLICING_RATIO, PLAYBACK_MODE,
)
from configs.settings_window import WINDOW_WIDTH, WINDOW_HEIGHT
from configs.settings_overlay import DISPLAY_COMPACT_OVERLAY
from configs.settings_camera import TURNTABLE
from process.handle import setup_logging, register_sigint_handler
from process.keys.effects import apply_compact_overlays
from process.data.loader import configure_slicing
from process.data.buffer import FrameBuffer
from process.data.pointcloud_buffer import is_pointcloud_splat
from process.data.pointcloud_caps import notify_unsupported
from process.launch_inputs import load_inputs  # noqa: F401
from process.camera import (
    init_camera_from_splat, cam_pos_from_viewmat, _viewmat_from_cam,
)
from process.mode import configure_startup_mode
from process.renderer.core import warmup_renderer
from process.common import (
    resolve_input_path, build_cache_config, build_json_session_key,
    build_output_stem,
)
from process.save import save_frames, resolve_save_target
from process.viewer.core import GSSplatWindow, force_exit
from process.sequence import init_seq_player, init_seq_players_unified

try:
    from plugins import load_plugins
except ImportError:
    def load_plugins(
        names_csv: str | None,
        resources: dict | None = None,
        input_ids: list[str] | None = None,
    ) -> list[object]:
        return []

logger = logging.getLogger(__name__)

@dataclass
class ViewerSession:

    paths: list[Path] = field(default_factory=list)
    primary_path: Path | None = None
    primary_id: str = ''
    input_ids: list[str] = field(default_factory=list)
    log_path: Path | None = None
    plugins: list[object] = field(default_factory=list)
    cache_cfg: dict = field(default_factory=dict)
    inputs: dict = field(default_factory=dict)

    chain_segments: list = field(default_factory=list)
    files: list = field(default_factory=list)
    buf: FrameBuffer | None = None
    first_splat: object = None
    cam: object = None
    K: object = None
    seq_players: dict = field(default_factory=dict)
    seq_player: object = None

def _apply_cli_slicing(args: argparse.Namespace) -> None:

    ratio = (
        args.slicing_ratio if args.slicing_ratio is not None
        else SLICING_RATIO
    )
    configure_slicing(ratio < 1.0, ratio)

def _apply_cli_mode(args: argparse.Namespace) -> None:
    configure_startup_mode(getattr(args, 'mode', None))

def init_session(args: argparse.Namespace) -> ViewerSession:
    raw_inputs = [s.strip() for s in args.input.split(',') if s.strip()]
    paths = [resolve_input_path(s) for s in raw_inputs]
    primary_path = paths[0]
    primary_id = (
        primary_path.stem if primary_path.is_file() else primary_path.name
    )
    input_ids = [p.stem if p.is_file() else p.name for p in paths]
    log_stem = build_output_stem(primary_id, input_ids)
    setup_logging(log_stem, verbose=args.verbose)
    _apply_cli_slicing(args)
    _apply_cli_mode(args)
    register_sigint_handler()
    plugins = load_plugins(
        args.plugin,
        resources={'audio': args.audio, 'frame_range': args.range},
        input_ids=input_ids,
    )
    return ViewerSession(
        paths=paths,
        primary_path=primary_path,
        primary_id=primary_id,
        input_ids=input_ids,
        log_path=LOGS_DIR / f'{log_stem}.log',
        plugins=plugins,
        cache_cfg=build_cache_config(args.no_cache),
    )

POINTCLOUD_STARTUP_MODE: str = 'PointCloud'

def setup_render_context(session: ViewerSession) -> None:
    buf = session.buf
    first_splat = buf.get(0)
    cam, K = init_camera_from_splat(first_splat, WINDOW_WIDTH, WINDOW_HEIGHT)
    if is_pointcloud_splat(first_splat):

        configure_startup_mode(POINTCLOUD_STARTUP_MODE)
        logger.info(
            'Pure point cloud input -> startup render mode: %s',
            POINTCLOUD_STARTUP_MODE,
        )
        session.first_splat = first_splat
        session.cam = cam
        session.K = K
        return
    warmup_renderer(first_splat, cam, K)

    if not TURNTABLE:
        buf.set_cam_pos(cam_pos_from_viewmat(_viewmat_from_cam(cam)))
    if session.cache_cfg['use_gpu_preload']:
        buf.preload_gpu_sync()
    session.first_splat = first_splat
    session.cam = cam
    session.K = K

def setup_seq_players(
    session: ViewerSession, args: argparse.Namespace,
) -> None:
    use_cache = session.cache_cfg['use_seq_cache']

    if session.chain_segments:
        specs = [
            (p.stem if p.is_file() else p.name, None, args.range, p)
            for p in session.paths
        ]
        seq_players = init_seq_players_unified(specs, use_cache=use_cache)
        session.seq_players = seq_players
        session.seq_player = seq_players.get(session.primary_id)
        return
    if len(session.inputs) == 1:
        entry = session.inputs[session.primary_id]
        sp = init_seq_player(
            None, session.primary_id, args.range,
            use_cache=use_cache, search_path=entry['path'],
        )
        seq_players: dict = (
            {session.primary_id: sp} if sp is not None else {}
        )
    else:
        specs = [
            (iid, None, args.range, entry['path'])
            for iid, entry in session.inputs.items()
        ]
        seq_players = init_seq_players_unified(specs, use_cache=use_cache)
    session.seq_players = seq_players
    session.seq_player = seq_players.get(session.primary_id)

def launch_viewer(
    session: ViewerSession,
    args: argparse.Namespace,
    start_time: float | None,
) -> None:
    app = QApplication(sys.argv)
    if args.silent_save:
        _run_silent_save(session, args)
        return
    win = _build_window(session, args, start_time)
    if DISPLAY_COMPACT_OVERLAY:

        apply_compact_overlays(win, True)

    notify_unsupported(win)
    register_sigint_handler(win._ctrl_c_exit)
    win.show()
    print('--')
    sys.exit(app.exec())

def _run_silent_save(
    session: ViewerSession, args: argparse.Namespace,
) -> None:
    ext = (args.format or SAVE_EXT).lower()
    plugin_names = [
        s.strip() for s in (args.plugin or '').split(',') if s.strip()
    ]
    save_dir, stem = resolve_save_target(
        session.primary_path, plugin_names, ext, session.input_ids,
    )
    save_frames(
        session.files, session.buf, session.cam, session.K,
        WINDOW_WIDTH, WINDOW_HEIGHT, save_dir,
        save_format=args.format, save_quality=args.quality, stem=stem,
    )
    print('--')
    force_exit(session.primary_id, session.log_path, len(session.files))

def _compute_save_limit(
    args: argparse.Namespace, files: list,
) -> int | None:
    if args.range is not None and len(files) == 1:
        s, e = args.range.split('-')
        return int(e) - int(s) + 1
    return None

def _build_window(
    session: ViewerSession,
    args: argparse.Namespace,
    start_time: float | None,
) -> GSSplatWindow:
    plugin_names = [
        s.strip() for s in (args.plugin or '').split(',') if s.strip()
    ]
    save_dir: Path | None = None
    save_stem = ''
    if args.save or args.save_quit:
        ext = (args.format or SAVE_EXT).lower()
        save_dir, save_stem = resolve_save_target(
            session.primary_path, plugin_names, ext, session.input_ids,
        )
    save_limit = _compute_save_limit(args, session.files)

    live_save_dir, live_save_stem = resolve_save_target(
        session.primary_path, plugin_names, 'mp4', session.input_ids,
    )
    json_key = build_json_session_key(
        list(session.inputs.keys()), plugin_names,
    )
    return GSSplatWindow(
        session.files, session.buf, session.first_splat,
        session.cam, session.K,
        save_dir=save_dir,
        save_stem=save_stem,
        input_name=session.primary_id,
        json_key=json_key,
        log_path=session.log_path,
        seq_player=session.seq_player,
        seq_players=session.seq_players,
        continuous=args.continuous,
        turntable=args.turntable,
        save_limit=save_limit,
        plugins=session.plugins,
        inputs=session.inputs,
        active_id=session.primary_id,
        save_quit=args.save_quit,
        start_time=start_time,
        save_format=args.format,
        save_quality=args.quality,
        playback_mode=(args.playback_mode or PLAYBACK_MODE),
        chain_segments=session.chain_segments,
        input_ids=session.input_ids,
        no_overlay=args.no_overlay,
        live_save_dir=live_save_dir,
        live_save_stem=live_save_stem,
    )
