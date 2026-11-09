"""Формы с проверкой перед закрытием: ошибки не теряют введённые данные."""

from typing import Any, Callable
from pathlib import Path
from sqlalchemy.exc import SQLAlchemyError
from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLabel, QLineEdit,
    QDateEdit, QSpinBox, QComboBox, QDialogButtonBox, QWidget, QTableWidget,
    QTableWidgetItem, QPushButton, QHBoxLayout, QHeaderView, QMessageBox)

from ..domain import category_from_class, team_label
from ..storage import Store
from ..excel import HEADERS, KEYS, read_rows, validate_rows
from .tasks import run_task


class Form(QDialog):
    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(460)
        self.outer = QVBoxLayout(self)
        self.form = QFormLayout()
        self.form.setSpacing(12)
        self.outer.addLayout(self.form)
        self.error = QLabel()
        self.error.setObjectName("error")
        self.error.setWordWrap(True)
        self.outer.addWidget(self.error)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("Сохранить")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Отмена")
        buttons.accepted.connect(self.submit)
        buttons.rejected.connect(self.reject)
        self.outer.addWidget(buttons)
        self.action: Callable[[], Any] = lambda: None
        self.result_id: int | None = None

    def submit(self) -> None:
        try:
            self.result_id = self.action()
        except (ValueError, OSError, SQLAlchemyError) as exc:
            self.error.setText(str(exc))
            return
        self.accept()

    def text(self, label: str, value: str = "") -> QLineEdit:
        field = QLineEdit(value)
        field.setAccessibleName(label)
        self.form.addRow(label, field)
        return field


class EventDialog(Form):
    def __init__(self, store: Store, item: dict[str, Any] | None = None, parent: QWidget | None = None) -> None:
        super().__init__("Редактировать мероприятие" if item else "Создать мероприятие", parent)
        item = item or {}
        name = self.text("Название", item.get("name", ""))
        day = QDateEdit(QDate.fromString(item["start_date"], "yyyy-MM-dd") if item else QDate.currentDate())
        day.setCalendarPopup(True)
        day.setDisplayFormat("dd.MM.yyyy")
        self.form.addRow("Дата начала мероприятия", day)
        organizer = self.text("Организатор", item.get("organizer", ""))
        self.action = lambda: store.save_event(name.text(), day.date().toString("yyyy-MM-dd"), organizer.text(), item.get("id"))


class TeamDialog(Form):
    def __init__(self, store: Store, event_id: int, item: dict[str, Any] | None = None, parent: QWidget | None = None) -> None:
        super().__init__("Редактировать команду" if item else "Создать команду", parent)
        item = item or {}
        number = QSpinBox()
        number.setRange(1, 2_147_483_647)
        number.setValue(item.get("number", 1))
        self.form.addRow("Номер команды", number)
        name = self.text("Название (необязательно)", item.get("name", ""))
        self.action = lambda: store.save_team(event_id, number.value(), name.text(), item.get("id"))


class TeamChoice(QDialog):
    def __init__(self, store: Store, event_id: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Назначить команду")
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Перед сохранением баллов выберите команду участника."))
        self.combo = QComboBox()
        self.combo.addItem("Выберите команду", None)
        for team in store.snapshot(event_id)["teams"]:
            self.combo.addItem(team_label(team), team["id"])
        layout.addWidget(self.combo)
        create = QPushButton("Создать команду")
        layout.addWidget(create)

        def add() -> None:
            dialog = TeamDialog(store, event_id, parent=self)
            if dialog.exec():
                team = next(t for t in store.snapshot(event_id)["teams"] if t["id"] == dialog.result_id)
                self.combo.addItem(team_label(team), team["id"])
                self.combo.setCurrentIndex(self.combo.count() - 1)

        create.clicked.connect(add)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Назначить и сохранить баллы")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Отмена")
        buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)
        self.combo.currentIndexChanged.connect(lambda: buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(self.combo.currentData() is not None))
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)


