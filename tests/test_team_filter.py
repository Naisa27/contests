from PySide6.QtCore import Qt

from school_contests.storage import Store
from school_contests.ui.window import Window


def test_team_filter_combines_filters_and_keeps_score_target(qtbot, store: Store, event_id: int) -> None:
    team = store.save_team(event_id, 2, "Совы")
    other = store.save_team(event_id, 10, "Совы")
    target = store.save_participant(event_id, "Иван", "289", "9а", 9, team)
    store.save_participant(event_id, "Иван", "289", "9а", 9, other)
    store.save_participant(event_id, "Иван", "193", "9а", 9, team)
    store.save_participant(event_id, "Иван", "289", "8а", 8, team)
    store.save_participant(event_id, "Пётр", "289", "9а", 9, team)
    store.save_participant(event_id, "Иван", "289", "9а", 9)
    contest = store.save_contest(event_id, "Логика")
    window = Window(store)
    qtbot.addWidget(window)
    window.open_event(event_id)
    combo = window.team_filter
    assert [combo.itemText(i) for i in range(combo.count())] == [
        "Все команды", "Без команды", "№ 2 — Совы", "№ 10 — Совы"]
    combo.setCurrentIndex(combo.findData(team))
    window.school_filter.setCurrentIndex(window.school_filter.findData("289"))
    window.category_filter.setCurrentIndex(window.category_filter.findData(9))
    window.proxy.search("ИВАН")
    window.proxy.sort(1, Qt.SortOrder.DescendingOrder)
    assert window.proxy.rowCount() == 1
    assert window.proxy.setData(window.proxy.index(0, 5), "17")
    assert store.snapshot(event_id)["scores"] == {(target, contest): 17}
    combo.setCurrentIndex(combo.findData(0))
    assert window.proxy.rowCount() == 1
    assert window.proxy.mapToSource(window.proxy.index(0, 1)).row() != -1
    combo.setCurrentIndex(0)
    assert window.proxy.rowCount() == 3


def test_team_options_refresh_and_reset_on_event_switch(qtbot, store: Store, event_id: int) -> None:
    team = store.save_team(event_id, 10, "Совы")
    participant = store.save_participant(event_id, "Иван", "289", "9а", 9)
    window = Window(store)
    qtbot.addWidget(window)
    window.open_event(event_id)
    combo = window.team_filter
    combo.setCurrentIndex(combo.findData(team))
    assert window.proxy.rowCount() == 0
    store.save_team(event_id, 2, "Новое имя", team_id=team)
    store.save_participant(event_id, "Иван", "289", "9а", 9, team, participant_id=participant)
    store.import_participants(event_id, [dict(name="Анна", school="193", class_name="8а", category=8,
                                            team_number=1, team_name="Импорт")])
    other = store.save_event("Другое", "2026-11-18", "Школа")
    store.save_team(other, 99, "Чужая команда")
    window.model.reload()
    assert combo.currentData() == team
    assert combo.currentText() == "№ 2 — Новое имя"
    assert [combo.itemText(i) for i in range(combo.count())] == [
        "Все команды", "Без команды", "№ 1 — Импорт", "№ 2 — Новое имя"]
    assert window.proxy.rowCount() == 1
    window.open_event(other)
    assert window.team_filter.currentData() is None
    assert window.proxy.team_id is None
    assert window.proxy.rowCount() == 0


def test_assigning_team_through_score_updates_filter_options(qtbot, store: Store, event_id: int) -> None:
    participant = store.save_participant(event_id, "Иван", "289", "9а", 9)
    contest = store.save_contest(event_id, "Логика")
    window = Window(store)
    qtbot.addWidget(window)
    window.open_event(event_id)
    combo = window.team_filter
    assert combo.count() == 2
    combo.setCurrentIndex(combo.findData(0))

    def choose_team() -> int:
        return store.save_team(event_id, 1, "Новая")

    window.model.choose_team = choose_team
    assert window.proxy.setData(window.proxy.index(0, 5), "3")
    assert window.proxy.rowCount() == 0
    assert combo.currentData() == 0
    assert combo.itemText(2) == "№ 1 — Новая"
    assert store.snapshot(event_id)["scores"] == {(participant, contest): 3}
