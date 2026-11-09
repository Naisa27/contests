from pathlib import Path
import json
import pytest
from sqlalchemy import select, insert, update
from sqlalchemy.exc import IntegrityError
from school_contests.storage import Store, results, scores, participants
from school_contests.domain import calculate, preliminary


def test_results_and_changes_are_persistent(store: Store, event_id: int) -> None:
    team = store.save_team(event_id, 3, "Радуга")
    contest = store.save_contest(event_id, "Логика")
    participant = store.save_participant(event_id, "Иванов Иван", "289 СПб", "9в", 9)
    assert preliminary(store.snapshot(event_id))
    with pytest.raises(ValueError, match="команду"):
        store.save_score(event_id, participant, contest, 12)
    store.save_score(event_id, participant, contest, 12, team)
    snapshot = store.snapshot(event_id)
    assert not preliminary(snapshot)
    assert snapshot["participants"][0]["team_id"] == team
    assert {row.kind for row in calculate(snapshot)} == {"team", "individual", "category", "within_team", "contest"}
    with store.engine.connect() as connection:
        payload = json.loads(connection.execute(select(results.c.payload)).scalar_one())
        assert payload[0]["winners"][0]["points"] == 12
    store.save_team(event_id, 3, "Новое имя", team)
    assert calculate(store.snapshot(event_id))[0].winners[0].name == "№ 3 — Новое имя"
    with pytest.raises(ValueError, match="есть оценки"):
        store.save_participant(event_id, "Иванов Иван", "289 СПб", "9в", 9, None, participant)
    store.save_score(event_id, participant, contest, 0)
    assert store.snapshot(event_id)["scores"][(participant, contest)] == 0
    store.save_score(event_id, participant, contest, "")
    assert store.snapshot(event_id)["scores"] == {}
    reopened = Store(store.path)
    assert reopened.snapshot(event_id)["participants"][0]["name"] == "Иванов Иван"
    reopened.close()


def test_cross_event_data_and_duplicate_team_rejected(store: Store, event_id: int) -> None:
    team = store.save_team(event_id, 1)
    with pytest.raises(ValueError):
        store.save_team(event_id, 1)
    other = store.save_event("Другое", "2026-11-10", "Школа")
    other_team = store.save_team(other, 1)
    with pytest.raises(ValueError):
        store.save_participant(event_id, "А", "Б", "1а", 1, other_team)
    participant = store.save_participant(event_id, "А", "Б", "1а", 1)
    contest = store.save_contest(other, "Чужой")
    with pytest.raises(ValueError):
        store.save_score(event_id, participant, contest, 5, team)
    assert store.snapshot(event_id)["participants"][0]["team_id"] is None


def test_db_rejects_score_without_team(store: Store, event_id: int) -> None:
    participant = store.save_participant(event_id, "А", "Б", "1", 1)
    contest = store.save_contest(event_id, "Логика")
    with pytest.raises(IntegrityError), store.engine.begin() as connection:
        connection.execute(insert(scores).values(event_id=event_id, participant_id=participant, contest_id=contest, points=1))


def test_import_rolls_back_participants_and_teams(store: Store, event_id: int) -> None:
    row = dict(name="А", school="Б", class_name="1а", category=1, team_number=7, team_name="Новая")
    with pytest.raises(ValueError):
        store.import_participants(event_id, [row, dict(row, category=12)])
    assert store.snapshot(event_id)["participants"] == []
    assert store.snapshot(event_id)["teams"] == []


def test_backup_restore(store: Store, event_id: int, tmp_path: Path) -> None:
    copy = tmp_path / "copy.sqlite3"
    store.backup(copy)
    store.save_contest(event_id, "Лишний")
    previous = store.restore(copy)
    assert previous.exists()
    assert store.snapshot(event_id)["contests"] == []
    old = Store(previous)
    assert len(old.snapshot(event_id)["contests"]) == 1
    old.close()


def test_remove_contest_recalculates(store: Store, event_id: int) -> None:
    team = store.save_team(event_id, 1)
    participant = store.save_participant(event_id, "А", "Б", "1а", 1, team)
    first = store.save_contest(event_id, "Один")
    second = store.save_contest(event_id, "Два")
    store.save_score(event_id, participant, first, 10)
    store.save_score(event_id, participant, second, 20)
    store.remove_contest(event_id, first)
    assert calculate(store.snapshot(event_id))[0].winners[0].points == 20


def test_team_and_category_transfer_rebuilds_all_groups(store: Store, event_id: int) -> None:
    first = store.save_team(event_id, 1, "Один")
    second = store.save_team(event_id, 2, "Два")
    contest = store.save_contest(event_id, "Логика")
    participant = store.save_participant(event_id, "Иван", "Школа", "8в", 8, first)
    unassigned = store.save_participant(event_id, "Мария", "Школа", "9в", 9)
    store.save_score(event_id, participant, contest, 10)
    store.save_participant(event_id, "Иван", "Школа", "8в", 9, second, participant)
    standings = calculate(store.snapshot(event_id))
    team_winners = next(row for row in standings if row.kind == "team").winners
    assert [winner.entity_id for winner in team_winners] == [second]
    assert [row.group_id for row in standings if row.kind == "category"] == [9]
    assert [row.group_id for row in standings if row.kind == "within_team"] == [second]
    individual = next(row for row in standings if row.kind == "individual")
    assert {winner.entity_id for winner in individual.winners} == {participant, unassigned}


def test_failed_recalculation_rolls_back_score_and_assignment(store: Store, event_id: int, monkeypatch) -> None:
    team = store.save_team(event_id, 1)
    contest = store.save_contest(event_id, "Логика")
    participant = store.save_participant(event_id, "Иван", "Школа", "1а", 1)

    def fail(*args) -> None:
        raise RuntimeError("Расчёт прерван")

    monkeypatch.setattr(store, "refresh", fail)
    with pytest.raises(RuntimeError):
        store.save_score(event_id, participant, contest, 20, team)
    snapshot = store.snapshot(event_id)
    assert snapshot["scores"] == {}
    assert snapshot["participants"][0]["team_id"] is None
