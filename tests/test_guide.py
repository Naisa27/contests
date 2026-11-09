from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QApplication

from school_contests.storage import Store
from school_contests.ui.guide import GuideDialog
from school_contests.ui.theme import QSS
from school_contests.ui.window import Window


def test_guide_navigation_boundaries_and_scroll_reset(qtbot) -> None:
    guide = GuideDialog()
    guide.setStyleSheet(QSS)
    qtbot.addWidget(guide)
    guide.show()
    assert not guide.previous.isEnabled()
    assert guide.next.isEnabled()
    assert "В какой последовательности действовать" in guide.body.toPlainText()
    qtbot.mouseClick(guide.next, Qt.MouseButton.LeftButton)
    assert guide.topics.currentRow() == 1
    assert "Создать мероприятие" in guide.body.toPlainText()
    guide.topics.setCurrentRow(6)
    guide.body.verticalScrollBar().setValue(guide.body.verticalScrollBar().maximum())
    qtbot.mouseClick(guide.next, Qt.MouseButton.LeftButton)
    assert "100, 100, 90, 80" in guide.body.toPlainText()
    assert guide.body.verticalScrollBar().value() == 0
    guide.topics.setCurrentRow(len(guide.sections) - 1)
    assert not guide.next.isEnabled()
    assert guide.previous.isEnabled()
    qtbot.mouseClick(guide.previous, Qt.MouseButton.LeftButton)
    assert "Восстановление заменяет все текущие данные" in guide.body.toPlainText()
    guide.close()


def test_guide_opens_from_home_events_and_conduct(qtbot, store: Store, event_id: int) -> None:
    window = Window(store)
    qtbot.addWidget(window)
    window.show()
    opened = []

    def close_guide() -> None:
        dialog = QApplication.activeModalWidget()
        assert isinstance(dialog, GuideDialog)
        opened.append(dialog.windowTitle())
        dialog.accept()

    for navigate in (lambda: None, window.show_events, lambda: window.open_event(event_id)):
        navigate()
        assert window.guide_button.isVisible()
        assert window.menuBar().cornerWidget(Qt.Corner.TopRightCorner).isAncestorOf(window.guide_button)
        QTimer.singleShot(0, close_guide)
        qtbot.mouseClick(window.guide_button, Qt.MouseButton.LeftButton)
    assert opened == ["Путеводитель по приложению"] * 3
    window.close()
