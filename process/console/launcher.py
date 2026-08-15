import json
import logging
import re
from pathlib import Path

from PySide6.QtCore import QTimer

from process.common.widget import request_repaint
from process.console.contributors import (
    apply_contributor_sections, merge_contributor_snapshots)
from process.console.defaults import default_json_path, ensure_default_json
from process.console.editor import CodeEditorWindow
from process.console.guide import console_guide_text
from process.console.help import (
    current_plugin_readme, show_console_guide, show_plugin_readme)
from process.console.live_expr import apply_expr_constants, inject_expr_text
from process.console.parse import _retry_lenient
from process.console.persist import collect_constants, ensure_json_suffix
from process.console.reload import apply_source
from process.console.uservars import user_var_exprs
from process.common.floatfmt import dumps_fixed

logger = logging.getLogger(__name__)

def _collect_value_hints(window) -> dict:
    hints: dict = {}
    for c in getattr(window, '_console_contributors', None) or []:
        getter = getattr(c, 'value_hints', None)
        if callable(getter):
            h = getter()
            if isinstance(h, dict):
                hints.update(h)
    return hints

def _annotate_body(body: str, hints: dict) -> str:
    if not hints:
        return body
    out = []
    for ln in body.splitlines():
        m = re.match(r'^\s*"([^"]+)"\s*:', ln)
        if m and m.group(1) in hints and '//' not in ln:
            out.append(f'{ln}  // {hints[m.group(1)]}')
        else:
            out.append(ln)
    return '\n'.join(out)

def _console_title_name(plugin) -> str:

    getter = getattr(plugin, 'console_title', None)
    if callable(getter):
        name = getter()
        if isinstance(name, str) and name.strip():
            return name.strip()
    label = getattr(plugin, 'overlay_label', None)
    if isinstance(label, str) and label.strip():
        return label.strip().title()
    return _plugin_dir_name(plugin) or 'Plugin'

def _plugin_dir_name(plugin) -> str:

    getp = getattr(plugin, 'settings_module_path', None)
    path = getp() if callable(getp) else None
    if not path:
        return ''
    return Path(path).parent.name.replace('_', ' ').title()

def open_script_console(window, plugin) -> None:
    path = plugin.settings_module_path()
    if path is None or not Path(path).is_file():
        logger.warning('Script Console: settings path missing: %s', path)
        return
    existing = getattr(window, '_script_console', None)
    if existing is not None:
        existing.close()

    source = _live_source(window, plugin, path)
    target = str(default_json_path(path)) if source is not None else path

    display = _console_title_name(plugin)
    readme = current_plugin_readme(path)
    help_entries = [
        (f'How to Use {display}',
         (lambda: show_console_guide(
             window, console_guide_text(window, display), display))),
    ]
    if readme is not None:

        about = readme[0].replace('_', ' ').title()
        help_entries.append(
            ('About',
             (lambda n=about, p=readme[1]:
              show_plugin_readme(window, n, p))))
    editor = CodeEditorWindow(
        target, parent=window, initial_source=source,
        help_entries=help_entries, title_name=display)
    editor.source_changed.connect(
        lambda p, src: _apply(window, plugin, p, src))
    editor.save_as_requested.connect(
        lambda p: _save_as(window, plugin, p))
    editor.load_override_requested.connect(
        lambda p: _load_override(window, plugin, p))

    editor.reset_default_requested.connect(
        lambda p: _default_action(
            window, plugin, 'reset_to_plugin_default', refresh=True))
    editor.reset_user_default_requested.connect(
        lambda p: _default_action(
            window, plugin, 'reset_to_user_default', refresh=True))
    editor.set_user_default_requested.connect(
        lambda p: _default_action(
            window, plugin, 'set_as_user_default', refresh=False))
    editor.promote_user_default_requested.connect(
        lambda p: _default_action(
            window, plugin, 'promote_user_default', refresh=True))

    _center_on(editor, window)
    editor.show()
    _center_on(editor, window)
    QTimer.singleShot(0, lambda: _center_on(editor, window))
    editor.raise_()
    editor.activateWindow()
    window._script_console = editor
    logger.info('Script Console opened: %s', Path(path).name)

