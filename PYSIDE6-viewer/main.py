import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtWidgets import QApplication, QDialog

from app import config, theme
from app.settings import Settings
from app.login_dialog import LoginDialog
from app.main_window import MainWindow


def main() -> int:
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    app.setOrganizationName(config.ORG_NAME)
    app.setApplicationName("OrizonViewer")
    app.setApplicationDisplayName(config.APP_NAME)
    app.setStyle("Fusion")
    # l'uscita avviene solo dopo il PIN (MainWindow chiama quit esplicitamente)
    app.setQuitOnLastWindowClosed(False)

    scale = config.compute_scale(app.primaryScreen())
    app.setProperty("ui_scale", scale)
    font = app.font()
    font.setFamilies(config.ui_fonts())
    font.setPixelSize(round(16 * scale))
    app.setFont(font)
    theme.apply_theme(app, Settings().theme())
    app.setWindowIcon(QIcon(config.resource_path(config.LOGO_FILE)))

    login = LoginDialog()
    login.show_fullscreen()
    if login.exec() != QDialog.Accepted:
        return 0

    window = MainWindow(scale)
    window.enter_fullscreen()  # unico punto in cui si entra in fullscreen
    window.start_session()     # solo dopo: ultimo file / wizard
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
