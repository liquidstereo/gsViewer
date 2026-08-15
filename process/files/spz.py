import gzip
import logging
import struct
import time
from collections.abc import Callable
from pathlib import Path

import numpy as np

from process.files._dequant import logit_from_u8, quat_normalize_safe

logger = logging.getLogger(__name__)

_SPZ_MAGIC: int = 0x5053474E
_GZIP_MAGIC: bytes = bytes([0x1F, 0x8B])
_ZSTD_MAGIC: bytes = bytes([0x28, 0xB5, 0x2F, 0xFD])
_HEADER_SIZE: int = 128
_HEADER_SIZE_V2: int = 16
_SH_BANDS: int = 16
_SCALE_FACTOR: float = 16.0
_SCALE_OFFSET: float = 8.0
_QUANT_CENTER: float = 128.0
_QUANT_SCALE: float = 128.0

def _find_zstd_offsets(data: bytes, n: int) -> list[int]:
    offsets: list[int] = []
    pos = 0
    while len(offsets) < n:
        idx = data.find(_ZSTD_MAGIC, pos)
        if idx == -1:
            break
        offsets.append(idx)
        pos = idx + 4
    return offsets

def _decompress_zstd_sections(
    data: bytes, n_sections: int
) -> list[bytes]:
    try:
        import zstandard as zstd
    except ImportError as exc:
        raise ImportError(
            'zstandard package required for SPZ v4: '
            'conda run -n gsViewer pip install zstandard'
        ) from exc
    offsets = _find_zstd_offsets(data, n_sections)
    if len(offsets) != n_sections:
        raise ValueError(
            f'Expected {n_sections} ZSTD sections, '
            f'found {len(offsets)}'
        )
    ends = offsets[1:] + [len(data)]
    dctx = zstd.ZstdDecompressor()
    return [dctx.decompress(data[s:e]) for s, e in zip(offsets, ends)]

def _decode_int24_col(arr: np.ndarray) -> np.ndarray:
    v = (
        arr[:, 0].astype(np.int32)
        | (arr[:, 1].astype(np.int32) << 8)
        | (arr[:, 2].astype(np.int32) << 16)
    )
    v[v >= (1 << 23)] -= (1 << 24)
    return v

def _decode_positions(
    sec: bytes, n: int, frac_bits: int
) -> np.ndarray:
    raw = np.frombuffer(sec, dtype=np.uint8).reshape(n, 9)
    scale = float(1 << frac_bits)
    xyz = [_decode_int24_col(raw[:, i * 3:(i + 1) * 3]) for i in range(3)]
    return np.stack(xyz, axis=1).astype(np.float32) / scale

def _decode_alphas(sec: bytes) -> np.ndarray:
    u8 = np.frombuffer(sec, dtype=np.uint8)
    return logit_from_u8(u8)

def _decode_sh_dc(sec: bytes, n: int) -> np.ndarray:
    u8 = np.frombuffer(sec, dtype=np.uint8).reshape(n, 3)
    return (u8.astype(np.float32) - _QUANT_CENTER) / _QUANT_SCALE

def _decode_scales(sec: bytes, n: int) -> np.ndarray:
    u8 = np.frombuffer(sec, dtype=np.uint8).reshape(n, 3)
    return (u8.astype(np.float32) / _SCALE_FACTOR - _SCALE_OFFSET)

def _decode_rotations(sec: bytes, n: int) -> np.ndarray:
    i8 = np.frombuffer(sec, dtype=np.int8).reshape(n, 4)
    raw = i8.astype(np.float32) / _QUANT_SCALE
    return quat_normalize_safe(raw)

def _decode_rotations_3c(sec: bytes, n: int) -> np.ndarray:
    i8 = np.frombuffer(sec, dtype=np.int8).reshape(n, 3)
    xyz = i8.astype(np.float32) / _QUANT_SCALE
    w = np.sqrt(np.clip(1.0 - np.sum(xyz**2, axis=1, keepdims=True), 0.0, None))
    return np.concatenate([w, xyz], axis=1).astype(np.float32)

def _decode_sh_higher(
    sec: bytes, n: int, sh_degree: int
) -> np.ndarray:
    n_higher = (sh_degree + 1) ** 2 - 1
    u8 = np.frombuffer(sec, dtype=np.uint8).reshape(n, n_higher * 3)
    high = (u8.astype(np.float32) - _QUANT_CENTER) / _QUANT_SCALE
    return high.reshape(n, 3, n_higher).transpose(0, 2, 1)

