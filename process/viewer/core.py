import concurrent.futures
import copy
import logging
import threading
from pathlib import Path

import torch
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication, QMainWindow

from configs.settings import (
    WINDOW_TITLE, SAVE_EXT, UNDO_LIMIT, AVOID_NAME_COLLISION,
    SAVE_ENCODE_WORKERS,
)
from process.save import unique_path
from process.common.blink import BlinkController
from process.console.defaults import apply_startup_defaults
from process.viewer.window_scale import build_central
from process.undo import UndoStack
from process.record import is_video_ext, create_recorder, FALLBACK_IMG_EXT
from configs.settings_window import (
    WINDOW_WIDTH, WINDOW_HEIGHT, SET_WINDOW_FIXED_SIZE,
    DISABLE_MAXIMIZE_BUTTON,
)
from configs.settings_overlay import (
    HIDE_ALL_OVERLAY, BUFFER_MESSAGE, LIVE_REC_BLINK_MS,
)
from process.keys.effects import apply_all_overlays_visible
from process.data.buffer import FrameBuffer
from process.component.random import (
    RandomComponent, register_random_console)
from process.component.time import (
    TimeComponent, register_time_console)
from process.component.spring import (
    SpringComponent, register_spring_console)
from process.component.wiggle import attach_wiggle_component
from process.camera import _viewmat_from_cam, cam_pos_from_viewmat
from process.sequence.player import SequencePlayer

from process.viewer.exit import force_exit
from process.viewer.mixin_playback import PlaybackMixin
from process.viewer.mixin_reslice import ResliceBufferMixin
from process.viewer.mixin_io import SaveRecordMixin
from process.viewer.mixin_lifecycle import LifecycleMixin
from process.viewer.mixin_frame import FrameMixin
from process.viewer.mixin_events import EventsMixin
from process.viewer.mixin_record_live import RecordLiveMixin
from process.widget.core import SplatWidget

from process.viewer.init_state import (
    init_annotation_state, init_display_state, init_help_state,
    init_hook_registry,
)
from process.transform import register_transform
from process.transform.object_plugin import install_object_plugin_gates
from process.objects import register_objects
from process.cursor import register_context_menu

from process.annotation.attr_section import register_annotation_attr_section
from process.widget.overlays import (
    register_attribute_editor, register_audio_list, register_region_list,
)

logger = logging.getLogger(__name__)

__all__ = ['GSSplatWindow', 'force_exit']

