from process.common.help import register_help_section
from process.component.region_volume import (
    RegionVolumeBoxController, attach_box_plugin,
    bind_key, box_help_entries,
)
from plugins.noise.attributes import register_attributes
from plugins.noise.curve_persist import dump_curves, load_curves
from plugins.noise.keys import (
    handle_cycle_noise_type, handle_threshold_down, handle_threshold_up,
    handle_toggle_noise,
)
from plugins.noise.settings import (
    NOISE_KEY_CYCLE_TYPE, NOISE_KEY_THRESHOLD_DOWN,
    NOISE_KEY_THRESHOLD_UP, NOISE_KEY_TRIGGER,
    DEFAULT_NOISE_REGION_SOFTNESS, STARTUP_NOISE_REGION_CENTER,
    STARTUP_NOISE_REGION_SIZE, STARTUP_VISIBILITY, VOLUME_SHAPE,
)
from plugins.noise.system import NoiseSystem

class NoisePlugin(RegionVolumeBoxController):

    overlay_label = 'NOISE'
    effect_key = NOISE_KEY_TRIGGER
    volume_shape = VOLUME_SHAPE
    startup_center = STARTUP_NOISE_REGION_CENTER
    startup_size = STARTUP_NOISE_REGION_SIZE
    startup_softness = DEFAULT_NOISE_REGION_SOFTNESS
    startup_visible = STARTUP_VISIBILITY
    system_class = NoiseSystem

    @property
    def reveal_scalars(self) -> dict:
        return {'threshold': self.system.threshold}

    def on_scalar_update(self, name: str, value: float) -> None:
        if name == 'threshold':
            self.system.threshold = float(value)

    def keyframe_scalars(self) -> dict:
        return {'threshold': self.system.threshold}

    def keyframe_extra(self) -> dict:
        return {
            'noise_type': self.system.noise_type,
            'curves': dump_curves(self.system),
        }

    def apply_keyframe_extra(self, extra: dict) -> None:
        noise_type = extra.get('noise_type')
        if noise_type:
            self.system.noise_type = noise_type
        load_curves(self.system, extra.get('curves', {}))

    def curve_state(self) -> dict:
        return dump_curves(self.system)

    def apply_curve_state(self, state: dict) -> None:
        load_curves(self.system, state)

    def attach(self, window) -> None:
        attach_box_plugin(
            window, self,
            channel='_noise_plugin',
            shape=VOLUME_SHAPE,
            register_attributes=register_attributes,
            log_name='Noise',
        )

    def _register_keys(self, window) -> None:
        bind_key(
            window, self, NOISE_KEY_TRIGGER, handle_toggle_noise,
            allow_when_hidden=True,
        )
        bind_key(
            window, self, NOISE_KEY_CYCLE_TYPE,
            handle_cycle_noise_type, allow_when_hidden=True,
        )
        bind_key(
            window, self, NOISE_KEY_THRESHOLD_UP,
            handle_threshold_up, allow_when_hidden=True,
        )
        bind_key(
            window, self, NOISE_KEY_THRESHOLD_DOWN,
            handle_threshold_down, allow_when_hidden=True,
        )
        repeatable = getattr(window, '_repeatable_keys', None)
        if repeatable is not None:
            repeatable.add(NOISE_KEY_THRESHOLD_UP)
            repeatable.add(NOISE_KEY_THRESHOLD_DOWN)

    def _register_help(self, window) -> None:
        register_help_section(window, 'NOISE', [
            (NOISE_KEY_TRIGGER, 'Toggle noise on/off'),
            (NOISE_KEY_CYCLE_TYPE, 'Cycle noise type'),
            (NOISE_KEY_THRESHOLD_UP, 'Noise threshold up'),
            (NOISE_KEY_THRESHOLD_DOWN, 'Noise threshold down'),
        ] + box_help_entries())

    def _process_frame(self, splat: dict) -> dict:
        return self.system.step(splat)
