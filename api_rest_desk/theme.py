from __future__ import annotations

from string import Template

from PyQt6.QtWidgets import QLabel, QWidget

from api_rest_desk.settings import load_settings


# ---------------------------------------------------------------------------
# Centralized color palette – every hex color used across the application.
# Keys are plain-English descriptions of the color itself.
# ---------------------------------------------------------------------------
PALETTE = {
    # ── Whites & near-whites ──────────────────────────────────────────────
    "white":                "#ffffff",
    "snow_white":           "#f8fafc",
    "ghost_white":          "#f3f5f8",
    "ice_blue":             "#f3f6fa",
    "alice_blue":           "#f1f5f9",
    "lavender_mist":        "#eef4ff",
    "pale_blue_gray":       "#eef3f8",
    "light_blue_gray":      "#eef2f6",
    "mint_cream":           "#ecfdf3",
    "pale_silver_blue":     "#e9eef5",
    "periwinkle_tint":      "#e8eef7",
    "pale_cornflower":      "#e6f0ff",
    "platinum":             "#e5e7eb",
    "light_silver":         "#e4e7ec",
    "pale_slate":           "#e2e8f0",
    "azure_mist":           "#eff8ff",

    # ── Light accent backgrounds ──────────────────────────────────────────
    "pale_sky_blue":        "#dbeafe",
    "pale_mint_green":      "#dcfae6",
    "pale_cerulean":        "#d1e9ff",
    "cream_yellow":         "#fffaeb",
    "misty_rose":           "#fff1f0",
    "champagne":            "#fef0c7",
    "pale_pink":            "#fee4e2",
    "light_pink":           "#fee2e2",
    "peach":                "#fecdca",
    "light_coral":          "#fecaca",
    "pale_yellow":          "#fef08a",
    "buff_yellow":          "#fde68a",

    # ── Silvers & grays ───────────────────────────────────────────────────
    "silver_blue":          "#d9e0ea",
    "silver_gray":          "#cbd5e1",
    "soft_periwinkle":      "#b2ccff",
    "baby_blue":            "#bfdbfe",
    "light_mint":           "#bbf7d0",
    "cadet_gray":           "#aab6c5",
    "cool_gray":            "#98a2b3",
    "slate_gray":           "#94a3b8",
    "storm_gray":           "#7d8ca1",

    # ── Mid tones ─────────────────────────────────────────────────────────
    "dark_slate_gray":      "#64748b",
    "dim_gray":             "#667085",
    "gunmetal":             "#475467",
    "charcoal_blue":        "#475569",

    # ── Blues ─────────────────────────────────────────────────────────────
    "cornflower_blue":      "#60a5fa",
    "royal_blue":           "#3b82f6",
    "vivid_blue":           "#2e6ff2",
    "sapphire_blue":        "#2563eb",
    "strong_blue":          "#1f63df",
    "medium_blue":          "#1f5fd3",
    "cobalt_blue":          "#1d4ed8",
    "yale_blue":            "#1849a9",
    "denim_blue":           "#175cd3",
    "deep_sapphire":        "#1e3a8a",

    # ── Dark blues & navies ───────────────────────────────────────────────
    "navy_teal":            "#25466f",
    "prussian_blue":        "#1e3a5f",
    "dark_navy_blue":       "#243044",
    "midnight_blue":        "#223047",
    "dark_blue_gray":       "#2f3d56",
    "dark_gunmetal":        "#334155",
    "dark_navy":            "#182230",
    "near_black":           "#111827",
    "rich_black":           "#101828",
    "dark_void":            "#0f172a",

    # ── Greens ────────────────────────────────────────────────────────────
    "deep_emerald":         "#064e3b",
    "emerald_green":        "#047857",
    "forest_green":         "#027a48",

    # ── Yellows & ambers ──────────────────────────────────────────────────
    "amber":                "#f59e0b",
    "dark_amber":           "#b45309",
    "burnt_orange":         "#b54708",

    # ── Reds & browns ─────────────────────────────────────────────────────
    "tomato_red":           "#ef4444",
    "dark_crimson":         "#b91c1c",
    "crimson_red":          "#b42318",
    "dark_blood_red":       "#991b1b",
    "maroon":               "#7f1d1d",
    "dark_sienna":          "#7a2e0e",
    "chocolate_brown":      "#78350f",

    # ── Charcoals ─────────────────────────────────────────────────────────
    "dark_charcoal":        "#1f2937",
}


