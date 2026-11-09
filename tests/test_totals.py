from PySide6.QtCore import Qt
from PySide6.QtTest import QAbstractItemModelTester

from school_contests.storage import Store
from school_contests.ui.models import ParticipantsModel, NameFilter


def test_total_tracks_edits_clearing_and_contest_changes(qtbot, store: Store, event_id: int) -> None:
    team = store.save_team(event_id, 1)
    store.save_participant(event_id, "Иван", "Школа", "1а", 1, team)
    model = ParticipantsModel(store, event_id, lambda: None)
    tester = QAbstractItemModelTester(model, QAbstractItemModelTester.FailureReportingMode.Warning)
    assert model.columnCount() == 5
    first = store.save_contest(event_id, "Логика")
    second = store.save_contest(event_id, "Эрудиция")
    model.reload()
    total = model.index(0, 7)
    assert model.headerData(7, Qt.Orientation.Horizontal) == "ИТОГО"
    assert model.data(total) == 0
    assert not model.flags(total) & Qt.ItemFlag.ItemIsEditable
    assert not model.setData(total, "999")
    with qtbot.waitSignal(model.dataChanged) as changed:
        assert model.setData(model.index(0, 5), "17")
    assert changed.args[1].column() == 7
    assert model.data(total) == 17
    assert model.setData(model.index(0, 6), "8")
    assert model.data(total) == 25
    assert not model.setData(model.index(0, 6), "-3")
    assert model.data(total) == 25
    assert model.setData(model.index(0, 5), "")
    assert model.data(total) == 8
    assert model.setData(model.index(0, 6), "0")
    assert model.data(total) == 0
    store.remove_contest(event_id, first)
    model.reload()
    assert model.columnCount() == 7
    assert model.headerData(6, Qt.Orientation.Horizontal) == "ИТОГО"
    store.remove_contest(event_id, second)
    model.reload()
    assert model.columnCount() == 5


def test_total_sorting_updates_after_score_edit(qtbot, store: Store, event_id: int) -> None:
    team = store.save_team(event_id, 1)
    first = store.save_participant(event_id, "Алексей", "Школа", "1а", 1, team)
    second = store.save_participant(event_id, "Иван", "Школа", "1а", 1, team)
    contest = store.save_contest(event_id, "Логика")
    store.save_score(event_id, first, contest, 9)
    store.save_score(event_id, second, contest, 10)
    model = ParticipantsModel(store, event_id, lambda: None)
    proxy = NameFilter()
    proxy.setSourceModel(model)
    proxy.sort(6, Qt.SortOrder.DescendingOrder)
    assert proxy.data(proxy.index(0, 1)) == "Иван"
    assert proxy.setData(proxy.index(1, 5), "11")
    assert proxy.data(proxy.index(0, 1)) == "Алексей"
    assert proxy.data(proxy.index(0, 6)) == 11
    proxy.search("иван")
    assert proxy.data(proxy.index(0, 6)) == 10
