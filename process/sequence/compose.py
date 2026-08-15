import numpy as np
from PIL import Image

def compose_layer_inset(
    base_img: np.ndarray,
    overlay_img: np.ndarray,
    alpha: float,
    inset_w: int,
    margin: int = 0,
) -> np.ndarray:
    if alpha <= 0.0:
        return base_img

    oh, ow = overlay_img.shape[:2]
    inset_h = max(1, int(round(inset_w * oh / ow)))
    resized = np.array(
        Image.fromarray(overlay_img).resize(
            (inset_w, inset_h), Image.BILINEAR
        )
    )

    H, W = base_img.shape[:2]
    x = max(0, W - inset_w - margin)
    y = max(0, H - inset_h - margin)
    x2 = min(W, x + inset_w)
    y2 = min(H, y + inset_h)
    resized = resized[:y2 - y, :x2 - x]

    result = base_img.copy()
    roi = result[y:y2, x:x2].astype(np.float32)
    if resized.ndim == 3 and resized.shape[2] == 4:
        ov_alpha = resized[:, :, 3:4].astype(np.float32) / 255.0
        overlay_rgb = resized[:, :, :3].astype(np.float32)
        combined = ov_alpha * alpha
    else:
        overlay_rgb = resized[:, :, :3].astype(np.float32)
        combined = alpha
    blended = roi * (1.0 - combined) + overlay_rgb * combined
    result[y:y2, x:x2] = blended.clip(0, 255).astype(np.uint8)
    return result
