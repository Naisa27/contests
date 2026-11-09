"""Главный экран, навигация и проведение мероприятия."""

from pathlib import Path
from typing import Any, Callable

from PySide6.QtCore import QDate, QDateTime, QLocale, QTimer, Qt, QRect, QSize
from PySide6.QtGui import QPainter, QPixmap, QColor, QCloseEvent, QShowEvent, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QStackedWidget, QListWidget, QListWidgetItem, QTableView,
    QTabWidget, QLineEdit, QComboBox, QHeaderView, QAbstractItemView, QInputDialog,
    QMessageBox, QFileDialog, QDialog, QScrollArea, QDialogButtonBox)

from .. import __version__
from ..domain import team_label
from ..storage import Store
from .. import excel
from .dialogs import EventDialog, TeamDialog, ParticipantDialog, TeamChoice, ImportDialog
from .models import ParticipantsModel, NameFilter, ScoreDelegate
from .tasks import run_task
from .placement import centered_frame
from .results import ResultsContent

RESOURCES = Path(__file__).resolve().parents[1] / "resources"


def button(text: str, action: Callable[..., Any], primary: bool = False) -> QPushButton:
    result = QPushButton(text)
    if primary:
        result.setObjectName("primary")
    result.clicked.connect(action)
    return result


class Home(QWidget):
    def __init__(self, create: Callable[[], None], browse: Callable[[], None], news: Callable[[], None]) -> None:
        super().__init__()
        self.logo = QPixmap(str(RESOURCES / "images" / "logo.jpg"))
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.addStretch(2)
        title = QLabel("Добро пожаловать в мир талантов!")
        title.setObjectName("hero")
        title.setWordWrap(True)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        subtitle = QLabel("Создавайте конкурсы, отмечайте достижения, открывайте новые имена.")
        subtitle.setWordWrap(True)
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)
        layout.addSpacing(24)
        self.clock = QLabel()
        self.clock.setObjectName("clock")
        self.day = QLabel()
        for label in (self.clock, self.day):
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(label)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(1000)
        self.tick()
        layout.addSpacing(28)
        actions = QHBoxLayout()
        actions.addStretch()
        actions.addWidget(button("Создать мероприятие", create, True))
        actions.addWidget(button("Все мероприятия", browse))
        actions.addStretch()
        layout.addLayout(actions)
        layout.addStretch(3)
        footer = QHBoxLayout()
        footer.addWidget(QLabel(f"Школьные конкурсы · {__version__}"))
        footer.addStretch()
        footer.addWidget(button("Что нового в этой версии", news))
        layout.addLayout(footer)

    def tick(self) -> None:
        now = QDateTime.currentDateTime()
        self.clock.setText(now.toString("HH:mm:ss"))
        self.day.setText(QLocale("ru_RU").toString(now.date(), "dddd, d MMMM yyyy"))

    def paintEvent(self, event: Any) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#F3F7F7"))
        if not self.logo.isNull():
            size = self.logo.size().scaled(self.size() * 0.85, Qt.AspectRatioMode.KeepAspectRatio)
            target = QRect((self.width() - size.width()) // 2, (self.height() - size.height()) // 2, size.width(), size.height())
            painter.drawPixmap(target, self.logo)
            painter.fillRect(self.rect(), QColor(255, 255, 255, 225))


class Window(QMainWindow):
    def __init__(self, store: Store) -> None:
        super().__init__()
        self.store = store
        self._initial_placement_pending = True
        self.setWindowTitle(f"Школьные конкурсы — {__version__}")
        self.resize(1240, 800)
        self.setMinimumSize(900, 600)
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)
        self.home = Home(self.create_event, self.show_events, self.show_news)
        self.stack.addWidget(self.home)
        self.event_page: QWidget | None = None
        self.list_page: QWidget | None = None
        menu = self.menuBar().addMenu("Данные")
        menu.addAction("Создать резервную копию…", self.backup)
        menu.addAction("Восстановить из копии…", self.restore)
        self.statusBar().showMessage("Данные сохраняются автоматически")

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        if self._initial_placement_pending:
            self._initial_placement_pending = False
            # После первого показа Windows уже определила монитор и размеры заголовка/рамки.
            QTimer.singleShot(0, self._center_initially)

    def _center_initially(self) -> None:
        screen = self.screen()
        if screen is None or self.isMaximized() or self.isFullScreen():
            return
        decoration = QSize(max(0, self.frameGeometry().width() - self.width()),
                           max(0, self.frameGeometry().height() - self.height()))
        frame = centered_frame(screen.availableGeometry(), self.size(), decoration)
        width, height = frame.width() - decoration.width(), frame.height() - decoration.height()
        self.setMinimumSize(min(900, width), min(600, height))
        self.resize(width, height)
        self.move(frame.topLeft())

    def attempt(self, action: Callable[[], Any]) -> Any:
        try:
            return action()
        except Exception as exc:
            # Последняя граница GUI: ошибка операции не должна завершать приложение.
            QMessageBox.warning(self, "Операция не выполнена", str(exc))
            return None

    def replace_page(self, name: str, page: QWidget) -> None:
        previous = getattr(self, name)
        if previous is not None:
            self.stack.removeWidget(previous)
            previous.deleteLater()
        setattr(self, name, page)
        self.stack.addWidget(page)
        self.stack.setCurrentWidget(page)

    def show_news(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Что нового — {__version__}")
        dialog.resize(560, 420)
        layout = QVBoxLayout(dialog)
        title = QLabel(f"Версия {__version__}")
        title.setObjectName("title")
        layout.addWidget(title)
        text = QLabel((RESOURCES / "changes.txt").read_text(encoding="utf-8"))
        text.setWordWrap(True)
        layout.addWidget(text)
        layout.addStretch()
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.button(QDialogButtonBox.StandardButton.Close).setText("Закрыть")
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        dialog.exec()

    def create_event(self) -> None:
        dialog = EventDialog(self.store, parent=self)
        if dialog.exec():
            self.open_event(dialog.result_id)

    def show_events(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 24, 28, 24)
        header = QHBoxLayout()
        header.addWidget(button("На главную", lambda: self.stack.setCurrentWidget(self.home)))
        title = QLabel("Все мероприятия")
        title.setObjectName("title")
        header.addWidget(title)
        header.addStretch()
        header.addWidget(button("Создать мероприятие", self.create_event, True))
        layout.addLayout(header)
        instruction = QLabel("Выберите нужное мероприятие")
        instruction.setObjectName("eventsInstruction")
        layout.addWidget(instruction)
        listing = QTableView()
        self.events_table = listing
        listing.setAccessibleName("Мероприятия: выберите строку и нажмите «Открыть» или «Редактировать»")
        model = QStandardItemModel(0, 3, listing)
        model.setHorizontalHeaderLabels(["Дата начала", "Название", "Организатор"])
        sort_role = Qt.ItemDataRole.UserRole + 1
        model.setSortRole(sort_role)
        for event in self.store.list_events():
            values = [QDate.fromString(event["start_date"], "yyyy-MM-dd").toString("dd.MM.yyyy"),
                      event["name"], event["organizer"]]
            cells = [QStandardItem(value) for value in values]
            cells[0].setData(event, Qt.ItemDataRole.UserRole)
            for column, cell in enumerate(cells):
                cell.setData(event["start_date"] if column == 0 else values[column].casefold(), sort_role)
                cell.setToolTip(values[column])
            model.appendRow(cells)
        listing.setModel(model)
        listing.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        listing.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        listing.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        listing.setAlternatingRowColors(True)
        listing.setSortingEnabled(True)
        listing.sortByColumn(0, Qt.SortOrder.DescendingOrder)
        listing.verticalHeader().hide()
        listing.verticalHeader().setDefaultSectionSize(44)
        listing.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        listing.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        listing.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        if model.rowCount() == 0:
            layout.addWidget(QLabel("Мероприятий пока нет. Создайте первое мероприятие."))
        layout.addWidget(listing)

        def selected_event() -> dict[str, Any] | None:
            rows = listing.selectionModel().selectedRows(0)
            return rows[0].data(Qt.ItemDataRole.UserRole) if rows else None

        def open_selected() -> None:
            event = selected_event()
            if event is not None:
                self.open_event(event["id"])

        def edit_selected() -> None:
            event = selected_event()
            if event is not None:
                if EventDialog(self.store, event, self).exec():
                    self.show_events()

        listing.doubleClicked.connect(lambda _: open_selected())
        footer = QHBoxLayout()
        self.open_event_button = button("Открыть", open_selected, True)
        self.edit_event_button = button("Редактировать", edit_selected)
        self.open_event_button.setEnabled(False)
        self.edit_event_button.setEnabled(False)

        def update_actions() -> None:
            enabled = listing.selectionModel().hasSelection()
            self.open_event_button.setEnabled(enabled)
            self.edit_event_button.setEnabled(enabled)

        listing.selectionModel().selectionChanged.connect(update_actions)
        footer.addWidget(self.open_event_button)
        footer.addWidget(self.edit_event_button)
        footer.addStretch()
        layout.addLayout(footer)
        self.replace_page("list_page", page)

    def open_event(self, event_id: int) -> None:
        self.event_id = event_id
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 20, 24, 20)
        header = QHBoxLayout()
        header.addWidget(button("Все мероприятия", self.show_events))
        event = self.store.snapshot(event_id)["event"]
        title = QLabel(event["name"])
        title.setWordWrap(True)
        title.setObjectName("title")
        header.addWidget(title, 1)
        header.addWidget(button("Экспорт Excel", lambda: self.save_file("Экспорт результатов", "Результаты.xlsx", lambda path: excel.export(path, self.store.snapshot(self.event_id)))))
        layout.addLayout(header)
        layout.addWidget(QLabel(f"Дата начала: {event['start_date']}   Организатор: {event['organizer']}"))
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        conduct = QWidget()
        controls = QVBoxLayout(conduct)
        tools = QHBoxLayout()
        tools.addWidget(button("Добавить участника", self.add_participant, True))
        tools.addWidget(button("Импорт Excel", self.import_excel))
        tools.addWidget(button("Скачать шаблон", lambda: self.save_file("Шаблон участников", "Шаблон.xlsx", excel.template)))
        tools.addStretch()
        tools.addWidget(button("Команды", self.manage_teams))
        tools.addWidget(button("Конкурсы", self.manage_contests))
        controls.addLayout(tools)
        search = QLineEdit()
        search.setPlaceholderText("Поиск по ФИО")
        search.setAccessibleName("Поиск по ФИО")
        filters = QHBoxLayout()
        filters.addWidget(search, 1)
        self.category_filter = QComboBox()
        self.category_filter.setAccessibleName("Фильтр по категории")
        self.category_filter.setMinimumWidth(180)
        category_label = QLabel("Категория:")
        category_label.setBuddy(self.category_filter)
        filters.addWidget(category_label)
        filters.addWidget(self.category_filter)
        controls.addLayout(filters)
        self.feedback = QLabel("Добавьте конкурсы и участников. Баллы вводятся прямо в таблице; двойной щелчок по ФИО открывает форму участника.")
        self.feedback.setWordWrap(True)
        controls.addWidget(self.feedback)
        self.model = ParticipantsModel(self.store, event_id, self.choose_team)
        self.model.failed.connect(self.show_error)
        self.model.changed.connect(self.score_saved)
        self.proxy = NameFilter()
        self.proxy.setSourceModel(self.model)
        search.textChanged.connect(self.proxy.search)
        self.category_filter.currentIndexChanged.connect(
            lambda: self.proxy.set_category(self.category_filter.currentData()))
        self.model.modelReset.connect(self.refresh_categories)
        self.refresh_categories()
        self.table = QTableView()
        self.table.setModel(self.proxy)
        self.table.setItemDelegate(ScoreDelegate(self.table))
        self.table.setSortingEnabled(True)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setDefaultSectionSize(155)
        self.table.setColumnWidth(1, 260)
        self.table.sortByColumn(1, Qt.SortOrder.AscendingOrder)
        self.table.verticalHeader().setDefaultSectionSize(38)
        self.table.doubleClicked.connect(self.edit_participant)
        controls.addWidget(self.table)
        self.tabs.addTab(conduct, "Проведение конкурса")
        self.results = QScrollArea()
        self.results.setWidgetResizable(True)
        self.tabs.addTab(self.results, "Результаты конкурса")
        self.tabs.currentChanged.connect(lambda index: self.render_results() if index == 1 else None)
        self.replace_page("event_page", page)

    def refresh_categories(self) -> None:
        selected = self.category_filter.currentData()
        categories = sorted({participant["category"] for participant in self.model.snapshot["participants"]})
        self.category_filter.blockSignals(True)
        try:
            self.category_filter.clear()
            self.category_filter.addItem("Все категории", None)
            for category in categories:
                self.category_filter.addItem(f"Категория {category}", category)
            self.category_filter.setCurrentIndex(max(0, self.category_filter.findData(selected)))
        finally:
            self.category_filter.blockSignals(False)
        self.proxy.set_category(self.category_filter.currentData())

    def show_error(self, message: str) -> None:
        self.feedback.setObjectName("error")
        self.feedback.setText(message)
        self.feedback.style().unpolish(self.feedback)
        self.feedback.style().polish(self.feedback)

    def score_saved(self) -> None:
        self.feedback.setObjectName("")
        self.feedback.setText("Баллы сохранены. Результаты пересчитаны.")
        self.feedback.style().unpolish(self.feedback)
        self.feedback.style().polish(self.feedback)

    def choose_team(self) -> int | None:
        dialog = TeamChoice(self.store, self.event_id, self)
        return dialog.combo.currentData() if dialog.exec() else None

    def add_participant(self) -> None:
        if ParticipantDialog(self.store, self.event_id, parent=self).exec():
            self.model.reload()

    def edit_participant(self, index: Any) -> None:
        if index.column() != 1:
            return
        row = self.proxy.mapToSource(index).row()
        if ParticipantDialog(self.store, self.event_id, self.model.snapshot["participants"][row], self).exec():
            self.model.reload()

    def manage_teams(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Команды мероприятия")
        dialog.resize(580, 460)
        layout = QVBoxLayout(dialog)
        listing = QListWidget()
        layout.addWidget(listing)

        def refresh() -> None:
            listing.clear()
            for team in self.store.snapshot(self.event_id)["teams"]:
                item = QListWidgetItem(team_label(team))
                item.setData(Qt.ItemDataRole.UserRole, team)
                listing.addItem(item)

        def edit(existing: bool = False) -> None:
            item = listing.currentItem().data(Qt.ItemDataRole.UserRole) if existing and listing.currentItem() else None
            if existing and item is None:
                return
            if TeamDialog(self.store, self.event_id, item, dialog).exec():
                refresh()

        refresh()
        actions = QHBoxLayout()
        actions.addWidget(button("Создать команду", lambda: edit(), True))
        actions.addWidget(button("Редактировать", lambda: edit(True)))
        actions.addWidget(button("Закрыть", dialog.accept))
        listing.itemDoubleClicked.connect(lambda _: edit(True))
        layout.addLayout(actions)
        dialog.exec()
        self.model.reload()

    def manage_contests(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Конкурсы мероприятия")
        dialog.resize(580, 460)
        layout = QVBoxLayout(dialog)
        listing = QListWidget()
        layout.addWidget(listing)

        def refresh() -> None:
            listing.clear()
            for contest in self.store.snapshot(self.event_id)["contests"]:
                item = QListWidgetItem(contest["name"])
                item.setData(Qt.ItemDataRole.UserRole, contest)
                listing.addItem(item)

        def edit(existing: bool = False) -> None:
            item = listing.currentItem().data(Qt.ItemDataRole.UserRole) if existing and listing.currentItem() else None
            if existing and item is None:
                return
            name, accepted = QInputDialog.getText(dialog, "Конкурс", "Название конкурса", text=item["name"] if item else "")
            if accepted:
                self.attempt(lambda: self.store.save_contest(self.event_id, name, item["id"] if item else None))
                refresh()

        def remove() -> None:
            if not listing.currentItem():
                return
            item = listing.currentItem().data(Qt.ItemDataRole.UserRole)
            if QMessageBox.question(dialog, "Удалить конкурс?", "Конкурс и все его оценки будут удалены. Продолжить?") == QMessageBox.StandardButton.Yes:
                self.attempt(lambda: self.store.remove_contest(self.event_id, item["id"]))
                refresh()

        refresh()
        actions = QHBoxLayout()
        actions.addWidget(button("Добавить", lambda: edit(), True))
        actions.addWidget(button("Переименовать", lambda: edit(True)))
        actions.addWidget(button("Удалить", remove))
        actions.addWidget(button("Закрыть", dialog.accept))
        layout.addLayout(actions)
        dialog.exec()
        self.model.reload()

    def render_results(self) -> None:
        self.results.setWidget(ResultsContent(self.store.snapshot(self.event_id)))

    def save_file(self, title: str, default: str, action: Callable[[Path], None]) -> None:
        filename, _ = QFileDialog.getSaveFileName(self, title, default, "Excel (*.xlsx)")
        if filename:
            path = Path(filename)
            if path.suffix.lower() != ".xlsx":
                path = path.with_suffix(".xlsx")
            def save() -> None:
                run_task(self, "Сохранение файла Excel…", lambda: action(path))
                self.statusBar().showMessage(f"Сохранено: {path}", 10000)
            self.attempt(save)

    def import_excel(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(self, "Импорт участников", "", "Excel (*.xlsx)")
        if filename:
            def load() -> None:
                dialog = ImportDialog(self.store, self.event_id, Path(filename), self)
                if dialog.exec():
                    self.model.reload()
                    self.feedback.setText("Участники импортированы.")
            self.attempt(load)

    def backup(self) -> None:
        filename, _ = QFileDialog.getSaveFileName(self, "Резервная копия", "contests-backup.sqlite3", "SQLite (*.sqlite3)")
        if filename:
            def save() -> None:
                run_task(self, "Создание резервной копии…", lambda: self.store.backup(Path(filename)))
                self.statusBar().showMessage(f"Резервная копия сохранена: {filename}", 10000)
            self.attempt(save)

    def restore(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(self, "Восстановить базу", "", "SQLite (*.sqlite3)")
        if filename and QMessageBox.question(self, "Восстановить базу?", "Текущие данные будут заменены. Перед заменой автоматически сохранится резервная копия. Продолжить?") == QMessageBox.StandardButton.Yes:
            def load() -> None:
                backup = run_task(self, "Восстановление базы…", lambda: self.store.restore(Path(filename)))
                self.stack.setCurrentWidget(self.home)
                self.statusBar().showMessage(f"База восстановлена. Предыдущая база: {backup}", 20000)
            self.attempt(load)

    def closeEvent(self, event: QCloseEvent) -> None:
        self.store.close()
        super().closeEvent(event)
