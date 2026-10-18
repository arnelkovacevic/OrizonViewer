"""Controlli statici di Avvia_OrizonViewer.bat, build_exe.bat, Ripristina_account.bat e dei file di build.
(Non si possono eseguire fuori da Windows: qui si verificano sintassi e contenuti.)"""
import os
import re
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BATS = ["Avvia_OrizonViewer.bat", "build_exe.bat", "Ripristina_account.bat"]


def read(name, binary=False):
    with open(os.path.join(ROOT, name), "rb" if binary else "r", **({} if binary else {"encoding": "utf-8", "newline": ""})) as f:
        return f.read()


@pytest.mark.parametrize("name", BATS)
def test_bat_basics(name):
    raw = read(name, binary=True)
    assert b"\r\n" in raw and b"\n" not in raw.replace(b"\r\n", b""), "servono terminatori CRLF"
    raw.decode("ascii")                                    # solo ASCII: niente problemi di codepage
    text = raw.decode("ascii")
    lines = text.split("\r\n")
    assert lines[0].lower() == "@echo off"
    labels = {l[1:].strip().lower() for l in lines if l.startswith(":") and not l.startswith("::")}
    for l in lines:
        m = re.match(r"\s*(?:if .*\s)?goto\s+:?(\S+)", l, re.I)
        if m and m.group(1).lower() != "eof":
            assert m.group(1).lower() in labels, f"{name}: etichetta mancante {m.group(1)}"


@pytest.mark.parametrize("name", BATS)
def test_bat_quotes_and_parentheses(name):
    lines = read(name).split("\r\n")
    depth = 0
    for n, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.lower().startswith("rem "):
            continue
        assert line.count('"') % 2 == 0, f"{name}:{n} virgolette dispari: {line}"
        is_echo = stripped.lower().startswith("echo")
        # blocchi ( ... ): le righe echo dentro un blocco non possono contenere parentesi
        if depth > 0 and is_echo:
            assert "(" not in stripped and ")" not in stripped, f"{name}:{n} parentesi in echo dentro un blocco"
        if stripped.startswith(")"):
            depth -= 1
        if stripped.endswith("(") and not is_echo:
            depth += 1
        assert depth >= 0, f"{name}:{n} parentesi chiusa in piu'"
    assert depth == 0, f"{name}: blocco ( non chiuso"


def test_launcher_content():
    t = read("Avvia_OrizonViewer.bat")
    assert 'cd /d "%~dp0"' in t                                      # funziona con percorsi con spazi
    assert t.index("py -3") < t.index("python --version")             # prima il launcher py, poi python
    assert "python.org" in t and "Add Python to PATH" in t and "pause" in t
    assert "Prima installazione in corso, attendere..." in t
    assert "-m venv venv" in t and "pip install --upgrade pip" in t and "pip install -r requirements.txt" in t
    assert "certutil -hashfile" in t and "SHA256" in t and r"venv\req.sha" in t
    assert 'start "" "venv\\Scripts\\pythonw.exe" main.py' in t
    assert "errorlevel" in t and "install_failed" in t and "installazione non riuscita" in t


def test_build_content_and_release_layout():
    t = read("build_exe.bat")
    assert 'cd /d "%~dp0"' in t and "-m venv venv" in t and "pip install pyinstaller" in t
    assert "-m PyInstaller --noconfirm --clean OrizonViewer.spec" in t
    assert r"release\OrizonViewer_v%VER%" in t and "print_version.py" in t
    for item in ("OrizonViewer.exe", "Ripristina_account.bat", r"tools\LEGGIMI.txt"):
        assert item in t
    assert t.count("pause") >= 3 and "creazione dell'exe non riuscita" in t
    assert "pause" in t.split("echo   FATTO")[1]


def test_print_version_matches_config():
    out = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "print_version.py")],
                         capture_output=True, text=True, check=True).stdout.strip()
    sys.path.insert(0, ROOT)
    from app import config
    assert out == config.APP_VERSION


def test_leggimi_content():
    t = read(os.path.join("tools", "LEGGIMI.txt"))
    for needle in ("Ulteriori informazioni", "Esegui comunque", "%APPDATA%\\Orizon-AIX\\OrizonViewer",
                   "Ripristina_account.bat", "Configurazione iniziale", "CODICE DI RECUPERO", "orizon.log"):
        assert needle in t


def test_spec_icon_and_data():
    spec = read("OrizonViewer.spec")
    assert "icon='assets/orizon.ico'" in spec and "('assets/orizon.ico', 'assets')" in spec
    assert "console=False" in spec
    from PIL import Image
    ico = Image.open(os.path.join(ROOT, "assets", "orizon.ico"))
    assert set(ico.info["sizes"]) == {(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)}


def test_requirements_are_minimums_only():
    lines = [l.strip() for l in read("requirements.txt").splitlines() if l.strip() and not l.startswith("#")]
    assert lines and all(">=" in l and "==" not in l for l in lines)
    names = {re.split(r"[<>=]", l)[0].lower() for l in lines}
    assert {"pyside6", "pandas", "openpyxl", "xlrd", "pyxlsb", "odfpy", "python-barcode", "qrcode", "pillow"} <= names


def test_gitignore_has_release():
    assert "release/" in read(".gitignore").split()
