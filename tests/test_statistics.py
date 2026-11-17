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
    assert result.by_school == result.by_category == result.by_school_category == result.duplicate_names == ()
