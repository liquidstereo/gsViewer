import logging

from configs.settings import PLAYBACK_FPS
from process.common.widget import request_repaint
from process.widget.overlays.attr_compose import (
    compose_specs, extra_specs, spec_when,
)
from process.widget.overlays.attr_spec import (
    AttrSpec, KIND_BOOL, KIND_CUSTOM, KIND_ENUM, KIND_METER,
)
from process.component.audio.channels import select_channel
from process.component.audio.overlay import make_equalizer_paint
from process.component.audio.settings import (
    ATTR_EXTRA_AUDIO, AUDIO_BAND_METER_VMAX, AUDIO_BAND_NUM,
    AUDIO_BAND_NUM_FMT, AUDIO_BAND_VALUE_FMT, AUDIO_OVERLAY_BOX_ROWS,
)

logger = logging.getLogger(__name__)

_TIP_ACTIVATE = 'Play audio only while enabled (default off).'
_TIP_MUTE = 'Keep running but output silence (visuals still update).'
_TIP_CHANNEL = ('Switch the shared audio source to another channel '
                '(multi-file directory input only).')

def _seek_to_frame(window, pb) -> None:

    if PLAYBACK_FPS <= 0 or pb.num_samples <= 0:
        return
    idx = int(getattr(window, '_idx', 0))
    pb.cursor = int(idx / PLAYBACK_FPS * pb.sample_rate) % pb.num_samples

def prepare_playback(window, pb) -> None:
    if getattr(window, '_audio_sync', False):
        _seek_to_frame(window, pb)
    pb.muted = bool(getattr(window, '_audio_mute', False))

def _audio_can_play(window) -> bool:

    return (getattr(window, '_playing', False)
            and not getattr(window, '_buffering', False))

def _ensure_playing(window, pb) -> None:

    prepare_playback(window, pb)
    if not pb.playing:
        pb.try_play()
    elif pb.paused:
        pb.resume()

def _set_active(window, value: bool) -> None:
    window._audio_active = bool(value)
    pb = getattr(window, '_audio_playback', None)
    if pb is not None:
        if value:
            if _audio_can_play(window):
                _ensure_playing(window, pb)
        else:
            pb.pause()
    request_repaint(window)

def toggle_active(window) -> None:
    value = not bool(getattr(window, '_audio_active', False))
    _set_active(window, value)

    logger.info('Audio active: %s', value)
    msg = 'AUDIO ON' if value else 'AUDIO OFF'
    if hasattr(window, '_message_overlay'):
        window._message_overlay = msg
        timer = getattr(window, '_message_overlay_timer', None)
        if timer is not None:
            timer.start()

def band_label(idx: int, names) -> str:
    name = names[idx] if idx < len(names) else f'Audio Band {idx}'
    if not AUDIO_BAND_NUM:
        return name
    return AUDIO_BAND_NUM_FMT.format(idx) + name

def _set_channel(window, value: str) -> None:
    select_channel(window, str(value))
    request_repaint(window)

def _set_mute(window, value: bool) -> None:
    window._audio_mute = bool(value)
    pb = getattr(window, '_audio_playback', None)
    if pb is not None:
        pb.muted = bool(value)
    request_repaint(window)

def build_audio_specs(window):
    paint = make_equalizer_paint(window)
    eq = AttrSpec('', KIND_CUSTOM, custom_paint=paint,
                  custom_rows=AUDIO_OVERLAY_BOX_ROWS)
    activate = AttrSpec(
        'Activate', KIND_BOOL,
        lambda: bool(getattr(window, '_audio_active', False)),
        lambda v: _set_active(window, v), tooltip=_TIP_ACTIVATE)
    mute = AttrSpec(
        'Mute', KIND_BOOL,
        lambda: bool(getattr(window, '_audio_mute', False)),
        lambda v: _set_mute(window, v), tooltip=_TIP_MUTE)

    def _channel_spec() -> list:

        channels = getattr(window, '_audio_channels', None)
        names = tuple(channels.names) if channels is not None else ()
        return spec_when(
            lambda: len(names) > 1,
            lambda: AttrSpec(
                'Select Channel', KIND_ENUM,
                lambda: channels.current,
                lambda v: _set_channel(window, v),
                options=names, tooltip=_TIP_CHANNEL))

    def _band_rows(src) -> list:
        names = getattr(src, 'band_names', [])
        return [AttrSpec(
                    band_label(i, names),
                    KIND_METER, (lambda i=i: src.magnitude(i)), None,
                    vmax=AUDIO_BAND_METER_VMAX, fmt=AUDIO_BAND_VALUE_FMT)
                for i in range(src.num_bands)]

    def _band_specs() -> list:

        src = getattr(window, '_audio_source', None)
        return spec_when(lambda: src is not None, lambda: _band_rows(src))

    def solo_specs() -> list:
        return compose_specs(
            activate, mute, _channel_spec(), eq, _band_specs(),
            extra_specs(window, ATTR_EXTRA_AUDIO))

    def _panel_specs() -> list:

        return compose_specs(
            _channel_spec(), eq, _band_specs(),
            extra_specs(window, ATTR_EXTRA_AUDIO))

    def merged_specs() -> list:
        return _panel_specs()

    def meta_specs() -> list:
        return _panel_specs()

    return solo_specs, merged_specs, meta_specs
