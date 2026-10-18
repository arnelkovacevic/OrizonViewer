import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="session")
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    app.setStyle("Fusion")
    app.setProperty("ui_scale", 1.0)
    from app import config, theme
    font = app.font()
    font.setPixelSize(16)
    app.setFont(font)
    theme.apply_theme(app, "dark")
    return app


@pytest.fixture()
def fixture_xlsx(tmp_path):
    from fixture_builder import build
    return build(str(tmp_path / "fixture.xlsx"))
