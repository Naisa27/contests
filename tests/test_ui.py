from PySide6.QtCore import Qt
from PySide6.QtTest import QAbstractItemModelTester
from school_contests.storage import Store
from school_contests.ui.models import ParticipantsModel, NameFilter
from school_contests.ui.window import Window
from school_contests.ui.theme import QSS
from school_contests.ui.tasks import run_task
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QWidget
from PySide6.QtWidgets import QLineEdit
import threading
import pytest


def test_filter_sort_edits_correct_participant(qtbot, store: Store, event_id: int) -> None:
    team = store.save_team(event_id, 1)
    store.save_participant(event_id, "Алексей", "Школа", "1а", 1, team)
    target = store.save_participant(event_id, "ИВАН Ёлкин", "Школа", "1а", 1, team)
    contest = store.save_contest(event_id, "Логика")
    model = ParticipantsModel(store, event_id, lambda: None)
    tester = QAbstractItemModelTester(model, QAbstractItemModelTester.FailureReportingMode.Warning)
    proxy = NameFilter()
    proxy.setSourceModel(model)
    proxy.search("иван ё")
    proxy.sort(1, Qt.SortOrder.DescendingOrder)
    assert proxy.rowCount() == 1
    assert proxy.setData(proxy.index(0, 5), "17")
    assert store.snapshot(event_id)["scores"] == {(target, contest): 17}


def test_cancel_team_keeps_blank_and_rejects_bad_input(qtbot, store: Store, event_id: int) -> None:
    store.save_participant(event_id, "Иван", "Школа", "1а", 1)
    store.save_contest(event_id, "Логика")
    model = ParticipantsModel(store, event_id, lambda: None)
    assert not model.setData(model.index(0, 5), "8")
    assert model.data(model.index(0, 5)) == ""
    with qtbot.waitSignal(model.failed):
        assert not model.setData(model.index(0, 5), "1.5")
    assert store.snapshot(event_id)["scores"] == {}


def test_window_navigation_and_results(qtbot, store: Store, event_id: int) -> None:
    window = Window(store)
    window.setStyleSheet(QSS)
    qtbot.addWidget(window)
    window.show()
    window.show_events()
    window.open_event(event_id)
    window.tabs.setCurrentIndex(1)
    assert window.results.widget() is not None
    window.close()


def test_task_keeps_event_loop_running(qtbot) -> None:
    parent = QWidget()
    qtbot.addWidget(parent)
    gate = threading.Event()
    timer = QTimer(parent)
    timer.setSingleShot(True)
    timer.timeout.connect(gate.set)
    timer.start(50)
    assert run_task(parent, "Проверка", lambda: gate.wait(2)) is True
    with pytest.raises(ValueError, match="Ошибка операции"):
        run_task(parent, "Проверка ошибки", lambda: (_ for _ in ()).throw(ValueError("Ошибка операции")))


def test_existing_numeric_score_can_be_cleared_in_table(qtbot, store: Store, event_id: int) -> None:
    team = store.save_team(event_id, 1)
    participant = store.save_participant(event_id, "Иван", "Школа", "1а", 1, team)
    contest = store.save_contest(event_id, "Логика")
    store.save_score(event_id, participant, contest, 17)
    window = Window(store)
    qtbot.addWidget(window)
    window.open_event(event_id)
    window.show()
    index = window.proxy.index(0, 5)
    window.table.edit(index)
    editor = window.table.findChild(QLineEdit)
    assert editor is not None
    editor.clear()
    qtbot.keyClick(editor, Qt.Key.Key_Return)
    qtbot.waitUntil(lambda: store.snapshot(event_id)["scores"] == {})
    assert window.proxy.data(window.proxy.index(0, 5)) == ""
    window.close()
