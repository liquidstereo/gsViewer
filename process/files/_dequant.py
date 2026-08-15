import numpy as np

_LOGIT_EPS: float = 0.000001
_NORM_EPS: float = 0.00000001

def logit_from_u8(u8: np.ndarray) -> np.ndarray:
    p = np.clip(u8.astype(np.float32) / 255.0, _LOGIT_EPS, 1.0 - _LOGIT_EPS)
    return np.log(p / (1.0 - p)).astype(np.float32)

def quat_normalize_safe(raw: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(raw, axis=1, keepdims=True)
    norm = np.where(norm < _NORM_EPS, 1.0, norm)
    return (raw / norm).astype(np.float32)