LIGHT_STYLESHEET = Template("""
QMainWindow, QDialog, QWidget {
    background: $ghost_white;
    color: $dark_navy;
    font-family: Segoe UI;
    font-size: 13px;
}
QMenuBar {
    background: $white;
    border-bottom: 1px solid $silver_blue;
    padding: 4px;
}
QMenuBar::item {
    border-radius: 5px;
    padding: 6px 10px;
}
QMenuBar::item:selected {
    background: $pale_blue_gray;
}
QStatusBar {
    background: $white;
    border-top: 1px solid $silver_blue;
}
QFrame#Sidebar {
    background: $white;
    border-right: 1px solid $silver_blue;
}
QFrame#Panel {
    background: $white;
    border: 1px solid $silver_blue;
    border-radius: 8px;
}
QFrame#Metrics {
    background: $snow_white;
    border: 1px solid $pale_slate;
    border-radius: 7px;
}
QLabel {
    background: transparent;
    border: 0;
    color: $dark_navy;
    padding: 0;
}
QLabel#AppTitle {
    font-size: 24px;
    font-weight: 800;
    color: $rich_black;
}
QLabel#SectionTitle {
    font-size: 17px;
    font-weight: 750;
    color: $rich_black;
}
QLabel#MutedLabel {
    color: $dim_gray;
    font-size: 12px;
}
QLabel#StatusBadge {
    border-radius: 12px;
    font-weight: 750;
    padding: 4px 10px;
    min-width: 58px;
}
QLabel#StatusBadge[statusClass="neutral"] {
    background: $light_blue_gray;
    color: $gunmetal;
}
QLabel#StatusBadge[statusClass="success"] {
    background: $pale_mint_green;
    color: $forest_green;
}
QLabel#StatusBadge[statusClass="redirect"] {
    background: $pale_cerulean;
    color: $denim_blue;
}
QLabel#StatusBadge[statusClass="client_error"] {
    background: $champagne;
    color: $burnt_orange;
}
QLabel#StatusBadge[statusClass="server_error"] {
    background: $pale_pink;
    color: $crimson_red;
}
QLabel#StatusBadge[statusClass="network_error"] {
    background: $pale_pink;
    color: $crimson_red;
}
QLabel#Toast {
    border-radius: 8px;
    font-weight: 650;
    padding: 10px 14px;
}
QLabel#Toast[toastKind="success"] {
    background: $forest_green;
    color: $white;
}
QLabel#Toast[toastKind="warning"] {
    background: $burnt_orange;
    color: $white;
}
QLabel#Toast[toastKind="error"] {
    background: $crimson_red;
    color: $white;
}
QLabel#Toast[toastKind="info"] {
    background: $yale_blue;
    color: $white;
}
QListWidget, QTreeWidget, QPlainTextEdit, QLineEdit, QComboBox, QTableWidget {
    background: $white;
    border: 1px solid $silver_gray;
    border-radius: 7px;
    selection-background-color: $vivid_blue;
}
QLineEdit, QComboBox {
    padding: 8px;
}
QPlainTextEdit {
    padding: 8px;
}
QTableWidget {
    gridline-color: $pale_slate;
    alternate-background-color: $snow_white;
}
QHeaderView::section {
    background: $alice_blue;
    border: 0;
    border-bottom: 1px solid $silver_blue;
    color: $gunmetal;
    font-weight: 700;
    padding: 8px;
}
QLineEdit:focus, QPlainTextEdit:focus, QComboBox:focus {
    border: 1px solid $vivid_blue;
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
    background: $alice_blue;
}
QListWidget::item:selected, QTreeWidget::item:selected {
    background: $pale_cornflower;
    color: $rich_black;
}
QPushButton {
    background: $white;
    border: 1px solid $cadet_gray;
    border-radius: 7px;
    color: $dark_navy;
    padding: 8px 12px;
    min-height: 18px;
}
QPushButton:hover {
    background: $ice_blue;
    border-color: $storm_gray;
}
QPushButton:pressed {
    background: $periwinkle_tint;
}
QPushButton:disabled {
    color: $cool_gray;
    background: $light_silver;
}
QPushButton#Primary {
    background: $vivid_blue;
    border-color: $medium_blue;
    color: $white;
    font-weight: 750;
    padding-left: 18px;
    padding-right: 18px;
}
QPushButton#Primary:hover {
    background: $strong_blue;
}
QPushButton#Secondary {
    background: $lavender_mist;
    border-color: $soft_periwinkle;
    color: $yale_blue;
    font-weight: 650;
}
QPushButton#Danger {
    background: $misty_rose;
    border-color: $peach;
    color: $crimson_red;
}
QTabWidget::pane {
    border: 1px solid $silver_blue;
    background: $white;
    border-radius: 7px;
    top: -1px;
}
QTabBar::tab {
    background: $pale_silver_blue;
    color: $gunmetal;
    padding: 8px 13px;
    border-top-left-radius: 7px;
    border-top-right-radius: 7px;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background: $white;
    color: $rich_black;
    font-weight: 750;
    border: 1px solid $silver_blue;
    border-bottom: 1px solid $white;
}
QSplitter::handle {
    background: $silver_blue;
}
""").substitute(PALETTE)


