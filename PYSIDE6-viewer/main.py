import datetime
import os
import sys
import threading
import traceback

from app import auth  # solo libreria standard: serve per il percorso del log anche se Qt non parte

# ------------------------------------------------------------------ gestione errori imprevisti
# Installata PRIMA degli import di Qt: anche un errore di avvio (es. libreria mancante) finisce nel log.
_handling_error = False
_bridge = None


def log_path() -> str:
    return os.path.join(auth.data_dir(), "orizon.log")


def write_crash_log(exc_type, exc, tb) -> str:
    """Scrive l'errore con traceback in orizon.log (anche prima che esista la QApplication)."""
    path = log_path()
    text = "".join(traceback.format_exception(exc_type, exc, tb))
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"\n{datetime.datetime.now():%Y-%m-%d %H:%M:%S} CRITICAL errore imprevisto\n{text}")
    except OSError:
        pass
    return path


def show_error_dialog(path: str):
    """Dialogo nello stile dell'app. Senza QApplication (errore all'avvio) resta solo il log."""
    global _handling_error
    try:
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()
    except Exception:  # noqa: BLE001 - Qt non importabile: solo log
        return
    if app is None or _handling_error:
        return
    _handling_error = True
    try:
        from app.error_dialog import ErrorDialog
        ErrorDialog(app.activeWindow(), path).exec()
    except Exception:  # noqa: BLE001 - se anche il dialogo fallisce, l'errore e' gia' nel log
        pass
    finally:
        _handling_error = False


def handle_exception(exc_type, exc, tb):
    if issubclass(exc_type, (KeyboardInterrupt, SystemExit)):
        sys.__excepthook__(exc_type, exc, tb)
        return
    path = write_crash_log(exc_type, exc, tb)
    if threading.current_thread() is threading.main_thread():
        show_error_dialog(path)
    elif _bridge is not None:
        _bridge.failed.emit(path)  # il dialogo si apre nel thread dell'interfaccia


def handle_thread_exception(args):
    handle_exception(args.exc_type, args.exc_value, args.exc_traceback)


def install_excepthooks():
    """sys.excepthook + threading.excepthook; con una QApplication abilita anche gli errori dai thread."""
    global _bridge
    sys.excepthook = handle_exception
    threading.excepthook = handle_thread_exception
    try:
        from PySide6.QtCore import QObject, Signal
        from PySide6.QtWidgets import QApplication
    except Exception:  # noqa: BLE001
        return
    if QApplication.instance() is not None and _bridge is None:
        class ErrorBridge(QObject):
            failed = Signal(str)

        _bridge = ErrorBridge()
        _bridge.failed.connect(show_error_dialog)


install_excepthooks()

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtGui import QGuiApplication, QIcon  # noqa: E402
from PySide6.QtWidgets import QApplication, QDialog  # noqa: E402

from app import config, theme  # noqa: E402
from app.settings import Settings  # noqa: E402
from app.login_dialog import LoginDialog  # noqa: E402
from app.main_window import MainWindow  # noqa: E402


def setup_logging():
    """Log su file nella cartella dati (mai segreti: solo eventi)."""
    import logging
    from logging.handlers import RotatingFileHandler
    try:
        os.makedirs(auth.data_dir(), exist_ok=True)
        handler = RotatingFileHandler(log_path(), maxBytes=200_000, backupCount=2, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        logging.getLogger().addHandler(handler)
        logging.getLogger().setLevel(logging.INFO)
    except OSError:
        pass


def main() -> int:
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    app.setOrganizationName(config.ORG_NAME)
    app.setApplicationName("OrizonViewer")
    app.setApplicationDisplayName(config.APP_NAME)
    app.setStyle("Fusion")
    setup_logging()
    install_excepthooks()  # ora che c'e' la QApplication: abilita anche il dialogo
    # l'uscita avviene solo dopo il PIN (MainWindow chiama quit esplicitamente)
    app.setQuitOnLastWindowClosed(False)

    scale = config.compute_scale(app.primaryScreen())
    app.setProperty("ui_scale", scale)
    font = app.font()
    font.setFamilies(config.ui_fonts())
    font.setPixelSize(round(16 * scale))
    app.setFont(font)
    theme.apply_theme(app, Settings().theme())
    app.setWindowIcon(QIcon(config.resource_path(config.ICON_FILE)))

    # primo avvio (o account.json mancante/illeggibile): registrazione; altrimenti login
    login = LoginDialog(auth.get_store())
    login.show_fullscreen()
    if login.exec() != QDialog.Accepted:
        return 0

    window = MainWindow(scale)
    window.enter_fullscreen()  # unico punto in cui si entra in fullscreen
    window.start_session()     # solo dopo: ultimo file / wizard
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
