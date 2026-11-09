"""Шаблон, проверка импорта и экспорт всех зачётов в XLSX."""

from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

from .domain import KINDS, calculate, category_from_class, integer, preliminary, team_label

HEADERS = ["ФИО", "Школа", "Класс", "Категория", "Номер команды", "Название команды"]
KEYS = ["name", "school", "class_name", "category", "team_number", "team_name"]


def write_text(sheet: Any, row: list[Any]) -> None:
    """Текст из пользовательских полей не превращается в формулы Excel."""
    sheet.append(row)
    for cell in sheet[sheet.max_row]:
        if isinstance(cell.value, str):
            cell.data_type = "s"


def style_workbook(workbook: Workbook) -> None:
    for sheet in workbook:
        sheet.freeze_panes = "A2"
        sheet.auto_filter.ref = sheet.dimensions
        for cell in sheet[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="17675E")
        for column in sheet.columns:
            width = min(65, max(15, max(len(str(cell.value or "")) for cell in column) + 3))
            sheet.column_dimensions[get_column_letter(column[0].column)].width = width
        for row in sheet:
            for cell in row:
                cell.alignment = Alignment(vertical="top", wrap_text=True)


def template(path: Path) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Участники"
    write_text(sheet, HEADERS)
    sheet = workbook.create_sheet("Инструкция")
    for row in [["Заполнение шаблона"], ["На листе «Участники» обязательны ФИО, школа и класс."],
                ["Категория определяется по классу или указывается числом 1–11."],
                ["Команда необязательна. Название команды указывается только вместе с номером."],
                ["Баллы конкурсов этим шаблоном не импортируются."]]:
        write_text(sheet, row)
    style_workbook(workbook)
    workbook.save(path)


def read_rows(path: Path) -> list[dict[str, Any]]:
    workbook = load_workbook(path, read_only=True, data_only=False)
    try:
        sheet = workbook["Участники"] if "Участники" in workbook.sheetnames else workbook.active
        rows = sheet.iter_rows(values_only=True)
        header = [str(value or "").strip() for value in next(rows, ())]
        if any(column not in header for column in HEADERS[:3]):
            raise ValueError("В первой строке нужны колонки: ФИО, Школа, Класс. Скачайте шаблон в приложении.")
        if any(header.count(column) > 1 for column in HEADERS):
            raise ValueError("В файле повторяются заголовки колонок.")
        result = []
        for number, values in enumerate(rows, 2):
            if all(value is None or str(value).strip() == "" for value in values):
                continue
            row: dict[str, Any] = {"row_number": number}
            for column, key in zip(HEADERS, KEYS):
                value = values[header.index(column)] if column in header and header.index(column) < len(values) else None
                row[key] = "" if value is None else str(value).strip()
            if not row["category"]:
                row["category"] = str(category_from_class(row["class_name"]) or "")
            result.append(row)
        return result
    finally:
        workbook.close()


def validate_rows(rows: list[dict[str, Any]], snapshot: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[int, list[str]], dict[int, list[str]]]:
    clean, errors, warnings = [], defaultdict(list), defaultdict(list)
    names: dict[int, set[str]] = defaultdict(set)
    known_names = {t["number"]: t["name"] for t in snapshot["teams"]}
    existing = {(p["name"].casefold(), p["school"].casefold(), p["class_name"].casefold()) for p in snapshot["participants"]}
    duplicates = Counter(tuple(str(row[key]).strip().casefold() for key in KEYS[:3]) for row in rows)
    for index, row in enumerate(rows):
        values: dict[str, Any] = dict(row)
        for key, label in zip(KEYS[:3], HEADERS[:3]):
            if not str(values[key]).strip():
                errors[index].append(f"Заполните «{label}»")
        try:
            values["category"] = integer(values["category"] or category_from_class(values["class_name"]), "Категория", 1, 11)
        except ValueError as exc:
            errors[index].append(str(exc))
        try:
            values["team_number"] = integer(values["team_number"], "Номер команды", 1) if values["team_number"] is not None and str(values["team_number"]).strip() else None
        except ValueError as exc:
            errors[index].append(str(exc))
            values["team_number"] = None
        values["team_name"] = str(values["team_name"]).strip()
        if values["team_name"] and values["team_number"] is None:
            errors[index].append("У названия команды должен быть номер")
        if values["team_number"] is not None:
            number = values["team_number"]
            if values["team_name"]:
                names[number].add(values["team_name"])
            if known_names.get(number) and values["team_name"] and known_names[number] != values["team_name"]:
                warnings[index].append(f"Команда № {number} будет переименована: {known_names[number]} → {values['team_name']}")
        identity = tuple(str(values[key]).strip().casefold() for key in KEYS[:3])
        if identity in existing or duplicates[identity] > 1:
            warnings[index].append("Возможный дубль участника")
        clean.append(values)
    for index, values in enumerate(clean):
        if len(names[values["team_number"]]) > 1:
            errors[index].append("Разные названия одного номера команды: задайте единое название")
    return clean, dict(errors), dict(warnings)


def export(path: Path, snapshot: dict[str, Any]) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Участники и баллы"
    write_text(sheet, HEADERS + [c["name"] for c in snapshot["contests"]])
    teams = {t["id"]: t for t in snapshot["teams"]}
    for participant in snapshot["participants"]:
        team = teams.get(participant["team_id"])
        write_text(sheet, [participant["name"], participant["school"], participant["class_name"], participant["category"],
                           team["number"] if team else None, team["name"] if team else ""] +
                   [snapshot["scores"].get((participant["id"], c["id"])) for c in snapshot["contests"]])
    notice = "Предварительные результаты: незаполненные баллы учитываются как 0" if preliminary(snapshot) else "Все баллы заполнены"
    stamp = f"{snapshot['event']['name']} | Сформировано {datetime.now():%d.%m.%Y %H:%M}"
    standings = calculate(snapshot)
    for kind, title in KINDS.items():
        sheet = workbook.create_sheet(title)
        write_text(sheet, ["Группа", "Место", "Участник или команда", "Школа, класс", "Баллы"])
        for standing in standings:
            if standing.kind == kind:
                write_text(sheet, [standing.title])
                for winner in standing.winners:
                    write_text(sheet, [standing.title, winner.place, winner.name, winner.detail, winner.points])
        write_text(sheet, [])
        write_text(sheet, [stamp])
        write_text(sheet, [notice])
    write_text(workbook.worksheets[0], [])
    write_text(workbook.worksheets[0], [stamp])
    write_text(workbook.worksheets[0], [notice])
    style_workbook(workbook)
    workbook.save(path)
