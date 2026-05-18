from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from urllib.parse import parse_qsl, urlencode

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QBrush, QColor, QFont, QTextCharFormat, QTextCursor
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFrame,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QInputDialog,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QSplitter,
    QStackedWidget,
    QStatusBar,
    QTabWidget,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from api_rest_desk.config import APP_NAME, APP_VERSION, DEFAULT_COLLECTION, HISTORY_LIMIT, HTTP_METHODS
from api_rest_desk.i18n import Translator
from api_rest_desk.models import CallHistory, RestCall
from api_rest_desk.storage import (
    StorageError,
    load_collection,
    load_folders,
    load_history,
    save_collection,
    save_folders,
    save_history,
)
from api_rest_desk.widgets import AuthEditor, HeaderEditor, KeyValueEditor
from api_rest_desk.theme import apply_theme, set_status_badge
from api_rest_desk.toast import ToastNotification
from api_rest_desk.settings_dialog import SettingsDialog
from api_rest_desk.workflow_dialog import WorkflowDialog
from api_rest_desk.workers import HttpWorker


class RestClientWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1240, 780)
        self.translator = Translator()
        self.t = self.translator.t
        self.calls: list[RestCall] = self._read_collection()
        self.folders: list[str] = self._read_folders()
        self.history: list[CallHistory] = self._read_history()
        self.current_worker: HttpWorker | None = None
        self.pending_call: RestCall | None = None
        self.toast: ToastNotification | None = None

        self._build_ui()
        self._apply_style()
        self.toast = ToastNotification(self)
        self.retranslate_ui()
        self._populate_call_list()
        self._populate_history_list()

        if self.calls:
            self._select_call(self.calls[0].id)
        elif self.history:
            self.sidebar_tabs.setCurrentIndex(1)
            self.history_list.setCurrentRow(0)

    def _build_ui(self) -> None:
        root_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.setCentralWidget(root_splitter)

        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(14, 14, 14, 14)
        sidebar_layout.setSpacing(12)

        app_title = QLabel(APP_NAME)
        app_title.setObjectName("AppTitle")
        self.app_subtitle = QLabel()
        self.app_subtitle.setObjectName("MutedLabel")
        sidebar_layout.addWidget(app_title)
        sidebar_layout.addWidget(self.app_subtitle)

        self.sidebar_tabs = QTabWidget()
        self.collection_search = QLineEdit()
        self.collection_search.textChanged.connect(self._filter_collection_tree)
        sidebar_layout.addWidget(self.collection_search)
        self.collection_tree = QTreeWidget()
        self.collection_tree.setHeaderHidden(True)
        self.collection_tree.currentItemChanged.connect(self._load_selected_call)
        self.history_list = QListWidget()
        self.history_list.currentItemChanged.connect(self._load_selected_history)
        self.sidebar_tabs.addTab(self.collection_tree, "")
        self.sidebar_tabs.addTab(self.history_list, "")
        sidebar_layout.addWidget(self.sidebar_tabs, 1)

        sidebar_buttons = QHBoxLayout()
        self.new_button = QPushButton()
        self.new_folder_button = QPushButton()
        self.duplicate_button = QPushButton()
        self.delete_button = QPushButton()
        self.delete_button.setObjectName("Danger")
        self.new_button.clicked.connect(self._new_call)
        self.new_folder_button.clicked.connect(self._new_folder)
        self.duplicate_button.clicked.connect(self._duplicate_call)
        self.delete_button.clicked.connect(self._delete_call)
        sidebar_buttons.addWidget(self.new_button)
        sidebar_buttons.addWidget(self.new_folder_button)
        sidebar_buttons.addWidget(self.duplicate_button)
        sidebar_buttons.addWidget(self.delete_button)
        sidebar_layout.addLayout(sidebar_buttons)

        history_buttons = QHBoxLayout()
        self.load_history_button = QPushButton()
        self.clear_history_button = QPushButton()
        self.clear_history_button.setObjectName("Danger")
        self.load_history_button.clicked.connect(self._load_current_history_request)
        self.clear_history_button.clicked.connect(self._clear_history)
        history_buttons.addWidget(self.load_history_button)
        history_buttons.addWidget(self.clear_history_button)
        sidebar_layout.addLayout(history_buttons)

        self.workflow_button = QPushButton()
        self.workflow_button.setObjectName("Secondary")
        self.workflow_button.clicked.connect(self._open_workflow_dialog)
        sidebar_layout.addWidget(self.workflow_button)

        editor = QWidget()
        editor_layout = QVBoxLayout(editor)
        editor_layout.setContentsMargins(18, 14, 18, 14)
        editor_layout.setSpacing(12)

        request_card = QFrame()
        request_card.setObjectName("Panel")
        request_layout = QVBoxLayout(request_card)
        request_layout.setContentsMargins(16, 16, 16, 16)
        request_layout.setSpacing(12)

        self.request_title = QLabel()
        self.request_title.setObjectName("SectionTitle")
        request_layout.addWidget(self.request_title)

        name_row = QHBoxLayout()
        self.name_input = QLineEdit()
        self.name_label = QLabel()
        self.save_button = QPushButton()
        self.save_button.setObjectName("Secondary")
        self.save_button.clicked.connect(self._save_current_call)
        name_row.addWidget(self.name_label)
        name_row.addWidget(self.name_input, 1)
        name_row.addWidget(self.save_button)
        request_layout.addLayout(name_row)

        request_row = QHBoxLayout()
        self.method_combo = QComboBox()
        self.method_combo.addItems(HTTP_METHODS)
        self.method_combo.setFixedWidth(118)
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://api.example.com/resource")
        self.send_button = QPushButton()
        self.send_button.setObjectName("Primary")
        self.send_button.clicked.connect(self._send_current_call)
        request_row.addWidget(self.method_combo)
        request_row.addWidget(self.url_input, 1)
        request_row.addWidget(self.send_button)
        request_layout.addLayout(request_row)

        request_tabs = QTabWidget()
        self.headers_editor = HeaderEditor()
        self.auth_editor = AuthEditor()
        self.params_editor = KeyValueEditor()
        self.body_editor = QPlainTextEdit()
        self.body_editor.setPlaceholderText('{\n  "name": "Mario"\n}')
        self.form_body_editor = KeyValueEditor()
        body_tools = QHBoxLayout()
        self.body_type_combo = QComboBox()
        self.body_type_combo.addItem("Raw", "raw")
        self.body_type_combo.addItem("JSON", "json")
        self.body_type_combo.addItem("Form URL Encoded", "form")
        self.body_type_combo.currentIndexChanged.connect(self._sync_body_editor)
        self.format_json_button = QPushButton()
        self.validate_json_button = QPushButton()
        self.format_json_button.clicked.connect(self._format_request_json)
        self.validate_json_button.clicked.connect(self._validate_request_json)
        body_tools.addWidget(self.body_type_combo)
        body_tools.addStretch(1)
        body_tools.addWidget(self.format_json_button)
        body_tools.addWidget(self.validate_json_button)
        request_layout.addLayout(body_tools)

        self.body_stack = QStackedWidget()
        self.body_stack.addWidget(self.body_editor)
        self.body_stack.addWidget(self.form_body_editor)
        body_tab = QWidget()
        body_tab_layout = QVBoxLayout(body_tab)
        body_tab_layout.setContentsMargins(0, 0, 0, 0)
        body_tab_layout.addWidget(self.body_stack)

        self.request_tabs = request_tabs
        request_tabs.addTab(self.headers_editor, "")
        request_tabs.addTab(self.auth_editor, "")
        request_tabs.addTab(self.params_editor, "")
        request_tabs.addTab(body_tab, "")
        request_layout.addWidget(request_tabs, 1)
        editor_layout.addWidget(request_card, 1)

        response = QWidget()
        response_layout = QVBoxLayout(response)
        response_layout.setContentsMargins(18, 14, 18, 14)
        response_layout.setSpacing(12)

        response_card = QFrame()
        response_card.setObjectName("Panel")
        response_card_layout = QVBoxLayout(response_card)
        response_card_layout.setContentsMargins(16, 16, 16, 16)
        response_card_layout.setSpacing(12)

        response_top = QHBoxLayout()
        self.response_title = QLabel()
        self.response_title.setObjectName("SectionTitle")
        response_top.addWidget(self.response_title)
        response_top.addStretch(1)
        self.response_search = QLineEdit()
        self.response_search.setFixedWidth(180)
        self.response_search.textChanged.connect(self._highlight_response_matches)
        self.response_search.returnPressed.connect(self._find_in_response)
        self.copy_response_button = QPushButton()
        self.save_response_button = QPushButton()
        self.copy_response_button.clicked.connect(self._copy_response_body)
        self.save_response_button.clicked.connect(self._save_response_body)
        response_top.addWidget(self.response_search)
        response_top.addWidget(self.copy_response_button)
        response_top.addWidget(self.save_response_button)
        response_card_layout.addLayout(response_top)

        response_header = QFrame()
        response_header.setObjectName("Metrics")
        response_header_layout = QFormLayout(response_header)
        response_header_layout.setContentsMargins(12, 10, 12, 10)
        response_header_layout.setHorizontalSpacing(22)
        self.status_value = QLabel("-")
        self.status_value.setObjectName("StatusBadge")
        self.status_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        set_status_badge(self.status_value, "-")
        self.time_value = QLabel("-")
        self.size_value = QLabel("-")
        self.status_label = QLabel()
        self.time_label = QLabel()
        self.size_label = QLabel()
        response_header_layout.addRow(self.status_label, self.status_value)
        response_header_layout.addRow(self.time_label, self.time_value)
        response_header_layout.addRow(self.size_label, self.size_value)
        response_card_layout.addWidget(response_header)

        response_tabs = QTabWidget()
        self.response_body = QPlainTextEdit()
        self.response_body.setReadOnly(True)
        self.response_raw = QPlainTextEdit()
        self.response_raw.setReadOnly(True)
        self.response_headers = QPlainTextEdit()
        self.response_headers.setReadOnly(True)
        self.response_tabs = response_tabs
        response_tabs.addTab(self.response_body, "")
        response_tabs.addTab(self.response_raw, "")
        response_tabs.addTab(self.response_headers, "")
        response_card_layout.addWidget(response_tabs, 1)
        response_layout.addWidget(response_card, 1)

        root_splitter.addWidget(sidebar)
        root_splitter.addWidget(editor)
        root_splitter.addWidget(response)
        root_splitter.setSizes([310, 510, 420])

        self.setStatusBar(QStatusBar())
        self._build_menu()

        monospace = QFont("Consolas")
        monospace.setStyleHint(QFont.StyleHint.Monospace)

        for editor_widget in (self.body_editor, self.response_body, self.response_raw, self.response_headers):
            editor_widget.setFont(monospace)
            editor_widget.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

    def _build_menu(self) -> None:
        self.collection_menu = self.menuBar().addMenu("")

        self.new_action = QAction(self)
        self.new_action.triggered.connect(self._new_call)
        self.collection_menu.addAction(self.new_action)

        self.new_folder_action = QAction(self)
        self.new_folder_action.triggered.connect(self._new_folder)
        self.collection_menu.addAction(self.new_folder_action)

        self.save_action = QAction(self)
        self.save_action.triggered.connect(self._save_current_call)
        self.collection_menu.addAction(self.save_action)

        self.send_action = QAction(self)
        self.send_action.setShortcut("Ctrl+Return")
        self.send_action.triggered.connect(self._send_current_call)
        self.collection_menu.addAction(self.send_action)

        self.history_menu = self.menuBar().addMenu("")
        self.reopen_action = QAction(self)
        self.reopen_action.triggered.connect(self._load_current_history_request)
        self.history_menu.addAction(self.reopen_action)

        self.clear_action = QAction(self)
        self.clear_action.triggered.connect(self._clear_history)
        self.history_menu.addAction(self.clear_action)

        self.workflow_menu = self.menuBar().addMenu("")
        self.open_workflow_action = QAction(self)
        self.open_workflow_action.triggered.connect(self._open_workflow_dialog)
        self.workflow_menu.addAction(self.open_workflow_action)

        self.settings_menu = self.menuBar().addMenu("")
        self.settings_action = QAction(self)
        self.settings_action.triggered.connect(self._open_settings_dialog)
        self.settings_menu.addAction(self.settings_action)

        self.about_menu = self.menuBar().addMenu("")
        self.about_action = QAction(self)
        self.about_action.triggered.connect(self._show_about_dialog)
        self.about_menu.addAction(self.about_action)

    def _apply_style(self) -> None:
        apply_theme(self)

    def retranslate_ui(self) -> None:
        self.t = self.translator.t
        self.app_subtitle.setText(self.t("rest_workspace"))
        self.sidebar_tabs.setTabText(0, self.t("collection"))
        self.sidebar_tabs.setTabText(1, self.t("history"))
        self.collection_search.setPlaceholderText(self.t("search"))
        self.new_button.setText(self.t("new"))
        self.new_folder_button.setText(self.t("folder"))
        self.duplicate_button.setText(self.t("duplicate"))
        self.delete_button.setText(self.t("delete"))
        self.load_history_button.setText(self.t("reopen_history"))
        self.clear_history_button.setText(self.t("clear_history"))
        self.workflow_button.setText(self.t("workflow"))
        self.request_title.setText(self.t("request"))
        self.name_label.setText(self.t("name"))
        self.name_input.setPlaceholderText(self.t("call_name_placeholder"))
        self.save_button.setText(self.t("save"))
        self.send_button.setText(self.t("send"))
        self.request_tabs.setTabText(0, self.t("headers"))
        self.request_tabs.setTabText(1, self.t("auth"))
        self.request_tabs.setTabText(2, self.t("params"))
        self.request_tabs.setTabText(3, self.t("body"))
        self.format_json_button.setText(self.t("format_json"))
        self.validate_json_button.setText(self.t("validate_json"))
        self.body_type_combo.setItemText(0, self.t("raw"))
        self.body_type_combo.setItemText(1, "JSON")
        self.body_type_combo.setItemText(2, self.t("form_urlencoded"))
        self.response_title.setText(self.t("response"))
        self.response_search.setPlaceholderText(self.t("find"))
        self.copy_response_button.setText(self.t("copy"))
        self.save_response_button.setText(self.t("save_response"))
        self.status_label.setText(self.t("status"))
        self.time_label.setText(self.t("time"))
        self.size_label.setText(self.t("size"))
        self.response_tabs.setTabText(0, self.t("pretty"))
        self.response_tabs.setTabText(1, self.t("raw"))
        self.response_tabs.setTabText(2, self.t("headers"))
        self.collection_menu.setTitle(self.t("collection_menu"))
        self.new_action.setText(self.t("new_call"))
        self.new_folder_action.setText(self.t("new_folder"))
        self.save_action.setText(self.t("save_call"))
        self.send_action.setText(self.t("send"))
        self.history_menu.setTitle(self.t("history_menu"))
        self.reopen_action.setText(self.t("reopen_selected"))
        self.clear_action.setText(self.t("clear_history"))
        self.workflow_menu.setTitle(self.t("workflow_menu"))
        self.open_workflow_action.setText(self.t("open_composer"))
        self.settings_menu.setTitle(self.t("settings"))
        self.settings_action.setText(self.t("settings"))
        self.about_menu.setTitle(self.t("about"))
        self.about_action.setText(self.t("about_app"))
        self.headers_editor.retranslate_ui(self.translator)
        self.auth_editor.retranslate_ui(self.translator)
        self.params_editor.retranslate_ui(self.translator, self.t("param_name"), self.t("value"))
        self.form_body_editor.retranslate_ui(self.translator, self.t("param_name"), self.t("value"))
        self._sync_body_editor()

    def _change_language(self, language: str) -> None:
        self.translator.set_language(language)
        self.retranslate_ui()

    def _read_collection(self) -> list[RestCall]:
        try:
            return load_collection()
        except StorageError as error:
            QMessageBox.warning(self, self.t("collection"), str(error))
            return []

    def _read_history(self) -> list[CallHistory]:
        try:
            return load_history()
        except StorageError as error:
            QMessageBox.warning(self, self.t("history"), str(error))
            return []

    def _read_folders(self) -> list[str]:
        try:
            folders = load_folders()
        except StorageError as error:
            QMessageBox.warning(self, self.t("folder"), str(error))
            folders = [DEFAULT_COLLECTION]
        for call in self.calls:
            if call.collection and call.collection not in folders:
                folders.append(call.collection)
        return folders

    def _collection_names(self) -> list[str]:
        names = set(self.folders)
        names.update(call.collection or DEFAULT_COLLECTION for call in self.calls)
        names.add(DEFAULT_COLLECTION)
        return sorted(names, key=str.casefold)

    def _populate_call_list(self) -> None:
        self.collection_tree.clear()
        folders: dict[str, QTreeWidgetItem] = {}

        for folder_name in self._collection_names():
            folder_item = QTreeWidgetItem([folder_name])
            folder_item.setData(0, Qt.ItemDataRole.UserRole, {"type": "folder", "name": folder_name})
            folder_item.setExpanded(True)
            folders[folder_name] = folder_item
            self.collection_tree.addTopLevelItem(folder_item)

        for call in self.calls:
            folder = call.collection or DEFAULT_COLLECTION
            if folder not in folders:
                folder_item = QTreeWidgetItem([folder])
                folder_item.setData(0, Qt.ItemDataRole.UserRole, {"type": "folder", "name": folder})
                folder_item.setExpanded(True)
                folders[folder] = folder_item
                self.collection_tree.addTopLevelItem(folder_item)

            item = QTreeWidgetItem([f"{call.method}  {call.name}\n{call.url}"])
            item.setData(0, Qt.ItemDataRole.UserRole, {"type": "call", "id": call.id})
            item.setForeground(0, QBrush(QColor(self._method_color(call.method))))
            folders[folder].addChild(item)

        self.collection_tree.expandAll()
        self._filter_collection_tree()

    def _filter_collection_tree(self) -> None:
        query = self.collection_search.text().strip().lower() if hasattr(self, "collection_search") else ""
        for folder_index in range(self.collection_tree.topLevelItemCount()):
            folder_item = self.collection_tree.topLevelItem(folder_index)
            visible_children = 0
            for child_index in range(folder_item.childCount()):
                child = folder_item.child(child_index)
                match = query in child.text(0).lower() or query in folder_item.text(0).lower()
                child.setHidden(bool(query) and not match)
                if not child.isHidden():
                    visible_children += 1
            folder_match = query in folder_item.text(0).lower()
            folder_item.setHidden(bool(query) and not folder_match and visible_children == 0)

    def _populate_history_list(self) -> None:
        self.history_list.clear()
        for history_item in self.history:
            status = str(history_item.status) if history_item.status is not None else "ERR"
            when = self._format_timestamp(history_item.timestamp)
            item = QListWidgetItem(f"{status}  {history_item.method}  {when}\n{history_item.url}")
            item.setData(Qt.ItemDataRole.UserRole, history_item.id)
            foreground, background = self._history_status_colors(history_item.status)
            item.setForeground(QBrush(QColor(foreground)))
            item.setBackground(QBrush(QColor(background)))
            self.history_list.addItem(item)

    def _selected_call(self) -> RestCall | None:
        item = self.collection_tree.currentItem()
        if item is None:
            return None

        metadata = item.data(0, Qt.ItemDataRole.UserRole)
        if not isinstance(metadata, dict) or metadata.get("type") != "call":
            return None

        call_id = metadata.get("id")
        return next((call for call in self.calls if call.id == call_id), None)

    def _selected_collection_name(self) -> str:
        item = self.collection_tree.currentItem()
        if item is None:
            return DEFAULT_COLLECTION

        metadata = item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(metadata, dict) and metadata.get("type") == "folder":
            return str(metadata.get("name") or DEFAULT_COLLECTION)

        call = self._selected_call()
        return call.collection if call is not None and call.collection else DEFAULT_COLLECTION

    def _selected_history(self) -> CallHistory | None:
        item = self.history_list.currentItem()
        if item is None:
            return None

        history_id = item.data(Qt.ItemDataRole.UserRole)
        return next((item for item in self.history if item.id == history_id), None)

    def _load_selected_call(self) -> None:
        call = self._selected_call()
        if call is None:
            return

        self.name_input.setText(call.name)
        self.method_combo.setCurrentText(call.method if call.method in HTTP_METHODS else "GET")
        self.url_input.setText(call.url)
        self.headers_editor.set_headers(call.headers)
        self.auth_editor.set_auth(call)
        self.params_editor.set_values(call.query_params)
        self._set_body_type(call.body_type, call.headers)
        self._set_request_body(call.body, str(self.body_type_combo.currentData() or "raw"))

    def _load_selected_history(self) -> None:
        history_item = self._selected_history()
        if history_item is not None:
            self._show_history_response(history_item)

    def _load_current_history_request(self) -> None:
        history_item = self._selected_history()
        if history_item is None:
            QMessageBox.information(self, self.t("select_history_title"), self.t("select_history_message"))
            return

        self.name_input.setText(history_item.name)
        self.method_combo.setCurrentText(history_item.method if history_item.method in HTTP_METHODS else "GET")
        self.url_input.setText(history_item.url)
        self.headers_editor.set_headers(history_item.request_headers)
        self.auth_editor.set_auth(None)
        self.params_editor.set_values(history_item.request_query_params)
        self._set_body_type(history_item.request_body_type, history_item.request_headers)
        self._set_request_body(history_item.request_body, str(self.body_type_combo.currentData() or "raw"))
        self.collection_tree.setCurrentItem(None)
        self._show_history_response(history_item)
        self.statusBar().showMessage(self.t("history_restored"), 2500)

    def _read_call_from_ui(self, call_id: str | None = None) -> RestCall:
        headers = self.headers_editor.headers()
        query_params = self.params_editor.values()
        body_type = str(self.body_type_combo.currentData() or "raw")
        body = self._request_body_from_ui(body_type)
        if body.strip() and body_type == "json":
            headers.setdefault("Content-Type", "application/json; charset=utf-8")
        elif body.strip() and body_type == "form":
            headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
        call = RestCall(
            name=self.name_input.text().strip() or "Nuova chiamata",
            method=self.method_combo.currentText(),
            url=self.url_input.text().strip(),
            collection=self._selected_collection_name(),
            headers=headers,
            query_params=query_params,
            body=body,
            body_type=body_type,
        )
        self.auth_editor.apply_to_call(call)
        if call_id:
            call.id = call_id
        return call

    def _save_current_call(self) -> None:
        call = self._selected_call()
        try:
            updated_call = self._read_call_from_ui(call.id if call else None)
        except ValueError as error:
            QMessageBox.warning(self, self.t("invalid_headers_title"), str(error))
            return

        if call is None:
            if updated_call.collection not in self.folders:
                self.folders.append(updated_call.collection)
                save_folders(self.folders)
            self.calls.append(updated_call)
        else:
            index = self.calls.index(call)
            self.calls[index] = updated_call

        save_collection(self.calls)
        self._populate_call_list()
        self._select_call(updated_call.id)
        self.statusBar().showMessage(self.t("request_saved"), 2500)

    def _new_call(self) -> None:
        call = RestCall(
            name="Nuova chiamata",
            method="GET",
            url="https://",
            collection=self._selected_collection_name(),
        )
        if call.collection not in self.folders:
            self.folders.append(call.collection)
            save_folders(self.folders)
        self.calls.append(call)
        save_collection(self.calls)
        self._populate_call_list()
        self._select_call(call.id)
        self.sidebar_tabs.setCurrentIndex(0)

    def _new_folder(self) -> None:
        name, accepted = QInputDialog.getText(self, self.t("new_folder_title"), self.t("new_folder_label"))
        folder_name = name.strip()
        if not accepted or not folder_name:
            return

        if folder_name in self._collection_names():
            QMessageBox.information(self, self.t("existing_folder_title"), self.t("existing_folder_message"))
            return

        self.folders.append(folder_name)
        save_folders(self.folders)
        self._populate_call_list()
        self._select_folder(folder_name)
        self.sidebar_tabs.setCurrentIndex(0)

    def _duplicate_call(self) -> None:
        call = self._selected_call()
        if call is None:
            return

        duplicated = RestCall(
            name=f"{call.name} copia",
            method=call.method,
            url=call.url,
            collection=call.collection,
            headers=dict(call.headers),
            query_params=dict(call.query_params),
            body=call.body,
            body_type=call.body_type,
            auth_type=call.auth_type,
            auth_username=call.auth_username,
            auth_password=call.auth_password,
            auth_token=call.auth_token,
            auth_key_name=call.auth_key_name,
            auth_key_value=call.auth_key_value,
            auth_key_location=call.auth_key_location,
        )
        if duplicated.collection not in self.folders:
            self.folders.append(duplicated.collection)
            save_folders(self.folders)
        self.calls.append(duplicated)
        save_collection(self.calls)
        self._populate_call_list()
        self._select_call(duplicated.id)
        self.sidebar_tabs.setCurrentIndex(0)

    def _delete_call(self) -> None:
        call = self._selected_call()
        if call is None:
            folder_name = self._selected_collection_name()
            if folder_name == DEFAULT_COLLECTION:
                return

            answer = QMessageBox.question(
                self,
                self.t("delete_folder_title"),
                self.t("delete_folder_message", name=folder_name),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return

            self.calls = [item for item in self.calls if item.collection != folder_name]
            self.folders = [item for item in self.folders if item != folder_name]
            save_folders(self.folders)
            save_collection(self.calls)
            self._populate_call_list()
            if self.calls:
                self._select_call(self.calls[0].id)
            return

        answer = QMessageBox.question(
            self,
            self.t("delete_call_title"),
            self.t("delete_call_message", name=call.name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        self.calls = [item for item in self.calls if item.id != call.id]
        save_collection(self.calls)
        self._populate_call_list()
        if self.calls:
            self._select_call(self.calls[0].id)

    def _clear_history(self) -> None:
        if not self.history:
            return

        answer = QMessageBox.question(
            self,
            self.t("clear_history"),
            self.t("clear_history") + "?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        self.history.clear()
        save_history(self.history)
        self._populate_history_list()
        self.statusBar().showMessage(self.t("history_cleared"), 2500)

    def _open_workflow_dialog(self) -> None:
        dialog = WorkflowDialog(self.calls, self.translator, self)
        dialog.exec()

    def _open_settings_dialog(self) -> None:
        dialog = SettingsDialog(self.translator, self)
        if not dialog.exec():
            return

        self.translator.set_language(str(dialog.selected_settings().get("language") or "it"))
        self._apply_style()
        self.retranslate_ui()
        self.statusBar().showMessage(self.t("settings_saved"), 2500)
        self._show_toast(self.t("settings_saved"), "success")

    def _show_about_dialog(self) -> None:
        QMessageBox.about(
            self,
            self.t("about"),
            f"{APP_NAME}\n{self.t('version')}: {APP_VERSION}",
        )

    def _show_toast(self, message: str, kind: str = "info") -> None:
        if self.toast is not None:
            self.toast.show_message(message, kind)

    def _sync_body_editor(self) -> None:
        body_type = str(self.body_type_combo.currentData() or "raw")
        is_form = body_type == "form"
        self.body_stack.setCurrentIndex(1 if is_form else 0)
        self.format_json_button.setEnabled(body_type == "json")
        self.validate_json_button.setEnabled(body_type == "json")

    def _request_body_from_ui(self, body_type: str) -> str:
        if body_type == "form":
            return urlencode(self.form_body_editor.values())
        return self.body_editor.toPlainText()

    def _set_request_body(self, body: str, body_type: str) -> None:
        if body_type == "form":
            self.form_body_editor.set_values(dict(parse_qsl(body, keep_blank_values=True)))
            self.body_editor.clear()
            return
        self.body_editor.setPlainText(body)
        self.form_body_editor.set_values({})

    def _format_request_json(self) -> None:
        try:
            parsed = json.loads(self.body_editor.toPlainText() or "{}")
        except json.JSONDecodeError as error:
            self.statusBar().showMessage(f"{self.t('json_invalid')}: {error}", 3500)
            self._show_toast(self.t("json_invalid"), "error")
            return
        self.body_editor.setPlainText(json.dumps(parsed, indent=2, ensure_ascii=False))
        self._show_toast(self.t("json_valid"), "success")

    def _set_body_type(self, body_type: str, headers: dict[str, str]) -> None:
        inferred = self._body_type_from_headers(headers)
        selected = body_type if body_type in {"raw", "json", "form"} else inferred
        if selected == "raw" and inferred != "raw":
            selected = inferred
        self.body_type_combo.setCurrentIndex(self.body_type_combo.findData(selected))

    def _set_body_type_from_headers(self, headers: dict[str, str]) -> None:
        self.body_type_combo.setCurrentIndex(self.body_type_combo.findData(self._body_type_from_headers(headers)))

    @staticmethod
    def _body_type_from_headers(headers: dict[str, str]) -> str:
        content_type = ""
        for key, value in headers.items():
            if key.lower() == "content-type":
                content_type = value.lower()
                break
        if "application/json" in content_type:
            return "json"
        if "application/x-www-form-urlencoded" in content_type:
            return "form"
        return "raw"

    def _validate_request_json(self) -> None:
        try:
            json.loads(self.body_editor.toPlainText() or "{}")
        except json.JSONDecodeError as error:
            self.statusBar().showMessage(f"{self.t('json_invalid')}: {error}", 3500)
            self._show_toast(self.t("json_invalid"), "error")
            return
        self.statusBar().showMessage(self.t("json_valid"), 2500)
        self._show_toast(self.t("json_valid"), "success")

    def _find_in_response(self) -> None:
        query = self.response_search.text().strip()
        if not query:
            return

        editor = self._active_response_editor()
        if editor is None:
            return

        if editor.find(query):
            return

        cursor = editor.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        editor.setTextCursor(cursor)
        editor.find(query)

    def _highlight_response_matches(self) -> None:
        query = self.response_search.text().strip()
        for editor in (self.response_body, self.response_raw, self.response_headers):
            editor.setExtraSelections(self._response_match_selections(editor, query))

    def _active_response_editor(self) -> QPlainTextEdit | None:
        current = self.response_tabs.currentWidget()
        if isinstance(current, QPlainTextEdit):
            return current
        return None

    @staticmethod
    def _response_match_selections(editor: QPlainTextEdit, query: str) -> list[QTextEdit.ExtraSelection]:
        if not query:
            return []

        selections: list[QTextEdit.ExtraSelection] = []
        document = editor.document()
        cursor = QTextCursor(document)
        highlight = QTextCharFormat()
        highlight.setBackground(QBrush(QColor("#fef08a")))
        highlight.setForeground(QBrush(QColor("#111827")))

        while True:
            cursor = document.find(query, cursor)
            if cursor.isNull():
                break
            selection = QTextEdit.ExtraSelection()
            selection.cursor = cursor
            selection.format = highlight
            selections.append(selection)

        return selections

    def _copy_response_body(self) -> None:
        QApplication.clipboard().setText(self.response_raw.toPlainText() or self.response_body.toPlainText())
        self._show_toast(self.t("copy"), "success")

    def _save_response_body(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, self.t("save_response"), "", "JSON (*.json);;Text (*.txt)")
        if not path:
            return
        with open(path, "w", encoding="utf-8") as file:
            file.write(self.response_raw.toPlainText() or self.response_body.toPlainText())
        self._show_toast(self.t("save_response"), "success")

    def _select_call(self, call_id: str) -> None:
        for folder_index in range(self.collection_tree.topLevelItemCount()):
            folder_item = self.collection_tree.topLevelItem(folder_index)
            for child_index in range(folder_item.childCount()):
                item = folder_item.child(child_index)
                metadata = item.data(0, Qt.ItemDataRole.UserRole)
                if isinstance(metadata, dict) and metadata.get("id") == call_id:
                    self.collection_tree.setCurrentItem(item)
                    return

    def _select_folder(self, folder_name: str) -> None:
        for folder_index in range(self.collection_tree.topLevelItemCount()):
            item = self.collection_tree.topLevelItem(folder_index)
            metadata = item.data(0, Qt.ItemDataRole.UserRole)
            if isinstance(metadata, dict) and metadata.get("name") == folder_name:
                self.collection_tree.setCurrentItem(item)
                return

    def _send_current_call(self) -> None:
        selected_call = self._selected_call()
        try:
            call = self._read_call_from_ui(selected_call.id if selected_call else None)
        except ValueError as error:
            QMessageBox.warning(self, self.t("invalid_headers_title"), str(error))
            return

        if not call.url:
            QMessageBox.warning(self, self.t("missing_url_title"), self.t("missing_url_message"))
            return

        self.pending_call = call
        self._set_sending_state(True)
        set_status_badge(self.status_value, self.t("sending"))
        self.time_value.setText("-")
        self.size_value.setText("-")
        self.response_body.clear()
        self.response_raw.clear()
        self.response_headers.clear()

        self.current_worker = HttpWorker(call)
        self.current_worker.finished_ok.connect(self._show_response)
        self.current_worker.failed.connect(self._show_error)
        self.current_worker.finished.connect(lambda: self._set_sending_state(False))
        self.current_worker.start()

    def _set_sending_state(self, sending: bool) -> None:
        self.send_button.setDisabled(sending)
        self.send_button.setText(self.t("sending") if sending else self.t("send"))

    def _show_response(self, response: dict[str, Any]) -> None:
        status = int(response["status"])
        reason = response["reason"]
        set_status_badge(self.status_value, f"{status} {reason}", status)
        self.time_value.setText(f"{response['elapsed_ms']} ms")
        self.size_value.setText(f"{response['size_bytes']} byte")
        self.response_body.setPlainText(self._format_body(str(response["body"])))
        self.response_raw.setPlainText(str(response["body"]))
        self.response_headers.setPlainText(self._headers_to_text(response["headers"]))

        if self.pending_call is not None:
            self._add_history_entry(self.pending_call, response)
            self.pending_call = None

        if 200 <= status < 400:
            self.statusBar().showMessage(self.t("response_saved"), 2500)
            self._show_toast(self.t("response_saved"), "success")
        else:
            self.statusBar().showMessage(self.t("http_error_saved"), 3500)
            self._show_toast(self.t("http_error_saved"), "warning")

    def _show_error(self, error: str) -> None:
        set_status_badge(self.status_value, self.t("network_error"), network_error=True)
        self.time_value.setText("-")
        self.size_value.setText("-")
        self.response_body.setPlainText(error)
        self.response_raw.setPlainText(error)
        self.response_headers.clear()

        if self.pending_call is not None:
            self._add_history_entry(self.pending_call, None, error=error)
            self.pending_call = None

        self.statusBar().showMessage(self.t("request_failed_saved"), 3500)
        self._show_toast(self.t("request_failed_saved"), "error")

    def _show_history_response(self, history_item: CallHistory) -> None:
        if history_item.status is None:
            set_status_badge(self.status_value, self.t("network_error"), network_error=True)
        else:
            set_status_badge(
                self.status_value,
                f"{history_item.status} {history_item.reason}".strip(),
                history_item.status,
            )

        self.time_value.setText("-" if history_item.elapsed_ms is None else f"{history_item.elapsed_ms} ms")
        self.size_value.setText("-" if history_item.size_bytes is None else f"{history_item.size_bytes} byte")

        if history_item.error:
            self.response_body.setPlainText(history_item.error)
            self.response_raw.setPlainText(history_item.error)
            self.response_headers.clear()
        else:
            self.response_body.setPlainText(self._format_body(history_item.response_body))
            self.response_raw.setPlainText(history_item.response_body)
            self.response_headers.setPlainText(self._headers_to_text(history_item.response_headers))

    def _add_history_entry(
        self,
        call: RestCall,
        response: dict[str, Any] | None,
        error: str = "",
    ) -> None:
        history_item = CallHistory(
            timestamp=datetime.now().astimezone().isoformat(timespec="seconds"),
            name=call.name,
            method=call.method,
            url=call.url,
            request_headers=dict(call.headers),
            request_query_params=dict(call.query_params),
            request_body=call.body,
            request_body_type=call.body_type,
            status=int(response["status"]) if response else None,
            reason=str(response["reason"]) if response else "",
            response_headers=dict(response["headers"]) if response else {},
            response_body=str(response["body"]) if response else "",
            elapsed_ms=response["elapsed_ms"] if response else None,
            size_bytes=response["size_bytes"] if response else None,
            error=error,
        )
        self.history.insert(0, history_item)
        self.history = self.history[:HISTORY_LIMIT]
        save_history(self.history)
        self._populate_history_list()
        self.sidebar_tabs.setCurrentIndex(1)
        self.history_list.setCurrentRow(0)

    @staticmethod
    def _headers_to_text(headers: dict[str, str]) -> str:
        return "\n".join(f"{key}: {value}" for key, value in headers.items())

    @staticmethod
    def _format_body(body: str) -> str:
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError:
            return body
        return json.dumps(parsed, indent=2, ensure_ascii=False)

    @staticmethod
    def _format_timestamp(value: str) -> str:
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return value
        return parsed.strftime("%d/%m %H:%M")

    @staticmethod
    def _history_status_colors(status: int | None) -> tuple[str, str]:
        if status is None:
            return "#b42318", "#fff1f0"
        if 200 <= status < 300:
            return "#027a48", "#ecfdf3"
        if 300 <= status < 400:
            return "#175cd3", "#eff8ff"
        if 400 <= status < 500:
            return "#b54708", "#fffaeb"
        if status >= 500:
            return "#b42318", "#fff1f0"
        return "#475467", "#f8fafc"

    @staticmethod
    def _method_color(method: str) -> str:
        colors = {
            "GET": "#027a48",
            "POST": "#175cd3",
            "PUT": "#b54708",
            "PATCH": "#7a2e0e",
            "DELETE": "#b42318",
        }
        return colors.get(method.upper(), "#475467")
