from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QScrollArea

from school_contests.statistics import participant_statistics
from school_contests.storage import Store
from school_contests.ui.statistics import StatisticsContent
from school_contests.ui.theme import QSS
from school_contests.ui.window import Window


def test_statistics_uses_entire_event_and_refreshes_after_edits_and_import(qtbot, store: Store, event_id: int) -> None:
    participant = store.save_participant(event_id, "Иванов Иван", "289 СПб", "2а", 2)
    store.save_participant(event_id, "Иванов Иван", "193 Москва", "10б", 10)
    other = store.save_event("Другое", "2026-11-18", "Школа")
    store.save_participant(other, "Иванов Иван", "Другая школа", "2а", 2)
    window = Window(store)
    qtbot.addWidget(window)
    window.open_event(event_id)
    window.proxy.search("Не найден")
    window.category_filter.setCurrentIndex(window.category_filter.findData(2))
    assert window.proxy.rowCount() == 0
    assert window.tabs.tabText(2) == "Статистика"
    window.tabs.setCurrentIndex(2)
    content = window.statistics.widget()
    assert content.total.text() == "Всего участников: 2"
    assert content.duplicates.table.model().rowCount() == 2
    assert content.categories.table.model().index(1, 0).data() == 10

    window.tabs.setCurrentIndex(0)
    store.save_participant(event_id, "Петров Пётр", "289 СПб", "3а", 3, participant_id=participant)
    store.import_participants(event_id, [dict(name="Сидоров Семён", school="289 СПб", class_name="3б", category=3,
                                            team_number=None, team_name="")])
    window.model.reload()
    window.tabs.setCurrentIndex(2)
    content = window.statistics.widget()
    assert content.total.text() == "Всего участников: 3"
    assert content.duplicates.table is None
    assert "Повторяющиеся ФИО отсутствуют." in [label.text() for label in content.findChildren(QLabel)]
    categories = content.categories.table.model()
    assert [(categories.index(i, 0).data(), categories.index(i, 1).data()) for i in range(categories.rowCount())] == [(3, 2), (10, 1)]
    window.close()


def test_empty_event_statistics_explains_empty_tables(qtbot, store: Store, event_id: int) -> None:
    window = Window(store)
    qtbot.addWidget(window)
    window.open_event(event_id)
    window.tabs.setCurrentIndex(2)
    content = window.statistics.widget()
    assert content.total.text() == "Всего участников: 0"
    assert all(section.table is None for section in (content.schools, content.categories, content.school_categories, content.duplicates))
    window.close()


def test_statistics_reflows_scrolls_long_names_and_sorts_counts_numerically(qtbot) -> None:
    long_school = "Школа № 289 с углублённым изучением отдельных предметов, Санкт-Петербург"
    participants = [dict(name="Константинопольский Александр Александрович", school=long_school,
                         class_name="10а", category=10) for _ in range(12)]
    participants.extend(dict(name=f"Участник {i}", school="193 Москва", class_name="2б", category=2) for i in range(2))
    scroll = QScrollArea()
    scroll.setStyleSheet(QSS)
    scroll.setWidgetResizable(True)
    content = StatisticsContent(participant_statistics(participants))
    scroll.setWidget(content)
    qtbot.addWidget(scroll)
    scroll.resize(1250, 800)
    scroll.show()
    qtbot.waitUntil(lambda: content.overview.columns > 0)
    table = content.schools.table
    table.sortByColumn(1, Qt.SortOrder.DescendingOrder)
    assert table.model().index(0, 1).data() == 12
    assert not table.model().flags(table.model().index(0, 1)) & Qt.ItemFlag.ItemIsEditable
    column_widths = [table.columnWidth(column) for column in range(table.model().columnCount())]
    scroll.resize(760, 600)
    qtbot.waitUntil(lambda: content.overview.width() < 760)
    assert scroll.horizontalScrollBar().maximum() == 0
    assert [table.columnWidth(column) for column in range(table.model().columnCount())] == column_widths
    assert content.duplicates.table.model().rowCount() == 12
    assert content.duplicates.table.verticalScrollBar().maximum() > 0
    name_index = content.duplicates.table.model().index(0, 0)
    assert name_index.data(Qt.ItemDataRole.ToolTipRole) == participants[0]["name"]


def test_all_three_statistics_blocks_fit_content_and_reflow_without_expanding(qtbot) -> None:
    scroll = QScrollArea()
    scroll.setStyleSheet(QSS)
    scroll.setWidgetResizable(True)
    content = StatisticsContent(participant_statistics([
        dict(name="Иван", school="289 СПб", class_name="2а", category=2),
    ]))
    scroll.setWidget(content)
    qtbot.addWidget(scroll)
    sections = content.overview.sections
    scroll.resize(2400, 700)
    scroll.show()
    qtbot.waitUntil(lambda: content.overview.columns == 3
                   and not content.overview.reflow_timer.isActive()
                   and all(section.width() == section.preferred_width() for section in sections))
    widths = [section.preferred_width() for section in sections]
    assert len({section.y() for section in sections}) == 1
    assert [section.width() for section in sections] == widths
    scroll.resize(sum(widths) + 300, 700)
    qtbot.waitUntil(lambda: content.overview.columns == 3 and not content.overview.reflow_timer.isActive())
    assert [section.width() for section in sections] == widths
    scroll.resize(max(120, min(widths) // 2), 600)
    qtbot.waitUntil(lambda: content.overview.columns == 1)
    assert sections[0].y() < sections[1].y() < sections[2].y()
    assert scroll.horizontalScrollBar().maximum() == 0
    scroll.resize(sum(widths) + 120, 700)
    qtbot.waitUntil(lambda: content.overview.columns == 3)
    assert [section.width() for section in sections] == widths
