"""Сборка onedir, переносного архива и установщика из одной версии."""

from pathlib import Path
import argparse
import os
import shutil
import subprocess
import sys
import tomllib

from school_contests import __version__

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--installer", action="store_true")
    args = parser.parse_args()
    project_version = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    if project_version != __version__:
        raise SystemExit("Версия в pyproject.toml не совпадает с версией приложения.")
    version_tuple = tuple(map(int, __version__.split("."))) + (0,)
    build = ROOT / "build"
    build.mkdir(exist_ok=True)
    version = build / "version.txt"
    version.write_text(f"""VSVersionInfo(
      ffi=FixedFileInfo(filevers={version_tuple}, prodvers={version_tuple}, mask=0x3f,
      flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
      kids=[StringFileInfo([StringTable('041904B0', [
      StringStruct('FileDescription', 'Школьные конкурсы'),
      StringStruct('FileVersion', '{__version__}'),
      StringStruct('ProductName', 'Школьные конкурсы'),
      StringStruct('ProductVersion', '{__version__}')])]), VarFileInfo([VarStruct('Translation', [1049, 1200])])])
    """.strip(), encoding="utf-8")
    resources = ROOT / "src/school_contests/resources"
    subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onedir", "--windowed",
                    "--name", "SchoolContests", "--paths", str(ROOT / "src"),
                    "--icon", str(resources / "images/app.ico"), "--version-file", str(version),
                    "--add-data", f"{resources};school_contests/resources",
                    "--add-data", f"{Path(__import__('PySide6').__file__).parent / 'translations/qtbase_ru.qm'};PySide6/translations",
                    "--exclude-module", "PySide6.QtWebEngineCore", "--exclude-module", "PySide6.QtWebEngineWidgets",
                    "--exclude-module", "PySide6.QtQml", "--exclude-module", "PySide6.QtQuick",
                    "--specpath", str(build), str(ROOT / "scripts/entry.py")], cwd=ROOT, check=True)
    application = ROOT / "dist/SchoolContests"
    shutil.copy2(ROOT / "README.md", application / "Инструкция.md")
    # Маркер есть только в переносном архиве, не в исходнике для установщика.
    marker = application / "portable.flag"
    marker.write_text("portable\n", encoding="utf-8")
    try:
        shutil.make_archive(str(ROOT / "dist" / f"SchoolContests-{__version__}-portable"), "zip", ROOT / "dist", "SchoolContests")
    finally:
        marker.unlink()
    if args.installer:
        compiler = shutil.which("ISCC.exe")
        if not compiler:
            candidates = [Path(os.environ.get("LOCALAPPDATA", "")) / "Programs/Inno Setup 6/ISCC.exe",
                          Path("C:/Program Files (x86)/Inno Setup 6/ISCC.exe")]
            compiler = next((str(path) for path in candidates if path.exists()), None)
        if compiler is None:
            raise SystemExit("Inno Setup 6 не найден. Установите его и повторите сборку с --installer.")
        subprocess.run([compiler, f"/DAppVersion={__version__}", str(ROOT / "installer/school-contests.iss")], cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