def _live_source(window, plugin, path: str) -> str | None:
    sync = getattr(plugin, 'sync_module_from_state', None)
    if not callable(sync):
        return None
    ensure = getattr(plugin, 'ensure_default_json', None)
    if callable(ensure):
        ensure()
    else:
        ensure_default_json(path)
    module = sync()
    if module is None:
        return None
    data: dict = {}
    merge_contributor_snapshots(window, data, skip_plugin=plugin)
    constants = collect_constants(module)
    augment = getattr(plugin, 'augment_console_constants', None)
    if callable(augment):
        augment(constants)
    inject_expr_text(window, path, constants)

    user_vars = user_var_exprs(window)
    if user_vars:
        merged = dict(user_vars)
        merged.update(constants)
        constants = merged
    data['constants'] = constants
    body = dumps_fixed(data, indent=2, ensure_ascii=False)

    hints = _collect_value_hints(window)
    plugin_hints = getattr(plugin, 'value_hints', None)
    if callable(plugin_hints):
        h = plugin_hints()
        if isinstance(h, dict):
            hints.update(h)
    return _annotate_body(body, hints)

def _center_on(editor, window) -> None:
    if window is None:
        return
    center = window.frameGeometry().center()
    frame = editor.frameGeometry()
    frame.moveCenter(center)
    editor.move(frame.topLeft())

def _is_default_json(path: str, settings_path: str) -> bool:
    return (Path(path).resolve()
            == default_json_path(settings_path).resolve())

def _parse_console_json(source: str) -> dict | None:
    cleaned = _strip_comments(source)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        data = _retry_lenient(cleaned)
        if data is None:
            return None
    return data if isinstance(data, dict) else None

def _strip_comments(source: str) -> str:
    return '\n'.join(
        _strip_inline_comment(ln) for ln in source.splitlines())

def _strip_inline_comment(line: str) -> str:

    in_str = False
    esc = False
    for i, ch in enumerate(line):
        if in_str:
            if esc:
                esc = False
            elif ch == '\\':
                esc = True
            elif ch == '"':
                in_str = False
        elif ch == '"':
            in_str = True
        elif ch == '/' and i + 1 < len(line) and line[i + 1] == '/':
            return line[:i].rstrip()
    return line

def _apply(window, plugin, path: str, source: str) -> None:
    settings_path = plugin.settings_module_path()
    if settings_path is None:
        return
    is_json = _is_default_json(path, settings_path)
    contributed = False
    if is_json:
        data = _parse_console_json(source)
        if data is None:
            return
        contributed = apply_contributor_sections(
            window, data, skip_plugin=plugin)
        raw = data.get('constants', data)

        applier = getattr(plugin, 'console_apply_constants', None)
        if callable(applier):
            module = applier(settings_path, raw)
        else:
            module = apply_expr_constants(window, plugin, settings_path, raw)
    else:
        module = apply_source(path, source)
    if module is None and not contributed:
        return
    reload_target = is_json or (
        Path(path).resolve() == Path(settings_path).resolve())
    if reload_target and module is not None:
        hook = getattr(plugin, 'on_settings_reload', None)
        if callable(hook):
            hook(module)
    request_repaint(window)

def _save_as(window, plugin, path: str) -> None:
    export = getattr(plugin, 'export_override', None)
    if callable(export):
        export(ensure_json_suffix(path))

def _default_action(
    window, plugin, hook_name: str, refresh: bool,
) -> None:
    hook = getattr(plugin, hook_name, None)
    if not callable(hook):
        logger.info('Console default action skipped (no hook): %s',
                    hook_name)
        return
    logger.info('Console default action: %s', hook_name)
    hook()
    if refresh:
        _refresh_console(window, plugin)
        request_repaint(window)

def _load_override(window, plugin, path: str) -> None:
    load = getattr(plugin, 'load_override_from', None)
    if callable(load):
        load(path)
    _refresh_console(window, plugin)
    request_repaint(window)

def _refresh_console(window, plugin) -> None:
    editor = getattr(window, '_script_console', None)
    if editor is None:
        return
    path = plugin.settings_module_path()
    if path is None:
        return
    source = _live_source(window, plugin, str(path))
    if source is not None:
        editor.refresh_source(source)