def _build_sh_coeffs(
    sh_dc: np.ndarray,
    sh_high: np.ndarray,
    n: int,
    sh_degree: int,
) -> np.ndarray:
    sh_coeffs = np.zeros((n, _SH_BANDS, 3), dtype=np.float32)
    sh_coeffs[:, 0, :] = sh_dc
    if sh_degree > 0:
        n_high = min(sh_high.shape[1], _SH_BANDS - 1)
        sh_coeffs[:, 1:1 + n_high, :] = sh_high[:, :n_high, :]
    return sh_coeffs

def _decode_secs(
    secs: list[bytes], n: int, sh_degree: int, frac_bits: int
) -> dict:
    means_np = _decode_positions(secs[0], n, frac_bits)
    opacity_logit = _decode_alphas(secs[1])
    sh_dc = _decode_sh_dc(secs[2], n)
    log_scales_np = _decode_scales(secs[3], n)
    quats_np = _decode_rotations(secs[4], n)
    sh_high = _decode_sh_higher(secs[5], n, sh_degree)
    sh_coeffs = _build_sh_coeffs(sh_dc, sh_high, n, sh_degree)
    return {
        'means_np': means_np,
        'log_scales_np': log_scales_np,
        'quats_np': quats_np,
        'opacity_logit': opacity_logit,
        'sh_coeffs': sh_coeffs,
    }

def _parse_v2(
    data: bytes, n: int, sh_degree: int, frac_bits: int
) -> dict:
    t0 = time.perf_counter()
    n_higher = (sh_degree + 1) ** 2 - 1

    sizes = [n * 9, n, n * 3, n * 3, n * 3, n * n_higher * 3]
    secs: list[bytes] = []
    pos = _HEADER_SIZE_V2
    for s in sizes:
        secs.append(data[pos:pos + s])
        pos += s
    means_np = _decode_positions(secs[0], n, frac_bits)
    opacity_logit = _decode_alphas(secs[1])
    log_scales_np = _decode_scales(secs[2], n)
    quats_np = _decode_rotations_3c(secs[3], n)
    sh_dc = _decode_sh_dc(secs[4], n)
    sh_high = _decode_sh_higher(secs[5], n, sh_degree)
    sh_coeffs = _build_sh_coeffs(sh_dc, sh_high, n, sh_degree)
    logger.debug(
        'SPZ v2 decoded: %d gaussians in %.2fs', n, time.perf_counter() - t0
    )
    return {
        'means_np': means_np,
        'log_scales_np': log_scales_np,
        'quats_np': quats_np,
        'opacity_logit': opacity_logit,
        'sh_coeffs': sh_coeffs,
    }

def _parse_v4(
    data: bytes,
    n: int,
    sh_degree: int,
    frac_bits: int,
    n_sections: int,
) -> dict:
    t0 = time.perf_counter()
    secs = _decompress_zstd_sections(data, n_sections)
    result = _decode_secs(secs, n, sh_degree, frac_bits)
    logger.debug(
        'SPZ v4 decoded: %d gaussians in %.2fs', n, time.perf_counter() - t0
    )
    return result

def load_spz_frame(
    path: Path,
    on_progress: Callable[[float], None] | None = None,
) -> dict:
    t0 = time.perf_counter()
    data = path.read_bytes()
    if data[:2] == _GZIP_MAGIC:
        data = gzip.decompress(data)
    magic, version, n_points = struct.unpack_from('<III', data, 0)
    if magic != _SPZ_MAGIC:
        raise ValueError(f'Invalid SPZ magic: 0x{magic:08X}')
    sh_degree = data[12]
    frac_bits = data[13]
    n_sections = data[15]
    if on_progress is not None:
        on_progress(0.3)
    if version == 2:
        result = _parse_v2(data, n_points, sh_degree, frac_bits)
    elif version == 4:
        result = _parse_v4(data, n_points, sh_degree, frac_bits, n_sections)
    else:
        raise NotImplementedError(
            f'SPZ version {version} not supported (v2/v4 only)'
        )
    if on_progress is not None:
        on_progress(1.0)
    logger.info(
        'Loaded %s: %d gaussians in %.2fs',
        path.name, n_points, time.perf_counter() - t0,
    )
    return result
