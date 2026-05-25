from __future__ import annotations

from api_rest_desk.exceptions import HeaderParseError

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QCompleter,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QStackedWidget,
    QTableWidget,
    QWidget,
    QVBoxLayout,
)

from api_rest_desk.config import COMMON_HEADERS
from api_rest_desk.i18n import Translator
from api_rest_desk.models import RestCall


class HeaderEditor(QWidget):
    """Table-based editor for HTTP request headers with auto-complete
    on common header names.
    """

    def __init__(self) -> None:
        super().__init__()
        self.translator = Translator()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(("Header", "Valore"))
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(46)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table, 1)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        self.add_button = QPushButton("Aggiungi")
        self.remove_button = QPushButton("Rimuovi")
        self.add_button.clicked.connect(lambda: self.add_row())
        self.remove_button.clicked.connect(self.remove_selected_rows)
        buttons.addWidget(self.add_button)
        buttons.addWidget(self.remove_button)
        layout.addLayout(buttons)
        self.retranslate_ui(self.translator)

    def retranslate_ui(self, translator: Translator) -> None:
        self.translator = translator
        self.table.setHorizontalHeaderLabels((translator.t("headers"), translator.t("value")))
        self.add_button.setText(translator.t("add"))
        self.remove_button.setText(translator.t("remove"))
        for row in range(self.table.rowCount()):
            name_widget = self.table.cellWidget(row, 0)
            value_widget = self.table.cellWidget(row, 1)
            if isinstance(name_widget, QComboBox):
                name_widget.lineEdit().setPlaceholderText(translator.t("headers"))
            if isinstance(value_widget, QLineEdit):
                value_widget.setPlaceholderText(translator.t("value"))

    def set_headers(self, headers: dict[str, str]) -> None:
        """Replace the table contents with the given header dictionary."""
        self.table.setRowCount(0)
        for name, value in headers.items():
            self.add_row(name, value)
        if not headers:
            self.add_row()

    def headers(self) -> dict[str, str]:
        """Read all header rows from the table and return them as a dictionary.

        Raises:
            HeaderParseError: When a row has a value but no header name.
        """
        parsed: dict[str, str] = {}
        for row in range(self.table.rowCount()):
            name_widget = self.table.cellWidget(row, 0)
            value_widget = self.table.cellWidget(row, 1)
            if not isinstance(name_widget, QComboBox) or not isinstance(value_widget, QLineEdit):
                continue

            name = name_widget.currentText().strip()
            value = value_widget.text().strip()
            if not name and not value:
                continue
            if not name:
                raise HeaderParseError("header_missing_name", row=row + 1)

            parsed[name] = value
        return parsed

    def add_row(self, name: str = "", value: str = "") -> None:
        """Append a new header row to the table."""
        row = self.table.rowCount()
        self.table.insertRow(row)

        name_input = QComboBox()
        name_input.setEditable(True)
        name_input.addItems(COMMON_HEADERS)
        name_input.completer().setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        name_input.completer().setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        name_input.setEditText(name)
        name_input.lineEdit().setPlaceholderText(self.translator.t("headers"))
        name_input.setMinimumHeight(34)

        value_input = QLineEdit(value)
        value_input.setPlaceholderText(self.translator.t("value"))
        value_input.setMinimumHeight(34)

        self.table.setCellWidget(row, 0, name_input)
        self.table.setCellWidget(row, 1, value_input)

    def remove_selected_rows(self) -> None:
        """Remove the currently selected rows, or the last row if none is selected."""
        selected_rows = sorted({index.row() for index in self.table.selectedIndexes()}, reverse=True)
        if not selected_rows:
            selected_rows = [self.table.rowCount() - 1]

        for row in selected_rows:
            if row >= 0:
                self.table.removeRow(row)

        if self.table.rowCount() == 0:
            self.add_row()


