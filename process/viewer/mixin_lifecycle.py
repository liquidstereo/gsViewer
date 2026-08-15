import gc
import logging
import time

import torch
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QApplication, QMessageBox

from configs.colorize import Msg
from configs.settings import WINDOW_TITLE
from configs.settings_window import CLOSE_DIALOG
from process.handle import (
    kill_child_workers, start_shutdown_blink, stop_shutdown_blink,
)
from process.perf.collector import fps_report, perf_report
from process.viewer.exit import force_exit
from process.viewer.utils import log_resources

logger = logging.getLogger(__name__)

class LifecycleMixin:

    def _run_shutdown_hooks(self) -> None:
        if not self._shutdown_hooks:
            return
        for hook in self._shutdown_hooks:
            try:
                hook()
            except Exception:
                logger.exception('Shutdown hook error')
        self._shutdown_hooks.clear()

    def closeEvent(self, event: QCloseEvent) -> None:

        if not self._programmatic_exit and not self._confirm_close():
            event.ignore()
            return
        t0 = time.perf_counter()

        self._run_shutdown_hooks()
        self._timer.stop()

        fps_report(self)
        perf_report(self)

        self.hide()
        QApplication.processEvents()

        blink_thread, blink_stop = start_shutdown_blink()

        if self._live_recording:
            self._stop_live_recording(announce=False)
        self._stop_sys_event.set()

        t = time.perf_counter()
        self._sys_thread.join(timeout=3.0)
        logger.info(
            'Shutdown [sys_thread join] %.3fsec',
            time.perf_counter() - t,
        )

        log_resources('Shutdown start')

        if self._recorder is not None:
            self._finalize_save_video_audio()

        if self._save_executor is not None:
            t = time.perf_counter()
            self._save_executor.shutdown(wait=True)
            logger.info(
                'Shutdown [save_executor flush] %.3fsec',
                time.perf_counter() - t,
            )

        t = time.perf_counter()
        for _entry in self._inputs.values():
            _entry['buf'].shutdown()
        logger.info(
            'Shutdown [buf.shutdown] %.3fsec',
            time.perf_counter() - t,
        )

        t = time.perf_counter()
        kill_child_workers()
        logger.info(
            'Shutdown [kill_workers] %.3fsec',
            time.perf_counter() - t,
        )

        t = time.perf_counter()
        torch.cuda.empty_cache()
        gc.collect()
        logger.info(
            'Shutdown [cuda+gc] %.3fsec',
            time.perf_counter() - t,
        )

        log_resources('Shutdown done ')
        logger.info(
            '%s closed: total %.3fsec',
            WINDOW_TITLE, time.perf_counter() - t0,
        )
        super().closeEvent(event)

        stop_shutdown_blink(blink_thread, blink_stop)

        msg_fn = self._exit_msg_fn or Msg.Result
        text = self._exit_text or (
            f'PLAYBACK FOR "{self._exit_input_label()}" FINISHED.'
        )
        force_exit(
            self._input_name,
            self._log_path,
            len(self._files),
            msg_fn=msg_fn,
            text=text,
            close_fn=None,
            extra_note=self._save_exit_note() or self._live_exit_note(),
        )

    def _confirm_close(self) -> bool:
        if not CLOSE_DIALOG:
            return True
        choice = QMessageBox.question(
            self, WINDOW_TITLE, 'Close the current window?',
            QMessageBox.StandardButton.Ok
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        return choice == QMessageBox.StandardButton.Ok

    def _exit_clean(self, msg_fn, text: str) -> None:

        self._programmatic_exit = True
        self._exit_msg_fn = msg_fn
        self._exit_text = text
        self._run_shutdown_hooks()
        self.close()

    def _ctrl_c_exit(self) -> None:
        self._exit_clean(
            Msg.Error,
            f'PLAYBACK FOR "{self._exit_input_label()}" INTERRUPTED.',
        )

    def _force_exit(self) -> None:
        self._exit_clean(
            Msg.Result,
            f'PLAYBACK FOR "{self._exit_input_label()}" FINISHED.',
        )

    def _ready_input_detail(self) -> str:

        input_name = self._input_name or 'primary'
        extra = len(self._inputs) - 1
        if extra > 0:
            return f'{input_name} +{extra} more'
        total_count = self._total_frames
        surfix = 'file' if total_count == 1 else 'files'
        return f'{input_name} . {total_count} {surfix}'

    def _exit_input_label(self) -> str:

        input_name = self._input_name or 'primary'
        extra = len(self._inputs) - 1
        if extra > 0:
            return f'{input_name} (+ {extra} more)'
        return input_name
