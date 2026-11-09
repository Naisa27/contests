"""Таблица адресует изменения по ID, независимо от фильтра и сортировки."""

from typing import Any, Callable
from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt, Signal, QSortFilterProxyModel
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import QStyledItemDelegate, QLineEdit, QWidget, QStyleOptionViewItem
from sqlalchemy.exc import SQLAlchemyError
from ..domain import integer, team_label
from ..storage import Store


class ScoreDelegate(QStyledItemDelegate):
    """Одинаковый текстовый редактор позволяет очистить и заполненную числовую ячейку."""

    def createEditor(self, parent: QWidget, option: QStyleOptionViewItem, index: QModelIndex) -> QWidget:
        editor = QLineEdit(parent)
        editor.setAccessibleName("Баллы: целое неотрицательное число или пустая ячейка")
        return editor

    def setEditorData(self, editor: QLineEdit, index: QModelIndex) -> None:
        editor.setText(str(index.data(Qt.ItemDataRole.EditRole)))
        editor.selectAll()

    def setModelData(self, editor: QLineEdit, model: QAbstractTableModel, index: QModelIndex) -> None:
        model.setData(index, editor.text(), Qt.ItemDataRole.EditRole)


class ParticipantsModel(QAbstractTableModel):
    changed = Signal()
    failed = Signal(str)

    def __init__(self, store: Store, event_id: int, choose_team: Callable[[], int | None]) -> None:
        super().__init__()
        self.store, self.event_id, self.choose_team = store, event_id, choose_team
        self.snapshot: dict[str, Any] = {}
        self.reload()

    def reload(self) -> None:
        data = self.store.snapshot(self.event_id)
        self.beginResetModel()
        self.snapshot = data
        self.teams = {t["id"]: t for t in data["teams"]}
        self.endResetModel()

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self.snapshot["participants"])

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        contests = len(self.snapshot["contests"])
        return 0 if parent.isValid() else 5 + contests + bool(contests)

    def is_score_column(self, column: int) -> bool:
        return 5 <= column < 5 + len(self.snapshot["contests"])

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Vertical:
            return section + 1
        return (["Команда", "ФИО", "Школа", "Класс", "Категория"] +
                [c["name"] for c in self.snapshot["contests"]] +
                (["ИТОГО"] if self.snapshot["contests"] else []))[section]

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid():
            return None
        row = self.snapshot["participants"][index.row()]
        col = index.column()
        is_total = bool(self.snapshot["contests"]) and col == self.columnCount() - 1
        if is_total:
            if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole, Qt.ItemDataRole.UserRole):
                return sum(self.snapshot["scores"].get((row["id"], contest["id"]), 0)
                           for contest in self.snapshot["contests"])
            if role == Qt.ItemDataRole.BackgroundRole:
                return QColor("#E5F1EF")
            if role == Qt.ItemDataRole.FontRole:
                font = QFont()
                font.setBold(True)
                return font
            if role == Qt.ItemDataRole.TextAlignmentRole:
                return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            if role == Qt.ItemDataRole.ToolTipRole:
                return "Сумма баллов по всем конкурсам. Пустые оценки учитываются как 0."
            return None
        if role == Qt.ItemDataRole.BackgroundRole and col >= 5:
            return QColor("#F4FAE9")
        if role == Qt.ItemDataRole.ToolTipRole and col >= 5:
            return "Введите целые неотрицательные баллы. Очистите ячейку, чтобы удалить оценку."
        if role not in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole, Qt.ItemDataRole.UserRole):
            return None
        if col < 5:
            return [team_label(self.teams.get(row["team_id"])), row["name"], row["school"], row["class_name"], row["category"]][col]
        points = self.snapshot["scores"].get((row["id"], self.snapshot["contests"][col - 5]["id"]))
        return points if points is not None else (-1 if role == Qt.ItemDataRole.UserRole else "")

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        flags = super().flags(index)
        return flags | Qt.ItemFlag.ItemIsEditable if index.isValid() and self.is_score_column(index.column()) else flags

    def setData(self, index: QModelIndex, value: Any, role: int = Qt.ItemDataRole.EditRole) -> bool:
        if role != Qt.ItemDataRole.EditRole or not index.isValid() or not self.is_score_column(index.column()):
            return False
        participant = self.snapshot["participants"][index.row()]
        contest_id = self.snapshot["contests"][index.column() - 5]["id"]
        try:
            points = None if not str(value).strip() else integer(value, "Баллы")
            team_id = None
            if points is not None and participant["team_id"] is None:
                team_id = self.choose_team()
                if team_id is None:
                    return False
            self.store.save_score(self.event_id, participant["id"], contest_id, points, team_id)
        except (ValueError, OSError, SQLAlchemyError) as exc:
            self.failed.emit(str(exc))
            return False
        if points is None:
            self.snapshot["scores"].pop((participant["id"], contest_id), None)
        else:
            self.snapshot["scores"][(participant["id"], contest_id)] = points
        if team_id is not None:
            participant["team_id"] = team_id
            self.teams = {t["id"]: t for t in self.store.snapshot(self.event_id)["teams"]}
        self.dataChanged.emit(self.index(index.row(), 0), self.index(index.row(), self.columnCount() - 1))
        self.changed.emit()
        return True


class NameFilter(QSortFilterProxyModel):
    def __init__(self) -> None:
        super().__init__()
        self.query = ""
        self.category: int | None = None
        self.setSortRole(Qt.ItemDataRole.UserRole)

    def search(self, text: str) -> None:
        self.beginFilterChange()
        self.query = text.casefold()
        self.endFilterChange(QSortFilterProxyModel.Direction.Rows)

    def set_category(self, category: int | None) -> None:
        if category == self.category:
            return
        self.beginFilterChange()
        self.category = category
        self.endFilterChange(QSortFilterProxyModel.Direction.Rows)

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        source = self.sourceModel()
        name_matches = self.query in str(source.data(source.index(source_row, 1, source_parent))).casefold()
        category_matches = self.category is None or source.data(source.index(source_row, 4, source_parent)) == self.category
        return name_matches and category_matches
