import logging

from configs.settings_annot import (
    ANNOT_ANIM_DURATION, ANNOT_ANIM_DURATION_MAX, ANNOT_ANIM_DURATION_MIN,
)
from configs.settings_attr import ATTR_BUTTONS_ORDER
from configs.settings_overlay import ATTR_PANEL_KEYFRAME_DURATION
from process.widget.overlays import AttrSection, AttrSpec, KIND_INT

logger = logging.getLogger(__name__)

def register_annotation_attr_section(window) -> None:
    sections = getattr(window, '_attr_sections', None)
    if sections is None:
        return

    def _set_duration(value: float) -> None:
        window._annot_animator.set_duration_ms(value)
        for listener in getattr(window, '_duration_listeners', []):
            listener(value)

    def _duration_spec() -> AttrSpec:
        animator = window._annot_animator
        return AttrSpec(
            label='Duration(ms)', kind=KIND_INT,
            get=lambda: animator.duration_ms,
            set=_set_duration,
            vmin=ANNOT_ANIM_DURATION_MIN, vmax=ANNOT_ANIM_DURATION_MAX,
            fmt='{:.0f}', default=ANNOT_ANIM_DURATION,
            tooltip='Duration of annotation-based keyframe movement in milliseconds.',
        )

    def _provider():
        specs = [_duration_spec()] if ATTR_PANEL_KEYFRAME_DURATION else []
        for provider in getattr(window, '_attr_keyframe_buttons', []):
            specs.extend(provider() or [])
        return specs

    def _title() -> str:
        return ('Annotation-based keyframe'
                if ATTR_PANEL_KEYFRAME_DURATION else '')

    sections.append(
        AttrSection(_title, _provider, order=ATTR_BUTTONS_ORDER))
    logger.debug('Annotation attr section registered')
