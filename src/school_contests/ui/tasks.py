"""Длительные операции выполняются вне GUI, часы и перерисовка продолжают работать."""

from typing import Any, Callable
from PySide6.QtCore import QThread, Qt
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QDialog, QLabel, QProgressBar, QVBoxLayout, QWidget


class Task(QThread):
    def __init__(self, action: Callable[[], Any]) -> None:
        super().__init__()
        self.action = action
        self.value: Any = None
        self.error: Exception | None = None

    def run(self) -> None:
        try:
            self.value = self.action()
        except Exception as exc:
            self.error = exc


class Progress(QDialog):
    def reject(self) -> None:
        pass

    def closeEvent(self, event: QCloseEvent) -> None:
        event.ignore()


def run_task(parent: QWidget, title: str, action: Callable[[], Any]) -> Any:
    dialog = Progress(parent)
    dialog.setWindowTitle(title)
    dialog.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, False)
    dialog.setMinimumWidth(400)
    layout = QVBoxLayout(dialog)
    layout.addWidget(QLabel(title))
    progress = QProgressBar()
    progress.setRange(0, 0)
    layout.addWidget(progress)
    worker = Task(action)
    worker.finished.connect(dialog.accept)
    worker.start()
    dialog.exec()
    worker.wait()
    if worker.error:
        raise worker.error
    return worker.value
