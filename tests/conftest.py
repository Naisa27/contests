from pathlib import Path
from collections.abc import Iterator
import pytest
from school_contests.storage import Store


@pytest.fixture
def store(tmp_path: Path) -> Iterator[Store]:
    value = Store(tmp_path / "test.sqlite3")
    yield value
    value.close()


@pytest.fixture
def event_id(store: Store) -> int:
    return store.save_event("Мир талантов", "2026-11-09", "Школа 289")
