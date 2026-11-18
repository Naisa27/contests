from school_contests.statistics import participant_statistics


def test_counts_include_every_record_and_exact_duplicate_names() -> None:
    participants = [
        dict(name="Иванов Иван", school="289 СПб", class_name="2а", category=2),
        dict(name="Иванов Иван", school="193 Москва", class_name="10б", category=10),
        dict(name="Иванов Иван", school="289 СПб", class_name="2а", category=2),
        dict(name="иванов Иван", school="289 СПб", class_name="10а", category=10),
        dict(name="Петров Пётр", school="193 Москва", class_name="2б", category=2),
    ]
    result = participant_statistics(participants)
    assert result.total == 5
    assert dict(result.by_school) == {"289 СПб": 3, "193 Москва": 2}
    assert result.by_category == ((2, 3), (10, 2))
    assert result.by_school_category == (
        ("193 Москва", 2, 1), ("193 Москва", 10, 1),
        ("289 СПб", 2, 2), ("289 СПб", 10, 1),
    )
    assert result.duplicate_names == (
        ("Иванов Иван", "193 Москва", "10б"),
        ("Иванов Иван", "289 СПб", "2а"),
        ("Иванов Иван", "289 СПб", "2а"),
    )


def test_empty_statistics() -> None:
    result = participant_statistics([])
    assert result.total == 0
    assert result.by_school == result.by_category == result.by_school_category == result.duplicate_names == result.by_team == ()


def test_team_counts_include_empty_teams_and_unassigned_participants() -> None:
    teams = [dict(id=1, number=10, name="Совы"), dict(id=2, number=2, name="Совы"),
             dict(id=3, number=3, name="")]
    participants = [dict(name="Иван", school="289", class_name="9а", category=9, team_id=team_id)
                    for team_id in (1, 1, 2, None)]
    result = participant_statistics(participants, teams)
    assert result.by_team == (("№ 2 — Совы", 1), ("№ 3", 0), ("№ 10 — Совы", 2), ("Без команды", 1))
    assert sum(count for _, count in result.by_team) == result.total
    assert participant_statistics([], teams).by_team == (("№ 2 — Совы", 0), ("№ 3", 0), ("№ 10 — Совы", 0))
