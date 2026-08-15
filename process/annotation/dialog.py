from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
)

from configs.settings_annot import (
    ANNOT_ANIM_DURATION_MAX,
    ANNOT_ANIM_DURATION_MIN,
)

def prompt_camera_keyframe(
    parent, default_label: str, default_duration: int, first: bool,
) -> tuple[str, int, bool]:
    dlg = QDialog(parent)
    dlg.setWindowTitle('Add Camera Keyframe')
    label_edit = QLineEdit(default_label)
    label_edit.selectAll()
    dur_spin = QSpinBox()
    dur_spin.setRange(ANNOT_ANIM_DURATION_MIN, ANNOT_ANIM_DURATION_MAX)
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
