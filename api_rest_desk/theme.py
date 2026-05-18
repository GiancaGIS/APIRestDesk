from __future__ import annotations

from PyQt6.QtWidgets import QLabel, QWidget

from api_rest_desk.settings import load_settings


LIGHT_STYLESHEET = """
QMainWindow, QDialog, QWidget {
    background: #f3f5f8;
    color: #182230;
    font-family: Segoe UI;
    font-size: 13px;
}
QMenuBar {
    background: #ffffff;
    border-bottom: 1px solid #d9e0ea;
    padding: 4px;
}
QMenuBar::item {
    border-radius: 5px;
    padding: 6px 10px;
}
QMenuBar::item:selected {
    background: #eef3f8;
}
QStatusBar {
    background: #ffffff;
    border-top: 1px solid #d9e0ea;
}
QFrame#Sidebar {
    background: #ffffff;
    border-right: 1px solid #d9e0ea;
}
QFrame#Panel {
    background: #ffffff;
    border: 1px solid #d9e0ea;
    border-radius: 8px;
}
QFrame#Metrics {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 7px;
}
QLabel#AppTitle {
    font-size: 24px;
    font-weight: 800;
    color: #101828;
}
QLabel#SectionTitle {
    font-size: 17px;
    font-weight: 750;
    color: #101828;
}
QLabel#MutedLabel {
    color: #667085;
    font-size: 12px;
}
QLabel#StatusBadge {
    border-radius: 12px;
    font-weight: 750;
    padding: 4px 10px;
    min-width: 58px;
}
QLabel#StatusBadge[statusClass="neutral"] {
    background: #eef2f6;
    color: #475467;
}
QLabel#StatusBadge[statusClass="success"] {
    background: #dcfae6;
    color: #027a48;
}
QLabel#StatusBadge[statusClass="redirect"] {
    background: #d1e9ff;
    color: #175cd3;
}
QLabel#StatusBadge[statusClass="client_error"] {
    background: #fef0c7;
    color: #b54708;
}
QLabel#StatusBadge[statusClass="server_error"] {
    background: #fee4e2;
    color: #b42318;
}
QLabel#StatusBadge[statusClass="network_error"] {
    background: #fee4e2;
    color: #b42318;
}
QLabel#Toast {
    border-radius: 8px;
    font-weight: 650;
    padding: 10px 14px;
}
QLabel#Toast[toastKind="success"] {
    background: #027a48;
    color: #ffffff;
}
QLabel#Toast[toastKind="warning"] {
    background: #b54708;
    color: #ffffff;
}
QLabel#Toast[toastKind="error"] {
    background: #b42318;
    color: #ffffff;
}
QLabel#Toast[toastKind="info"] {
    background: #1849a9;
    color: #ffffff;
}
QListWidget, QTreeWidget, QPlainTextEdit, QLineEdit, QComboBox, QTableWidget {
    background: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 7px;
    selection-background-color: #2e6ff2;
}
QLineEdit, QComboBox {
    padding: 8px;
}
QPlainTextEdit {
    padding: 8px;
}
QTableWidget {
    gridline-color: #e2e8f0;
    alternate-background-color: #f8fafc;
}
QHeaderView::section {
    background: #f1f5f9;
    border: 0;
    border-bottom: 1px solid #d9e0ea;
    color: #475467;
    font-weight: 700;
    padding: 8px;
}
QLineEdit:focus, QPlainTextEdit:focus, QComboBox:focus {
    border: 1px solid #2e6ff2;
}
QListWidget, QTreeWidget {
    padding: 5px;
}
QListWidget::item, QTreeWidget::item {
    padding: 9px 8px;
    border-radius: 6px;
    margin: 1px;
}
QListWidget::item:hover, QTreeWidget::item:hover {
    background: #f1f5f9;
}
QListWidget::item:selected, QTreeWidget::item:selected {
    background: #e6f0ff;
    color: #101828;
}
QPushButton {
    background: #ffffff;
    border: 1px solid #aab6c5;
    border-radius: 7px;
    color: #182230;
    padding: 8px 12px;
    min-height: 18px;
}
QPushButton:hover {
    background: #f3f6fa;
    border-color: #7d8ca1;
}
QPushButton:pressed {
    background: #e8eef7;
}
QPushButton:disabled {
    color: #98a2b3;
    background: #e4e7ec;
}
QPushButton#Primary {
    background: #2e6ff2;
    border-color: #1f5fd3;
    color: #ffffff;
    font-weight: 750;
    padding-left: 18px;
    padding-right: 18px;
}
QPushButton#Primary:hover {
    background: #1f63df;
}
QPushButton#Secondary {
    background: #eef4ff;
    border-color: #b2ccff;
    color: #1849a9;
    font-weight: 650;
}
QPushButton#Danger {
    background: #fff1f0;
    border-color: #fecdca;
    color: #b42318;
}
QTabWidget::pane {
    border: 1px solid #d9e0ea;
    background: #ffffff;
    border-radius: 7px;
    top: -1px;
}
QTabBar::tab {
    background: #e9eef5;
    color: #475467;
    padding: 8px 13px;
    border-top-left-radius: 7px;
    border-top-right-radius: 7px;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background: #ffffff;
    color: #101828;
    font-weight: 750;
    border: 1px solid #d9e0ea;
    border-bottom: 1px solid #ffffff;
}
QSplitter::handle {
    background: #d9e0ea;
}
"""


