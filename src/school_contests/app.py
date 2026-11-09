"""Запуск, выбор каталога данных и блокировка второго экземпляра."""

from pathlib import Path
import os
import sys
import ctypes
from sqlalchemy.exc import SQLAlchemyError

from PySide6.QtCore import QLockFile, QLocale, QTranslator, QLibraryInfo
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from . import __version__
from .storage import Store
from .ui.theme import QSS
from .ui.window import Window, RESOURCES


def data_path() -> Path:
    if os.environ.get("SCHOOL_CONTESTS_DATA"):
        return Path(os.environ["SCHOOL_CONTESTS_DATA"]).resolve()
    if getattr(sys, "frozen", False):
        directory = Path(sys.executable).parent
        if (directory / "portable.flag").exists():
            return directory / "data" / "contests.sqlite3"
        return Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "SchoolContests" / "data" / "contests.sqlite3"
    return Path(__file__).resolve().parents[2] / ".local" / "contests.sqlite3"


def main() -> int:
    if sys.platform == "win32":
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("SchoolContests.Desktop")
    app = QApplication(sys.argv)
    app.setApplicationName("Школьные конкурсы")
    app.setApplicationVersion(__version__)
    app.setOrganizationName("SchoolContests")
    app.setStyle("Fusion")
    app.setStyleSheet(QSS)
    app.setWindowIcon(QIcon(str(RESOURCES / "images" / "app.ico")))
    QLocale.setDefault(QLocale("ru_RU"))
    translator = QTranslator(app)
    translator.load("qtbase_ru", QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath))
    app.installTranslator(translator)
    try:
        path = data_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        lock = QLockFile(str(path) + ".lock")
        lock.setStaleLockTime(0)
        if not lock.tryLock(0):
            QMessageBox.information(None, "Приложение уже открыто", "Эта база уже открыта другим экземпляром приложения.")
            return 1
        store = Store(path)
    except (OSError, ValueError, SQLAlchemyError) as exc:
        QMessageBox.critical(None, "Не удалось открыть данные", f"{exc}\nПеренесите переносную версию в папку с правом записи или проверьте доступ к каталогу данных.")
        return 1
    window = Window(store)
    window.show()
    result = app.exec()
    lock.unlock()
    return result
