import pytest
from PySide6.QtCore import QRect, QSize
from school_contests.ui.placement import centered_frame
from school_contests.ui.window import Window
from school_contests.storage import Store


@pytest.mark.parametrize("available", [QRect(0, 0, 1920, 1040), QRect(-1920, -240, 1920, 1040),
                                      QRect(1920, 0, 1366, 728), QRect(0, 40, 800, 560)])
def test_frame_fits_and_centers_on_selected_monitor(available: QRect) -> None:
    frame = centered_frame(available, QSize(1240, 800), QSize(16, 39))
    assert available.contains(frame)
    assert abs(frame.center().x() - available.center().x()) <= 1
    assert abs(frame.center().y() - available.center().y()) <= 1


def test_first_show_centers_but_reopening_keeps_user_position(qtbot, store: Store) -> None:
    window = Window(store)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitUntil(lambda: window.screen().availableGeometry().contains(window.frameGeometry()))
    qtbot.waitUntil(lambda: abs(window.frameGeometry().center().x() - window.screen().availableGeometry().center().x()) <= 1)
    assert abs(window.frameGeometry().center().y() - window.screen().availableGeometry().center().y()) <= 1
    window.move(window.pos().x() + 5, window.pos().y() + 5)
    position = window.pos()
    window.hide()
    window.show()
    qtbot.wait(20)
    assert window.pos() == position
    window.close()
