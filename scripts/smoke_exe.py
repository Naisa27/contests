"""Запуск готового exe с отдельной базой и штатное закрытие через WM_CLOSE."""

from pathlib import Path
import ctypes
from ctypes import wintypes
import os
import sqlite3
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    output = ROOT / ".local/smoke-exe"
    output.mkdir(parents=True, exist_ok=True)
    database = output / "smoke.sqlite3"
    environment = dict(os.environ, QT_QPA_PLATFORM="windows", SCHOOL_CONTESTS_DATA=str(database))
    process = subprocess.Popen([str(ROOT / "dist/SchoolContests/SchoolContests.exe")], env=environment)
    user32 = ctypes.windll.user32
    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    found: list[tuple[int, str]] = []
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    @callback_type
    def callback(handle: int, parameter: int) -> bool:
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(handle, ctypes.byref(pid))
        if pid.value == process.pid and user32.IsWindowVisible(handle):
            text = ctypes.create_unicode_buffer(512)
            user32.GetWindowTextW(handle, text, 512)
            found.append((handle, text.value))
        return True

    try:
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            found.clear()
            user32.EnumWindows(callback, 0)
            if any(title.startswith("Школьные конкурсы —") for _, title in found):
                break
            if process.poll() is not None:
                raise RuntimeError(f"Приложение завершилось до появления окна: {process.returncode}")
            time.sleep(0.2)
        else:
            raise RuntimeError(f"Главное окно не появилось: {found}")
        with sqlite3.connect(database) as connection:
            assert connection.execute("PRAGMA user_version").fetchone()[0] == 1
            assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        for handle, title in found:
            if title.startswith("Школьные конкурсы —"):
                user32.PostMessageW(handle, 0x0010, 0, 0)
        assert process.wait(timeout=15) == 0
        assert not Path(str(database) + ".lock").exists()
        print("EXE smoke test passed: window, database, clean shutdown")
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=10)


if __name__ == "__main__":
    main()
