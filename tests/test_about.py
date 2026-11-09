from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QApplication, QPushButton

from school_contests import __version__
from school_contests.storage import Store
from school_contests.ui.about import AboutDialog
from school_contests.ui.window import Window


def test_about_uses_current_version_and_public_links(qtbot) -> None:
    dialog = AboutDialog()
    qtbot.addWidget(dialog)
    assert dialog.version_label.text() == f"Версия {__version__}"
    assert dialog.developer_label.text()
    assert "https://github.com/Naisa27/contests" in dialog.project_link.text()
    assert dialog.project_link.openExternalLinks()
    assert "mailto:r-r-y@yandex.ru" in dialog.email_link.text()
    assert "https://t.me/reginar27" in dialog.telegram_link.text()
    assert dialog.email_link.openExternalLinks()
    assert dialog.telegram_link.openExternalLinks()
    dialog.close()


def test_about_opens_from_home_button_and_help_menu(qtbot, store: Store, event_id: int) -> None:
    window = Window(store)
    qtbot.addWidget(window)
    window.show()
    opened = []

    def close_about() -> None:
        dialog = QApplication.activeModalWidget()
        assert isinstance(dialog, AboutDialog)
        opened.append(dialog.version_label.text())
        dialog.accept()

    home_button = next(button for button in window.home.findChildren(QPushButton) if button.text() == "О программе")
    QTimer.singleShot(0, close_about)
    qtbot.mouseClick(home_button, Qt.MouseButton.LeftButton)
    window.open_event(event_id)
    QTimer.singleShot(0, close_about)
    window.about_action.trigger()
    assert opened == [f"Версия {__version__}"] * 2
    window.close()
