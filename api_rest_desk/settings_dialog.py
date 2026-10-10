from __future__ import annotations

from copy import deepcopy

from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from api_rest_desk.i18n import SUPPORTED_LANGUAGES, Translator
from api_rest_desk.environment_selector import environment_label
from api_rest_desk.settings import load_settings, save_settings
from api_rest_desk.theme import apply_theme
from api_rest_desk.widgets import KeyValueEditor


class SettingsDialog(QDialog):
    def __init__(self, translator: Translator, parent=None) -> None:
        super().__init__(parent)
        self.translator = translator
        self.t = translator.t
        self.settings = load_settings()
        self.setWindowTitle(self.t("settings"))
        self.resize(640, 500)
        self.environments = deepcopy(self.settings["environments"])
        self._edited_environment = self.settings["active_environment"]

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
        self.auto_updates_check = QCheckBox(self.t("auto_updates"))
        self.auto_updates_check.setChecked(self.settings.get("check_updates_automatically", True) is True)
        form.addRow(self.auto_updates_check)

        self.environment_title = QLabel(self.t("environment_variables"))
        self.environment_title.setObjectName("SectionTitle")
        layout.addWidget(self.environment_title)
        environment_row = QHBoxLayout()
        self.environment_combo = QComboBox()
        environment_row.addWidget(self.environment_combo, 1)
        self.add_environment_button = QPushButton(self.t("environment_add"))
        self.rename_environment_button = QPushButton(self.t("environment_rename"))
        self.delete_environment_button = QPushButton(self.t("environment_delete"))
        self.add_environment_button.clicked.connect(self._add_environment)
        self.rename_environment_button.clicked.connect(self._rename_environment)
        self.delete_environment_button.clicked.connect(self._delete_environment)
        for button in (self.add_environment_button, self.rename_environment_button, self.delete_environment_button):
            environment_row.addWidget(button)
        layout.addLayout(environment_row)
        self.environment_editor = KeyValueEditor(self.t("variable"), self.t("value"))
        self._refresh_environments()
        self.environment_combo.currentIndexChanged.connect(self._switch_environment)
        layout.addWidget(self.environment_editor, 1)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

        apply_theme(self)

    def _store_environment(self) -> None:
        self.environments[self._edited_environment] = self.environment_editor.values()

    def _refresh_environments(self) -> None:
        self.environment_combo.blockSignals(True)
        self.environment_combo.clear()
        for name in self.environments:
            self.environment_combo.addItem(environment_label(name, self.translator), name)
        self.environment_combo.setCurrentIndex(self.environment_combo.findData(self._edited_environment))
        self.environment_combo.blockSignals(False)
        self.environment_editor.set_values({
            key: str(value) for key, value in self.environments[self._edited_environment].items()
        })
        self.delete_environment_button.setEnabled(len(self.environments) > 1)

    def _switch_environment(self) -> None:
        name = self.environment_combo.currentData()
        if name is None or name == self._edited_environment:
            return
        self._store_environment()
        self._edited_environment = name
        self._refresh_environments()

    def _ask_environment_name(self, current: str = "") -> str | None:
        name, accepted = QInputDialog.getText(
            self, self.t("environment_variables"), self.t("environment_name"),
            text=environment_label(current, self.translator) if current else "",
        )
        if not accepted:
            return None
        name = name.strip()
        if current and name == environment_label(current, self.translator):
            return current
        labels = {environment_label(key, self.translator) for key in self.environments if key != current}
        if not name or (name in self.environments and name != current) or name in labels:
            QMessageBox.warning(self, self.t("environment_variables"), self.t("environment_name_invalid"))
            return None
        return name

    def _add_environment(self) -> None:
        name = self._ask_environment_name()
        if name is None:
            return
        self._store_environment()
        self.environments[name] = {}
        self._edited_environment = name
        self._refresh_environments()

    def _rename_environment(self) -> None:
        name = self._ask_environment_name(self._edited_environment)
        if name is None or name == self._edited_environment:
            return
        self._store_environment()
        self.environments = {
            name if key == self._edited_environment else key: value
            for key, value in self.environments.items()
        }
        self._edited_environment = name
        self._refresh_environments()

    def _delete_environment(self) -> None:
        if len(self.environments) <= 1:
            return
        answer = QMessageBox.question(
            self, self.t("environment_delete"),
            self.t("environment_delete_message", name=environment_label(self._edited_environment, self.translator)),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        del self.environments[self._edited_environment]
        self._edited_environment = next(iter(self.environments))
        self._refresh_environments()

    def selected_settings(self) -> dict:
        settings = dict(self.settings)
        settings["language"] = self.language_combo.currentData()
        settings["theme"] = self.theme_combo.currentData()
        self._store_environment()
        settings["environments"] = deepcopy(self.environments)
        settings["active_environment"] = self._edited_environment
        settings["environment"] = deepcopy(self.environments[self._edited_environment])
        settings["check_updates_automatically"] = self.auto_updates_check.isChecked()
        return settings

    def accept(self) -> None:
        save_settings(self.selected_settings())
        super().accept()
