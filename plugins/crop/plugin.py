from process.common.help import register_help_section
from process.component.region_volume import (
    RegionVolumeBoxController, attach_box_plugin,
    bind_key, box_help_entries,
)
from plugins.crop.attributes import register_attributes
from plugins.crop.keys import handle_toggle_crop, handle_toggle_invert
from plugins.crop.settings import (
    CROP_KEY_INVERT, CROP_KEY_TRIGGER,
    DEFAULT_CROP_REGION_SOFTNESS, STARTUP_CROP_REGION_CENTER,
    STARTUP_CROP_REGION_SIZE, STARTUP_VISIBILITY, VOLUME_SHAPE,
)
from plugins.crop.system import CropSystem

class CropPlugin(RegionVolumeBoxController):

    overlay_label = 'CROP'
    effect_key = CROP_KEY_TRIGGER
    volume_shape = VOLUME_SHAPE
    startup_center = STARTUP_CROP_REGION_CENTER
    startup_size = STARTUP_CROP_REGION_SIZE
    startup_softness = DEFAULT_CROP_REGION_SOFTNESS
    startup_visible = STARTUP_VISIBILITY
    system_class = CropSystem

    def attach(self, window) -> None:
        attach_box_plugin(
            window, self,
            channel='_crop_plugin',
            shape=VOLUME_SHAPE,
            register_attributes=register_attributes,
            log_name='Crop',
        )

    def _register_keys(self, window) -> None:
        bind_key(window, self, CROP_KEY_TRIGGER, handle_toggle_crop,
                 allow_when_hidden=True)
        bind_key(window, self, CROP_KEY_INVERT, handle_toggle_invert,
                 allow_when_hidden=True)

    def _register_help(self, window) -> None:
        register_help_section(window, 'CROP', [
            (CROP_KEY_TRIGGER, 'Toggle crop (show region only)'),
            (CROP_KEY_INVERT, 'Invert (keep inside / outside)'),
        ] + box_help_entries())

    def _process_frame(self, splat: dict) -> dict:
        return self.system.step(splat)
