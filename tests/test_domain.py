import pytest
from school_contests.domain import Winner, rank, category_from_class, integer, calculate


def test_dense_ranks_include_all_ties() -> None:
    rows = rank([Winner(i, str(i), "", value) for i, value in enumerate([100, 100, 90, 80, 70])])
    assert [row.place for row in rows] == [1, 1, 2, 3]


def test_zero_can_win() -> None:
    assert [row.place for row in rank([Winner(1, "А", "", 0), Winner(2, "Б", "", 0)])] == [1, 1]


@pytest.mark.parametrize("value,expected", [("9в", 9), ("11 А", 11), ("1", 1), ("12а", None), ("0", None), ("неизвестно", None)])
def test_category(value: str, expected: int | None) -> None:
    assert category_from_class(value) == expected


@pytest.mark.parametrize("value", ["1.5", "-1", True, "NaN", "2147483648"])
def test_invalid_points(value: object) -> None:
    with pytest.raises(ValueError):
        integer(value, "Баллы")
