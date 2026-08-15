import json
import logging
from pathlib import Path
from process.common.floatfmt import dumps_fixed

logger = logging.getLogger(__name__)

def save_object_attrs(controller) -> None:
    path = getattr(controller, 'attrs_path', None)
    if path is None:
        return
    ids = controller.hidden | controller.locked
    data = {
        iid: {
            'hidden': iid in controller.hidden,
            'locked': controller.is_locked(iid),
        }
        for iid in ids
    }
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(dumps_fixed(data, indent=2), encoding='utf-8')
    except OSError as e:
        logger.warning('Object attrs save failed: %s', e)

def load_object_attrs(controller) -> dict:
    path = getattr(controller, 'attrs_path', None)
    if path is None or not Path(path).is_file():
        return {}
    try:
        data = json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as e:
        logger.warning('Object attrs load failed: %s', e)
        return {}
    logger.info('Object attrs loaded: %s', Path(path).name)
    return data
