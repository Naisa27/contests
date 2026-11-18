from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLineEdit

from school_contests.storage import Store
from school_contests.ui.window import Window


def test_school_options_sort_numbers_before_alphabetical_names(qtbot, store: Store, event_id: int) -> None:
    for school in ["10", "2", "100", "1", "Школа 2", "Гимназия", "Академия", "№ 5", "02"]:
        store.save_participant(event_id, "Иван", school, "9а", 9)
    window = Window(store)
    qtbot.addWidget(window)
    window.open_event(event_id)
    combo = window.school_filter
    assert [combo.itemData(i) for i in range(combo.count())] == [
        None, "1", "02", "2", "10", "100", "Академия", "Гимназия", "Школа 2", "№ 5",
    ]
    combo.setCurrentIndex(combo.findData("10"))
    store.save_participant(event_id, "Пётр", "3", "8а", 8)
    window.model.reload()
    assert [combo.itemData(i) for i in range(1, 7)] == ["1", "02", "2", "3", "10", "100"]
    assert combo.currentData() == "10"
    assert window.proxy.rowCount() == 1


def test_school_category_and_name_filters_keep_score_target(qtbot, store: Store, event_id: int) -> None:
    team = store.save_team(event_id, 1)
    store.save_participant(event_id, "Иванов Иван", "Школа 10", "8а", 8, team)
    store.save_participant(event_id, "Иванов Иван", "Школа 1", "9а", 9, team)
    target = store.save_participant(event_id, "Иванов Иван", "Школа 10", "9а", 9, team)
    store.save_participant(event_id, "Петров Пётр", "Школа 10", "9б", 9, team)
    contest = store.save_contest(event_id, "Логика")
    window = Window(store)
    qtbot.addWidget(window)
    window.open_event(event_id)
    window.school_filter.setCurrentIndex(window.school_filter.findData("Школа 10"))
    assert window.proxy.rowCount() == 3
    window.category_filter.setCurrentIndex(window.category_filter.findData(9))
    assert window.proxy.rowCount() == 2
    search = next(widget for widget in window.event_page.findChildren(QLineEdit)
                  if widget.accessibleName() == "Поиск по ФИО")
    search.setText("ИВАНОВ")
    assert window.proxy.rowCount() == 1
    window.proxy.sort(1, Qt.SortOrder.DescendingOrder)
    assert window.proxy.setData(window.proxy.index(0, 5), "13")
    assert store.snapshot(event_id)["scores"] == {(target, contest): 13}
    window.school_filter.setCurrentIndex(0)
    assert window.proxy.rowCount() == 2
    window.category_filter.setCurrentIndex(0)
    search.clear()
    assert window.proxy.rowCount() == 4


def test_school_options_refresh_preserve_selection_and_use_all_participants(qtbot, store: Store, event_id: int) -> None:
    participant = store.save_participant(event_id, "Иван", "Школа 1", "9а", 9)
    window = Window(store)
    qtbot.addWidget(window)
    window.open_event(event_id)
    combo = window.school_filter
    assert [combo.itemData(i) for i in range(combo.count())] == [None, "Школа 1"]
    combo.setCurrentIndex(combo.findData("Школа 1"))
    window.category_filter.setCurrentIndex(window.category_filter.findData(9))
    store.save_participant(event_id, "Пётр", "Школа 2", "8а", 8)
    store.save_participant(event_id, "Анна", "Школа 2", "8б", 8)
    other_event = store.save_event("Другое", "2026-11-18", "Организатор")
    store.save_participant(other_event, "Олег", "Чужая школа", "8а", 8)
    window.model.reload()
    assert [combo.itemData(i) for i in range(combo.count())] == [None, "Школа 1", "Школа 2"]
    assert combo.currentData() == "Школа 1"
    assert window.proxy.rowCount() == 1
    store.save_participant(event_id, "Иван", "Школа 2", "9а", 9, participant_id=participant)
    window.model.reload()
    assert combo.currentData() is None
    assert window.proxy.school is None
    assert window.proxy.rowCount() == 1
    window.category_filter.setCurrentIndex(0)
    assert window.proxy.rowCount() == 3


def test_school_filter_empty_event_and_switching_events(qtbot, store: Store, event_id: int) -> None:
    window = Window(store)
    qtbot.addWidget(window)
    window.open_event(event_id)
    assert window.school_filter.count() == 1
    assert window.school_filter.currentText() == "Все школы"
    store.save_participant(event_id, "Иван", "Школа 1", "9а", 9)
    window.model.reload()
    window.school_filter.setCurrentIndex(1)
    other_event = store.save_event("Другое", "2026-11-18", "Организатор")
    window.open_event(other_event)
    assert window.school_filter.count() == 1
    assert window.proxy.school is None
    assert window.proxy.rowCount() == 0
