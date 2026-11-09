"""Воспроизводимые снимки экранов на отдельной демонстрационной базе."""

from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from school_contests.storage import Store
from school_contests.ui.window import Window
from school_contests.ui.theme import QSS
from school_contests.ui.dialogs import ImportDialog, ParticipantDialog
from school_contests.ui.guide import GuideDialog
from school_contests.ui.about import AboutDialog
from school_contests.ui.feedback import FeedbackDialog
from school_contests.excel import template
from openpyxl import load_workbook


def main() -> int:
    app = QApplication([])
    app.setStyle("Fusion")
    app.setStyleSheet(QSS)
    output = Path(".local/preview")
    output.mkdir(parents=True, exist_ok=True)
    store = Store(output / "demo.sqlite3")
    events = store.list_events()
    if events:
        event_id = events[0]["id"]
    else:
        event_id = store.save_event("Мир талантов — осенний фестиваль", "2026-11-09", "Школа № 289, Санкт-Петербург")
        teams = [store.save_team(event_id, 1, "Радуга"), store.save_team(event_id, 2, "Открытие")]
        contests = [store.save_contest(event_id, name) for name in ("Логика", "Творчество", "Эрудиция")]
        for i, name in enumerate(("Иванов Иван", "Петрова Мария", "Соколова Анна", "Орлов Алексей", "Смирнова Елена")):
            participant = store.save_participant(event_id, name, "289 СПб", f"{8 + i % 2}в", 8 + i % 2, teams[i % 2])
            for j, contest in enumerate(contests):
                if i == 4 and j == 2:
                    continue
                store.save_score(event_id, participant, contest, [12, 15, 8, 12, 0][i] + j)
    window = Window(store)
    window.show()
    app.processEvents()
    available, frame = window.screen().availableGeometry(), window.frameGeometry()
    assert available.contains(frame), (available, frame)
    assert abs(available.center().x() - frame.center().x()) <= 1, (available, frame)
    assert abs(available.center().y() - frame.center().y()) <= 1, (available, frame)
    print(f"Initial placement verified: screen={available.getRect()}, frame={frame.getRect()}")
    window.grab().save(str(output / "home.png"))
    window.show_events()
    app.processEvents()
    window.grab().save(str(output / "events.png"))
    if window.events_table.model().rowCount():
        window.events_table.selectRow(0)
        app.processEvents()
        window.grab().save(str(output / "events-selected.png"))
    window.open_event(event_id)
    app.processEvents()
    window.grab().save(str(output / "conduct.png"))
    window.tabs.setCurrentIndex(1)
    app.processEvents()
    window.grab().save(str(output / "results.png"))
    window.resize(900, 600)
    app.processEvents()
    window.grab().save(str(output / "results-900.png"))
    window.stack.setCurrentWidget(window.home)
    app.processEvents()
    window.grab().save(str(output / "home-900.png"))

    def capture_news() -> None:
        dialog = app.activeModalWidget()
        if dialog is not None:
            dialog.grab().save(str(output / "news.png"))
            dialog.accept()

    QTimer.singleShot(100, capture_news)
    window.show_news()
    about = AboutDialog(window)
    about.show()
    app.processEvents()
    about.grab().save(str(output / "about.png"))
    about.close()
    feedback = FeedbackDialog(window)
    feedback.show()
    app.processEvents()
    feedback.grab().save(str(output / "feedback.png"))
    feedback.close()
    guide = GuideDialog(window)
    guide.show()
    app.processEvents()
    guide.grab().save(str(output / "guide-start.png"))
    guide.topics.setCurrentRow(6)
    app.processEvents()
    guide.grab().save(str(output / "guide-scores.png"))
    guide.resize(760, 520)
    app.processEvents()
    guide.grab().save(str(output / "guide-small.png"))
    guide.close()
    form = ParticipantDialog(store, event_id, parent=window)
    form.show()
    app.processEvents()
    form.grab().save(str(output / "participant.png"))
    form.reject()
    sample = output / "import-sample.xlsx"
    template(sample)
    workbook = load_workbook(sample)
    sheet = workbook["Участники"]
    sheet.append(["Иванов Иван", "289 СПб", "8в", None, 1, "Радуга"])
    sheet.append(["Новая участница", "193 Москва", "9а", None, None, None])
    sheet.append(["Участник с ошибкой", "5 Калининград", "?", None, None, "Без номера"])
    workbook.save(sample)
    workbook.close()
    preview = ImportDialog(store, event_id, sample, window)
    preview.show()
    app.processEvents()
    preview.grab().save(str(output / "import.png"))
    preview.reject()
    window.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
