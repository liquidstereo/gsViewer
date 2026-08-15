import logging
from pathlib import Path
from typing import Callable

from configs.settings import MUTE_ON_SAVE, PLAYBACK_FPS
from process.transform.attr_overlay import register_solo_flag
from process.widget.text_case import keep_case
from process.widget.overlays.audio_attribute_overlay import (
    init_audio_attribute_overlay_state, make_show_audio_provider,
    register_audio_attribute_overlay,
)
from process.component.audio.analyzer import AudioAnalyzer
from process.component.audio.channels import (
    init_channel_source, make_single_source,
)
from process.component.audio.display import display_label
from process.component.audio.live_segments import build_live_segments
from process.component.audio.attributes import (
    build_audio_specs, prepare_playback, toggle_active,
)
from process.component.audio.playback import AudioPlayback
from process.component.audio.save_segments import collect_save_segments
from process.component.audio.region import (
    register_audio_entries, register_region_entry,
)
from process.component.audio.status import register_audio_status
from process.component.audio.settings import (
    AUDIO_ACTIVATE_KEY, AUDIO_MUTE_DEFAULT, AUDIO_OVERLAY_ACTIVE_DEFAULT,
    AUDIO_SECTION_ORDER, AUDIO_SYNC_DEFAULT, DEFAULT_FFT_WIN, DEFAULT_HOP,
)

logger = logging.getLogger(__name__)

