# Orizon Viewer — versione 1.2.0

🇮🇹 **Italiano**

Orizon Viewer è un visualizzatore di tabelle in modalità kiosk (schermo intero), con ricerca istantanea, dettaglio articolo e codice a barre. La versione attuale è **1.2.0** (PySide6 / Qt6) e si trova nella cartella [`PYSIDE6-viewer/`](PYSIDE6-viewer/).

🔹 Novità della 1.2.0
- Account locale per computer: registrazione al primo avvio, PIN personale, codice di recupero, blocco dopo 5 tentativi errati
- Formati supportati: .xlsx .xlsm .xls .xlsb .ods .csv .tsv .txt
- Procedura guidata «Configurazione file» (foglio, colonne, popup) con configurazioni salvate
- Popup articolo con Code128, Code39, EAN-13, EAN-8, UPC-A, ITF, QR Code
- Tema scuro / chiaro, avvio con doppio clic (`Avvia_OrizonViewer.bat`) e creazione dell'exe (`build_exe.bat`)

🚀 Avvio rapido (Windows)
1. Installa Python 3.9+ da python.org e spunta «Add Python to PATH»
2. Doppio clic su `PYSIDE6-viewer\Avvia_OrizonViewer.bat`

Da terminale: `cd PYSIDE6-viewer`, `pip install -r requirements.txt`, `python main.py`.
Documentazione completa: [PYSIDE6-viewer/README.md](PYSIDE6-viewer/README.md).

ℹ️ I file `Orizon_Viewer.py` e `Orizon_Viewer.spec` in questa cartella sono la vecchia versione (CustomTkinter) e non vengono più sviluppati.

---

🇬🇧 **English**

Orizon Viewer is a kiosk-mode table viewer with instant search, article detail dialog and barcode generation. The current version is **1.2.0** (PySide6 / Qt6), located in [`PYSIDE6-viewer/`](PYSIDE6-viewer/).

🔹 What's new in 1.2.0
- Local per-computer account: first-run registration, personal PIN, recovery code, lockout after 5 failed attempts
- Supported formats: .xlsx .xlsm .xls .xlsb .ods .csv .tsv .txt
- "Configurazione file" wizard (sheet, columns, popup) with saved profiles
- Detail popup with Code128, Code39, EAN-13, EAN-8, UPC-A, ITF, QR Code
- Dark / light theme, double-click launcher (`Avvia_OrizonViewer.bat`) and exe builder (`build_exe.bat`)

🚀 Quick start (Windows)
1. Install Python 3.9+ from python.org and tick "Add Python to PATH"
2. Double-click `PYSIDE6-viewer\Avvia_OrizonViewer.bat`

From a terminal: `cd PYSIDE6-viewer`, `pip install -r requirements.txt`, `python main.py`.
Full documentation: [PYSIDE6-viewer/README.md](PYSIDE6-viewer/README.md).

ℹ️ `Orizon_Viewer.py` and `Orizon_Viewer.spec` in this folder are the legacy version (CustomTkinter) and are no longer developed.
