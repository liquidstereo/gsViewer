from process.component.region_volume.settings import (
    REGION_VOLUME_KEY_KEYFRAME_ADD, REGION_VOLUME_KEY_KEYFRAME_CLEAR,
    REGION_VOLUME_KEY_KEYFRAME_NEXT, REGION_VOLUME_KEY_KEYFRAME_PREV,
    REGION_VOLUME_KEY_CYCLE_SHAPE,
    REGION_VOLUME_KEY_KEYFRAME_REMOVE, REGION_VOLUME_KEY_LOCK,
    REGION_VOLUME_KEY_RESET,
    REGION_VOLUME_KEY_STRENGTH_DOWN, REGION_VOLUME_KEY_STRENGTH_UP,
    REGION_VOLUME_KEY_TOOL_ROTATE, REGION_VOLUME_KEY_TOOL_SCALE,
    REGION_VOLUME_KEY_TOOL_TRANSLATE, REGION_VOLUME_KEY_VISIBLE,
)

def box_help_entries(with_strength: bool = False) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    if with_strength:
        entries.append(
            (REGION_VOLUME_KEY_STRENGTH_UP, 'Strength scale up'))
        entries.append(
            (REGION_VOLUME_KEY_STRENGTH_DOWN, 'Strength scale down'))
    entries.extend([
        (REGION_VOLUME_KEY_VISIBLE,        'Region visible toggle'),
        (REGION_VOLUME_KEY_LOCK,           'Lock region transform'),
        ('Shift+1~9',                      'Select box N (multi)'),
        (REGION_VOLUME_KEY_TOOL_TRANSLATE, 'Translate tool'),
        (REGION_VOLUME_KEY_TOOL_ROTATE,    'Rotate tool'),
        (REGION_VOLUME_KEY_TOOL_SCALE,     'Scale tool'),
        (REGION_VOLUME_KEY_CYCLE_SHAPE,    'Cycle region shape'),
        (REGION_VOLUME_KEY_RESET,          'Reset region'),
        (REGION_VOLUME_KEY_KEYFRAME_ADD,
         'Add Region Volume keyframe'),
        (REGION_VOLUME_KEY_KEYFRAME_REMOVE,
         'Remove last Region Volume keyframe'),
        (REGION_VOLUME_KEY_KEYFRAME_CLEAR,
         'Clear all Region Volume keyframes'),
        (REGION_VOLUME_KEY_KEYFRAME_PREV,
         'Prev Region Volume keyframe'),
        (REGION_VOLUME_KEY_KEYFRAME_NEXT,
         'Next Region Volume keyframe'),
    ])
    return entries
