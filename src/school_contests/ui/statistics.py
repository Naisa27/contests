"""Читаемые таблицы статистики в общей светлой теме приложения."""

from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtGui import QResizeEvent, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QAbstractItemView, QFrame, QHBoxLayout, QHeaderView, QLabel, QLayout,
    QSizePolicy, QTableView, QVBoxLayout, QWidget,
)

from ..statistics import ParticipantStatistics


class StatisticsTable(QTableView):
    def __init__(self, title: str, headers: tuple[str, ...],
                 rows: tuple[tuple[str | int, ...], ...]) -> None:
        super().__init__()
        self.setAccessibleName(title)
        model = QStandardItemModel(0, len(headers), self)
        model.setHorizontalHeaderLabels(headers)
        for row in rows:
            items = []
            for value in row:
                item = QStandardItem()
                item.setData(value, Qt.ItemDataRole.DisplayRole)
                item.setToolTip(str(value))
                item.setEditable(False)
                if isinstance(value, int):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                items.append(item)
            model.appendRow(items)
        self.setModel(model)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setAlternatingRowColors(True)
        self.setWordWrap(False)
        self.setTextElideMode(Qt.TextElideMode.ElideNone)
        self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.verticalHeader().hide()
        self.verticalHeader().setMinimumSectionSize(38)
        self.horizontalHeader().setMinimumSectionSize(0)
        self.horizontalHeader().setStretchLastSection(False)
        self.horizontalHeader().setResizeContentsPrecision(-1)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.setSortingEnabled(True)
        self.sortByColumn(0, Qt.SortOrder.AscendingOrder)
        self.horizontalHeader().sectionResized.connect(self.fit_rows)
        self.horizontalScrollBar().rangeChanged.connect(self.fit_rows)
        model.layoutChanged.connect(self.fit_rows)
        self.ensurePolished()
        self.resizeColumnsToContents()
        self.fit_rows()

    def fit_rows(self) -> None:
        # До восьми строк видны целиком, большие списки прокручиваются со своими заголовками.
        self.resizeRowsToContents()
        visible_rows = min(8, self.model().rowCount())
        height = sum(self.rowHeight(row) for row in range(visible_rows))
        if self.horizontalScrollBar().maximum() > 0:
            height += self.horizontalScrollBar().sizeHint().height()
        self.setFixedHeight(self.horizontalHeader().height() + height + 2 * self.frameWidth())


class StatisticsSection(QFrame):
    def __init__(self, title: str, headers: tuple[str, ...],
                 rows: tuple[tuple[str | int, ...], ...], empty_text: str) -> None:
        super().__init__()
        self.setObjectName("statisticsSection")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(10)
        self.heading = QLabel(title)
        self.heading.setObjectName("statisticsHeading")
        self.heading.setWordWrap(True)
        layout.addWidget(self.heading)
        self.table: StatisticsTable | None = None
        if rows:
            self.table = StatisticsTable(title, headers, rows)
            layout.addWidget(self.table)
        else:
            empty = QLabel(empty_text)
            empty.setObjectName("muted")
            empty.setWordWrap(True)
            layout.addWidget(empty)
        layout.addStretch()

    def preferred_width(self) -> int:
        """Ширина таблицы с рамкой и отступами; заголовок блока также остаётся читаемым."""
        self.ensurePolished()
        margins = self.layout().contentsMargins()
        heading_width = self.heading.fontMetrics().horizontalAdvance(self.heading.text())
        if self.table is None:
            content_width = 300
        else:
            content_width = self.table.horizontalHeader().length() + 2 * self.table.frameWidth()
            if self.table.model().rowCount() > 8:
                content_width += self.table.verticalScrollBar().sizeHint().width()
        return max(content_width, heading_width) + margins.left() + margins.right() + 2 * self.frameWidth()


class StatisticsOverview(QWidget):
    def __init__(self, sections: tuple[StatisticsSection, ...]) -> None:
        super().__init__()
        self.sections = sections
        self.columns = 0
        self.rows = QVBoxLayout(self)
        self.rows.setContentsMargins(0, 0, 0, 0)
        self.rows.setSpacing(16)
        self.rows.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)
        self._arrangement: tuple[tuple[int, ...], ...] = ()
        self.reflow_timer = QTimer(self)
        self.reflow_timer.setSingleShot(True)
        self.reflow_timer.timeout.connect(self.reflow)
        for section in sections:
            if section.table is not None:
                section.table.horizontalHeader().sectionResized.connect(lambda: self.reflow_timer.start(0))
        self.reflow_timer.start(0)

    def minimumSizeHint(self) -> QSize:
        return QSize(0, super().minimumSizeHint().height())

    def reflow(self) -> None:
        # Ряды независимы: широкая таблица снизу не растягивает блоки в верхнем ряду.
        available = max(1, self.width())
        groups: list[list[int]] = [[]]
        occupied = 0
        for section in self.sections:
            width = min(section.preferred_width(), available)
            if groups[-1] and occupied + 16 + width > available:
                groups.append([])
                occupied = 0
            groups[-1].append(width)
            occupied += (16 if occupied else 0) + width
        arrangement = tuple(tuple(group) for group in groups)
        if arrangement == self._arrangement:
            return
        self._arrangement = arrangement
        self.columns = max(map(len, groups))
        while self.rows.count():
            row = self.rows.takeAt(0).layout()
            while row.count():
                row.takeAt(0)
            row.deleteLater()
        index = 0
        for group in groups:
            row = QHBoxLayout()
            row.setSpacing(16)
            for width in group:
                section = self.sections[index]
                section.setFixedWidth(width)
                row.addWidget(section, 0, Qt.AlignmentFlag.AlignTop)
                index += 1
            row.addStretch()
            self.rows.addLayout(row)
        self.updateGeometry()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self.reflow()


class StatisticsContent(QWidget):
    def __init__(self, statistics: ParticipantStatistics) -> None:
        super().__init__()
        self.setObjectName("statisticsContent")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 12, 8, 12)
        layout.setSpacing(16)
        layout.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)
        self.total = QLabel(f"Всего участников: {statistics.total}")
        self.total.setObjectName("statisticsTotal")
        layout.addWidget(self.total)
        hint = QLabel("Все участники мероприятия, независимо от поиска и фильтра категории.")
        hint.setObjectName("muted")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        empty = "Участников пока нет. Добавьте их на вкладке «Проведение конкурса»."
        self.schools = StatisticsSection("Участники по школам", ("Школа", "Участников"), statistics.by_school, empty)
        self.categories = StatisticsSection("Участники по категориям", ("Категория", "Участников"), statistics.by_category, empty)
        self.school_categories = StatisticsSection(
            "Категории в каждой школе", ("Школа", "Категория", "Участников"), statistics.by_school_category, empty)
        self.overview = StatisticsOverview((self.schools, self.categories, self.school_categories))
        layout.addWidget(self.overview)
        self.duplicates = StatisticsSection(
            "Повторяющиеся ФИО", ("ФИО", "Школа", "Класс"), statistics.duplicate_names,
            "Повторяющиеся ФИО отсутствуют.")
        layout.addWidget(self.duplicates)
        if self.duplicates.table is not None:
            self.duplicates.table.horizontalHeader().sectionResized.connect(self.fit_duplicates)
        layout.addStretch()

    def minimumSizeHint(self) -> QSize:
        return QSize(0, super().minimumSizeHint().height())

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self.fit_duplicates()

    def fit_duplicates(self) -> None:
        margins = self.layout().contentsMargins()
        available = max(1, self.width() - margins.left() - margins.right())
        self.duplicates.setFixedWidth(min(self.duplicates.preferred_width(), available))
