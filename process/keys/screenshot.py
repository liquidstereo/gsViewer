import logging
from datetime import datetime

from configs.settings import SCREENSHOT_DIR

logger = logging.getLogger(__name__)

def handle_screenshot(win) -> None:
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime('%y%m%d_%H%M%S')
    stem = (
        win._files[win._local_idx].stem if win._files else 'frame'
    )
    out = SCREENSHOT_DIR / f'screenshot_{stem}_{ts}.png'
    pixmap = win._widget.grab()
    ok = pixmap.save(str(out), 'PNG')
    if ok:
        logger.info('Screenshot saved: %s', out)
    else:
        logger.error('Screenshot failed: %s', out)
    win._render_current()
