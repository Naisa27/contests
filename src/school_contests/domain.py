"""Независимые от интерфейса правила расчёта финалистов."""

from dataclasses import dataclass
import re
from typing import Any


def category_from_class(value: str) -> int | None:
    match = re.match(r"^\s*(1[01]|[1-9])(?:\s*[^\d].*)?$", value)
    return int(match[1]) if match else None


def integer(value: Any, label: str, minimum: int = 0, maximum: int = 2_147_483_647) -> int:
    """Не допускает округления дробей и переполнения SQLite INTEGER."""
    if isinstance(value, bool) or not re.fullmatch(r"\d+", str(value).strip()):
        raise ValueError(f"{label}: введите целое число от {minimum} до {maximum}.")
    number = int(str(value).strip())
    if not minimum <= number <= maximum:
        raise ValueError(f"{label}: допустимы значения от {minimum} до {maximum}.")
    return number


def team_label(team: dict[str, Any] | None) -> str:
    if team is None:
        return "Без команды"
    return f"№ {team['number']}" + (f" — {team['name']}" if team['name'] else "")


@dataclass(frozen=True)
class Winner:
    entity_id: int
    name: str
    detail: str
    points: int
    place: int = 0


@dataclass(frozen=True)
class Standing:
    kind: str
    group_id: int
    title: str
    winners: tuple[Winner, ...]


KINDS = {
    "team": "Командный зачёт",
    "individual": "Общий индивидуальный",
    "category": "По категориям",
    "within_team": "Внутри команд",
    "contest": "По конкурсам",
}


def rank(entries: list[Winner]) -> tuple[Winner, ...]:
    """Три лучших различных результата: 100, 100, 90, 80 → 1, 1, 2, 3."""
    levels = sorted({row.points for row in entries}, reverse=True)[:3]
    return tuple(
        Winner(row.entity_id, row.name, row.detail, row.points, levels.index(row.points) + 1)
        for row in sorted(entries, key=lambda row: (-row.points, row.name.casefold(), row.entity_id))
        if row.points in levels
    )


def calculate(snapshot: dict[str, Any]) -> list[Standing]:
    participants, contests, teams = (snapshot[key] for key in ("participants", "contests", "teams"))
    if not participants or not contests:
        return []
    scores = snapshot["scores"]
    totals = {p["id"]: sum(scores.get((p["id"], c["id"]), 0) for c in contests) for p in participants}

    def entries(rows: list[dict[str, Any]], contest_id: int | None = None) -> list[Winner]:
        return [Winner(p["id"], p["name"], f"{p['school']}, {p['class_name']}",
                       totals[p["id"]] if contest_id is None else scores.get((p["id"], contest_id), 0)) for p in rows]

    occupied = [t for t in teams if any(p["team_id"] == t["id"] for p in participants)]
    result = [Standing("team", 0, KINDS["team"], rank([
        Winner(t["id"], team_label(t), "", sum(totals[p["id"]] for p in participants if p["team_id"] == t["id"]))
        for t in occupied
    ])), Standing("individual", 0, KINDS["individual"], rank(entries(participants)))]
    result.extend(Standing("category", category, f"Категория {category}", rank(entries([
        p for p in participants if p["category"] == category
    ]))) for category in sorted({p["category"] for p in participants}))
    result.extend(Standing("within_team", t["id"], team_label(t), rank(entries([
        p for p in participants if p["team_id"] == t["id"]
    ]))) for t in occupied)
    result.extend(Standing("contest", c["id"], c["name"], rank(entries(participants, c["id"]))) for c in contests)
    return result


def preliminary(snapshot: dict[str, Any]) -> bool:
    return len(snapshot["scores"]) < len(snapshot["participants"]) * len(snapshot["contests"])
