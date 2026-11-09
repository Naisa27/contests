from PySide6.QtCore import Qt
from PySide6.QtWidgets import QScrollArea

from school_contests.domain import Standing, Winner
from school_contests.ui.results import CardsGrid, WinnerRow
from school_contests.ui.theme import QSS


def test_grid_reflows_without_losing_tied_winners(qtbot) -> None:
    winners = tuple(Winner(i, "Константинопольский Александр Александрович", "Школа № 289, Санкт-Петербург, 11а", 20, 1)
                    for i in range(5))
    standings = [Standing("contest", i, f"Конкурс {i}", winners) for i in range(3)]
    scroll = QScrollArea()
    scroll.setStyleSheet(QSS)
    scroll.setWidgetResizable(True)
    grid = CardsGrid(standings)
    scroll.setWidget(grid)
    qtbot.addWidget(scroll)
    scroll.resize(1200, 650)
    scroll.show()
    qtbot.waitUntil(lambda: grid.columns == 2)
    assert grid.grid.getItemPosition(1)[:2] == (0, 1)
    assert grid.grid.getItemPosition(2)[:2] == (1, 0)
    assert len(grid.findChildren(WinnerRow)) == 15
    scroll.resize(760, 650)
    qtbot.waitUntil(lambda: grid.columns == 1)
    assert grid.grid.getItemPosition(1)[:2] == (1, 0)
    assert scroll.horizontalScrollBar().maximum() == 0
    assert len(grid.findChildren(WinnerRow)) == 15
    scroll.resize(1200, 650)
    qtbot.waitUntil(lambda: grid.columns == 2)
    assert grid.grid.getItemPosition(2)[:2] == (1, 0)
    assert len(grid.findChildren(WinnerRow)) == 15