class KeyValueEditor(QWidget):
    """Generic two-column table editor for key-value pairs
    (used for query params and form body fields).
    """

    def __init__(self, key_label: str = "Key", value_label: str = "Value") -> None:
        super().__init__()
        self.translator = Translator()
        self.key_label = key_label
        self.value_label = value_label
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels((self.key_label, self.value_label))
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(42)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table, 1)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        self.add_button = QPushButton()
        self.remove_button = QPushButton()
        self.add_button.clicked.connect(lambda: self.add_row())
        self.remove_button.clicked.connect(self.remove_selected_rows)
        buttons.addWidget(self.add_button)
        buttons.addWidget(self.remove_button)
        layout.addLayout(buttons)
        self.retranslate_ui(self.translator)

    def retranslate_ui(self, translator: Translator, key_label: str | None = None, value_label: str | None = None) -> None:
        self.translator = translator
        self.key_label = key_label or self.key_label
        self.value_label = value_label or self.value_label
        self.table.setHorizontalHeaderLabels((self.key_label, self.value_label))
        self.add_button.setText(translator.t("add"))
        self.remove_button.setText(translator.t("remove"))
        for row in range(self.table.rowCount()):
            key_widget = self.table.cellWidget(row, 0)
            value_widget = self.table.cellWidget(row, 1)
            if isinstance(key_widget, QLineEdit):
                key_widget.setPlaceholderText(self.key_label)
            if isinstance(value_widget, QLineEdit):
                value_widget.setPlaceholderText(self.value_label)

    def set_values(self, values: dict[str, str]) -> None:
        """Replace the table contents with the given key-value dictionary."""
        self.table.setRowCount(0)
        for key, value in values.items():
            self.add_row(key, value)
        if not values:
            self.add_row()

    def values(self) -> dict[str, str]:
        """Read all key-value rows from the table and return them as a dictionary."""
        parsed: dict[str, str] = {}
        for row in range(self.table.rowCount()):
            key_widget = self.table.cellWidget(row, 0)
            value_widget = self.table.cellWidget(row, 1)
            if not isinstance(key_widget, QLineEdit) or not isinstance(value_widget, QLineEdit):
                continue
            key = key_widget.text().strip()
            value = value_widget.text().strip()
            if not key and not value:
                continue
            if not key:
                raise ValueError(f"Riga {row + 1}: inserisci il nome del parametro.")
            parsed[key] = value
        return parsed

    def add_row(self, key: str = "", value: str = "") -> None:
        row = self.table.rowCount()
        self.table.insertRow(row)

        key_input = QLineEdit(key)
        key_input.setPlaceholderText(self.key_label)
        key_input.setMinimumHeight(32)
        value_input = QLineEdit(value)
        value_input.setPlaceholderText(self.value_label)
        value_input.setMinimumHeight(32)

        self.table.setCellWidget(row, 0, key_input)
        self.table.setCellWidget(row, 1, value_input)

    def remove_selected_rows(self) -> None:
        selected_rows = sorted({index.row() for index in self.table.selectedIndexes()}, reverse=True)
        if not selected_rows:
            selected_rows = [self.table.rowCount() - 1]

        for row in selected_rows:
            if row >= 0:
                self.table.removeRow(row)

        if self.table.rowCount() == 0:
            self.add_row()


