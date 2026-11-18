from pathlib import Path
from openpyxl import load_workbook, Workbook
from school_contests import excel
from school_contests.storage import Store


def test_template_roundtrip_and_optional_team(tmp_path: Path, store: Store, event_id: int) -> None:
    path = tmp_path / "template.xlsx"
    excel.template(path)
    workbook = load_workbook(path)
    workbook["Участники"].append(["Иван Иванов", "289 СПб", "9в"])
    workbook.save(path)
    rows = excel.read_rows(path)
    clean, errors, warnings = excel.validate_rows(rows, store.snapshot(event_id))
    assert not errors
    assert clean[0]["category"] == 9
    assert clean[0]["team_number"] is None
    store.import_participants(event_id, clean)
    assert len(store.snapshot(event_id)["participants"]) == 1


def test_conflicts_and_duplicates(store: Store, event_id: int) -> None:
    row = dict(name="Иван", school="Школа", class_name="1а", category="1", team_number="3", team_name="А")
    _, errors, warnings = excel.validate_rows([row, dict(row, team_name="Б")], store.snapshot(event_id))
    assert len(errors) == 2
    assert len(warnings) == 2


def test_export_six_sheets_keeps_zero_blank_and_literal_text(tmp_path: Path, store: Store, event_id: int) -> None:
    team = store.save_team(event_id, 1, "Радуга")
    participant = store.save_participant(event_id, "=1+1", "289 СПб", "9в", 9, team)
    first = store.save_contest(event_id, "А")
    store.save_contest(event_id, "Б")
    store.save_score(event_id, participant, first, 0)
    path = tmp_path / "results.xlsx"
    excel.export(path, store.snapshot(event_id))
    workbook = load_workbook(path)
    assert len(workbook.sheetnames) == 6
    sheet = workbook.worksheets[0]
    assert sheet["A2"].value == "=1+1" and sheet["A2"].data_type == "s"
    assert sheet["G2"].value == 0 and sheet["H2"].value is None
    for result_sheet in workbook.worksheets[1:]:
        assert all(row[1] is None for row in result_sheet.iter_rows(min_row=2, values_only=True))


def test_export_only_positive_winners_in_corresponding_contest(tmp_path: Path, store: Store, event_id: int) -> None:
    team = store.save_team(event_id, 1)
    positive = store.save_participant(event_id, "Призёр", "1", "9а", 9, team)
    zero = store.save_participant(event_id, "Ноль", "1", "9а", 9, team)
    first = store.save_contest(event_id, "Первый")
    second = store.save_contest(event_id, "Второй")
    store.save_score(event_id, positive, first, 5)
    store.save_score(event_id, positive, second, 0)
    store.save_score(event_id, zero, first, 0)
    path = tmp_path / "positive-results.xlsx"
    excel.export(path, store.snapshot(event_id))
    workbook = load_workbook(path)
    for sheet in workbook.worksheets[1:]:
        winners = [row for row in sheet.iter_rows(min_row=2, values_only=True) if row[1] is not None]
        assert len(winners) == 1
        assert winners[0][1] == 1
        assert winners[0][4] == 5
    contest_winners = [row for row in workbook["По конкурсам"].iter_rows(min_row=2, values_only=True)
                       if row[1] is not None]
    assert contest_winners[0][0] == "Первый"
