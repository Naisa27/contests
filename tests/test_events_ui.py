from PySide6.QtCore import Qt

from school_contests.storage import Store
from school_contests.ui.window import Window


def test_events_require_row_selection_and_open_correct_sorted_event(qtbot, store: Store, event_id: int) -> None:
    other = store.save_event("Второе мероприятие", "2027-01-15", "Организатор")
    window = Window(store)
    qtbot.addWidget(window)
    window.show()
    window.show_events()
    table = window.events_table
    assert not window.open_event_button.isEnabled()
    assert not window.edit_event_button.isEnabled()
    assert table.model().columnCount() == 3
    assert table.model().index(0, 0).data() == "15.01.2027"
    table.selectRow(0)
    assert window.open_event_button.isEnabled()
    assert window.edit_event_button.isEnabled()
    table.clearSelection()
    assert not window.open_event_button.isEnabled()
    assert not window.edit_event_button.isEnabled()
    table.sortByColumn(0, Qt.SortOrder.AscendingOrder)
    table.selectRow(0)
    qtbot.mouseClick(window.open_event_button, Qt.MouseButton.LeftButton)
    assert window.event_id == event_id
    window.show_events()
    assert not window.open_event_button.isEnabled()
    assert not window.edit_event_button.isEnabled()
    window.events_table.selectRow(0)
    qtbot.mouseClick(window.open_event_button, Qt.MouseButton.LeftButton)
    assert window.event_id == other
    window.close()


def test_empty_events_have_disabled_actions(qtbot, store: Store) -> None:
    window = Window(store)
    qtbot.addWidget(window)
    window.show_events()
    assert window.events_table.model().rowCount() == 0
    assert not window.open_event_button.isEnabled()
    assert not window.edit_event_button.isEnabled()
    window.close()
