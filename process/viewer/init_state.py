import logging

from PySide6.QtCore import Qt, QPoint, QTimer

from configs.keybinding import SPLAT_SIZE_UP, SPLAT_SIZE_DOWN
from configs.settings_camera import TURNTABLE
from configs.settings_effects import (
    FOG_ENABLED, FOG_POINT_BG, SPLAT_SCALE_DEFAULT,
)
from configs.settings_overlay import (
    MESSAGE_OVERLAY_DURATION, STARTUP_COLORMAP, STARTUP_LOGS,
)
from configs.settings_window import (
    STARTUP_ANNOTATION, STARTUP_BBOX, STARTUP_GRID, DEPTH_OCCLUSION,
)
from process.annotation.animation import AnnotationAnimator
from process.annotation.model import Annotations
from process.common import json_root_path
from process.mode import RenderMode, startup_mode
from process.widget.text_case import keep_case

logger = logging.getLogger(__name__)

def init_hook_registry(window) -> None:

    window._frame_index_mappers = []

    window._seq_overlay_follow_mapper = True

    window._frame_warm_source = None

    window._playback_catchup = None

    window._audio_timeline_source = None

    window._audio_display_name = None

    window._audio_status_brief = False

    window._live_audio_pos_source = None

    window._camera_frame_driver = None

    window._timeline_seek = None
    window._extra_handlers = {}
    window._extra_release_handlers = {}

    window._repeatable_keys = {SPLAT_SIZE_UP, SPLAT_SIZE_DOWN}
    window._shutdown_hooks = []
    window._pause_hooks = []

    window._prestart_hooks = []

    window._delete_providers = []

    window._playback_start_hooks = []

    window._playback_clock_frame = None

    window._playlist_switch_hook = None

    window._playlist_frame_sync = None

    window._playback_frame_sync = None

    window._playback_seek_sync = None

    window._save_audio_segments = None

    window._preview_hooks = []

    window._overlay_visibility_hooks = []

    window._mouse_handlers = []

    window._attr_sections = []

    window._region_entry_sources = []

    window._attr_solo_flags = []

def init_display_state(window, turntable: bool) -> None:
    window._cam_dirty = False
    window._render_mode: RenderMode = startup_mode()
    window._scale_mult = SPLAT_SCALE_DEFAULT
    window._show_bbox = STARTUP_BBOX
    window._show_grid = STARTUP_GRID
    window._show_colormap = STARTUP_COLORMAP
    window._depth_occlusion = DEPTH_OCCLUSION
    window._show_logs = STARTUP_LOGS
    window._last_log_snapshot: list[str] = []

    window._last_alert_seq = 0
    window._fog_enabled = FOG_ENABLED
    window._fog_point_bg = FOG_POINT_BG
    window._turntable = turntable or TURNTABLE

def init_annotation_state(window) -> None:
    window._annot: Annotations = Annotations()
    window._annot_file = json_root_path(window._json_key, 'camera.json')
    loaded = window._annot.load(window._annot_file)
    window._annot_loaded_from_file = loaded and window._annot.count() > 0
    if window._annot_loaded_from_file:
        logger.warning(
            'Existing annotation file loaded: %s (%d items)',
            keep_case(window._annot_file.name), window._annot.count(),
        )
    window._show_annot = STARTUP_ANNOTATION
    window._show_object_kf = STARTUP_ANNOTATION
    window._show_global_kf = STARTUP_ANNOTATION
    window._annot_cursor = -1
    window._annot_animator = AnnotationAnimator(window)
    window._message_overlay = ''

    window._hover_overlay = ''
    window._message_overlay_timer = QTimer(window)
    window._message_overlay_timer.setSingleShot(True)
    window._message_overlay_timer.setInterval(
        int(MESSAGE_OVERLAY_DURATION * 1000))
    window._message_overlay_timer.timeout.connect(
        window._clear_message_overlay
    )
    if window._annot_loaded_from_file:
        n = window._annot.count()
        window._message_overlay = (
            f'Annotation: {keep_case(window._annot_file.name)}'
            f'  ({n} items)'
        )
        window._message_overlay_timer.start()

def init_help_state(window) -> None:
    window._show_help = False

    window._help_page = 0
    window._show_plugin_help = False

    window._plugin_help_sections: list[tuple[str, list]] = []

    window._plugin_help_page = 0
    window._drag_pos: QPoint | None = None
    window._drag_btn: Qt.MouseButton | None = None

    window._exit_msg_fn = None
    window._exit_text: str | None = None

    window._programmatic_exit = False
