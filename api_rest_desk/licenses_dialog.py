from __future__ import annotations

from pathlib import Path
import tomllib

from PyQt6.QtCore import QSize
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QVBoxLayout,
)

from api_rest_desk.i18n import Translator
from api_rest_desk.resources import legal_directory
from api_rest_desk.theme import apply_theme


class LicensesDialog(QDialog):
    def __init__(self, translator: Translator, parent=None) -> None:
        super().__init__(parent)
        self.t = translator.t
        self.legal_root = Path(legal_directory())
        self.setWindowTitle(self.t("licenses"))
        self.resize(800, 600)
        self.setMinimumSize(500, 450)

        layout = QVBoxLayout(self)
        self.sections = QListWidget()
        self.sections.setObjectName("LicenseSections")
        self.sections.setAccessibleName(self.t("licenses"))
        self.documents = (
            ("license_program", "LICENSE"),
            ("license_copyright", "COPYRIGHT"),
            ("license_third_party", "THIRD_PARTY_NOTICES.md"),
            ("license_source", "SOURCE_CODE.md"),
            ("license_qt", "licenses/PyQt6-Qt6/INSTALLED-0-LICENSE.txt"),
            ("license_pyqt", "licenses/PyQt6/INSTALLED-0-LICENSE.txt"),
            ("license_versions", "SOURCE_MANIFEST.toml"),
            ("license_archives", "SOURCE_MANIFEST.toml"),
        )
        row_height = max(26, self.fontMetrics().height() + 8)
        for key, _ in self.documents:
            item = QListWidgetItem(self.t(key))
            item.setSizeHint(QSize(0, row_height))
            self.sections.addItem(item)
        self.sections.setFixedHeight(row_height * len(self.documents) + 12)
        self.sections.setStyleSheet(
            "QListWidget#LicenseSections { padding: 4px; }"
            "QListWidget#LicenseSections::item { padding: 2px 4px; margin: 0; border-radius: 0; }"
        )
        layout.addWidget(self.sections)

        self.content = QPlainTextEdit()
        self.content.setReadOnly(True)
        self.content.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        layout.addWidget(self.content, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.button(QDialogButtonBox.StandardButton.Close).setText(self.t("license_close"))
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        apply_theme(self)
        self.sections.currentRowChanged.connect(self._show_document)
        self.sections.setCurrentRow(0)

    def _show_document(self, row: int) -> None:
        if not 0 <= row < len(self.documents):
            return
        key, filename = self.documents[row]
        self.content.setAccessibleName(self.t(key))
        try:
            text = (self.legal_root / filename).read_text(encoding="utf-8")
            if key == "license_versions":
                sources = tomllib.loads(text)["sources"]
                text = self.t("license_versions_intro") + "\n\n" + "\n".join(
                    f"{source['name']}: {source['version']} — {source['license']}"
                    for source in sources
                )
        except (OSError, UnicodeError, ValueError, KeyError, TypeError):
            text = self.t("license_document_unavailable", document=self.t(key))
        self.content.setPlainText(text)
        self.content.verticalScrollBar().setValue(0)
