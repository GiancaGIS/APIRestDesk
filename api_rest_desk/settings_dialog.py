from __future__ import annotations

from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QVBoxLayout,
)

from api_rest_desk.i18n import SUPPORTED_LANGUAGES, Translator
from api_rest_desk.settings import load_settings, save_settings
from api_rest_desk.theme import apply_theme


class SettingsDialog(QDialog):
    def __init__(self, translator: Translator, parent=None) -> None:
        super().__init__(parent)
        self.translator = translator
        self.t = translator.t
        self.settings = load_settings()
        self.setWindowTitle(self.t("settings"))
        self.resize(360, 180)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        layout.addLayout(form)

        self.language_combo = QComboBox()
        for code, label in SUPPORTED_LANGUAGES.items():
            self.language_combo.addItem(label, code)
        self.language_combo.setCurrentIndex(
            max(0, self.language_combo.findData(self.settings.get("language", translator.language)))
        )

        self.theme_combo = QComboBox()
        self.theme_combo.addItem(self.t("light"), "light")
        self.theme_combo.addItem(self.t("dark"), "dark")
        self.theme_combo.setCurrentIndex(max(0, self.theme_combo.findData(self.settings.get("theme", "light"))))

        form.addRow(self.t("language_menu"), self.language_combo)
        form.addRow(self.t("theme"), self.theme_combo)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

        apply_theme(self)

    def selected_settings(self) -> dict:
        settings = dict(self.settings)
        settings["language"] = self.language_combo.currentData()
        settings["theme"] = self.theme_combo.currentData()
        return settings

    def accept(self) -> None:
        save_settings(self.selected_settings())
        super().accept()
