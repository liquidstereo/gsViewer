from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
)

def prompt_keyframe(
    parent,
    title: str,
    default_label: str,
    default_duration: int,
    first: bool,
    duration_min: int = 1,
    duration_max: int = 600_000,
) -> tuple[str, int, bool]:
    dlg = QDialog(parent)
    dlg.setWindowTitle(title)
    label_edit = QLineEdit(default_label)
    label_edit.selectAll()
    dur_spin = QSpinBox()
    dur_spin.setRange(int(duration_min), int(duration_max))
    dur_spin.setValue(int(default_duration))
    dur_spin.setSuffix(' ms')
    if first:
        dur_spin.setEnabled(False)
    form = QFormLayout()
    form.addRow('Label:', label_edit)
    form.addRow('Duration:', dur_spin)
    buttons = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Ok
        | QDialogButtonBox.StandardButton.Cancel
    )
    buttons.accepted.connect(dlg.accept)
    buttons.rejected.connect(dlg.reject)
    layout = QVBoxLayout(dlg)
    layout.addLayout(form)
    layout.addWidget(buttons)
    ok = dlg.exec() == QDialog.DialogCode.Accepted
    duration = 0 if first else int(dur_spin.value())
    return label_edit.text().strip(), duration, ok
