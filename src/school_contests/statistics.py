"""Подсчёт участников мероприятия без зависимости от фильтров интерфейса."""

from collections import Counter
from dataclasses import dataclass
from typing import Any

from .domain import team_label


@dataclass(frozen=True)
class ParticipantStatistics:
    total: int
    by_school: tuple[tuple[str, int], ...]
    by_category: tuple[tuple[int, int], ...]
    by_school_category: tuple[tuple[str, int, int], ...]
    duplicate_names: tuple[tuple[str, str, str], ...]
    by_team: tuple[tuple[str, int], ...]


def participant_statistics(participants: list[dict[str, Any]],
                           teams: list[dict[str, Any]] | None = None) -> ParticipantStatistics:
    """Каждая запись учитывается отдельно; совпадение ФИО строгое, включая регистр."""
    schools = Counter(row["school"] for row in participants)
    categories = Counter(row["category"] for row in participants)
    school_categories = Counter((row["school"], row["category"]) for row in participants)
    names = Counter(row["name"] for row in participants)
    team_counts = Counter(row.get("team_id") for row in participants)
    by_team = [(team_label(team), team_counts[team["id"]])
               for team in sorted(teams or [], key=lambda team: team["number"])]
    if team_counts[None]:
        by_team.append((team_label(None), team_counts[None]))
    duplicates = sorted(
        ((row["name"], row["school"], row["class_name"])
         for row in participants if names[row["name"]] > 1),
        key=lambda row: (row[0].casefold(), row[0], row[1].casefold(), row[1], row[2]),
    )
    return ParticipantStatistics(
        total=len(participants),
        by_school=tuple(sorted(schools.items(), key=lambda row: (row[0].casefold(), row[0]))),
        by_category=tuple(sorted(categories.items())),
        by_school_category=tuple(
            (school, category, school_categories[school, category])
            for school, category in sorted(school_categories, key=lambda key: (key[0].casefold(), key[0], key[1]))
        ),
        duplicate_names=tuple(duplicates),
        by_team=tuple(by_team),
    )