DARK_STYLESHEET = """
QMainWindow, QDialog, QWidget {
    background: #111827;
    color: #e5e7eb;
    font-family: Segoe UI;
    font-size: 13px;
}
QMenuBar {
    background: #182230;
    color: #e5e7eb;
    border-bottom: 1px solid #334155;
    padding: 4px;
}
QMenuBar::item {
    border-radius: 5px;
    padding: 6px 10px;
}
QMenuBar::item:selected {
    background: #243044;
}
QMenu {
    background: #182230;
    color: #e5e7eb;
    border: 1px solid #334155;
}
QMenu::item:selected {
    background: #243044;
}
QStatusBar {
    background: #182230;
    color: #cbd5e1;
    border-top: 1px solid #334155;
}
QFrame#Sidebar {
    background: #182230;
    border-right: 1px solid #334155;
}
QFrame#Panel {
    background: #182230;
    border: 1px solid #334155;
    border-radius: 8px;
}
QFrame#Metrics {
    background: #0f172a;
    border: 1px solid #334155;
    border-radius: 7px;
}
QLabel {
    color: #e5e7eb;
}
QLabel#AppTitle {
    font-size: 24px;
    font-weight: 800;
    color: #f8fafc;
}
QLabel#SectionTitle {
    font-size: 17px;
    font-weight: 750;
    color: #f8fafc;
}
QLabel#MutedLabel {
    color: #cbd5e1;
    font-size: 12px;
}
QLabel#StatusBadge {
    border-radius: 12px;
    font-weight: 750;
    padding: 4px 10px;
    min-width: 58px;
}
QLabel#StatusBadge[statusClass="neutral"] {
    background: #334155;
    color: #e2e8f0;
}
QLabel#StatusBadge[statusClass="success"] {
    background: #064e3b;
    color: #bbf7d0;
}
QLabel#StatusBadge[statusClass="redirect"] {
    background: #1e3a8a;
    color: #bfdbfe;
}
QLabel#StatusBadge[statusClass="client_error"] {
    background: #78350f;
    color: #fde68a;
}
QLabel#StatusBadge[statusClass="server_error"],
QLabel#StatusBadge[statusClass="network_error"] {
    background: #7f1d1d;
    color: #fecaca;
}
QLabel#Toast {
    border-radius: 8px;
    font-weight: 650;
    padding: 10px 14px;
}
QLabel#Toast[toastKind="success"] {
    background: #047857;
    color: #ffffff;
}
QLabel#Toast[toastKind="warning"] {
    background: #b45309;
    color: #ffffff;
}
QLabel#Toast[toastKind="error"] {
    background: #b91c1c;
    color: #ffffff;
}
QLabel#Toast[toastKind="info"] {
    background: #1d4ed8;
    color: #ffffff;
}
QListWidget, QTreeWidget, QPlainTextEdit, QLineEdit, QComboBox, QTableWidget {
    background: #0f172a;
    color: #e5e7eb;
    border: 1px solid #475569;
    border-radius: 7px;
    selection-background-color: #2563eb;
    selection-color: #ffffff;
}
QLineEdit, QComboBox {
    padding: 8px;
}
QPlainTextEdit {
    padding: 8px;
}
QTableWidget {
    gridline-color: #334155;
    alternate-background-color: #182230;
}
QHeaderView::section {
    background: #223047;
    border: 0;
    border-bottom: 1px solid #334155;
    color: #e5e7eb;
    font-weight: 700;
    padding: 8px;
}
QLineEdit:focus, QPlainTextEdit:focus, QComboBox:focus {
    border: 1px solid #60a5fa;
}
QComboBox QAbstractItemView {
    background: #0f172a;
    color: #e5e7eb;
    border: 1px solid #475569;
    selection-background-color: #2563eb;
}
QListWidget, QTreeWidget {
    padding: 5px;
}
QListWidget::item, QTreeWidget::item {
    padding: 9px 8px;
    border-radius: 6px;
    margin: 1px;
}
QListWidget::item:hover, QTreeWidget::item:hover {
    background: #223047;
}
QListWidget::item:selected, QTreeWidget::item:selected {
    background: #1e3a5f;
    color: #ffffff;
}
QPushButton {
    background: #223047;
    border: 1px solid #64748b;
    border-radius: 7px;
    color: #f8fafc;
    padding: 8px 12px;
    min-height: 18px;
}
QPushButton:hover {
    background: #2f3d56;
    border-color: #94a3b8;
}
QPushButton:pressed {
    background: #334155;
}
QPushButton:disabled {
    color: #94a3b8;
    background: #1f2937;
    border-color: #334155;
}
QPushButton#Primary {
    background: #2563eb;
    border-color: #60a5fa;
    color: #ffffff;
    font-weight: 750;
    padding-left: 18px;
    padding-right: 18px;
}
QPushButton#Primary:hover {
    background: #1d4ed8;
}
QPushButton#Secondary {
    background: #1e3a5f;
    border-color: #3b82f6;
    color: #dbeafe;
    font-weight: 650;
}
QPushButton#Secondary:hover {
    background: #25466f;
}
QPushButton#Danger {
    background: #7f1d1d;
    border-color: #ef4444;
    color: #fee2e2;
}
QPushButton#Danger:hover {
    background: #991b1b;
}
QTabWidget::pane {
    border: 1px solid #334155;
    background: #182230;
    border-radius: 7px;
    top: -1px;
}
QTabBar::tab {
    background: #223047;
    color: #cbd5e1;
    padding: 8px 13px;
    border-top-left-radius: 7px;
    border-top-right-radius: 7px;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background: #182230;
    color: #f8fafc;
    font-weight: 750;
    border: 1px solid #334155;
    border-bottom: 1px solid #182230;
}
QSplitter::handle {
    background: #334155;
}
"""


def apply_theme(widget: QWidget) -> None:
    theme = str(load_settings().get("theme") or "light")
    widget.setStyleSheet(DARK_STYLESHEET if theme == "dark" else LIGHT_STYLESHEET)


def status_class(status: int | None, network_error: bool = False) -> str:
    if network_error:
        return "network_error"
    if status is None:
        return "neutral"
    if 200 <= status < 300:
        return "success"
    if 300 <= status < 400:
        return "redirect"
    if 400 <= status < 500:
        return "client_error"
    if status >= 500:
        return "server_error"
    return "neutral"


def set_status_badge(label: QLabel, text: str, status: int | None = None, network_error: bool = False) -> None:
    label.setText(text)
    label.setProperty("statusClass", status_class(status, network_error))
    label.style().unpolish(label)
    label.style().polish(label)
