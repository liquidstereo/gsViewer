from PySide6.QtCore import QPoint
from PySide6.QtGui import QPolygon

def filled_arrowhead_poly(
    ox: int, oy: int, tx: int, ty: int,
    head_len: float, head_half: float,
) -> tuple[int, int, QPolygon]:
    dx = tx - ox
    dy = ty - oy
    seg_len = max(1.0, (dx * dx + dy * dy) ** 0.5)
    ux, uy = dx / seg_len, dy / seg_len
    bx = tx - ux * head_len
    by = ty - uy * head_len
    v1 = QPoint(int(bx - uy * head_half), int(by + ux * head_half))
    v2 = QPoint(int(bx + uy * head_half), int(by - ux * head_half))
    return int(bx), int(by), QPolygon([QPoint(int(tx), int(ty)), v1, v2])
