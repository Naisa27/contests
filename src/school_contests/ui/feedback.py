"""Форма отправки сообщения без запуска браузера или почтовой программы."""

from uuid import uuid4

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (QDialog, QWidget, QVBoxLayout, QFormLayout, QLabel,
                               QPlainTextEdit, QLineEdit, QPushButton, QHBoxLayout, QMessageBox)

from ..feedback import Feedback, FeedbackError, MAX_MESSAGE, send_feedback
from .tasks import Task


class FeedbackDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Обратная связь: вопросы и пожелания")
        self.resize(640, 550)
        self.setMinimumSize(500, 460)
        self.worker: Task | None = None
        self.request_id = str(uuid4())
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)
        title = QLabel("Вопросы и пожелания")
        title.setObjectName("title")
        layout.addWidget(title)
        message_label = QLabel("Сообщение (обязательно)")
        layout.addWidget(message_label)
        self.message = QPlainTextEdit()
        self.message.setPlaceholderText("опишите свой вопрос или проблему")
        self.message.setAccessibleName("Сообщение (обязательно)")
        self.message.setTabChangesFocus(True)
        message_label.setBuddy(self.message)
        layout.addWidget(self.message, 1)
        self.counter = QLabel(f"0 / {MAX_MESSAGE}")
        self.counter.setObjectName("muted")
        layout.addWidget(self.counter)
        form = QFormLayout()
        self.name = QLineEdit()
        self.name.setMaxLength(120)
        self.name.setAccessibleName("Имя (необязательно)")
        self.contact = QLineEdit()
        self.contact.setMaxLength(240)
        self.contact.setPlaceholderText("Почта, телефон или Telegram — если хотите получить ответ")
        self.contact.setAccessibleName("Контакт для связи (необязательно)")
        form.addRow("Имя (необязательно)", self.name)
        form.addRow("Контакт для связи\n(необязательно)", self.contact)
        layout.addLayout(form)
        notice = QLabel("Разработчику будут переданы сообщение, указанные имя и контакт, версия приложения и ваш внешний IP-адрес. Для отправки нужен интернет.")
        notice.setWordWrap(True)
        notice.setObjectName("muted")
        layout.addWidget(notice)
        self.status = QLabel()
        self.status.setWordWrap(True)
        self.status.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.status)
        actions = QHBoxLayout()
        actions.addStretch()
        self.cancel_button = QPushButton("Закрыть")
        self.cancel_button.clicked.connect(self.reject)
        self.send_button = QPushButton("Отправить")
        self.send_button.setObjectName("primary")
        self.send_button.clicked.connect(self.submit)
        actions.addWidget(self.cancel_button)
        actions.addWidget(self.send_button)
        layout.addLayout(actions)
        self.message.textChanged.connect(self.edited)
        self.name.textChanged.connect(self.edited)
        self.contact.textChanged.connect(self.edited)

    def edited(self) -> None:
        self.request_id = str(uuid4())
        length = len(self.message.toPlainText())
        self.counter.setText(f"{length} / {MAX_MESSAGE}")
        self.send_button.setEnabled(length <= MAX_MESSAGE)
        self.status.clear()

    def submit(self) -> None:
        if self.worker is not None:
            return
        feedback = Feedback(self.message.toPlainText(), self.name.text(), self.contact.text())
        try:
            feedback.validate()
        except FeedbackError as exc:
            self.show_error(str(exc))
            self.message.setFocus()
            return
        for widget in (self.message, self.name, self.contact, self.send_button, self.cancel_button):
            widget.setEnabled(False)
        self.status.setObjectName("muted")
        self.status.setText("Отправляем сообщение…")
        self.status.style().unpolish(self.status)
        self.status.style().polish(self.status)
        request_id = self.request_id
        self.worker = Task(lambda: send_feedback(feedback, request_id))
        self.worker.finished.connect(self.completed)
        self.worker.start()

    def completed(self) -> None:
        worker = self.worker
        if worker is None:
            return
        worker.wait()
        self.worker = None
        worker.deleteLater()
        for widget in (self.message, self.name, self.contact, self.send_button, self.cancel_button):
            widget.setEnabled(True)
        if worker.error is not None:
            self.show_error(str(worker.error) if isinstance(worker.error, FeedbackError)
                            else "Не удалось отправить сообщение. Текст сохранён; попробуйте позже.")
            return
        QMessageBox.information(self, "Обратная связь", "Сообщение успешно отправлено разработчику.")
        self.accept()

    def show_error(self, text: str) -> None:
        self.status.setObjectName("error")
        self.status.setText(text)
        self.status.style().unpolish(self.status)
        self.status.style().polish(self.status)

    def reject(self) -> None:
        if self.worker is None:
            super().reject()

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.worker is not None:
            event.ignore()
        else:
            super().closeEvent(event)