class GSSplatWindow(
    PlaybackMixin, ResliceBufferMixin, SaveRecordMixin, LifecycleMixin,
    FrameMixin, EventsMixin, RecordLiveMixin, QMainWindow,
):
    def __init__(
        self,
        files: list[Path],
        buf: FrameBuffer,
        first_splat: dict,
        cam: dict,
        K: torch.Tensor,
        w: int = WINDOW_WIDTH,
        h: int = WINDOW_HEIGHT,
        save_dir: Path | None = None,
        save_stem: str = '',
        input_name: str = '',
        json_key: str = '',
        log_path: Path | None = None,
        seq_player: SequencePlayer | None = None,
        seq_players: dict | None = None,
        continuous: bool = False,
        turntable: bool = False,
        save_limit: int | None = None,
        plugins: list | None = None,
        inputs: dict | None = None,
        active_id: str | None = None,
        save_quit: bool = False,
        start_time: float | None = None,
        save_format: str | None = None,
        save_quality: str | None = None,
        playback_mode: str = 'loop',
        chain_segments: list | None = None,
        input_ids: list | None = None,
        no_overlay: bool = False,
        live_save_dir: Path | None = None,
        live_save_stem: str = '',
    ):
        super().__init__()

        if inputs is None:
            inputs = {input_name or 'primary': {'files': files, 'buf': buf}}
        self._inputs: dict = inputs

        self._input_ids: list = input_ids or list(inputs.keys())
        self._active_id: str = (
            active_id or input_name or next(iter(inputs))
        )

        self._init_playback_state(inputs, playback_mode, chain_segments)
        self._cam = cam
        self._K = K
        self._w = w
        self._h = h
        self._idx = 0

        self._seq_idx = 0

        self._anim_tick = 0
        self._playing = False

        self._last_frame_time: float = 0.0

        self._last_tick_time: float = 0.0

        self._playback_started: bool = False

        self._buffering: bool = False

        self._needs_rebuffer: bool = False

        self._buffer_message: str = BUFFER_MESSAGE
        self._save_dir = save_dir

        self._save_out_dir: Path | None = save_dir
        self._last_ts: float = 0.0
        self._fps: float = 0.0
        self._save_continuous: bool = continuous
        self._save_quit: bool = save_quit
        self._save_count: int = 0

        self._save_frame_primed: bool = False

        self._save_audio_positions: list = []
        _default_limit = save_limit if save_limit is not None else len(files)
        self._save_limit: int = (
            _default_limit if (save_dir is not None and not continuous) else 0
        )
        if self._save_dir is not None:
            self._save_dir.mkdir(parents=True, exist_ok=True)
            logger.info(
                'Auto-save enabled: %s (limit=%s)',
                self._save_dir,
                self._save_limit if not continuous else 'unlimited',
            )
        self._save_executor: (
            concurrent.futures.ThreadPoolExecutor | None
        ) = (
            concurrent.futures.ThreadPoolExecutor(
                max_workers=max(1, SAVE_ENCODE_WORKERS)
            )
            if self._save_dir is not None else None
        )

        self._recorder = None
        self._save_quality: str | None = save_quality
        self._save_stem: str = save_stem or input_name or 'primary'

        self._save_out_file: Path | None = None
        self._save_renamed: tuple[Path, Path] | None = None

        self._save_time_diff_msg: str = ''

        self._live_recording: bool = False
        self._live_recorder = None
        self._live_executor: (
            concurrent.futures.ThreadPoolExecutor | None
        ) = None
        self._live_out_file: Path | None = None
        self._live_last_tick: int = -1

        self._live_audio_positions: list = []
        self._live_cur_audio_pos = None
        self._live_sync_orig = None
        self._live_plist_orig = None

        self._live_dir: Path | None = live_save_dir
        self._live_stem: str = live_save_stem

        self._live_saved_file: Path | None = None
        self._live_saved_count: int = 0
        save_ext = (save_format or SAVE_EXT).lower()
        self._save_img_ext: str = save_ext
        if self._save_dir is not None and is_video_ext(save_ext):
            rec_stem = self._save_stem
            out_path = self._save_dir / f'{rec_stem}.{save_ext}'
            if AVOID_NAME_COLLISION:
                uniq = unique_path(out_path)
                if uniq != out_path:
                    self._save_renamed = (out_path, uniq)
                out_path = uniq
                rec_stem = out_path.stem
            self._save_out_file = out_path
            self._recorder = create_recorder(
                self._save_dir, rec_stem, save_ext, w, h,
                quality=save_quality,
            )
            if self._recorder is None:
                self._save_img_ext = FALLBACK_IMG_EXT
                self._save_out_file = None
                self._save_renamed = None
        self._input_name: str = input_name

        self._json_key: str = json_key or input_name
        self._log_path: Path | None = log_path
        self._start_time: float | None = start_time
        self._seq_player: SequencePlayer | None = seq_player
        self._seq_players: dict[str, SequencePlayer] = seq_players or {}
        self._splats: dict = {self._active_id: first_splat}
        self._splat = first_splat
        self._particles = None
        self._frame_processors: list = []

        self._random_component = RandomComponent()

        self._console_contributors: list = []
        register_random_console(self)

        self._time_component = TimeComponent()
        register_time_console(self)

        self._spring_component = SpringComponent()
        register_spring_console(self)

        attach_wiggle_component(self)

        self._rendering: bool = False

        init_hook_registry(self)
        self._init_cam: dict = copy.deepcopy(cam)

        self._ortho_active: str | None = None
        self._ortho_saved: dict | None = None
        self._camera_model: str = 'pinhole'
        self._viewmat = _viewmat_from_cam(cam)
        _cam_pos = cam_pos_from_viewmat(self._viewmat)
        for _entry in self._inputs.values():
            _entry['buf'].set_cam_pos(_cam_pos)

        init_display_state(self, turntable)
        init_annotation_state(self)
        init_help_state(self)

        self._widget = SplatWidget(self._on_cam_event, self)
        self._widget.setFixedSize(w, h)
        self._widget.set_first_paint_callback(self._on_first_paint)

        central, self._disp_w, self._disp_h = build_central(
            self._widget, w, h
        )
        if (self._disp_w, self._disp_h) != (w, h):
            logger.warning(
                'Viewer window downscaled by FORCE_RESIZE_WINDOW: '
                'render %dx%d -> display %dx%d. '
                'Saved output keeps full %dx%d resolution.',
                w, h, self._disp_w, self._disp_h, w, h,
                extra={'alert': 'Viewer window downscaled to fit'},
            )
        self.setCentralWidget(central)

        if DISABLE_MAXIMIZE_BUTTON:
            self.setWindowFlags(
                self.windowFlags()
                & ~Qt.WindowType.WindowMaximizeButtonHint)

        if SET_WINDOW_FIXED_SIZE:
            self.setFixedSize(self._disp_w, self._disp_h)
        geom = QApplication.primaryScreen().availableGeometry()
        self.move(
            geom.x() + (geom.width() - self._disp_w) // 2,
            geom.y() + (geom.height() - self._disp_h) // 2,
        )

        self._timer = QTimer(self)
        self._timer.setInterval(0)
        self._timer.timeout.connect(self._on_timer)

        self._live_blink = BlinkController(
            self, LIVE_REC_BLINK_MS, self._on_live_blink_change,
        )

        self._sys_info: dict | None = None
        self._gpu_info: dict | None = None
        self._stop_sys_event = threading.Event()
        self._sys_thread = threading.Thread(
            target=self._sys_monitor_loop, daemon=True)
        self._sys_thread.start()

        if len(self._input_ids) > 1:
            title_name = f'{input_name} and more...'
        else:
            title_name = input_name
        self.setWindowTitle(f'{WINDOW_TITLE} - {title_name}')

        self._load_initial_splat()
        self._undo_stack = UndoStack(UNDO_LIMIT)
        self._plugins = list(plugins or [])
        for _p in self._plugins:
            _p.attach(self)

            apply_startup_defaults(_p)
        install_object_plugin_gates(self)
        register_transform(self)
        register_context_menu(self)

        register_attribute_editor(self)
        register_region_list(self)
        register_audio_list(self)
        register_objects(self)
        register_annotation_attr_section(self)

        self._render_current()

        if no_overlay or HIDE_ALL_OVERLAY:
            apply_all_overlays_visible(self, False)
