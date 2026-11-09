from school_contests.storage import Store
from school_contests.ui.models import ParticipantsModel, NameFilter
from school_contests.ui.window import Window


def test_category_and_name_filters_combine_and_keep_correct_score_target(qtbot, store: Store, event_id: int) -> None:
    team = store.save_team(event_id, 1)
    store.save_participant(event_id, "Иванов Иван", "Школа", "8а", 8, team)
    target = store.save_participant(event_id, "Иванов Иван", "Школа", "9а", 9, team)
    store.save_participant(event_id, "Петров Пётр", "Школа", "9б", 9, team)
    contest = store.save_contest(event_id, "Логика")
    model = ParticipantsModel(store, event_id, lambda: None)
    proxy = NameFilter()
    proxy.setSourceModel(model)
    proxy.set_category(9)
    assert proxy.rowCount() == 2
    proxy.search("ИВАНОВ")
    assert proxy.rowCount() == 1
    assert proxy.setData(proxy.index(0, 5), "13")
    assert store.snapshot(event_id)["scores"] == {(target, contest): 13}
    proxy.set_category(None)
    assert proxy.rowCount() == 2
    proxy.search("")
    assert proxy.rowCount() == 3


def test_filter_options_refresh_after_participant_changes(qtbot, store: Store, event_id: int) -> None:
    participant = store.save_participant(event_id, "Иван", "Школа", "9а", 9)
    window = Window(store)
    qtbot.addWidget(window)
    window.open_event(event_id)
    combo = window.category_filter
    assert [combo.itemData(i) for i in range(combo.count())] == [None, 9]
    combo.setCurrentIndex(combo.findData(9))
    store.save_participant(event_id, "Пётр", "Школа", "8а", 8)
    window.model.reload()
    assert [combo.itemData(i) for i in range(combo.count())] == [None, 8, 9]
    assert combo.currentData() == 9
    assert window.proxy.rowCount() == 1
    store.save_participant(event_id, "Иван", "Школа", "8а", 8, participant_id=participant)
    window.model.reload()
    assert combo.currentData() is None
    assert window.proxy.category is None
    assert window.proxy.rowCount() == 2
    window.close()
