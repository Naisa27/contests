"""Компактные карточки финалистов с адаптивной сеткой и цветами призовых мест."""

from typing import Any

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import (QWidget, QFrame, QLabel, QVBoxLayout, QHBoxLayout,
                               QGridLayout, QSizePolicy, QLayout)

from ..domain import KINDS, Standing, Winner, calculate, preliminary


class WinnerRow(QFrame):
    def __init__(self, winner: Winner) -> None:
        super().__init__()
        self.setObjectName("winnerRow")
        self.setProperty("place", str(winner.place))
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(10)
        place = QLabel(f"{winner.place} место")
        place.setObjectName("winnerPlace")
        place.setFixedWidth(62)
        layout.addWidget(place, 0, Qt.AlignmentFlag.AlignTop)
        identity = QVBoxLayout()
        identity.setSpacing(2)
        name = QLabel(winner.name)
        name.setTextFormat(Qt.TextFormat.PlainText)
        name.setWordWrap(True)
        name.setObjectName("winnerName")
        identity.addWidget(name)
        if winner.detail:
            detail = QLabel(winner.detail)
            detail.setTextFormat(Qt.TextFormat.PlainText)
            detail.setWordWrap(True)
            detail.setObjectName("winnerDetail")
            identity.addWidget(detail)
        layout.addLayout(identity, 1)
        points = QLabel(f"{winner.points} балл.")
        points.setObjectName("winnerPoints")
        layout.addWidget(points, 0, Qt.AlignmentFlag.AlignTop)


class ResultCard(QFrame):
    def __init__(self, standing: Standing) -> None:
        super().__init__()
        self.setObjectName("resultCard")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(6)
        title = QLabel(standing.title)
        title.setObjectName("resultCardTitle")
        title.setTextFormat(Qt.TextFormat.PlainText)
        title.setWordWrap(True)
        layout.addWidget(title)
        if not standing.winners:
            empty = QLabel("Назначьте участникам команды для командного зачёта.")
            empty.setWordWrap(True)
            layout.addWidget(empty)
        for winner in standing.winners:
            layout.addWidget(WinnerRow(winner))
        layout.addStretch()


class CardsGrid(QWidget):
    def __init__(self, standings: list[Standing]) -> None:
        super().__init__()
        self.cards = [ResultCard(standing) for standing in standings]
        self.grid = QGridLayout(self)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setSpacing(12)
        self.grid.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)
        self.columns = 0
        self.arrange(1)

    def minimumSizeHint(self) -> QSize:
        # Минимум двухколоночной сетки не должен мешать её сужению до одной колонки.
        return QSize(max((card.minimumSizeHint().width() for card in self.cards), default=0),
                     super().minimumSizeHint().height())

    def arrange(self, columns: int) -> None:
        if columns == self.columns:
            return
        self.columns = columns
        while self.grid.count():
            self.grid.takeAt(0)
        self.grid.setColumnStretch(0, 1)
        self.grid.setColumnStretch(1, 1 if columns == 2 else 0)
        for index, card in enumerate(self.cards):
            self.grid.addWidget(card, index // columns, index % columns)
        self.updateGeometry()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        # Две карточки должны оставлять место для ФИО, школы и баллов.
        self.arrange(2 if self.width() >= 880 else 1)


class ResultsContent(QWidget):
    def __init__(self, snapshot: dict[str, Any]) -> None:
        super().__init__()
        self.setObjectName("resultsContent")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 12, 8, 12)
        layout.setSpacing(14)
        if not snapshot["participants"] or not snapshot["contests"]:
            empty = QLabel("Добавьте участников и хотя бы один конкурс, чтобы увидеть результаты.")
            empty.setWordWrap(True)
            layout.addWidget(empty)
        else:
            if preliminary(snapshot):
                notice = QLabel("Предварительные результаты: незаполненные баллы учитываются как 0")
                notice.setObjectName("resultsNotice")
                notice.setWordWrap(True)
                layout.addWidget(notice)
            standings = calculate(snapshot)
            layout.addWidget(CardsGrid([row for row in standings if row.kind in ("team", "individual")]))
            for kind in ("category", "within_team", "contest"):
                group = [row for row in standings if row.kind == kind]
                if not group:
                    continue
                heading = QLabel(KINDS[kind])
                heading.setObjectName("resultsHeading")
                layout.addWidget(heading)
                layout.addWidget(CardsGrid(group))
        layout.addStretch()
