"""Проверяет ресурсы, свежесть ключевых модулей, ZIP и единый номер версии."""

from pathlib import Path
from zipfile import ZipFile
from types import CodeType
from PyInstaller.archive.readers import ZlibArchiveReader
from PyInstaller.utils.win32.versioninfo import read_version_info_from_executable
from school_contests import __version__
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
    dialogs = archive.extract("school_contests.ui.dialogs")
    assert any("resizeRowsToContents" in code.co_names for code in walk(dialogs)), "Устаревший предпросмотр импорта"
    application = ROOT / "dist/SchoolContests"
    info = read_version_info_from_executable(str(application / "SchoolContests.exe"))
    expected = tuple(map(int, __version__.split("."))) + (0,)
    assert info.ffi.fileVersionMS == expected[0] * 65536 + expected[1]
    assert info.ffi.fileVersionLS == expected[2] * 65536 + expected[3]
    for name in ("images/logo.jpg", "images/app.ico", "images/app-icon.png", "changes.txt"):
        assert (application / "_internal/school_contests/resources" / name).is_file()
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
