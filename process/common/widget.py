def request_repaint(win) -> None:
    if hasattr(win, '_render_current'):
        win._render_current()

def set_message_overlay(win, text: str) -> None:
    if not hasattr(win, '_message_overlay'):
        return
    win._message_overlay = text
    timer = getattr(win, '_message_overlay_timer', None)
    if timer is not None:
        timer.start()
    widget = getattr(win, '_widget', None)
    if widget is not None:
        widget.set_message_overlay(text)
        widget.update()
