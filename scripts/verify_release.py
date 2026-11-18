"""Проверяет ресурсы, свежесть ключевых модулей, ZIP и единый номер версии."""

from pathlib import Path
from zipfile import ZipFile
from types import CodeType, FunctionType
from collections import Counter
from PyInstaller.archive.readers import ZlibArchiveReader
from PyInstaller.utils.win32.versioninfo import read_version_info_from_executable
from school_contests import __version__
from school_contests.domain import Winner, team_label
from school_contests.statistics import ParticipantStatistics
from school_contests.ui.theme import QSS

ROOT = Path(__file__).resolve().parents[1]


def walk(code: CodeType) -> list[CodeType]:
    return [code] + [child for value in code.co_consts if isinstance(value, CodeType) for child in walk(value)]


def main() -> None:
    archive = ZlibArchiveReader(str(ROOT / "build/SchoolContests/PYZ-00.pyz"))
    theme = archive.extract("school_contests.ui.theme")
    assert QSS in theme.co_consts, "В exe устаревшая тема"
    model = archive.extract("school_contests.ui.models")
    assert any(code.co_name == "ScoreDelegate" for code in walk(model)), "Нет редактора очистки оценок"
    assert any(code.co_name == "set_school" for code in walk(model)), "Нет фильтра по школе"
    assert any(code.co_name == "set_team" for code in walk(model)), "Нет фильтра по команде"
    window = archive.extract("school_contests.ui.window")
    assert any(code.co_name == "refresh_schools" for code in walk(window)), "Нет обновления списка школ"
    assert any(code.co_name == "refresh_teams" for code in walk(window)), "Нет обновления списка команд"
    assert any("AdjustToContents" in code.co_names for code in walk(window)), "Нет ширины фильтров по содержимому"
    assert any("isdecimal" in code.co_names for code in walk(window)), "Нет числовой сортировки школ"
    domain = archive.extract("school_contests.domain")
    rank_code = next(code for code in walk(domain) if code.co_name == "rank")
    packaged_rank = FunctionType(rank_code, {"Winner": Winner})
    assert packaged_rank([Winner(1, "Ноль", "", 0)]) == (), "Нулевой результат попадает в призёры"
    assert [row.place for row in packaged_rank([Winner(1, "А", "", 5), Winner(2, "Б", "", 5),
                                               Winner(3, "В", "", 2), Winner(4, "Г", "", 0)])] == [1, 1, 2]
    dialogs = archive.extract("school_contests.ui.dialogs")
    assert any("resizeRowsToContents" in code.co_names for code in walk(dialogs)), "Устаревший предпросмотр импорта"
    guide = archive.extract("school_contests.ui.guide")
    assert any(code.co_name == "GuideDialog" for code in walk(guide)), "Нет окна путеводителя"
    about = archive.extract("school_contests.ui.about")
    assert any(code.co_name == "AboutDialog" for code in walk(about)), "Нет окна «О программе»"
    feedback = archive.extract("school_contests.ui.feedback")
    assert any(code.co_name == "FeedbackDialog" for code in walk(feedback)), "Нет формы обратной связи"
    statistics = archive.extract("school_contests.ui.statistics")
    assert any(code.co_name == "StatisticsContent" for code in walk(statistics)), "Нет вкладки статистики"
    assert any(code.co_name == "reflow" for code in walk(statistics)), "Нет адаптивного размещения таблиц"
    counts = archive.extract("school_contests.statistics")
    assert any(code.co_name == "participant_statistics" for code in walk(counts)), "Нет подсчётов участников"
    counts_code = next(code for code in walk(counts) if code.co_name == "participant_statistics")
    packaged_counts = FunctionType(counts_code, {
        "Counter": Counter, "ParticipantStatistics": ParticipantStatistics, "team_label": team_label,
    })
    team_counts = packaged_counts(
        [dict(name="Иван", school="289", class_name="9а", category=9, team_id=1),
         dict(name="Анна", school="193", class_name="8а", category=8, team_id=None)],
        [dict(id=1, number=1, name="Совы"), dict(id=2, number=2, name="")],
    )
    assert team_counts.by_team == (("№ 1 — Совы", 1), ("№ 2", 0), ("Без команды", 1)), "Неверная статистика команд в exe"
    assert __version__ in archive.extract("school_contests").co_consts, "В exe неверная версия пакета"
    application = ROOT / "dist/SchoolContests"
    expected = tuple(map(int, __version__.split("."))) + (0,)
    installer = ROOT / "dist" / f"SchoolContests-{__version__}-setup.exe"
    for executable in (application / "SchoolContests.exe", installer):
        info = read_version_info_from_executable(str(executable))
        assert info.ffi.fileVersionMS == expected[0] * 65536 + expected[1], executable
        assert info.ffi.fileVersionLS == expected[2] * 65536 + expected[3], executable
    for name in ("images/logo.jpg", "images/app.ico", "images/app-icon.png", "changes.txt", "guide.md", "about.json", "feedback.json"):
        assert (application / "_internal/school_contests/resources" / name).is_file()
    for name in ("guide.md", "changes.txt", "about.json", "feedback.json"):
        assert (application / "_internal/school_contests/resources" / name).read_bytes() == (ROOT / "src/school_contests/resources" / name).read_bytes()
    assert (application / "Путеводитель.md").read_bytes() == (ROOT / "src/school_contests/resources/guide.md").read_bytes()
    assert "../src/school_contests/resources/guide.md" not in (application / "Инструкция.md").read_text(encoding="utf-8")
    assert not (application / "portable.flag").exists()
    with ZipFile(ROOT / "dist" / f"SchoolContests-{__version__}-portable.zip") as zipped:
        assert "SchoolContests/portable.flag" in zipped.namelist()
        assert zipped.testzip() is None
    assert (ROOT / "dist" / f"SchoolContests-{__version__}-setup.exe").stat().st_size > 0
    print("Release verified: modules, resources, version, portable ZIP")
    for path in (ROOT / "dist").iterdir():
        if path.is_file():
            print(f"{path.name}: {path.stat().st_size / 1048576:.1f} MiB")


if __name__ == "__main__":
    main()
