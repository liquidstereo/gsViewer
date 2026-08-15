from dataclasses import dataclass
from typing import Callable

KIND_FLOAT = 'float'
KIND_INT = 'int'
KIND_ENUM = 'enum'
KIND_BUTTON = 'button'
KIND_BOOL = 'bool'
KIND_CURVE = 'curve'
KIND_CUSTOM = 'custom'
KIND_LABEL = 'label'
KIND_METER = 'meter'

STANDARD_BUTTON_LABELS: tuple[str, ...] = (
    'Set Key', 'Del Key', 'Apply', 'Reset',
)
CONSOLE_BUTTON_LABEL: str = 'Script Console'

@dataclass
class AttrSpec:

    label: str
    kind: str
    get: Callable[[], object] | None = None
    set: Callable[[object], None] | None = None
    vmin: float = 0.0
    vmax: float = 1.0
    options: tuple[str, ...] = ()
    fmt: str = '{:.2f}'
    action: Callable[[], None] | None = None

    collapsed_default: bool = True

    on_commit: Callable[[], None] | None = None

    row_break: bool = False

    tooltip: str = ''

    default: object | None = None

    menu_provider: Callable[[], list] | None = None
    menu_toggle: Callable[[str], None] | None = None

    custom_paint: Callable[[object, object], None] | None = None
    custom_rows: int = 4

    def value_text(self) -> str:
        if (self.kind in (KIND_BUTTON, KIND_BOOL, KIND_CURVE)
                or self.get is None):
            return ''
        v = self.get()
        if self.kind == KIND_ENUM:
            return str(v)
        try:
            return self.fmt.format(v)
        except (ValueError, TypeError):
            return str(v)

    def norm(self) -> float:
        if self.kind == KIND_ENUM:
            return 0.0
        span = self.vmax - self.vmin
        if span <= 0.0:
            return 0.0
        return min(1.0, max(0.0, (float(self.get()) - self.vmin) / span))

    def set_from_norm(self, ratio: float) -> None:
        ratio = min(1.0, max(0.0, ratio))
        value = self.vmin + ratio * (self.vmax - self.vmin)
        if self.kind == KIND_INT:
            value = float(round(value))
        self.set(value)

@dataclass
class AttrSection:

    title: 'str | Callable[[], str]'
    provider: Callable[[], 'list[AttrSpec] | None']

    order: int = 0

    def title_text(self) -> str:
        t = self.title
        return t() if callable(t) else t

    def specs(self) -> list:
        items = self.provider()
        return list(items) if items else []

@dataclass
class AttrRow:

    spec: AttrSpec
    control_x: float
    control_y: float
    control_w: float
    control_h: float

    role: str = ''

    section: str = ''

    def hit(self, mx: float, my: float) -> bool:
        return (
            self.control_x <= mx <= self.control_x + self.control_w
            and self.control_y <= my <= self.control_y + self.control_h
        )
