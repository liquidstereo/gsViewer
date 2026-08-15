import numpy as np

CAMERA_MODEL_ORTHO: str = 'ortho'

def _as_numpy(mat) -> np.ndarray:

    arr = mat.detach().cpu().numpy() if hasattr(mat, 'detach') else (
        np.asarray(mat))
    arr = np.asarray(arr, dtype=np.float32)
    if arr.ndim == 3 and arr.shape[0] == 1:
        arr = arr[0]
    return arr

def _validate(viewmat: np.ndarray, K: np.ndarray, w: int, h: int,
              near: float, far: float) -> None:
    if w <= 0 or h <= 0:
        raise ValueError(f'Viewport must be positive: w={w} h={h}')
    if not near > 0.0:
        raise ValueError(f'near must be > 0: {near}')
    if not far > near:
        raise ValueError(f'far must be > near: near={near} far={far}')
    if viewmat.shape != (4, 4):
        raise ValueError(f'viewmat must be (4, 4): {viewmat.shape}')
    if K.shape != (3, 3):
        raise ValueError(f'K must be (3, 3): {K.shape}')

def _projection(K: np.ndarray, w: int, h: int, near: float, far: float,
                camera_model: str) -> np.ndarray:
    fx, fy = float(K[0, 0]), float(K[1, 1])
    cx, cy = float(K[0, 2]), float(K[1, 2])
    proj = np.zeros((4, 4), dtype=np.float32)
    proj[0, 0] = 2.0 * fx / w
    proj[1, 1] = -2.0 * fy / h
    if camera_model == CAMERA_MODEL_ORTHO:

        proj[0, 3] = 2.0 * cx / w - 1.0
        proj[1, 3] = 1.0 - 2.0 * cy / h
        proj[2, 2] = 2.0 / (far - near)
        proj[2, 3] = -(far + near) / (far - near)
        proj[3, 3] = 1.0
        return proj

    proj[0, 2] = 2.0 * cx / w - 1.0
    proj[1, 2] = 1.0 - 2.0 * cy / h
    proj[2, 2] = (far + near) / (far - near)
    proj[2, 3] = -2.0 * far * near / (far - near)
    proj[3, 2] = 1.0
    return proj

def mvp_from_viewmat_k(
    viewmat, K, w: int, h: int, near: float, far: float,
    camera_model: str = 'pinhole',
) -> np.ndarray:
    vm = _as_numpy(viewmat)
    k = _as_numpy(K)
    _validate(vm, k, w, h, near, far)
    proj = _projection(k, w, h, near, far, camera_model)
    return np.ascontiguousarray(proj @ vm, dtype=np.float32)

def project_ndc(mvp: np.ndarray, points: np.ndarray) -> np.ndarray:
    pts = np.asarray(points, dtype=np.float32).reshape(-1, 3)
    homo = np.hstack([pts, np.ones((len(pts), 1), dtype=np.float32)])
    clip = homo @ np.asarray(mvp, dtype=np.float32).T
    w_clip = clip[:, 3:4]
    ndc = np.full((len(pts), 3), np.nan, dtype=np.float32)
    valid = (w_clip[:, 0] > 0.0)
    if valid.any():
        ndc[valid] = clip[valid, :3] / w_clip[valid]
    return ndc

def ndc_to_pixel(ndc: np.ndarray, w: int, h: int) -> np.ndarray:
    arr = np.asarray(ndc, dtype=np.float32).reshape(-1, 3)
    u = (arr[:, 0] + 1.0) * 0.5 * w
    v = (1.0 - arr[:, 1]) * 0.5 * h
    return np.ascontiguousarray(np.column_stack([u, v]), dtype=np.float32)