class AudioAnalyzerPlugin:

    def __init__(
        self, audio_path: str | list[str] | None = None,
        frame_range: str | None = None,
    ) -> None:

        if isinstance(audio_path, str):
            paths = [s.strip() for s in audio_path.split(',') if s.strip()]
        elif audio_path:
            paths = [str(p) for p in audio_path]
        else:
            paths = []
        self._audio_paths: list[str] = paths
        self._audio_path: str | None = paths[0] if paths else None

        self._frame_range: str | None = frame_range

        self._audio_map: dict = {}

        self._current_playback: AudioPlayback | None = None

    def attach(self, window) -> None:
        if getattr(window, '_audio_source', None) is not None:
            logger.info('Audio source already registered; skip')
            return

        input_ids = getattr(window, '_input_ids', None) or []
        if getattr(window, '_playback_mode', None) == 'loop' and\
                len(input_ids) > 1:
            logger.info(
                'AudioAnalyzerPlugin: multi-input loop is silent; skip audio')
            return
        if not self._audio_paths:
            logger.info('AudioAnalyzerPlugin attached (no audio source)')
            return

        scheduler = getattr(window, '_scheduler', None)
        chain_segs = getattr(window, '_chain_segments', None)
        if (scheduler is not None or chain_segs) and\
                len(self._audio_paths) > 1:
            self._attach_playlist(window)
        else:
            self._attach_single(window, self._audio_path)

    def _init_window_audio(self, window, analyzer, playback) -> None:

        window._audio_source = analyzer
        window._audio_selected = False
        register_solo_flag(window, '_audio_selected')
        window._audio_active = AUDIO_OVERLAY_ACTIVE_DEFAULT
        window._audio_sync = AUDIO_SYNC_DEFAULT
        window._audio_mute = AUDIO_MUTE_DEFAULT
        playback.muted = AUDIO_MUTE_DEFAULT

        window._attr_solo_key = AUDIO_ACTIVATE_KEY
        window._attr_solo_toggle = lambda: toggle_active(window)

        window._attr_solo_flag = '_audio_selected'

        init_audio_attribute_overlay_state(window)

    def _register_audio_section(
        self, window, title: str | Callable[[], str],
    ) -> None:

        solo, merged, meta = build_audio_specs(window)
        register_audio_attribute_overlay(
            window, title, solo, merged, meta, AUDIO_SECTION_ORDER)

    def _attach_single(self, window, path: str | None) -> None:

        source = init_channel_source(window, path, self._frame_range)
        if source is None and not (path and Path(path).is_file()):
            logger.info('AudioAnalyzerPlugin attached (no audio source)')
            return
        try:
            analyzer, playback = source or make_single_source(
                path, self._frame_range)
        except Exception as e:
            logger.error('Audio source init failed: %s', e)
            return
        self._init_window_audio(window, analyzer, playback)
        self._register_hooks(window, playback)
        self._register_ui(window, Path(path).name)
        logger.info(
            'Audio source registered (shared, %d bands)', analyzer.num_bands
        )

    def _attach_playlist(self, window) -> None:

        chain_segs = getattr(window, '_chain_segments', None)
        input_ids = (
            getattr(window, '_input_ids', None)
            or list(window._inputs.keys())
        )
        self._audio_map = {}
        for iid, path in zip(input_ids, self._audio_paths):
            if not (path and Path(path).is_file()):
                continue
            try:
                analyzer = AudioAnalyzer(
                    path, DEFAULT_FFT_WIN, DEFAULT_HOP,
                    frame_range=self._frame_range)
                playback = analyzer.make_playback()
            except Exception as e:
                logger.error('Audio init failed (%s): %s', iid, e)
                continue
            self._audio_map[iid] = (analyzer, playback, path)
        if not self._audio_map:
            logger.info('AudioAnalyzerPlugin attached (no valid audio)')
            return

        seg0 = chain_segs[0][0] if chain_segs else window._active_id
        iid0 = (
            seg0 if seg0 in self._audio_map
            else next(iter(self._audio_map))
        )
        analyzer0, playback0, _path0 = self._audio_map[iid0]
        self._init_window_audio(window, analyzer0, playback0)
        self._register_hooks(window, playback0)

        entries = [

            (i, '' + keep_case(Path(pp).name))
            for i, (_a, _pb, pp) in self._audio_map.items()
        ]
        register_audio_entries(window, entries)

        label_map = dict(entries)

        def _audio_title() -> str:
            active = (getattr(window, '_chain_active_iid', None)
                      or getattr(window, '_active_id', None))
            return display_label(
                window, label_map.get(active, entries[0][1]))

        self._register_audio_section(window, _audio_title)
        self._register_show_audio(window)
        window._playlist_switch_hook = (
            lambda iid: self._on_playlist_switch(window, iid))
        window._playlist_frame_sync = (
            lambda iid, local, count:
            self._sync_audio_frame(window, iid, local, count))
        logger.info(
            'Audio playlist registered (%d inputs)', len(self._audio_map)
        )

    def _sync_audio_frame(
        self, window, iid: str, local: int, count: int,
    ) -> None:

        entry = self._audio_map.get(iid)
        if entry is None:
            return
        playback = entry[1]
        if playback is not self._current_playback:
            return
        n = playback.num_samples
        if n <= 0 or count <= 0:
            return
        playback.cursor = int(local / count * n)

    def _on_playlist_switch(self, window, iid: str) -> None:

        entry = self._audio_map.get(iid)
        cur = self._current_playback
        if entry is None:
            if cur is not None:
                cur.stop()
            return
        analyzer, playback, _path = entry
        if cur is playback:
            return
        if cur is not None:
            cur.stop()
        playback.cursor = 0
        playback.paused = False
        playback.muted = getattr(window, '_audio_mute', False)
        self._current_playback = playback
        window._audio_source = analyzer
        window._audio_playback = playback
        if getattr(window, '_playing', False) and\
                getattr(window, '_audio_active', False):
            playback.try_play()

    def _stop_all(self) -> None:
        if self._audio_map:
            for _a, pb, _p in self._audio_map.values():
                pb.stop()
        elif self._current_playback is not None:
            self._current_playback.stop()

    def _register_ui(self, window, filename: str) -> None:

        label = keep_case(filename)
        register_region_entry(window, label)

        self._register_audio_section(
            window, lambda: display_label(window, label))
        self._register_show_audio(window)

    def _register_show_audio(self, window) -> None:

        providers = getattr(window, '_box_extra_spec_providers', None)
        if providers is None:
            providers = []
            window._box_extra_spec_providers = providers
        providers.append(make_show_audio_provider(window))

    def _pin_audio_frame(
        self, window, iid: str, local: int, count: int,
    ) -> None:

        pb = self._current_playback
        if pb is None:
            return
        if not getattr(window, '_audio_active', False):
            return
        if not getattr(window, '_audio_sync', False):
            return
        if not (pb.playing and not pb.paused):
            return
        n = pb.num_samples
        if n <= 0 or count <= 0:
            return
        pb.cursor = int(local / count * n)

    def _register_hooks(self, window, playback: AudioPlayback) -> None:

        self._current_playback = playback
        window._audio_playback = playback

        window._playback_frame_sync = (
            lambda iid, local, count:
            self._pin_audio_frame(window, iid, local, count))

        window._playback_seek_sync = (
            lambda: self._on_seek_pause(window))

        window._save_audio_segments = (
            lambda: self._collect_save_audio(window))

        window._live_audio_segments = (
            lambda positions:
            self._collect_live_audio(window, positions))
        if hasattr(window, '_playback_start_hooks'):
            window._playback_start_hooks.append(
                lambda: self._on_playback_start(
                    window, self._current_playback))
        if hasattr(window, '_shutdown_hooks'):
            window._shutdown_hooks.append(self._stop_all)
        if hasattr(window, '_pause_hooks'):
            window._pause_hooks.append(
                lambda paused: self._on_pause(
                    window, self._current_playback, paused))

        register_audio_status(window)

    def _collect_save_audio(self, window):

        return collect_save_segments(window, self._audio_map,
                                     self._audio_path)

    def _collect_live_audio(self, window, positions):

        return build_live_segments(
            positions, self._audio_map, self._audio_path, PLAYBACK_FPS)

    def _on_seek_pause(self, window) -> None:

        pb = self._current_playback
        if pb is None:
            return
        window._audio_active = False
        pb.pause()
        if window._playlist_frame_sync is not None:
            return
        n = pb.num_samples
        if n <= 0:
            return

        src = getattr(window, '_audio_timeline_source', None)
        pos = src() if src is not None else None
        if pos is not None:
            local, count = pos

            if count <= 0:
                return
            pb.cursor = int(local / count * n)
            return
        total = max(1, getattr(window, '_total_frames', 1))
        frame = window._idx % total
        pb.cursor = int(frame / total * n)

    def _on_playback_start(self, window, playback: AudioPlayback) -> None:

        window._audio_active = True

        if MUTE_ON_SAVE and getattr(window, '_save_dir', None) is not None:
            return
        if not playback.playing:
            prepare_playback(window, playback)
            playback.try_play()

    def _on_pause(
        self, window, playback: AudioPlayback, paused: bool,
    ) -> None:

        if paused:
            window._audio_active = False
            playback.pause()
            return
        window._audio_active = True
        prepare_playback(window, playback)
        if not playback.playing:
            playback.try_play()
        elif playback.paused:
            playback.resume()
