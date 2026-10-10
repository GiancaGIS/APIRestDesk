from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QWidget

from api_rest_desk.i18n import Translator
from api_rest_desk.settings import load_settings, update_setting


def environment_label(name: str, translator: Translator) -> str:
    if name in {"development", "test", "production"}:
        return translator.t(f"environment_{name}")
    return name


class EnvironmentSelector(QWidget):
    environment_changed = pyqtSignal(str)

    def __init__(self, translator: Translator, parent=None):
        super().__init__(parent)
        self.translator = translator
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.label = QLabel()
        self.combo = QComboBox()
        self.combo.setMinimumWidth(180)
        layout.addWidget(self.label)
        layout.addWidget(self.combo, 1)
        self.combo.currentIndexChanged.connect(self._changed)
        self.refresh()

    def refresh(self) -> None:
        settings = load_settings()
        self.label.setText(self.translator.t("active_environment"))
        self.combo.blockSignals(True)
        self.combo.clear()
        for name in settings["environments"]:
            self.combo.addItem(environment_label(name, self.translator), name)
        self.combo.setCurrentIndex(self.combo.findData(settings["active_environment"]))
        self.combo.blockSignals(False)

    def _changed(self) -> None:
        name = self.combo.currentData()
        if name is not None:
            update_setting("active_environment", name)
            self.environment_changed.emit(name)
