"""Сведения о приложении и публичные контакты разработчика."""

from html import escape
import json
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
                               QLabel, QDialogButtonBox, QWidget)

from .. import __version__

RESOURCES = Path(__file__).resolve().parents[1] / "resources"


class AboutDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("О программе")
        self.setMinimumWidth(490)
        self.resize(580, 390)
        metadata = json.loads((RESOURCES / "about.json").read_text(encoding="utf-8"))
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 20)
        layout.setSpacing(18)
        header = QHBoxLayout()
        icon = QLabel()
        icon.setPixmap(QPixmap(str(RESOURCES / "images/app-icon.png")).scaled(
            72, 72, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        header.addWidget(icon)
        headings = QVBoxLayout()
        headings.setSpacing(4)
        title = QLabel("Школьные конкурсы")
        title.setObjectName("title")
        headings.addWidget(title)
        self.version_label = QLabel(f"Версия {__version__}")
        self.version_label.setObjectName("muted")
        headings.addWidget(self.version_label)
        header.addLayout(headings, 1)
        layout.addLayout(header)
        description = QLabel("Помощник учителей и организаторов: подготовка участников, ввод баллов и подведение итогов школьных конкурсов.")
        description.setWordWrap(True)
        layout.addWidget(description)
        form = QFormLayout()
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(12)
        self.developer_label = QLabel(metadata["developer"])
        self.developer_label.setTextFormat(Qt.TextFormat.PlainText)
        self.developer_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        form.addRow("Разработчик", self.developer_label)
        self.email_link = self.link(metadata["email"], f"mailto:{metadata['email']}")
        form.addRow("Электронная почта", self.email_link)
        self.telegram_link = self.link(metadata["telegram"], metadata["telegram_url"])
        form.addRow("Telegram", self.telegram_link)
        self.project_link = self.link(metadata["project_url"].removeprefix("https://"), metadata["project_url"])
        form.addRow("Проект на GitHub", self.project_link)
        layout.addLayout(form)
        note = QLabel("Нажмите на контакт, чтобы открыть почтовое приложение или Telegram. Страница проекта открывается в браузере.")
        note.setObjectName("muted")
        note.setWordWrap(True)
        layout.addWidget(note)
        layout.addStretch()
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.button(QDialogButtonBox.StandardButton.Close).setText("Закрыть")
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @staticmethod
    def link(text: str, url: str) -> QLabel:
        label = QLabel(f'<a href="{escape(url, quote=True)}" style="color: #17675E;">{escape(text)}</a>')
        label.setTextFormat(Qt.TextFormat.RichText)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        label.setOpenExternalLinks(True)
        label.setWordWrap(True)
        label.setAccessibleName(text)
        return label