DARK_STYLESHEET = Template("""
QMainWindow, QDialog, QWidget {
    background: $near_black;
    color: $platinum;
    font-family: Segoe UI;
    font-size: 13px;
}
QMenuBar {
    background: $dark_navy;
    color: $platinum;
    border-bottom: 1px solid $dark_gunmetal;
    padding: 4px;
}
QMenuBar::item {
    border-radius: 5px;
    padding: 6px 10px;
}
QMenuBar::item:selected {
    background: $dark_navy_blue;
}
QMenu {
    background: $dark_navy;
    color: $platinum;
    border: 1px solid $dark_gunmetal;
}
QMenu::item:selected {
    background: $dark_navy_blue;
}
QStatusBar {
    background: $dark_navy;
    color: $silver_gray;
    border-top: 1px solid $dark_gunmetal;
}
QFrame#Sidebar {
    background: $dark_navy;
    border-right: 1px solid $dark_gunmetal;
}
QFrame#Panel {
    background: $dark_navy;
    border: 1px solid $dark_gunmetal;
    border-radius: 8px;
}
QFrame#Metrics {
    background: $dark_void;
    border: 1px solid $dark_gunmetal;
    border-radius: 7px;
}
QLabel {
    background: transparent;
    border: 0;
    color: $platinum;
    padding: 0;
}
QLabel#AppTitle {
    font-size: 24px;
    font-weight: 800;
    color: $snow_white;
}
QLabel#SectionTitle {
    font-size: 17px;
    font-weight: 750;
    color: $snow_white;
}
QLabel#MutedLabel {
    color: $silver_gray;
    font-size: 12px;
}
QLabel#StatusBadge {
    border-radius: 12px;
    font-weight: 750;
    padding: 4px 10px;
    min-width: 58px;
}
QLabel#StatusBadge[statusClass="neutral"] {
    background: $dark_gunmetal;
    color: $pale_slate;
}
QLabel#StatusBadge[statusClass="success"] {
    background: $deep_emerald;
    color: $light_mint;
}
QLabel#StatusBadge[statusClass="redirect"] {
    background: $deep_sapphire;
    color: $baby_blue;
}
QLabel#StatusBadge[statusClass="client_error"] {
    background: $chocolate_brown;
    color: $buff_yellow;
}
QLabel#StatusBadge[statusClass="server_error"],
QLabel#StatusBadge[statusClass="network_error"] {
    background: $maroon;
    color: $light_coral;
}
QLabel#Toast {
    border-radius: 8px;
    font-weight: 650;
    padding: 10px 14px;
}
QLabel#Toast[toastKind="success"] {
    background: $emerald_green;
    color: $white;
}
QLabel#Toast[toastKind="warning"] {
    background: $dark_amber;
    color: $white;
}
QLabel#Toast[toastKind="error"] {
    background: $dark_crimson;
    color: $white;
}
QLabel#Toast[toastKind="info"] {
    background: $cobalt_blue;
    color: $white;
}
QListWidget, QTreeWidget, QPlainTextEdit, QLineEdit, QComboBox, QTableWidget {
    background: $dark_void;
    color: $platinum;
    border: 1px solid $charcoal_blue;
    border-radius: 7px;
    selection-background-color: $sapphire_blue;
    selection-color: $white;
}
QLineEdit, QComboBox {
    padding: 8px;
}
QPlainTextEdit {
    padding: 8px;
}
QTableWidget {
    gridline-color: $dark_gunmetal;
    alternate-background-color: $dark_navy;
}
QHeaderView::section {
    background: $midnight_blue;
    border: 0;
    border-bottom: 1px solid $dark_gunmetal;
    color: $platinum;
    font-weight: 700;
    padding: 8px;
}
QLineEdit:focus, QPlainTextEdit:focus, QComboBox:focus {
    border: 1px solid $cornflower_blue;
}
QComboBox QAbstractItemView {
    background: $dark_void;
    color: $platinum;
    border: 1px solid $charcoal_blue;
    selection-background-color: $sapphire_blue;
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
    background: $midnight_blue;
}
QListWidget::item:selected, QTreeWidget::item:selected {
    background: $prussian_blue;
    color: $white;
}
QPushButton {
    background: $midnight_blue;
    border: 1px solid $dark_slate_gray;
    border-radius: 7px;
    color: $snow_white;
    padding: 8px 12px;
    min-height: 18px;
}
QPushButton:hover {
    background: $dark_blue_gray;
    border-color: $slate_gray;
}
QPushButton:pressed {
    background: $dark_gunmetal;
}
QPushButton:disabled {
    color: $slate_gray;
    background: $dark_charcoal;
    border-color: $dark_gunmetal;
}
QPushButton#Primary {
    background: $sapphire_blue;
    border-color: $cornflower_blue;
    color: $white;
    font-weight: 750;
    padding-left: 18px;
    padding-right: 18px;
}
QPushButton#Primary:hover {
    background: $cobalt_blue;
}
QPushButton#Secondary {
    background: $prussian_blue;
    border-color: $royal_blue;
    color: $pale_sky_blue;
    font-weight: 650;
}
QPushButton#Secondary:hover {
    background: $navy_teal;
}
QPushButton#Danger {
    background: $maroon;
    border-color: $tomato_red;
    color: $light_pink;
}
QPushButton#Danger:hover {
    background: $dark_blood_red;
}
QTabWidget::pane {
    border: 1px solid $dark_gunmetal;
    background: $dark_navy;
    border-radius: 7px;
    top: -1px;
}
QTabBar::tab {
    background: $midnight_blue;
    color: $silver_gray;
    padding: 8px 13px;
    border-top-left-radius: 7px;
    border-top-right-radius: 7px;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background: $dark_navy;
    color: $snow_white;
    font-weight: 750;
    border: 1px solid $dark_gunmetal;
    border-bottom: 1px solid $dark_navy;
}
QSplitter::handle {
    background: $dark_gunmetal;
}
""").substitute(PALETTE)


def apply_theme(widget: QWidget) -> None:
    """Apply the active theme (light or dark) stylesheet to *widget*."""
    theme = str(load_settings().get("theme") or "light")
    widget.setStyleSheet(DARK_STYLESHEET if theme == "dark" else LIGHT_STYLESHEET)


def status_class(status: int | None, network_error: bool = False) -> str:
    """Map an HTTP status code to a CSS status class name.

    Returns one of ``"neutral"``, ``"success"``, ``"redirect"``,
    ``"client_error"``, ``"server_error"``, or ``"network_error"``.
    """
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
    """Update a status badge QLabel with *text* and restyle it
    according to the HTTP *status* code.
    """
    label.setText(text)
    label.setProperty("statusClass", status_class(status, network_error))
    label.style().unpolish(label)
    label.style().polish(label)