class AuthEditor(QWidget):
    """Stacked widget that provides input forms for different
    authentication methods: None, Basic, Bearer, and API Key.
    """

    def __init__(self) -> None:
        super().__init__()
        self.translator = Translator()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.auth_type_combo = QComboBox()
        self.auth_type_combo.addItem("", "none")
        self.auth_type_combo.addItem("", "basic")
        self.auth_type_combo.addItem("", "bearer")
        self.auth_type_combo.addItem("", "api_key")
        self.auth_type_combo.currentIndexChanged.connect(self._sync_auth_view)
        layout.addWidget(self.auth_type_combo)

        self.stack = QStackedWidget()
        layout.addWidget(self.stack, 1)

        self.none_view = QWidget()
        none_layout = QVBoxLayout(self.none_view)
        none_layout.setContentsMargins(0, 0, 0, 0)
        self.none_label = QLabel()
        self.none_label.setObjectName("MutedLabel")
        self.none_label.setWordWrap(True)
        none_layout.addWidget(self.none_label)
        none_layout.addStretch(1)

        self.basic_view = QWidget()
        basic_layout = QFormLayout(self.basic_view)
        basic_layout.setContentsMargins(0, 0, 0, 0)
        basic_layout.setSpacing(10)
        self.username_label = QLabel()
        self.username_input = QLineEdit()
        self.password_label = QLabel()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        basic_layout.addRow(self.username_label, self.username_input)
        basic_layout.addRow(self.password_label, self.password_input)

        self.bearer_view = QWidget()
        bearer_layout = QFormLayout(self.bearer_view)
        bearer_layout.setContentsMargins(0, 0, 0, 0)
        bearer_layout.setSpacing(10)
        self.token_label = QLabel()
        self.token_input = QLineEdit()
        self.token_input.setEchoMode(QLineEdit.EchoMode.Password)
        bearer_layout.addRow(self.token_label, self.token_input)

        self.api_key_view = QWidget()
        api_key_layout = QFormLayout(self.api_key_view)
        api_key_layout.setContentsMargins(0, 0, 0, 0)
        api_key_layout.setSpacing(10)
        self.key_name_label = QLabel()
        self.key_name_input = QLineEdit()
        self.key_value_label = QLabel()
        self.key_value_input = QLineEdit()
        self.key_value_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_location_label = QLabel()
        self.key_location_combo = QComboBox()
        self.key_location_combo.addItem("", "header")
        self.key_location_combo.addItem("", "query")
        api_key_layout.addRow(self.key_name_label, self.key_name_input)
        api_key_layout.addRow(self.key_value_label, self.key_value_input)
        api_key_layout.addRow(self.key_location_label, self.key_location_combo)

        self.stack.addWidget(self.none_view)
        self.stack.addWidget(self.basic_view)
        self.stack.addWidget(self.bearer_view)
        self.stack.addWidget(self.api_key_view)
        self.retranslate_ui(self.translator)

    def retranslate_ui(self, translator: Translator) -> None:
        self.translator = translator
        self.auth_type_combo.setItemText(0, translator.t("auth_none"))
        self.auth_type_combo.setItemText(1, translator.t("auth_basic"))
        self.auth_type_combo.setItemText(2, translator.t("auth_bearer"))
        self.auth_type_combo.setItemText(3, translator.t("auth_api_key"))
        self.none_label.setText(translator.t("auth_none_info"))
        self.username_label.setText(translator.t("username"))
        self.password_label.setText(translator.t("password"))
        self.token_label.setText(translator.t("token"))
        self.key_name_label.setText(translator.t("key_name"))
        self.key_value_label.setText(translator.t("key_value"))
        self.key_location_label.setText(translator.t("key_location"))
        self.key_location_combo.setItemText(0, translator.t("headers"))
        self.key_location_combo.setItemText(1, translator.t("query_params"))
        self.username_input.setPlaceholderText(translator.t("username"))
        self.password_input.setPlaceholderText(translator.t("password"))
        self.token_input.setPlaceholderText(translator.t("token"))
        self.key_name_input.setPlaceholderText(translator.t("key_name"))
        self.key_value_input.setPlaceholderText(translator.t("key_value"))
        self._sync_auth_view()

    def set_auth(self, call: RestCall | None) -> None:
        """Populate the auth fields from a :class:`RestCall`,
        or clear all fields when *call* is ``None``.
        """
        if call is None:
            auth_type = "none"
            self.username_input.clear()
            self.password_input.clear()
            self.token_input.clear()
            self.key_name_input.clear()
            self.key_value_input.clear()
            self.key_location_combo.setCurrentIndex(self.key_location_combo.findData("header"))
        else:
            auth_type = call.auth_type or "none"
            self.username_input.setText(call.auth_username)
            self.password_input.setText(call.auth_password)
            self.token_input.setText(call.auth_token)
            self.key_name_input.setText(call.auth_key_name)
            self.key_value_input.setText(call.auth_key_value)
            location_index = self.key_location_combo.findData(call.auth_key_location or "header")
            self.key_location_combo.setCurrentIndex(location_index if location_index >= 0 else 0)

        type_index = self.auth_type_combo.findData(auth_type)
        self.auth_type_combo.setCurrentIndex(type_index if type_index >= 0 else 0)

    def apply_to_call(self, call: RestCall) -> None:
        """Write the current auth editor state back into *call*'s
        authentication fields.
        """
        call.auth_type = str(self.auth_type_combo.currentData() or "none")
        call.auth_username = self.username_input.text().strip()
        call.auth_password = self.password_input.text()
        call.auth_token = self.token_input.text().strip()
        call.auth_key_name = self.key_name_input.text().strip()
        call.auth_key_value = self.key_value_input.text().strip()
        call.auth_key_location = str(self.key_location_combo.currentData() or "header")

    def _sync_auth_view(self) -> None:
        mode = str(self.auth_type_combo.currentData() or "none")
        index_by_mode = {"none": 0, "basic": 1, "bearer": 2, "api_key": 3}
        self.stack.setCurrentIndex(index_by_mode.get(mode, 0))