class ParticipantDialog(Form):
    def __init__(self, store: Store, event_id: int, item: dict[str, Any] | None = None, parent: QWidget | None = None) -> None:
        super().__init__("Редактировать участника" if item else "Добавить участника", parent)
        item = item or {}
        name = self.text("ФИО", item.get("name", ""))
        school = self.text("Школа и город", item.get("school", ""))
        class_name = self.text("Класс", item.get("class_name", ""))
        category = QSpinBox()
        category.setRange(0, 11)
        category.setSpecialValueText("Укажите категорию")
        category.setValue(item.get("category", 0))
        self.form.addRow("Категория (1–11)", category)

        def infer(value: str) -> None:
            category.setValue(category_from_class(value) or 0)

        class_name.textEdited.connect(infer)
        self.team = QComboBox()
        self.team.addItem("Без команды", None)
        for team in store.snapshot(event_id)["teams"]:
            self.team.addItem(team_label(team), team["id"])
        self.team.setCurrentIndex(max(0, self.team.findData(item.get("team_id"))))
        self.form.addRow("Команда", self.team)
        self.action = lambda: store.save_participant(event_id, name.text(), school.text(), class_name.text(),
                                                     category.value(), self.team.currentData(), item.get("id"))


class ImportDialog(QDialog):
    def __init__(self, store: Store, event_id: int, path: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.store, self.event_id = store, event_id
        self.source = run_task(parent or self, "Чтение файла Excel…", lambda: read_rows(path))
        self.setWindowTitle("Предпросмотр импорта")
        self.resize(1180, 680)
        layout = QVBoxLayout(self)
        note = QLabel("Исправьте ошибки двойным щелчком по ячейке. Снимите отметку у строк, которые не нужно добавлять.\n"
                      "При разных названиях команды задайте единое название. Указанное название заменит существующее.")
        note.setWordWrap(True)
        layout.addWidget(note)
        self.table = QTableWidget(len(self.source), 9)
        self.table.setHorizontalHeaderLabels(["Добавить", "Строка"] + HEADERS + ["Проверка"])
        for index, row in enumerate(self.source):
            checked = QTableWidgetItem()
            checked.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            checked.setCheckState(Qt.CheckState.Checked)
            self.table.setItem(index, 0, checked)
            number = QTableWidgetItem(str(row["row_number"]))
            number.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.table.setItem(index, 1, number)
            for column, key in enumerate(KEYS, 2):
                self.table.setItem(index, column, QTableWidgetItem(str(row[key])))
            status = QTableWidgetItem()
            status.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.table.setItem(index, 8, status)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)
        self.error = QLabel()
        self.error.setObjectName("error")
        self.error.setWordWrap(True)
        layout.addWidget(self.error)
        footer = QHBoxLayout()
        self.check_button = QPushButton("Проверить")
        self.import_button = QPushButton("Импортировать выбранные строки")
        self.import_button.setObjectName("primary")
        cancel = QPushButton("Отмена")
        for button in (self.check_button, self.import_button, cancel):
            footer.addWidget(button)
        layout.addLayout(footer)
        cancel.clicked.connect(self.reject)
        self.check_button.clicked.connect(self.validate)
        self.import_button.clicked.connect(self.submit)
        self.table.itemChanged.connect(self.invalidate)
        self.clean: list[dict[str, Any]] = []
        self.validate()

    def invalidate(self, item: QTableWidgetItem) -> None:
        if item.column() != 8:
            self.import_button.setEnabled(False)
            self.error.setText("Данные изменены. Нажмите «Проверить».")

    def validate(self) -> bool:
        rows, indices = [], []
        for row in range(self.table.rowCount()):
            self.table.item(row, 8).setText("Исключена")
            if self.table.item(row, 0).checkState() == Qt.CheckState.Checked:
                rows.append({key: self.table.item(row, col).text().strip() for col, key in enumerate(KEYS, 2)})
                indices.append(row)
        self.clean, errors, warnings = validate_rows(rows, self.store.snapshot(self.event_id))
        for index, row in enumerate(indices):
            message = "; ".join(errors.get(index, []) + warnings.get(index, [])) or "Готова к импорту"
            self.table.item(row, 8).setText(message)
            self.table.item(row, 8).setToolTip(message)
        self.table.resizeRowsToContents()
        valid = bool(rows) and not errors
        self.import_button.setEnabled(valid)
        self.error.setText(f"Выбрано строк: {len(rows)}. Строк с ошибками: {len(errors)}. Предупреждений: {len(warnings)}.")
        return valid

    def submit(self) -> None:
        if not self.validate():
            return
        try:
            run_task(self, "Импорт участников…", lambda: self.store.import_participants(self.event_id, self.clean))
        except (ValueError, OSError, SQLAlchemyError) as exc:
            self.error.setText(str(exc))
            return
        self.accept()
