from typing import Iterable

def register_help_section(
    window,
    title: str,
    entries: Iterable[tuple[str, str]],
) -> None:
    if not hasattr(window, '_plugin_help_sections'):
        return
    window._plugin_help_sections.append((title, list(entries)))
