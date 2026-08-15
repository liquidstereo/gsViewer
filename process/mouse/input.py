import logging
import math

import numpy as np

from configs.settings_camera import (
    ORBIT_SPEED, PAN_SPEED, ZOOM_SPEED, EL_CLAMP,
)

logger = logging.getLogger(__name__)

def orbit(win, dx: int, dy: int) -> None:

    if getattr(win, '_ortho_active', None) is not None:
        return
    win._cam['azimuth'] += dx * ORBIT_SPEED
    win._cam['elevation'] += dy * ORBIT_SPEED
    win._update_cam()
    logger.debug(
        'Orbit az=%.3f el=%.3f',
        win._cam['azimuth'], win._cam['elevation'],
    )

def _cam_basis(cam: dict) -> tuple[np.ndarray, np.ndarray]:
    az = cam['azimuth']
    el = float(np.clip(cam['elevation'], -EL_CLAMP, EL_CLAMP))
    dist = cam['distance']
    tgt = cam['target']
    eye = tgt + np.array([
        -dist * math.sin(az) * math.cos(el),
        -dist * math.sin(el),
        -dist * math.cos(az) * math.cos(el),
    ])
    fwd = tgt - eye
    fwd /= np.linalg.norm(fwd)
    world_up = np.array([0.0, 1.0, 0.0])
    right = np.cross(world_up, fwd)
    if np.linalg.norm(right) < 0.000001:
        right = np.cross(np.array([0.0, 0.0, 1.0]), fwd)
    right /= np.linalg.norm(right)
    up = np.cross(fwd, right)
    return right, up

def pan(win, dx: int, dy: int) -> None:
    right, up = _cam_basis(win._cam)
    pan_dist = PAN_SPEED * win._cam['distance']
    win._cam['target'] -= (right * dx + up * dy) * pan_dist
    win._update_cam()

def zoom(win, steps: float) -> None:
    factor = max(0.0, 1.0 - ZOOM_SPEED * steps)
    win._cam['distance'] = max(0.01, win._cam['distance'] * factor)
    win._update_cam()
    logger.debug('Dolly distance=%.3f', win._cam['distance'])

def zoom_fov(win, steps: float) -> None:
    factor = max(0.001, 1.0 + ZOOM_SPEED * steps)
    cur = float(win._cam.get('fx_scale', 1.0))
    win._cam['fx_scale'] = max(0.05, min(50.0, cur * factor))
    win._update_cam()
    logger.debug('Zoom fx_scale=%.3f', win._cam['fx_scale'])
