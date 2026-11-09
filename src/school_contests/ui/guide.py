"""Локальный путеводитель с оглавлением и последовательным переходом между темами."""

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QTextCursor, QTextBlockFormat
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListWidget,
                               QTextBrowser, QPushButton, QWidget, QSplitter)

GUIDE_PATH = Path(__file__).resolve().parents[1] / "resources/guide.md"


@dataclass(frozen=True)
class GuideSection:
    title: str
    body: str


def load_sections() -> tuple[GuideSection, ...]:
    sections = []
    for part in GUIDE_PATH.read_text(encoding="utf-8").split("\n## ")[1:]:
        title, _, body = part.partition("\n")
        sections.append(GuideSection(title.strip(), body.strip()))
    if not sections:
        raise ValueError("В путеводителе отсутствуют разделы.")
    return tuple(sections)


class GuideDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Путеводитель по приложению")
        self.sections = load_sections()
        screen = self.screen()
        area = screen.availableGeometry() if screen else None
        width = min(1060, area.width() - 64) if area else 1060
        height = min(740, area.height() - 80) if area else 740
        self.resize(width, height)
        self.setMinimumSize(min(760, width), min(500, height))
        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 18, 20, 18)
        outer.setSpacing(12)
        title = QLabel("Путеводитель по приложению")
        title.setObjectName("title")
        outer.addWidget(title)
        subtitle = QLabel("Для учителей и организаторов: от подготовки участников до награждения")
        subtitle.setObjectName("muted")
        subtitle.setWordWrap(True)
        outer.addWidget(subtitle)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        self.topics = QListWidget()
        self.topics.setObjectName("guideTopics")
        self.topics.setAccessibleName("Темы путеводителя")
        self.topics.setMinimumWidth(200)
        self.topics.addItems([f"{i + 1}. {section.title}" for i, section in enumerate(self.sections)])
        splitter.addWidget(self.topics)
        article = QWidget()
        body_layout = QVBoxLayout(article)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(8)
        self.section_title = QLabel()
        self.section_title.setObjectName("guideSectionTitle")
        self.section_title.setWordWrap(True)
        body_layout.addWidget(self.section_title)
        self.body = QTextBrowser()
        self.body.setObjectName("guideBody")
        self.body.setAccessibleName("Инструкция по выбранной теме")
        self.body.setOpenExternalLinks(False)
        self.body.setOpenLinks(False)
        body_layout.addWidget(self.body)
        splitter.addWidget(article)
        splitter.setSizes([260, 740])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        outer.addWidget(splitter, 1)
        footer = QHBoxLayout()
        self.previous = QPushButton("Назад")
        self.next = QPushButton("Далее")
        self.next.setObjectName("primary")
        self.position = QLabel()
        self.position.setObjectName("muted")
        close = QPushButton("Закрыть")
        self.previous.clicked.connect(lambda: self.topics.setCurrentRow(self.topics.currentRow() - 1))
        self.next.clicked.connect(lambda: self.topics.setCurrentRow(self.topics.currentRow() + 1))
        close.clicked.connect(self.accept)
        footer.addWidget(self.previous)
        footer.addWidget(self.next)
        footer.addWidget(self.position)
        footer.addStretch()
        footer.addWidget(close)
        outer.addLayout(footer)
        self.topics.currentRowChanged.connect(self.show_section)
        self.topics.setCurrentRow(0)

    def show_section(self, index: int) -> None:
        if not 0 <= index < len(self.sections):
            return
        section = self.sections[index]
        self.section_title.setText(section.title)
        self.body.setMarkdown(section.body)
        block = self.body.document().begin()
        while block.isValid():
            cursor = QTextCursor(block)
            formatting = block.blockFormat()
            formatting.setTopMargin(10 if formatting.headingLevel() else 0)
            formatting.setBottomMargin(4 if block.textList() else 10)
            formatting.setLineHeight(130, QTextBlockFormat.LineHeightTypes.ProportionalHeight.value)
            cursor.setBlockFormat(formatting)
            block = block.next()
        self.body.verticalScrollBar().setValue(0)
        self.previous.setEnabled(index > 0)
        self.next.setEnabled(index < len(self.sections) - 1)
        self.position.setText(f"Тема {index + 1} из {len(self.sections)}")
