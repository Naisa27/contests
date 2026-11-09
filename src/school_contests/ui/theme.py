"""Общая светлая тема с видимым клавиатурным фокусом."""

QSS = """
QWidget { color: #183C3A; font-family: 'Segoe UI'; font-size: 14px; }
QMainWindow, QDialog { background: #F3F7F7; }
QLabel { background: transparent; }
QLabel#title { font-size: 28px; font-weight: 600; }
QLabel#hero { font-size: 36px; font-weight: 600; }
QLabel#clock { font-size: 44px; font-weight: 300; }
QLabel#muted { color: #496461; }
QLabel#error { color: #A32525; }
QLabel#eventsInstruction { font-size: 18px; font-weight: 600; padding: 8px 0; }
QPushButton#guideButton { margin: 4px 8px; padding: 6px 12px; }
QListWidget#guideTopics { border-radius: 4px; }
QListWidget#guideTopics::item { padding: 9px 10px; }
QListWidget#guideTopics::item:selected { background: #D1E8E2; color: #183C3A; }
QListWidget#guideTopics::item:focus { border: 1px solid #17675E; }
QLabel#guideSectionTitle { font-size: 23px; font-weight: 600; }
QTextBrowser#guideBody { background: white; border: 1px solid #B5C8C5; border-radius: 4px; padding: 14px; font-size: 16px; selection-background-color: #D1E8E2; selection-color: #183C3A; }
QPushButton { background: white; border: 1px solid #8CA6A3; border-radius: 6px; padding: 9px 16px; }
QPushButton:hover { background: #E5F1EF; border-color: #17675E; }
QPushButton:pressed { background: #CCE2DD; }
QPushButton:focus, QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDateEdit:focus { border: 2px solid #17675E; }
QPushButton#primary { background: #17675E; color: white; border-color: #17675E; font-weight: 600; }
QPushButton#primary:hover { background: #104E47; }
QPushButton:disabled { color: #718481; background: #E7EDEC; border-color: #CBD7D5; }
QPushButton#primary:disabled { color: #627572; background: #DFE8E6; border-color: #B5C8C5; }
QLineEdit, QComboBox, QSpinBox, QDateEdit { background: white; border: 1px solid #8CA6A3; border-radius: 4px; padding: 7px; min-height: 20px; }
QPlainTextEdit { background: white; border: 1px solid #8CA6A3; border-radius: 4px; padding: 8px; }
QPlainTextEdit:focus { border: 2px solid #17675E; }
QTableView, QListWidget { background: white; alternate-background-color: #F0F6F5; gridline-color: #D9E5E3; border: 1px solid #B5C8C5; selection-background-color: #D1E8E2; selection-color: #183C3A; }
QHeaderView::section { background: #E7F0EE; color: #183C3A; padding: 10px; border: none; border-bottom: 1px solid #B5C8C5; font-weight: 600; }
QTabWidget::pane { border: none; }
QTabBar::tab { padding: 12px 22px; background: #E4EEEC; margin-right: 4px; }
QTabBar::tab:selected { background: #17675E; color: white; }
QGroupBox { background: white; border: 1px solid #B5C8C5; border-radius: 6px; margin-top: 18px; padding: 16px; }
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; font-weight: 600; }
QScrollArea { background: transparent; border: none; }
QStatusBar { color: #496461; }
QWidget#resultsContent { background: #F3F7F7; }
QLabel#resultsHeading { font-size: 20px; font-weight: 600; margin-top: 4px; }
QLabel#resultsNotice { color: #68511A; background: #FFF5D6; border-radius: 4px; padding: 9px 12px; }
QFrame#resultCard { background: white; border: 1px solid #B5C8C5; border-radius: 6px; }
QLabel#resultCardTitle { font-size: 17px; font-weight: 600; padding-bottom: 4px; }
QFrame#winnerRow { border: none; border-radius: 4px; }
QFrame#winnerRow[place="1"] { background: #FFF5D6; }
QFrame#winnerRow[place="2"] { background: #EDF2F7; }
QFrame#winnerRow[place="3"] { background: #FCEBDD; }
QFrame#winnerRow[place="1"] QLabel#winnerPlace { color: #684B00; }
QFrame#winnerRow[place="2"] QLabel#winnerPlace { color: #34465A; }
QFrame#winnerRow[place="3"] QLabel#winnerPlace { color: #77421F; }
QLabel#winnerPlace, QLabel#winnerName, QLabel#winnerPoints { font-weight: 600; }
QLabel#winnerDetail { color: #496461; font-size: 13px; }
"""
