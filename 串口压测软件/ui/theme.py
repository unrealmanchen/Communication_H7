"""界面配色、字体与全局 QSS 主题。"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QColor, QFont, QFontDatabase, QGuiApplication, QPalette
from PySide6.QtWidgets import QApplication

ASSET_DIR = Path(__file__).resolve().parent / "assets"

# ---- 调色板 ----------------------------------------------------------------
BG = "#070D18"
BG_SOFT = "#0A1220"
SIDEBAR_TOP = "#0F1B2E"
SIDEBAR_BOTTOM = "#091120"
CARD = "#0D1728"
CARD_RAISED = "#101D30"
CARD_BORDER = "#1B2B45"
CARD_BORDER_ACTIVE = "#2C4463"
TEXT = "#E8F0FB"
TEXT_SOFT = "#A8BAD4"
MUTED = "#6E829F"
ACCENT = "#2DD4BF"
ACCENT_BRIGHT = "#5EEAD4"
ACCENT_DARK = "#0F3F3B"
BLUE = "#38BDF8"
GREEN = "#34D399"
RED = "#F87171"
AMBER = "#FBBF24"
PINK = "#F472B6"
PURPLE = "#A78BFA"
ORANGE = "#FB923C"
CYAN = "#22D3EE"

PORT_COLORS = (BLUE, GREEN, AMBER, PURPLE, PINK, ORANGE, CYAN)

UI_FONT = "Microsoft YaHei UI"
MONO_FONT = "Cascadia Mono"


def pick_mono_font() -> str:
    if QGuiApplication.instance() is None:
        return "Consolas"
    families = set(QFontDatabase.families())
    for candidate in ("Cascadia Mono", "JetBrains Mono", "Consolas", "Courier New"):
        if candidate in families:
            return candidate
    return "Consolas"


def rgba(hex_color: str, alpha: float) -> str:
    color = QColor(hex_color)
    return f"rgba({color.red()}, {color.green()}, {color.blue()}, {alpha:.3f})"


def with_alpha(hex_color: str, alpha: int) -> QColor:
    color = QColor(hex_color)
    color.setAlpha(alpha)
    return color


QSS = """
* {
    font-family: "@UI_FONT@";
    outline: none;
}
QWidget {
    color: @TEXT@;
    font-size: 13px;
}
QMainWindow, QWidget#Root {
    background: @BG@;
}
QFrame#Sidebar {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 @SIDEBAR_TOP@, stop:1 @SIDEBAR_BOTTOM@);
    border-right: 1px solid @CARD_BORDER@;
}
QLabel#AppTitle {
    font-size: 19px;
    font-weight: 700;
    color: @TEXT@;
    letter-spacing: 0.5px;
}
QLabel#AppSubtitle {
    font-size: 9px;
    color: @MUTED@;
    letter-spacing: 1.4px;
}
QLabel#NavSection {
    color: #566A88;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1.6px;
    padding-left: 12px;
}
QPushButton#NavButton {
    text-align: left;
    padding: 11px 14px;
    border: 1px solid transparent;
    border-left: 3px solid transparent;
    border-radius: 8px;
    background: transparent;
    color: @TEXT_SOFT@;
    font-size: 13.5px;
    font-weight: 500;
}
QPushButton#NavButton:hover {
    background: rgba(255, 255, 255, 0.035);
    color: @TEXT@;
}
QPushButton#NavButton:checked {
    background: rgba(45, 212, 191, 0.10);
    border-left: 3px solid @ACCENT@;
    color: @ACCENT_BRIGHT@;
    font-weight: 700;
}
QFrame#SidebarStatus {
    background: rgba(10, 20, 36, 0.72);
    border: 1px solid @CARD_BORDER@;
    border-radius: 10px;
}
QLabel#SidebarStatusTitle {
    color: @MUTED@;
    font-size: 10px;
    letter-spacing: 1.1px;
}
QLabel#SidebarStatusValue {
    color: @TEXT@;
    font-size: 15px;
    font-weight: 700;
}
QLabel#PageTitle {
    font-size: 23px;
    font-weight: 700;
    color: @TEXT@;
}
QLabel#PageSubtitle {
    color: @MUTED@;
    font-size: 12px;
}
QLabel#Muted {
    color: @MUTED@;
}
QLabel#Soft {
    color: @TEXT_SOFT@;
}
QLabel#CardTitle {
    font-size: 14px;
    font-weight: 700;
    color: @TEXT@;
}
QLabel#CardHint {
    color: @MUTED@;
    font-size: 10.5px;
}
QLabel#FieldLabel {
    color: @MUTED@;
    font-size: 11px;
}
QLabel#Mono {
    font-family: "@MONO_FONT@";
    font-size: 11px;
    color: @TEXT_SOFT@;
}
QLabel#Pill {
    border-radius: 8px;
    padding: 2px 8px;
    font-size: 10px;
    font-weight: 600;
}
QFrame#Card {
    background: @CARD@;
    border: 1px solid @CARD_BORDER@;
    border-radius: 12px;
}
QFrame#Card[active="true"] {
    background: @CARD_RAISED@;
    border: 1px solid @CARD_BORDER_ACTIVE@;
}
QFrame#Strip {
    background: @BG_SOFT@;
    border: 1px solid @CARD_BORDER@;
    border-radius: 12px;
}
QFrame#Terminal {
    background: #060C16;
    border: 1px solid @CARD_BORDER@;
    border-radius: 12px;
}
QFrame#FreqChip {
    background: @CARD@;
    border: 1px solid @CARD_BORDER@;
    border-radius: 10px;
}
QFrame#FreqChip[selected="true"] {
    background: @CARD_RAISED@;
    border: 1px solid @ACCENT@;
}
QFrame#FreqChip[active="true"] {
    border: 1px solid @CARD_BORDER_ACTIVE@;
}
QPushButton {
    border-radius: 7px;
    padding: 7px 14px;
    font-size: 12.5px;
}
QPushButton#Primary {
    background: @ACCENT@;
    color: #03211D;
    border: 1px solid @ACCENT@;
    font-weight: 700;
}
QPushButton#Primary:hover {
    background: @ACCENT_BRIGHT@;
    border-color: @ACCENT_BRIGHT@;
}
QPushButton#Primary:pressed {
    background: #14B8A6;
}
QPushButton#Primary:disabled {
    background: #1C3A38;
    border-color: #1C3A38;
    color: #52706C;
}
QPushButton#Danger {
    background: rgba(248, 113, 113, 0.06);
    border: 1px solid rgba(248, 113, 113, 0.42);
    color: #FCA5A5;
    font-weight: 600;
}
QPushButton#Danger:hover {
    background: rgba(248, 113, 113, 0.14);
    border-color: @RED@;
    color: #FECACA;
}
QPushButton#Ghost {
    background: rgba(255, 255, 255, 0.025);
    border: 1px solid @CARD_BORDER@;
    color: @TEXT_SOFT@;
    font-weight: 500;
}
QPushButton#Ghost:hover {
    background: rgba(255, 255, 255, 0.05);
    border-color: @CARD_BORDER_ACTIVE@;
    color: @TEXT@;
}
QPushButton#Ghost:checked {
    background: rgba(45, 212, 191, 0.12);
    border-color: rgba(45, 212, 191, 0.5);
    color: @ACCENT_BRIGHT@;
}
QPushButton#LinkButton {
    background: transparent;
    border: none;
    color: @MUTED@;
    padding: 4px 6px;
    font-size: 11px;
}
QPushButton#LinkButton:hover {
    color: @ACCENT_BRIGHT@;
}
QPushButton#Segment {
    background: transparent;
    border: 1px solid transparent;
    border-radius: 6px;
    color: @MUTED@;
    padding: 6px 16px;
    font-weight: 600;
}
QPushButton#Segment:hover {
    color: @TEXT@;
}
QPushButton#Segment:checked {
    background: rgba(45, 212, 191, 0.13);
    border-color: rgba(45, 212, 191, 0.40);
    color: @ACCENT_BRIGHT@;
}
QComboBox, QDoubleSpinBox, QSpinBox, QLineEdit {
    background: #091221;
    border: 1px solid #223553;
    border-radius: 6px;
    padding: 4px 8px;
    min-height: 22px;
    color: @TEXT@;
    selection-background-color: @ACCENT@;
    selection-color: #03211D;
}
QComboBox:hover, QDoubleSpinBox:hover, QSpinBox:hover, QLineEdit:hover {
    border-color: @CARD_BORDER_ACTIVE@;
}
QComboBox:focus, QDoubleSpinBox:focus, QSpinBox:focus, QLineEdit:focus {
    border-color: @ACCENT@;
}
QComboBox:disabled, QDoubleSpinBox:disabled, QSpinBox:disabled, QLineEdit:disabled {
    color: #51637D;
    background: #08101C;
    border-color: #17253B;
}
QComboBox::drop-down {
    width: 22px;
    border: none;
    border-left: 1px solid #1B2C46;
    background: transparent;
}
QComboBox::down-arrow {
    image: url("@ASSETS@/chevron-down.svg");
    width: 9px;
    height: 6px;
}
QComboBox QAbstractItemView {
    background: #0C1727;
    border: 1px solid @CARD_BORDER_ACTIVE@;
    border-radius: 7px;
    padding: 4px;
    color: @TEXT@;
    selection-background-color: rgba(45, 212, 191, 0.16);
    selection-color: @ACCENT_BRIGHT@;
    outline: none;
}
QComboBox QAbstractItemView::item {
    min-height: 24px;
    padding: 3px 8px;
    border-radius: 4px;
}
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button,
QSpinBox::up-button, QSpinBox::down-button {
    width: 0px;
    height: 0px;
    border: none;
}
QCheckBox {
    color: @TEXT_SOFT@;
    spacing: 8px;
    font-size: 12px;
}
QCheckBox::indicator {
    width: 15px;
    height: 15px;
    border-radius: 4px;
    border: 1px solid #2A3E5C;
    background: #091221;
}
QCheckBox::indicator:hover {
    border-color: @ACCENT@;
}
QCheckBox::indicator:checked {
    background: @ACCENT@;
    border-color: @ACCENT@;
    image: url("@ASSETS@/check.svg");
}
QScrollBar:vertical {
    background: transparent;
    width: 9px;
    margin: 2px;
}
QScrollBar::handle:vertical {
    background: #24364F;
    min-height: 24px;
    border-radius: 4px;
}
QScrollBar::handle:vertical:hover {
    background: #35506F;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: transparent;
}
QScrollBar:horizontal {
    background: transparent;
    height: 9px;
    margin: 2px;
}
QScrollBar::handle:horizontal {
    background: #24364F;
    min-width: 24px;
    border-radius: 4px;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}
