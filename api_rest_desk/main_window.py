from __future__ import annotations

import json
import re
import shlex
from dataclasses import asdict
from datetime import datetime
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QBrush, QColor, QFont, QTextCharFormat, QTextCursor
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
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
    QSpinBox,
    QStackedWidget,
    QStatusBar,
    QTabWidget,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from api_rest_desk.config import APP_NAME, APP_VERSION, DEFAULT_COLLECTION, HISTORY_LIMIT, HTTP_METHODS, AUTHOR
from api_rest_desk.exceptions import (
    AssertionAPIError,
    CurlParseError,
    HeaderParseError,
    ImportExportError,
    OpenApiParseError,
)
from api_rest_desk.i18n import Translator
from api_rest_desk.models import CallHistory, RestCall, Workflow
from api_rest_desk.settings import load_settings, save_settings
from api_rest_desk.storage import (
    StorageError,
    load_collection,
    load_folders,
    load_history,
    load_session_cookies,
    load_workflows,
    save_collection,
    save_folders,
    save_history,
    save_session_cookies,
    save_workflows,
)
from api_rest_desk.widgets import AuthEditor, HeaderEditor, KeyValueEditor
from api_rest_desk.theme import PALETTE, apply_theme, set_status_badge
from api_rest_desk.toast import ToastNotification
from api_rest_desk.settings_dialog import SettingsDialog
from api_rest_desk.workflow import WorkflowRunner
from api_rest_desk.workflow_dialog import WorkflowDialog
from api_rest_desk.workers import HttpWorker
from api_rest_desk.http_client import RestClient


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
        self.session_cookies: dict[str, str] = self._read_session_cookies()
        self.current_worker: HttpWorker | None = None
        self.pending_call: RestCall | None = None
        self.toast: ToastNotification | None = None
        self._workflow_dialog: WorkflowDialog | None = None

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
        self._sync_sidebar_state()

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
        self.collection_search.textChanged.connect(self._filter_active_sidebar)
        sidebar_layout.addWidget(self.collection_search)
        self.collection_tree = QTreeWidget()
        self.collection_tree.setHeaderHidden(True)
        self.collection_tree.currentItemChanged.connect(self._load_selected_call)
        self.collection_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.collection_tree.customContextMenuRequested.connect(self._show_tree_context_menu)
        self.history_list = QListWidget()
        self.history_list.currentItemChanged.connect(self._load_selected_history)
        self.sidebar_tabs.addTab(self.collection_tree, "")
        self.sidebar_tabs.addTab(self.history_list, "")
        self.sidebar_tabs.currentChanged.connect(self._sync_sidebar_state)
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
        self.url_input.setMinimumWidth(300)
        self.sync_url_params_button = QPushButton()
        self.sync_url_params_button.clicked.connect(self._sync_params_from_url)
        self.send_button = QPushButton()
        self.send_button.setObjectName("Primary")
        self.send_button.clicked.connect(self._send_current_call)
        request_row.addWidget(self.method_combo)
        request_row.addWidget(self.url_input, 1)
        request_layout.addLayout(request_row)

        self.timeout_label = QLabel()
        self.timeout_spin = QDoubleSpinBox()
        self.timeout_spin.setRange(0.1, 600.0)
        self.timeout_spin.setDecimals(1)
        self.timeout_spin.setSingleStep(1.0)
        self.timeout_spin.setValue(30.0)
        self.follow_redirects_check = QCheckBox()
        self.follow_redirects_check.setChecked(True)
        self.retry_count_label = QLabel()
        self.retry_count_spin = QSpinBox()
        self.verify_rest_call = QCheckBox()
        self.verify_rest_call.setChecked(True)
        self.retry_count_spin.setRange(0, 10)
        self.retry_statuses_label = QLabel()
        self.retry_statuses_input = QLineEdit("429,500,502,503,504")
        self.use_session_cookies_check = QCheckBox()

        request_tabs = QTabWidget()
        self.headers_editor = HeaderEditor()
        self.auth_editor = AuthEditor()
        self.params_editor = KeyValueEditor()
        self.body_editor = QPlainTextEdit()
        self.body_editor.setPlaceholderText('{\n  "name": "Mario"\n}')
        self.form_body_editor = KeyValueEditor()
        self.body_type_combo = QComboBox()
        self.body_type_combo.addItem("Raw", "raw")
        self.body_type_combo.addItem("JSON", "json")
        self.body_type_combo.addItem("Form URL Encoded", "form")
        self.body_type_combo.setFixedWidth(190)
        self.body_type_combo.currentIndexChanged.connect(self._sync_body_editor)
        self.format_json_button = QPushButton()
        self.format_json_button.setObjectName("Secondary")
        self.format_json_button.clicked.connect(self._format_request_json)

        request_actions_row = QHBoxLayout()
        request_actions_row.addWidget(self.body_type_combo)
        request_actions_row.addStretch(1)
        request_actions_row.addWidget(self.sync_url_params_button)
        request_actions_row.addWidget(self.send_button)
        request_layout.addLayout(request_actions_row)

        self.body_stack = QStackedWidget()
        self.body_stack.addWidget(self.body_editor)
        self.body_stack.addWidget(self.form_body_editor)
        body_tab = QWidget()
        self.body_tab = body_tab
        body_tab_layout = QVBoxLayout(body_tab)
        body_tab_layout.setContentsMargins(0, 0, 0, 0)
        body_tab_layout.setSpacing(8)
        self.body_format_bar = QWidget()
        body_format_layout = QHBoxLayout(self.body_format_bar)
        body_format_layout.setContentsMargins(0, 0, 0, 0)
        body_format_layout.addStretch(1)
        body_format_layout.addWidget(self.format_json_button)
        body_tab_layout.addWidget(self.body_format_bar)
        body_tab_layout.addWidget(self.body_stack)

        options_tab = QWidget()
        options_layout = QFormLayout(options_tab)
        options_layout.setContentsMargins(0, 0, 0, 0)
        options_layout.setSpacing(10)
        options_layout.addRow(self.timeout_label, self.timeout_spin)
        options_layout.addRow("", self.follow_redirects_check)
        options_layout.addRow("", self.use_session_cookies_check)
        options_layout.addRow(self.retry_count_label, self.retry_count_spin)
        options_layout.addRow("", self.verify_rest_call)
        options_layout.addRow(self.retry_statuses_label, self.retry_statuses_input)

        self.assertions_editor = QPlainTextEdit()
        self.assertions_editor.setPlaceholderText("status == 200\njson token exists\ntime < 1000")
        tests_tab = QWidget()
        tests_layout = QVBoxLayout(tests_tab)
        tests_layout.setContentsMargins(0, 0, 0, 0)
        tests_layout.addWidget(self.assertions_editor)

        self.request_tabs = request_tabs
        request_tabs.currentChanged.connect(self._sync_body_editor)
        request_tabs.addTab(self.headers_editor, "")
        request_tabs.addTab(self.auth_editor, "")
        request_tabs.addTab(self.params_editor, "")
        request_tabs.addTab(body_tab, "")
        request_tabs.addTab(options_tab, "")
        request_tabs.addTab(tests_tab, "")
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
        self.copy_json_path_button = QPushButton()
        self.copy_response_button.clicked.connect(self._copy_response_body)
        self.save_response_button.clicked.connect(self._save_response_body)
        self.copy_json_path_button.clicked.connect(self._copy_selected_json_path)
        response_top.addWidget(self.response_search)
        response_top.addWidget(self.copy_json_path_button)
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
        self.response_tests = QPlainTextEdit()
        self.response_tests.setReadOnly(True)
        self.response_json_tree = QTreeWidget()
        self.response_json_tree.setHeaderLabels(("Path", "Value"))
        self.response_tabs = response_tabs
        response_tabs.addTab(self.response_body, "")
        response_tabs.addTab(self.response_raw, "")
        response_tabs.addTab(self.response_headers, "")
        response_tabs.addTab(self.response_json_tree, "")
        response_tabs.addTab(self.response_tests, "")
        response_card_layout.addWidget(response_tabs, 1)
        response_layout.addWidget(response_card, 1)

        root_splitter.addWidget(sidebar)
        root_splitter.addWidget(editor)
        root_splitter.addWidget(response)
        root_splitter.setSizes([290, 620, 380])
        root_splitter.setStretchFactor(0, 0)
        root_splitter.setStretchFactor(1, 2)
        root_splitter.setStretchFactor(2, 1)

        self.setStatusBar(QStatusBar())
        self._build_menu()

        monospace = QFont("Consolas")
        monospace.setStyleHint(QFont.StyleHint.Monospace)

        for editor_widget in (
            self.body_editor,
            self.assertions_editor,
            self.response_body,
            self.response_raw,
            self.response_headers,
            self.response_tests,
        ):
            editor_widget.setFont(monospace)
            editor_widget.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

        self.response_json_tree.header().setStretchLastSection(True)

    def _build_menu(self) -> None:
        self.collection_menu = self.menuBar().addMenu("")

        self.new_action = QAction(self)
        self.new_action.triggered.connect(self._new_call)
        self.collection_menu.addAction(self.new_action)

        self.new_folder_action = QAction(self)
        self.new_folder_action.triggered.connect(self._new_folder)
        self.collection_menu.addAction(self.new_folder_action)

        self.rename_folder_action = QAction(self)
        self.rename_folder_action.triggered.connect(self._rename_folder_via_menu)
        self.collection_menu.addAction(self.rename_folder_action)

        self.save_action = QAction(self)
        self.save_action.triggered.connect(self._save_current_call)
        self.collection_menu.addAction(self.save_action)

        self.import_workspace_action = QAction(self)
        self.import_workspace_action.triggered.connect(self._import_workspace)
        self.collection_menu.addAction(self.import_workspace_action)

        self.export_workspace_action = QAction(self)
        self.export_workspace_action.triggered.connect(self._export_workspace)
        self.collection_menu.addAction(self.export_workspace_action)

        self.import_openapi_action = QAction(self)
        self.import_openapi_action.triggered.connect(self._import_openapi)
        self.collection_menu.addAction(self.import_openapi_action)

        self.import_curl_action = QAction(self)
        self.import_curl_action.triggered.connect(self._import_curl)
        self.collection_menu.addAction(self.import_curl_action)

        self.copy_curl_action = QAction(self)
        self.copy_curl_action.triggered.connect(self._copy_curl)
        self.collection_menu.addAction(self.copy_curl_action)

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

        self.clear_cookies_action = QAction(self)
        self.clear_cookies_action.triggered.connect(self._clear_session_cookies)
        self.settings_menu.addAction(self.clear_cookies_action)

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
        self.sync_url_params_button.setText(self.t("sync_params"))
        self.send_button.setText(self.t("send"))
        self.timeout_label.setText(self.t("timeout"))
        self.follow_redirects_check.setText(self.t("follow_redirects"))
        self.use_session_cookies_check.setText(self.t("use_session_cookies"))
        self.verify_rest_call.setText(self.t("verify_rest_call"))
        self.retry_count_label.setText(self.t("retry_count"))
        self.retry_statuses_label.setText(self.t("retry_statuses"))
        self.retry_statuses_input.setPlaceholderText(self.t("retry_statuses"))
        self.assertions_editor.setPlaceholderText(self.t("assertions_placeholder"))
        self.request_tabs.setTabText(0, self.t("headers"))
        self.request_tabs.setTabText(1, self.t("auth"))
        self.request_tabs.setTabText(2, self.t("params"))
        self.request_tabs.setTabText(3, self.t("body"))
        self.request_tabs.setTabText(4, self.t("request_options"))
        self.request_tabs.setTabText(5, self.t("tests"))
        self.format_json_button.setText(self.t("format_json"))
        self.body_type_combo.setItemText(0, self.t("raw"))
        self.body_type_combo.setItemText(1, "JSON")
        self.body_type_combo.setItemText(2, self.t("form_urlencoded"))
        self.response_title.setText(self.t("response"))
        self.response_search.setPlaceholderText(self.t("find"))
        self.copy_json_path_button.setText(self.t("copy_path"))
        self.copy_response_button.setText(self.t("copy"))
        self.save_response_button.setText(self.t("save_response"))
        self.status_label.setText(self.t("status"))
        self.time_label.setText(self.t("time"))
        self.size_label.setText(self.t("size"))
        self.response_tabs.setTabText(0, self.t("pretty"))
        self.response_tabs.setTabText(1, self.t("raw"))
        self.response_tabs.setTabText(2, self.t("headers"))
        self.response_tabs.setTabText(3, self.t("json_tree"))
        self.response_tabs.setTabText(4, self.t("tests"))
        self.collection_menu.setTitle(self.t("collection_menu"))
        self.new_action.setText(self.t("new_call"))
        self.new_folder_action.setText(self.t("new_folder"))
        self.rename_folder_action.setText(self.t("rename_folder"))
        self.save_action.setText(self.t("save_call"))
        self.import_workspace_action.setText(self.t("import_workspace"))
        self.export_workspace_action.setText(self.t("export_workspace"))
        self.import_openapi_action.setText(self.t("import_openapi"))
        self.import_curl_action.setText(self.t("import_curl"))
        self.copy_curl_action.setText(self.t("copy_curl"))
        self.send_action.setText(self.t("send"))
        self.history_menu.setTitle(self.t("history_menu"))
        self.reopen_action.setText(self.t("reopen_selected"))
        self.clear_action.setText(self.t("clear_history"))
        self.workflow_menu.setTitle(self.t("workflow_menu"))
        self.open_workflow_action.setText(self.t("open_composer"))
        self.settings_menu.setTitle(self.t("settings"))
        self.settings_action.setText(self.t("settings"))
        self.clear_cookies_action.setText(self.t("clear_session_cookies"))
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

    def _sync_sidebar_state(self) -> None:
        self._sync_sidebar_action_state()
        self._filter_active_sidebar()

    def _sync_sidebar_action_state(self) -> None:
        collection_active = self.sidebar_tabs.currentIndex() == 0
        for button in (
            self.new_button,
            self.new_folder_button,
            self.duplicate_button,
            self.delete_button,
        ):
            button.setEnabled(collection_active)

        for action_name in ("new_action", "new_folder_action"):
            action = getattr(self, action_name, None)
            if action is not None:
                action.setEnabled(collection_active)

    def _filter_active_sidebar(self) -> None:
        if self.sidebar_tabs.currentIndex() == 1:
            self._filter_history_list()
            return
        self._filter_collection_tree()

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

    def _read_session_cookies(self) -> dict[str, str]:
        try:
            return load_session_cookies()
        except StorageError as error:
            QMessageBox.warning(self, self.t("session_cookies"), str(error))
            return {}

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
        self._filter_history_list()

    def _filter_history_list(self) -> None:
        query = self.collection_search.text().strip().lower() if hasattr(self, "collection_search") else ""
        for row in range(self.history_list.count()):
            item = self.history_list.item(row)
            history_id = item.data(Qt.ItemDataRole.UserRole)
            history_item = next((entry for entry in self.history if entry.id == history_id), None)
            haystack = item.text()
            if history_item is not None:
                haystack = "\n".join(
                    (
                        haystack,
                        history_item.name,
                        history_item.method,
                        history_item.url,
                        str(history_item.status or ""),
                        history_item.reason,
                        history_item.request_body,
                        history_item.response_body,
                        history_item.error,
                    )
                )
            item.setHidden(bool(query) and query not in haystack.lower())

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
        self.timeout_spin.setValue(float(call.timeout))
        self.follow_redirects_check.setChecked(bool(call.follow_redirects))
        self.verify_rest_call.setChecked(bool(call.verify))
        self.retry_count_spin.setValue(int(call.retry_count))
        self.retry_statuses_input.setText(call.retry_statuses)
        self.use_session_cookies_check.setChecked(bool(call.use_session_cookies))
        self.assertions_editor.setPlainText(call.assertions)

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
        self.timeout_spin.setValue(float(history_item.request_timeout))
        self.follow_redirects_check.setChecked(bool(history_item.request_follow_redirects))
        self.retry_count_spin.setValue(int(history_item.request_retry_count))
        self.retry_statuses_input.setText(history_item.request_retry_statuses)
        self.use_session_cookies_check.setChecked(bool(history_item.request_use_session_cookies))
        self.assertions_editor.setPlainText(history_item.request_assertions)
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
            verify=self.verify_rest_call.isChecked(),
            timeout=float(self.timeout_spin.value()),
            follow_redirects=self.follow_redirects_check.isChecked(),
            retry_count=int(self.retry_count_spin.value()),
            retry_statuses=self.retry_statuses_input.text().strip() or "429,500,502,503,504",
            use_session_cookies=self.use_session_cookies_check.isChecked(),
            assertions=self.assertions_editor.toPlainText(),
        )
        self.auth_editor.apply_to_call(call)
        if call_id:
            call.id = call_id
        return call

    def _save_current_call(self) -> None:
        call = self._selected_call()
        try:
            updated_call = self._read_call_from_ui(call.id if call else None)
        except HeaderParseError as error:
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
        self._notify_workflow_calls_changed()
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
        self._notify_workflow_calls_changed()
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

    def _show_tree_context_menu(self, position) -> None:
        """Show a right-click context menu on the collection tree."""
        item = self.collection_tree.itemAt(position)
        if item is None:
            return

        metadata = item.data(0, Qt.ItemDataRole.UserRole)
        if not isinstance(metadata, dict):
            return

        from PyQt6.QtWidgets import QMenu
        menu = QMenu(self)

        if metadata.get("type") == "folder":
            folder_name = str(metadata.get("name") or "")
            if folder_name != DEFAULT_COLLECTION:
                rename_action = menu.addAction(self.t("rename_folder"))
                delete_action = menu.addAction(self.t("delete"))
                chosen = menu.exec(self.collection_tree.viewport().mapToGlobal(position))
                if chosen == rename_action:
                    self._rename_folder_dialog(folder_name)
                elif chosen == delete_action:
                    self.collection_tree.setCurrentItem(item)
                    self._delete_call()
        elif metadata.get("type") == "call":
            self.collection_tree.setCurrentItem(item)
            duplicate_action = menu.addAction(self.t("duplicate"))
            delete_action = menu.addAction(self.t("delete"))
            chosen = menu.exec(self.collection_tree.viewport().mapToGlobal(position))
            if chosen == duplicate_action:
                self._duplicate_call()
            elif chosen == delete_action:
                self._delete_call()

    def _rename_folder_via_menu(self) -> None:
        """Rename the currently selected folder from the menu bar action."""
        item = self.collection_tree.currentItem()
        if item is None:
            return
        metadata = item.data(0, Qt.ItemDataRole.UserRole)
        if not isinstance(metadata, dict) or metadata.get("type") != "folder":
            return
        old_name = str(metadata.get("name") or "")
        if old_name == DEFAULT_COLLECTION:
            return
        self._rename_folder_dialog(old_name)

    def _rename_folder_dialog(self, old_name: str) -> None:
        """Show a dialog to rename a folder."""
        new_name, accepted = QInputDialog.getText(
            self, self.t("rename_folder"), self.t("new_folder_label"), text=old_name
        )
        new_name = new_name.strip()
        if not accepted or not new_name or new_name == old_name:
            return
        if new_name in self._collection_names():
            QMessageBox.information(self, self.t("existing_folder_title"), self.t("existing_folder_message"))
            return
        self._apply_folder_rename(old_name, new_name)

    def _apply_folder_rename(self, old_name: str, new_name: str) -> None:
        """Rename a folder, updating all calls and persisting the change."""
        # Update folder list
        self.folders = [new_name if f == old_name else f for f in self.folders]
        save_folders(self.folders)
        # Update all calls belonging to the old folder
        for call in self.calls:
            if call.collection == old_name:
                call.collection = new_name
        save_collection(self.calls)
        self._notify_workflow_calls_changed()
        self._populate_call_list()
        self._select_folder(new_name)

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
            timeout=call.timeout,
            follow_redirects=call.follow_redirects,
            retry_count=call.retry_count,
            retry_statuses=call.retry_statuses,
            use_session_cookies=call.use_session_cookies,
            assertions=call.assertions,
        )
        if duplicated.collection not in self.folders:
            self.folders.append(duplicated.collection)
            save_folders(self.folders)
        self.calls.append(duplicated)
        save_collection(self.calls)
        self._notify_workflow_calls_changed()
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
            self._notify_workflow_calls_changed()
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
        self._notify_workflow_calls_changed()
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
        if self._workflow_dialog is not None and self._workflow_dialog.isVisible():
            self._workflow_dialog.raise_()
            self._workflow_dialog.activateWindow()
            return
        dialog = WorkflowDialog(self.calls, self.translator, self)
        dialog.navigate_to_call.connect(self._navigate_to_call_from_workflow)
        dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        dialog.destroyed.connect(self._on_workflow_dialog_closed)
        self._workflow_dialog = dialog
        dialog.show()

    def _on_workflow_dialog_closed(self) -> None:
        self._workflow_dialog = None

    def _navigate_to_call_from_workflow(self, call_id: str) -> None:
        """Bring main window to front and select the call from a workflow step."""
        self.raise_()
        self.activateWindow()
        self.sidebar_tabs.setCurrentIndex(0)
        self._select_call(call_id)

    def _notify_workflow_calls_changed(self) -> None:
        """Refresh the calls list in the open workflow dialog, if any."""
        if self._workflow_dialog is not None and self._workflow_dialog.isVisible():
            self._workflow_dialog.refresh_calls(self.calls)

    def _open_settings_dialog(self) -> None:
        dialog = SettingsDialog(self.translator, self)
        if not dialog.exec():
            return

        self.translator.set_language(str(dialog.selected_settings().get("language") or "it"))
        self._apply_style()
        self.retranslate_ui()
        self.statusBar().showMessage(self.t("settings_saved"), 2500)
        self._show_toast(self.t("settings_saved"), "success")

    def _export_workspace(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            self.t("export_workspace"),
            "api_rest_desk_workspace.json",
            "JSON (*.json)",
        )
        if not path:
            return

        payload = {
            "app": APP_NAME,
            "version": APP_VERSION,
            "collection": [asdict(call) for call in self.calls],
            "folders": list(self.folders),
            "history": [asdict(item) for item in self.history],
            "workflows": [asdict(workflow) for workflow in load_workflows()],
            "settings": load_settings(),
            "session_cookies": dict(self.session_cookies),
        }
        with open(path, "w", encoding="utf-8") as file:
            json.dump(payload, file, indent=2, ensure_ascii=False)
        self.statusBar().showMessage(self.t("workspace_exported"), 2500)
        self._show_toast(self.t("workspace_exported"), "success")

    def _import_workspace(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, self.t("import_workspace"), "", "JSON (*.json)")
        if not path:
            return

        try:
            with open(path, "r", encoding="utf-8") as file:
                payload = json.load(file)
            if not isinstance(payload, dict):
                raise ImportExportError("import_root_not_object")
            
            calls = [RestCall.from_dict(item) for item in payload.get("collection", []) if isinstance(item, dict)]
            folders = [str(item) for item in payload.get("folders", []) if str(item).strip()]
            history = [CallHistory.from_dict(item) for item in payload.get("history", []) if isinstance(item, dict)]
            workflows = [Workflow.from_dict(item) for item in payload.get("workflows", []) if isinstance(item, dict)]
            settings = payload.get("settings") if isinstance(payload.get("settings"), dict) else None
            session_cookies = (
                {str(key): str(value) for key, value in payload.get("session_cookies", {}).items()}
                if isinstance(payload.get("session_cookies"), dict)
                else None
            )
        except (OSError, json.JSONDecodeError, ImportExportError) as error:
            QMessageBox.warning(self, self.t("workspace_import_error"), str(error))
            return

        self.calls = calls
        self.folders = folders or [DEFAULT_COLLECTION]
        self.history = history[:HISTORY_LIMIT]
        save_collection(self.calls)
        self._notify_workflow_calls_changed()
        save_folders(self.folders)
        save_history(self.history)
        save_workflows(workflows)
        if settings is not None:
            save_settings(settings)
            self.translator.set_language(str(load_settings().get("language") or "it"))
            self._apply_style()
            self.retranslate_ui()
        if session_cookies is not None:
            self.session_cookies = session_cookies
            save_session_cookies(self.session_cookies)
        self._populate_call_list()
        self._populate_history_list()
        if self.calls:
            self._select_call(self.calls[0].id)
        self.statusBar().showMessage(self.t("workspace_imported"), 2500)
        self._show_toast(self.t("workspace_imported"), "success")

    def _import_openapi(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, self.t("import_openapi"), "", "JSON (*.json)")
        if not path:
            return

        try:
            with open(path, "r", encoding="utf-8") as file:
                payload = json.load(file)
            calls, folder = self._calls_from_openapi(payload)
        except (OSError, json.JSONDecodeError, OpenApiParseError) as error:
            return

        if not calls:
            QMessageBox.information(self, self.t("import_openapi"), self.t("openapi_no_operations"))
            return

        if folder not in self.folders:
            self.folders.append(folder)
            save_folders(self.folders)
        self.calls.extend(calls)
        save_collection(self.calls)
        self._notify_workflow_calls_changed()
        self._populate_call_list()
        self._select_call(calls[0].id)
        self.sidebar_tabs.setCurrentIndex(0)
        message = self.t("openapi_imported", count=len(calls))
        self.statusBar().showMessage(message, 3000)
        self._show_toast(message, "success")

    def _clear_session_cookies(self) -> None:
        self.session_cookies = {}
        save_session_cookies(self.session_cookies)
        self.statusBar().showMessage(self.t("session_cookies_cleared"), 2500)
        self._show_toast(self.t("session_cookies_cleared"), "success")

    def _show_about_dialog(self) -> None:
        QMessageBox.about(
            self,
            self.t("about"),
            f"{APP_NAME} by {AUTHOR}\n{self.t('version')}: {APP_VERSION}",
        )

    def _show_toast(self, message: str, kind: str = "info") -> None:
        if self.toast is not None:
            self.toast.show_message(message, kind)

    def _sync_params_from_url(self) -> None:
        parsed = urlsplit(self.url_input.text().strip())
        query_values = dict(parse_qsl(parsed.query, keep_blank_values=True))
        if not query_values:
            return

        merged = self.params_editor.values()
        merged.update(query_values)
        self.params_editor.set_values(merged)
        clean_url = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", parsed.fragment))
        self.url_input.setText(clean_url)
        self.request_tabs.setCurrentWidget(self.params_editor)

    def _import_curl(self) -> None:
        text, accepted = QInputDialog.getMultiLineText(
            self,
            self.t("curl_import_title"),
            self.t("curl_import_label"),
        )
        if not accepted or not text.strip():
            return

        try:
            call = self._call_from_curl(text)
        except CurlParseError as error:
            QMessageBox.warning(self, self.t("curl_import_error"), str(error))
            return

        call.collection = self._selected_collection_name()
        self._apply_call_to_editor(call)
        self.statusBar().showMessage(self.t("curl_imported"), 2500)
        self._show_toast(self.t("curl_imported"), "success")

    def _copy_curl(self) -> None:
        try:
            call = self._read_call_from_ui(self._selected_call().id if self._selected_call() else None)
        except HeaderParseError as error:
            QMessageBox.warning(self, self.t("invalid_headers_title"), str(error))
            return

        QApplication.clipboard().setText(self._curl_from_call(call))
        self.statusBar().showMessage(self.t("curl_copied"), 2500)
        self._show_toast(self.t("curl_copied"), "success")

    def _apply_call_to_editor(self, call: RestCall) -> None:
        self.name_input.setText(call.name)
        self.method_combo.setCurrentText(call.method if call.method in HTTP_METHODS else "GET")
        self.url_input.setText(call.url)
        self.headers_editor.set_headers(call.headers)
        self.auth_editor.set_auth(call)
        self.params_editor.set_values(call.query_params)
        self._set_body_type(call.body_type, call.headers)
        self._set_request_body(call.body, str(self.body_type_combo.currentData() or "raw"))
        self.timeout_spin.setValue(float(call.timeout))
        self.follow_redirects_check.setChecked(bool(call.follow_redirects))
        self.retry_count_spin.setValue(int(call.retry_count))
        self.retry_statuses_input.setText(call.retry_statuses)

    @classmethod
    def _call_from_curl(cls, curl_text: str) -> RestCall:
        normalized = (
            curl_text.strip()
            .replace("\\\r\n", " ")
            .replace("\\\n", " ")
            .replace("^\r\n", " ")
            .replace("^\n", " ")
        )
        try:
            tokens = shlex.split(normalized, posix=True)
        except ValueError as error:
            raise CurlParseError("curl_parse_failed", detail=str(error)) from error

        if tokens and tokens[0].lower() == "curl":
            tokens = tokens[1:]

        method = ""
        url = ""
        headers: dict[str, str] = {}
        body_parts: list[str] = []
        follow_redirects = False
        timeout = 30.0
        auth_user = ""
        auth_password = ""
        index = 0

        while index < len(tokens):
            token = tokens[index]
            option, inline_value = cls._split_curl_option(token)

            if option in {"-X", "--request"}:
                value, index = cls._curl_option_value(tokens, index, inline_value, option)
                method = value.upper()
            elif option in {"--url"}:
                url, index = cls._curl_option_value(tokens, index, inline_value, option)
            elif option in {"-H", "--header"}:
                value, index = cls._curl_option_value(tokens, index, inline_value, option)
                if ":" in value:
                    key, header_value = value.split(":", 1)
                    headers[key.strip()] = header_value.strip()
            elif option in {"-d", "--data", "--data-raw", "--data-binary", "--data-urlencode"}:
                value, index = cls._curl_option_value(tokens, index, inline_value, option)
                body_parts.append(value)
            elif option in {"-u", "--user"}:
                value, index = cls._curl_option_value(tokens, index, inline_value, option)
                auth_user, _, auth_password = value.partition(":")
            elif option in {"-L", "--location"}:
                follow_redirects = True
            elif option in {"--max-time", "--connect-timeout"}:
                value, index = cls._curl_option_value(tokens, index, inline_value, option)
                try:
                    timeout = max(0.1, float(value))
                except ValueError:
                    timeout = 30.0
            elif not token.startswith("-") and not url:
                url = token

            index += 1

        if not url:
            raise CurlParseError("curl_no_url")

        body = "&".join(body_parts)
        if not method:
            method = "POST" if body else "GET"

        body_type = cls._body_type_from_headers(headers)
        if body and body_type == "raw" and cls._looks_like_form_body(body):
            body_type = "form"
            headers.setdefault("Content-Type", "application/x-www-form-urlencoded")

        parsed_url = urlsplit(url)
        query_params = dict(parse_qsl(parsed_url.query, keep_blank_values=True))
        clean_url = urlunsplit((parsed_url.scheme, parsed_url.netloc, parsed_url.path, "", parsed_url.fragment))
        name = parsed_url.netloc or "cURL import"
        if parsed_url.path and parsed_url.path != "/":
            name = parsed_url.path.rstrip("/").split("/")[-1] or name

        call = RestCall(
            name=name,
            method=method,
            url=clean_url,
            headers=headers,
            query_params=query_params,
            body=body,
            body_type=body_type,
            timeout=timeout,
            follow_redirects=follow_redirects,
        )
        if auth_user or auth_password:
            call.auth_type = "basic"
            call.auth_username = auth_user
            call.auth_password = auth_password
        return call

    @classmethod
    def _calls_from_openapi(cls, payload: dict[str, Any]) -> tuple[list[RestCall], str]:
        if not isinstance(payload, dict):
            raise OpenApiParseError("openapi_root_not_object")

        info = payload.get("info") if isinstance(payload.get("info"), dict) else {}
        title = str(info.get("title") or "OpenAPI")
        folder = f"OpenAPI - {title}"
        base_url = cls._openapi_base_url(payload)
        paths = payload.get("paths")
        if not isinstance(paths, dict):
            raise OpenApiParseError("openapi_no_paths")

        calls: list[RestCall] = []
        for route, path_item in paths.items():
            if not isinstance(path_item, dict):
                continue
            path_parameters = path_item.get("parameters") if isinstance(path_item.get("parameters"), list) else []
            for method, operation in path_item.items():
                method_upper = str(method).upper()
                if method_upper not in HTTP_METHODS or not isinstance(operation, dict):
                    continue

                parameters = [
                    item
                    for item in [*path_parameters, *(operation.get("parameters") or [])]
                    if isinstance(item, dict)
                ]
                query_params = cls._openapi_params(parameters, "query")
                headers = {"Accept": "application/json"}
                headers.update(cls._openapi_params(parameters, "header"))
                body, body_type, body_headers = cls._openapi_body(operation)
                headers.update(body_headers)
                operation_id = operation.get("operationId")
                summary = operation.get("summary")
                name = str(operation_id or summary or f"{method_upper} {route}")
                calls.append(
                    RestCall(
                        name=name,
                        method=method_upper,
                        url=base_url.rstrip("/") + "/" + str(route).lstrip("/"),
                        collection=folder,
                        headers=headers,
                        query_params=query_params,
                        body=body,
                        body_type=body_type,
                    )
                )
        return calls, folder

    @staticmethod
    def _openapi_base_url(payload: dict[str, Any]) -> str:
        servers = payload.get("servers")
        if isinstance(servers, list) and servers and isinstance(servers[0], dict):
            url = str(servers[0].get("url") or "")
            variables = servers[0].get("variables")
            if isinstance(variables, dict):
                for name, metadata in variables.items():
                    default = ""
                    if isinstance(metadata, dict):
                        default = str(metadata.get("default") or "")
                    url = url.replace("{" + str(name) + "}", default)
            return url or "https://"

        schemes = payload.get("schemes") if isinstance(payload.get("schemes"), list) else ["https"]
        scheme = str(schemes[0] if schemes else "https")
        host = str(payload.get("host") or "")
        base_path = str(payload.get("basePath") or "")
        return f"{scheme}://{host}{base_path}" if host else "https://"

    @classmethod
    def _openapi_params(cls, parameters: list[dict[str, Any]], location: str) -> dict[str, str]:
        values: dict[str, str] = {}
        for parameter in parameters:
            if parameter.get("in") != location:
                continue
            name = str(parameter.get("name") or "").strip()
            if not name:
                continue
            value = parameter.get("example", parameter.get("default", ""))
            schema = parameter.get("schema") if isinstance(parameter.get("schema"), dict) else {}
            if value == "" and schema:
                value = schema.get("example", schema.get("default", ""))
            values[name] = cls._stringify_openapi_value(value)
        return values

    @classmethod
    def _openapi_body(cls, operation: dict[str, Any]) -> tuple[str, str, dict[str, str]]:
        request_body = operation.get("requestBody")
        if not isinstance(request_body, dict):
            return "", "raw", {}

        content = request_body.get("content")
        if not isinstance(content, dict):
            return "", "raw", {}

        json_content = content.get("application/json")
        if isinstance(json_content, dict):
            example = cls._openapi_content_example(json_content)
            return json.dumps(example, indent=2, ensure_ascii=False), "json", {
                "Content-Type": "application/json; charset=utf-8"
            }

        form_content = content.get("application/x-www-form-urlencoded")
        if isinstance(form_content, dict):
            example = cls._openapi_content_example(form_content)
            if isinstance(example, dict):
                return urlencode({str(key): cls._stringify_openapi_value(value) for key, value in example.items()}), "form", {
                    "Content-Type": "application/x-www-form-urlencoded"
                }

        return "", "raw", {}

    @classmethod
    def _openapi_content_example(cls, content: dict[str, Any]) -> Any:
        if "example" in content:
            return content["example"]
        examples = content.get("examples")
        if isinstance(examples, dict) and examples:
            first = next(iter(examples.values()))
            if isinstance(first, dict) and "value" in first:
                return first["value"]
        schema = content.get("schema") if isinstance(content.get("schema"), dict) else {}
        return cls._openapi_schema_example(schema)

    @classmethod
    def _openapi_schema_example(cls, schema: dict[str, Any]) -> Any:
        if "example" in schema:
            return schema["example"]
        if "default" in schema:
            return schema["default"]
        if "enum" in schema and isinstance(schema["enum"], list) and schema["enum"]:
            return schema["enum"][0]
        schema_type = schema.get("type")
        if schema_type == "object" or "properties" in schema:
            properties = schema.get("properties") if isinstance(schema.get("properties"), dict) else {}
            return {str(name): cls._openapi_schema_example(value) for name, value in properties.items() if isinstance(value, dict)}
        if schema_type == "array":
            items = schema.get("items") if isinstance(schema.get("items"), dict) else {}
            return [cls._openapi_schema_example(items)]
        if schema_type in {"integer", "number"}:
            return 0
        if schema_type == "boolean":
            return False
        return ""

    @staticmethod
    def _stringify_openapi_value(value: Any) -> str:
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False)
        return "" if value is None else str(value)

    @staticmethod
    def _split_curl_option(token: str) -> tuple[str, str | None]:
        if token.startswith("--") and "=" in token:
            option, value = token.split("=", 1)
            return option, value
        return token, None

    @staticmethod
    def _curl_option_value(tokens: list[str], index: int, inline_value: str | None, option: str) -> tuple[str, int]:
        if inline_value is not None:
            return inline_value, index
        if index + 1 >= len(tokens):
            raise CurlParseError("curl_option_no_value", option=option)
        return tokens[index + 1], index + 1

    @staticmethod
    def _looks_like_form_body(body: str) -> bool:
        return "=" in body and bool(parse_qsl(body, keep_blank_values=True))

    def _curl_from_call(self, call: RestCall) -> str:
        headers, params = self._request_parts_for_export(call)
        parts = ["curl", "-X", call.method, self._quote_shell(self._url_with_query(call.url, params))]
        for key, value in headers.items():
            parts.extend(["-H", self._quote_shell(f"{key}: {value}")])
        if call.auth_type == "basic" and (call.auth_username or call.auth_password):
            parts.extend(["-u", self._quote_shell(f"{call.auth_username}:{call.auth_password}")])
        if call.follow_redirects:
            parts.append("-L")
        if call.timeout != 30.0:
            parts.extend(["--max-time", str(call.timeout)])
        if call.method not in {"GET", "DELETE"} and call.body.strip():
            parts.extend(["--data-raw", self._quote_shell(call.body)])
        return " \\\n  ".join(parts)

    @staticmethod
    def _request_parts_for_export(call: RestCall) -> tuple[dict[str, str], dict[str, str]]:
        headers = dict(call.headers)
        params = dict(call.query_params)
        if call.auth_type == "bearer" and call.auth_token:
            headers["Authorization"] = f"Bearer {call.auth_token}"
        elif call.auth_type == "api_key" and call.auth_key_name and call.auth_key_value:
            if call.auth_key_location == "query":
                params[call.auth_key_name] = call.auth_key_value
            else:
                headers[call.auth_key_name] = call.auth_key_value
        return headers, params

    @staticmethod
    def _url_with_query(url: str, params: dict[str, str]) -> str:
        if not params:
            return url
        parsed = urlsplit(url)
        query = dict(parse_qsl(parsed.query, keep_blank_values=True))
        query.update(params)
        return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(query), parsed.fragment))

    @staticmethod
    def _quote_shell(value: str) -> str:
        return "'" + value.replace("'", "'\"'\"'") + "'"

    @staticmethod
    def _environment_vars() -> dict[str, Any]:
        environment = load_settings().get("environment")
        if not isinstance(environment, dict):
            return {}
        return {str(key): value for key, value in environment.items()}

    def _render_call_for_send(self, call: RestCall) -> RestCall:
        return WorkflowRunner()._render_call(call, self._environment_vars())

    def _sync_body_editor(self) -> None:
        body_type = str(self.body_type_combo.currentData() or "raw")
        is_form = body_type == "form"
        self.body_stack.setCurrentIndex(1 if is_form else 0)
        show_format = body_type == "json" and getattr(self, "request_tabs", None) is not None
        show_format = show_format and self.request_tabs.currentWidget() is getattr(self, "body_tab", None)
        self.body_format_bar.setVisible(show_format)
        self.format_json_button.setEnabled(show_format)

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
        highlight.setBackground(QBrush(QColor(PALETTE["pale_yellow"])))
        highlight.setForeground(QBrush(QColor(PALETTE["near_black"])))

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

    def _copy_selected_json_path(self) -> None:
        item = self.response_json_tree.currentItem()
        if item is None:
            return
        path = str(item.data(0, Qt.ItemDataRole.UserRole) or "")
        if not path:
            return
        QApplication.clipboard().setText(path)
        self._show_toast(self.t("copy_path"), "success")

    def _populate_json_tree(self, body: str) -> None:
        self.response_json_tree.clear()
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            return

        root = QTreeWidgetItem(["$", self._json_tree_value(payload)])
        root.setData(0, Qt.ItemDataRole.UserRole, "")
        self.response_json_tree.addTopLevelItem(root)
        self._add_json_tree_children(root, payload, "")
        root.setExpanded(True)
        self.response_json_tree.resizeColumnToContents(0)

    def _add_json_tree_children(self, parent: QTreeWidgetItem, value: Any, path: str) -> None:
        if isinstance(value, dict):
            for key, child_value in value.items():
                child_path = f"{path}.{key}" if path else str(key)
                item = QTreeWidgetItem([str(key), self._json_tree_value(child_value)])
                item.setData(0, Qt.ItemDataRole.UserRole, child_path)
                parent.addChild(item)
                self._add_json_tree_children(item, child_value, child_path)
        elif isinstance(value, list):
            for index, child_value in enumerate(value):
                child_path = f"{path}[{index}]" if path else f"[{index}]"
                item = QTreeWidgetItem([f"[{index}]", self._json_tree_value(child_value)])
                item.setData(0, Qt.ItemDataRole.UserRole, child_path)
                parent.addChild(item)
                self._add_json_tree_children(item, child_value, child_path)

    @staticmethod
    def _json_tree_value(value: Any) -> str:
        if isinstance(value, (dict, list)):
            return f"{len(value)} item"
        return str(value)

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
        except HeaderParseError as error:
            QMessageBox.warning(self, self.t("invalid_headers_title"), str(error))
            return
        call = self._render_call_for_send(call)

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
        self.response_json_tree.clear()
        self.response_tests.clear()

        client = RestClient(session_cookies=self.session_cookies if call.use_session_cookies else None)
        self.current_worker = HttpWorker(call, client)
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
        self._populate_json_tree(str(response["body"]))

        assertion_results = self._evaluate_assertions(
            self.pending_call.assertions if self.pending_call is not None else "",
            response,
        )
        response["assertion_results"] = assertion_results
        self.response_tests.setPlainText(self._format_assertion_results(assertion_results))

        if self.pending_call is not None:
            if self.pending_call.use_session_cookies:
                self.session_cookies.update({str(k): str(v) for k, v in response.get("cookies", {}).items()})
                save_session_cookies(self.session_cookies)
            self._add_history_entry(self.pending_call, response)
            self.pending_call = None

        failed_assertions = [item for item in assertion_results if not item.get("passed")]
        if 200 <= status < 400:
            message = self.t("tests_failed") if failed_assertions else self.t("response_saved")
            self.statusBar().showMessage(message, 3000 if failed_assertions else 2500)
            self._show_toast(message, "warning" if failed_assertions else "success")
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
        self.response_json_tree.clear()
        self.response_tests.clear()

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
            self.response_json_tree.clear()
            self.response_tests.clear()
        else:
            self.response_body.setPlainText(self._format_body(history_item.response_body))
            self.response_raw.setPlainText(history_item.response_body)
            self.response_headers.setPlainText(self._headers_to_text(history_item.response_headers))
            self._populate_json_tree(history_item.response_body)
            self.response_tests.setPlainText(self._format_assertion_results(history_item.assertion_results))

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
            request_timeout=call.timeout,
            request_follow_redirects=call.follow_redirects,
            request_retry_count=call.retry_count,
            request_retry_statuses=call.retry_statuses,
            request_use_session_cookies=call.use_session_cookies,
            request_assertions=call.assertions,
            assertion_results=list(response.get("assertion_results", [])) if response else [],
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

    def _evaluate_assertions(self, assertions: str, response: dict[str, Any]) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for raw_line in assertions.replace(";", "\n").splitlines():
            expression = raw_line.strip()
            if not expression or expression.startswith("#"):
                continue
            try:
                passed, detail = self._evaluate_assertion(expression, response)
            except (AssertionAPIError, json.JSONDecodeError) as error:
                passed, detail = False, str(error)
            results.append({"expression": expression, "passed": passed, "detail": detail})
        return results

    def _evaluate_assertion(self, expression: str, response: dict[str, Any]) -> tuple[bool, str]:
        status = int(response.get("status") or 0)
        elapsed_ms = float(response.get("elapsed_ms") or 0)
        body = str(response.get("body") or "")
        headers = {str(key).lower(): str(value) for key, value in dict(response.get("headers") or {}).items()}

        match = re.fullmatch(r"status\s*(==|!=|<=|>=|<|>)\s*(\d{3})", expression, re.IGNORECASE)
        if match:
            operator, expected = match.groups()
            return self._compare_number(status, operator, int(expected)), f"status={status}"

        match = re.fullmatch(r"time\s*(==|!=|<=|>=|<|>)\s*(\d+(?:\.\d+)?)", expression, re.IGNORECASE)
        if match:
            operator, expected = match.groups()
            return self._compare_number(elapsed_ms, operator, float(expected)), f"time={elapsed_ms} ms"

        match = re.fullmatch(r"body\s+contains\s+(.+)", expression, re.IGNORECASE)
        if match:
            expected = self._strip_quotes(match.group(1).strip())
            return expected in body, f"body length={len(body)}"

        match = re.fullmatch(r"header\s+(.+?)\s+contains\s+(.+)", expression, re.IGNORECASE)
        if match:
            header_name, expected = match.groups()
            value = headers.get(header_name.strip().lower(), "")
            expected = self._strip_quotes(expected.strip())
            return expected.lower() in value.lower(), f"{header_name.strip()}={value}"

        match = re.fullmatch(r"json\s+(.+?)\s+exists", expression, re.IGNORECASE)
        if match:
            path = match.group(1).strip()
            value = self._json_value(body, path)
            return value is not None, f"{path}={value}"

        match = re.fullmatch(r"json\s+(.+?)\s*(==|!=|contains)\s*(.+)", expression, re.IGNORECASE)
        if match:
            path, operator, expected = match.groups()
            operator = operator.lower()
            value = self._json_value(body, path.strip())
            expected_value = self._parse_expected_value(expected.strip())
            if operator == "contains":
                return str(expected_value) in str(value), f"{path.strip()}={value}"
            return self._compare_value(value, operator, expected_value), f"{path.strip()}={value}"

        raise AssertionAPIError("assertion_unknown")

    @staticmethod
    def _json_value(body: str, path: str) -> Any:
        payload = json.loads(body)
        return WorkflowRunner.extract_path(payload, path)

    @staticmethod
    def _compare_number(value: float, operator: str, expected: float) -> bool:
        if operator == "==":
            return value == expected
        if operator == "!=":
            return value != expected
        if operator == "<":
            return value < expected
        if operator == "<=":
            return value <= expected
        if operator == ">":
            return value > expected
        if operator == ">=":
            return value >= expected
        return False

    @staticmethod
    def _compare_value(value: Any, operator: str, expected: Any) -> bool:
        if operator == "==":
            return value == expected or str(value) == str(expected)
        if operator == "!=":
            return not (value == expected or str(value) == str(expected))
        return False

    @staticmethod
    def _parse_expected_value(value: str) -> Any:
        value = RestClientWindow._strip_quotes(value)
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value

    @staticmethod
    def _strip_quotes(value: str) -> str:
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            return value[1:-1]
        return value

    def _format_assertion_results(self, results: list[dict[str, Any]]) -> str:
        if not results:
            return self.t("tests_not_configured")
        lines = []
        for item in results:
            prefix = "PASS" if item.get("passed") else "FAIL"
            lines.append(f"{prefix}  {item.get('expression', '')}  ({item.get('detail', '')})")
        return "\n".join(lines)

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
            return PALETTE["crimson_red"], PALETTE["misty_rose"]
        if 200 <= status < 300:
            return PALETTE["forest_green"], PALETTE["mint_cream"]
        if 300 <= status < 400:
            return PALETTE["denim_blue"], PALETTE["azure_mist"]
        if 400 <= status < 500:
            return PALETTE["burnt_orange"], PALETTE["cream_yellow"]
        if status >= 500:
            return PALETTE["crimson_red"], PALETTE["misty_rose"]
        return PALETTE["gunmetal"], PALETTE["snow_white"]

    @staticmethod
    def _method_color(method: str) -> str:
        colors = {
            "GET": PALETTE["forest_green"],
            "POST": PALETTE["denim_blue"],
            "PUT": PALETTE["burnt_orange"],
            "PATCH": PALETTE["dark_sienna"],
            "DELETE": PALETTE["crimson_red"],
        }
        return colors.get(method.upper(), PALETTE["gunmetal"])
