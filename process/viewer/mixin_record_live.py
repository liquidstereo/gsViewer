import concurrent.futures
import logging

from configs.settings import OUTPUT_DIR
from process.record import create_recorder, qimage_to_rgb_bytes
from process.record.settings import DEFAULT_SAVE_FPS
from process.save import unique_path
from process.capture import grab_frame_for_save
from process.widget.text_case import keep_case

logger = logging.getLogger(__name__)

class RecordLiveMixin:

    def _toggle_live_recording(self) -> None:
        if self._live_recording:
            self._stop_live_recording()
            return
        self._start_live_recording()

    def _start_live_recording(self) -> None:

        if self._save_dir is not None:
            logger.warning('Live recording ignored: batch save in progress')
            self._flash_message('RECORDING UNAVAILABLE DURING SAVE')
            return
        base_dir = self._live_dir or OUTPUT_DIR
        base_stem = self._live_stem or self._save_stem
        out_path = unique_path(base_dir / f'liveRec_{base_stem}.mp4')
        out_path.parent.mkdir(parents=True, exist_ok=True)
        recorder = create_recorder(
            out_path.parent, out_path.stem, 'mp4', self._w, self._h,
            fps=DEFAULT_SAVE_FPS,
        )
        if recorder is None:
            logger.error('Live recording start failed: recorder unavailable')
            self._flash_message('RECORDING START FAILED')
            return
        self._live_recorder = recorder
        self._live_out_file = out_path
        self._live_executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=1
        )
        self._live_recording = True

        self._live_audio_positions = []
        self._live_cur_audio_pos = None
        self._install_live_audio_taps()

        self._live_last_tick = self._anim_tick

        self._live_frames_out = 0
        self._submit_live_frame()

        logger.info(
            'Live recording started: %s', out_path,
            extra={'overlay': False},
        )

        self._widget._live_rec_on = True
        self._live_blink.start(True)
        self._flash_message('LIVE RECORDING STARTED...')

    def _install_live_audio_taps(self) -> None:

        self._live_sync_orig = self._playback_frame_sync
        self._live_plist_orig = self._playlist_frame_sync
        if self._live_sync_orig is not None:
            self._playback_frame_sync = self._make_audio_tap(
                self._live_sync_orig)
        if self._live_plist_orig is not None:
            self._playlist_frame_sync = self._make_audio_tap(
                self._live_plist_orig)

    def _live_audio_pos(self, back: int = 0):

        src = self._live_audio_pos_source
        if src is not None:
            pos = src(back)
            if pos is not None:
                return pos
        return self._live_cur_audio_pos

    def _make_audio_tap(self, orig):

        def tap(iid, local, count):
            self._live_cur_audio_pos = (iid, local, count)
            return orig(iid, local, count)
        return tap

    def _remove_live_audio_taps(self) -> None:

        if self._live_sync_orig is not None:
            self._playback_frame_sync = self._live_sync_orig
        if self._live_plist_orig is not None:
            self._playlist_frame_sync = self._live_plist_orig
        self._live_sync_orig = None
        self._live_plist_orig = None

    def _on_live_blink_change(self, on: bool) -> None:

        self._widget._live_rec_dot = on
        self._widget.update()

    def _capture_live_frame(self) -> None:

        if self._live_recorder is None or self._buffering:
            return
        steps = self._anim_tick - self._live_last_tick
        if steps <= 0:
            return
        self._live_last_tick = self._anim_tick
        self._submit_live_frame(repeat=steps)

    def _submit_live_frame(self, repeat: int = 1) -> None:

        arr = self._widget._image_arr
        if arr is None:
            return
        w = self._widget

        img = grab_frame_for_save(self, arr)
        data = qimage_to_rgb_bytes(img)
        ex = self._live_executor
        rec = self._live_recorder
        if ex is None or rec is None:
            return

        for back in range(max(1, repeat) - 1, -1, -1):
            ex.submit(rec.write, data)
            self._live_audio_positions.append(self._live_audio_pos(back))

        self._live_frames_out += max(1, repeat)
        w._live_rec_seconds = (
            self._live_frames_out / float(DEFAULT_SAVE_FPS))

    def _stop_live_recording(self, announce: bool = True) -> None:
        if not self._live_recording:
            return
        self._live_recording = False

        self._remove_live_audio_taps()

        self._live_blink.stop(False)
        self._widget._live_rec_on = False
        self._widget._live_rec_seconds = None
        ex = self._live_executor
        rec = self._live_recorder
        out = self._live_out_file
        self._live_executor = None
        self._live_recorder = None
        self._live_out_file = None

        if ex is not None:
            try:
                ex.shutdown(wait=True)
            except Exception:
                logger.exception('Live recording executor flush error')
        frames = 0
        if rec is not None:
            rec.close()
            frames = rec.frames
        self._live_saved_file = out
        self._live_saved_count = frames
        logger.info(
            'Live recording stopped: %s (%d frames)', out, frames,
            extra={'overlay': False},
        )
        self._mux_live_audio(out, frames)
        if out is not None and announce:

            self._flash_message('RECORDING SAVED: ' + keep_case(f'./{out}'))

    def _mux_live_audio(self, out, frames: int) -> None:

        provider = getattr(self, '_live_audio_segments', None)
        positions = self._live_audio_positions
        self._live_audio_positions = []
        if out is None or frames <= 0 or provider is None or not positions:
            return
        try:
            segments = provider(positions)
        except Exception:
            logger.exception('Live audio segment provider error')
            return
        if not segments:
            return
        from process.record.mux import mux_audio
        mux_audio(out, segments)

    def _live_exit_note(self) -> str | None:

        if self._live_saved_file is None or self._live_saved_count <= 0:
            return None
        word = 'frame' if self._live_saved_count == 1 else 'frames'
        return (
            f'Frame Export Complete. '
            f'({self._live_saved_count} {word} to ./{self._live_saved_file})'
        )

    def _flash_message(self, text: str) -> None:

        self._widget._live_rec_message = text
        self._message_overlay = text
        self._message_overlay_timer.start()
        self._render_current()