QTextEdit#LogView, QPlainTextEdit#LogView {
    background: #060C16;
    border: 1px solid @CARD_BORDER@;
    border-radius: 10px;
    color: @TEXT@;
    font-family: "@MONO_FONT@";
    font-size: 11.5px;
    padding: 8px 10px;
    selection-background-color: rgba(45, 212, 191, 0.28);
}
QTextEdit#LogView QScrollBar:vertical {
    background: transparent;
}
QStatusBar {
    background: @BG@;
    border-top: 1px solid #142138;
    color: @MUTED@;
    font-size: 11px;
}
QTabWidget::pane {
    border: none;
    background: transparent;
}
QTabBar::tab {
    background: transparent;
    color: @MUTED@;
    padding: 7px 22px;
    margin-right: 4px;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 600;
}
QTabBar::tab:hover {
    color: @TEXT@;
    background: rgba(255, 255, 255, 0.04);
}
QTabBar::tab:selected {
    background: rgba(45, 212, 191, 0.12);
    color: @ACCENT_BRIGHT@;
}
QStatusBar::item {
    border: none;
}
QToolTip {
    background: #122236;
    color: @TEXT@;
    border: 1px solid @CARD_BORDER_ACTIVE@;
    padding: 5px 8px;
    border-radius: 5px;
}
QMenu {
    background: #0C1727;
    border: 1px solid @CARD_BORDER_ACTIVE@;
    border-radius: 8px;
    padding: 5px;
    color: @TEXT@;
}
QMenu::item {
    padding: 6px 20px;
    border-radius: 4px;
}
QMenu::item:selected {
    background: rgba(45, 212, 191, 0.14);
    color: @ACCENT_BRIGHT@;
}
"""



def build_qss() -> str:
    replacements = {
        "@UI_FONT@": UI_FONT,
        "@MONO_FONT@": pick_mono_font(),
        "@ASSETS@": ASSET_DIR.as_posix(),
        "@BG@": BG,
        "@BG_SOFT@": BG_SOFT,
        "@SIDEBAR_TOP@": SIDEBAR_TOP,
        "@SIDEBAR_BOTTOM@": SIDEBAR_BOTTOM,
        "@CARD@": CARD,
        "@CARD_RAISED@": CARD_RAISED,
        "@CARD_BORDER@": CARD_BORDER,
        "@CARD_BORDER_ACTIVE@": CARD_BORDER_ACTIVE,
        "@TEXT@": TEXT,
        "@TEXT_SOFT@": TEXT_SOFT,
        "@MUTED@": MUTED,
        "@ACCENT@": ACCENT,
        "@ACCENT_BRIGHT@": ACCENT_BRIGHT,
        "@GREEN@": GREEN,
        "@RED@": RED,
    }
    qss = QSS
    for key, value in replacements.items():
        qss = qss.replace(key, value)
    return qss


def apply_theme(app: QApplication) -> None:
    app.setStyle("Fusion")
    font = QFont(UI_FONT, 10)
    font.setHintingPreference(QFont.HintingPreference.PreferFullHinting)
    app.setFont(font)

    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(BG))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(TEXT))
    palette.setColor(QPalette.ColorRole.Base, QColor("#091221"))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(CARD))
    palette.setColor(QPalette.ColorRole.Text, QColor(TEXT))
    palette.setColor(QPalette.ColorRole.Button, QColor(CARD))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(TEXT))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(ACCENT))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#03211D"))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#122236"))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(TEXT))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(MUTED))
    app.setPalette(palette)
    app.setStyleSheet(build_qss())
