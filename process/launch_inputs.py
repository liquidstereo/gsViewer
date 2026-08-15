import argparse
import logging
from pathlib import Path

from configs.settings import GPU_AHEAD, CHAIN_GPU_AHEAD, PLAYBACK_MODE
from process.camera import auto_apply_world_rot
from process.data.buffer import FrameBuffer
from process.data.loader import apply_frame_range, collect_ply_files
from process.data.pointcloud import is_pure_point_cloud
from process.data.pointcloud_buffer import PointCloudBuffer
from process.data.preload import preload_unified
from process.playmode import is_playlist, build_ordered_segments

logger = logging.getLogger(__name__)

def _load_chain_inputs(
    session, args: argparse.Namespace, cache_cfg: dict,
    mode: str,
) -> None:

    specs: list = []
    for p in session.paths:
        iid = p.stem if p.is_file() else p.name
        _files = apply_frame_range(collect_ply_files(p), args.range)
        if p is session.primary_path:
            auto_apply_world_rot(_files)
        specs.append((iid, _files))
    all_files, segments = build_ordered_segments(specs, mode)

    buf = FrameBuffer(
        all_files, gpu_ahead=CHAIN_GPU_AHEAD,
        use_cache=cache_cfg['use_disk_cache'],
    )
    buf.preload_with_progress()
    cid = session.primary_id
    session.inputs = {cid: {'files': all_files, 'buf': buf,
                            'path': session.primary_path}}
    session.chain_segments = segments
    session.files = all_files
    session.buf = buf

def _is_pointcloud_input(files: list) -> bool:

    if not files:
        return False
    if not is_pure_point_cloud(files[0]):
        return False
    if len(files) > 1:
        logger.warning(
            'Point cloud sequence is not supported yet - using the '
            'first frame only (%s)', files[0].name,
        )
    return True

def _build_pointcloud_input(files: list, path: Path, cache_cfg: dict) -> dict:

    buf = PointCloudBuffer(
        files[:1], use_cache=cache_cfg['use_disk_cache'],
    )
    return {'files': files[:1], 'buf': buf, 'path': path}

def load_inputs(
    session, args: argparse.Namespace,
) -> None:
    cache_cfg = session.cache_cfg
    mode = args.playback_mode or PLAYBACK_MODE
    n_inputs = len(
        {(p.stem if p.is_file() else p.name) for p in session.paths}
    )

    if (args.playback_mode is None and n_inputs > 1
            and all(p.is_file() for p in session.paths)):
        mode = 'loop'
        logger.info('Multi single-file input -> loop (merge) mode')

    if mode in ('chain', 'shuffle', 'random') and n_inputs > 1:
        _load_chain_inputs(session, args, cache_cfg, mode)
        return

    playlist = is_playlist(mode, n_inputs)
    inputs: dict = {}
    for p in session.paths:
        iid = p.stem if p.is_file() else p.name
        if iid in inputs:
            continue
        _files = apply_frame_range(collect_ply_files(p), args.range)
        if _is_pointcloud_input(_files):
            inputs[iid] = _build_pointcloud_input(_files, p, cache_cfg)
            continue
        if p is session.primary_path:
            auto_apply_world_rot(_files)
        ahead = (
            0 if (playlist and p is not session.primary_path) else GPU_AHEAD
        )
        _buf = FrameBuffer(
            _files, gpu_ahead=ahead, use_cache=cache_cfg['use_disk_cache'],
        )
        inputs[iid] = {'files': _files, 'buf': _buf, 'path': p}
    if len(inputs) == 1:
        inputs[session.primary_id]['buf'].preload_with_progress()
    else:
        preload_unified([e['buf'] for e in inputs.values()])
    session.inputs = inputs
    session.files = inputs[session.primary_id]['files']
    session.buf = inputs[session.primary_id]['buf']
