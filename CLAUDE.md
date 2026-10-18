# CLAUDE.md — kontekst projekta (Orizon Viewer)

## Projekat
- **Orizon Viewer**, Orizon-AIX (developer: Arnel Kovacevic). Kiosk/touch desktop aplikacija za pregled skladišta rezervnih dijelova iz Excela/CSV-a, s pretragom i barkodom.
- **Aktivna aplikacija: `PYSIDE6-viewer/`** (PySide6 / Qt6, Python). Trenutna verzija **1.2.0**.
- Fajlovi u rootu (`Orizon_Viewer.py`, `Orizon_Viewer.spec`, `dist/`, `Orizon-com.jpg`, `Orizon_Viewer` binarni) su **STARA Tkinter verzija 2.1.1**. Ne diraj ih bez izričitog zahtjeva.
- Razvoj na macOS-u, cilj je Windows (exe preko PyInstallera).

## Arhitektura (PYSIDE6-viewer/)
**Korijen**
- `main.py` — pokretanje; excepthook (sys + threading) i log u `orizon.log` instaliraju se prije importa Qt-a; login pa `MainWindow.enter_fullscreen()` i `start_session()`.
- `requirements.txt` — samo minimalne verzije. `OrizonViewer.spec` — PyInstaller (onefile, console=False, ikona).
- `Avvia_OrizonViewer.bat` — pravi `venv`, instalira zavisnosti (hash `requirements.txt` u `venv\req.sha`), pokreće app preko `pythonw`.
- `build_exe.bat` — venv + PyInstaller, pa `release\OrizonViewer_v<verzija>\` (exe, `Ripristina_account.bat`, `LEGGIMI.txt`).
- `Ripristina_account.bat` — briše samo `account.json` (traži "SI", provjerava da app nije pokrenut).

**`app/` (jezgro i logika)**
- `config.py` — konstante, `APP_VERSION`, putanje resursa, `compute_scale`, fontovi.
- `auth.py` — lokalni račun: PBKDF2 hashevi, PIN, kod za oporavak, brojač pokušaja i blokada (30 s), `data_dir()`.
- `readers.py` — jedinstveni sloj čitanja svih formata (xlsx/xlsm/xls/xlsb/ods/csv/tsv/txt), auto kodiranje i separator; `xlsx_reader.py` — openpyxl engine i `to_text`.
- `file_profiles.py` — profili po fajlu (potpis = format + sheet + nazivi kolona); `details.py` — postavke popupa i validacija barkodova (bez Qt-a).
- `search.py` — brza pretraga (normalizacija, multi-word, `%`), bez Qt-a.
- `settings.py` — QSettings (tema, zadnji fajl, "Ricorda ultimo file").
- `theme.py` — tokeni boja (dark/light), generiše QSS iz `styles.qss`; `styles.qss` je jedini stylesheet.
- `barcode_utils.py` — generisanje barkoda kao QPixmap.

**`app/` (interfejs)**
- `main_window.py` — glavni prozor: header (sat, pretraga, ikone, logo), tabela, prazno stanje, tok importa i profila.
- `table_model.py` — QAbstractTableModel, delegate s isticanjem, `ExcelLoader` (QThread).
- `login_dialog.py` — jedan fullscreen prozor: registracija, login, oporavak. `auth_widgets.py` — polja za lozinku, kod za oporavak, forme iz Sicurezza.
- `modal_overlay.py` — `BaseModal` (zajednička modal klasa, zatamnjenje + blur, `finalize()`), `pin_dialog.py`, `confirm_dialog.py`, `error_dialog.py`, `detail_dialog.py` (popup s barkodom).
- `settings_dialog.py` + `settings_tabs/` — Generale, File, Sicurezza, Info. `toggle_switch.py`, `toast.py`.
- `wizard/` — čarobnjak "Configurazione file": `wizard_dialog.py`, `step_sheet.py` (i opcije teksta), `step_columns.py`, `step_details.py`, `common.py`.

**Ostalo**
- `tools/` — `make_icon.py` (pravi `assets/orizon.ico`), `print_version.py`, `LEGGIMI.txt` (ide u release).
- `tests/` — pytest: logika (`test_search`, `test_readers`, `test_auth`, `test_details_profiles`), GUI offscreen (`test_wizard`, `test_auth_ui`, `test_kiosk`, `test_crash`) i statička provjera `.bat` fajlova (`test_windows_scripts`). Pomoćnici: `gui_helpers.py` (`run_modal`, `pump`), `fixture_builder.py`.

## Historija verzija i šta je urađeno
- **v1.0.1**: prelazak s Tkintera na PySide6; QTableView + QAbstractTableModel; brza pretraga s debounceom, multi-word i `%` (npr. "BANCO%VITE" nalazi "VITE TCE 16x50 BANCO OSCILLANTE"); kiosk fullscreen (Esc/Alt+F4/X blokirani, izlaz samo uz PIN); header sa satom (HH:mm:ss, dd/MM/yyyy), search, ikone Impostazioni/Importa/Esci, logo; modali sa zatamnjenjem i blurom; tema Scura/Chiara (`theme.py` tokeni); toggle "Ricorda ultimo file aperto"; prazno stanje; popup s barkodom fiksne veličine (bez resizeEvent petlji).
- **v1.1.0**: čarobnjak "Configurazione file" (Foglio → Colonne → Dettagli) s pregledom uživo; profili po fajlu (`file_profiles.py`, potpis sheet+kolone); tipovi barkoda (Code128, Code39, EAN-13, EAN-8, UPC-A, ITF, QR) s auto-prijedlogom i provjerom; kartica File u Impostazioni; fix fullscreena: `MainWindow.enter_fullscreen()` prvo postavi veličinu ekrana (`setGeometry`), pa `showFullScreen()`; `changeEvent` vraća fullscreen ako se izgubi.
- **Formati**: `readers.py` — xlsx, xlsm, xls, xlsb, ods, csv, tsv, txt (auto separator i kodiranje, cp1252 za talijanske CSV-ove).
- **v1.2.0**: lokalni account (`auth.py`, `account.json` u `%APPDATA%\Orizon-AIX\OrizonViewer`, PBKDF2 hashevi); Configurazione iniziale; lični PIN umjesto fiksnog; kod za oporavak; blokada 5 pokušaja / 30 s; kartica Sicurezza; `Ripristina_account.bat`; excepthook + `error_dialog`; ikona; `Avvia_OrizonViewer.bat` i `build_exe.bat` (`release\OrizonViewer_v<verzija>\`).

## Pravila rada (OBAVEZNO)
- Sav UI tekst je na **ITALIJANSKOM**.
- Uvijek kompletni fajlovi, bez izostavljenih linija.
- **NE mijenjaj stil ni izgled** ako nije izričito traženo. Male, inkrementalne izmjene, bez redizajna.
- Bez `QMessageBox` i sistemskih popupa: koristi postojeći `Toast` i vlastite dijaloge preko zajedničke modal klase (`BaseModal`).
- Modali: fiksna veličina (`finalize()` poziva `setFixedSize` jednom), bez resizeEvent/adjustSize petlji.
- Skaliranje kroz postojeći faktor (`config.compute_scale`). Testirati na 1024x600 i 1920x1080, obje teme.
- Verzija samo u `app/config.py` (`APP_VERSION`). Test provjerava da se slaže s README-ima i LEGGIMI.
- Tajne nikad u čistom tekstu, nikad hardkodirane lozinke.
- `*.xlsx` i podaci korisnika se **NIKAD** ne commitaju.

## Zamke koje smo već naučili
- macOS: `showFullScreen()` bez prethodne veličine vraća prozor na sizeHint (1120x549). Fullscreen samo kroz `enter_fullscreen()`.
- Globalni QSS `QWidget { font-size }` pobjeđuje `setFont`: za fiksne fontove koristi inline `setStyleSheet("font-size: Npx")`.
- QLabel s wordWrap podcjenjuje visinu u layoutu: visinu računaj ručno (`fontMetrics().boundingRect`) i fiksiraj.
- QSS ne podržava `letter-spacing`.
- PyInstaller ne radi s Pythonom 3.10.0 (bug u `dis`): koristi 3.10.1+ (preporuka 3.11+).
- Pandas ODS čitač pretvara tekst `#N/A` u prazno.
- `git push` se ponekad zaglavi bez ispisa: prekini proces i ponovi.
- Testovi koriste `QT_QPA_PLATFORM=offscreen`; poruke `propagateSizeHints`/`raise()` dolaze od tog plugina, na pravoj platformi ih nema.

## Git workflow
- Prije veće izmjene: backup grana (`backup/…`). Rad na feature granama. Merge u `main` tek kad Arnel potvrdi. Tag za svaku verziju (`vX.Y.Z`).
- Postojeće grane: `main`, `feature/configurazione-file`, `backup/pyside6-v1.0.1`; lokalno i `backup/main-con-merge-v1.2.0`. Tag `v1.2.0` (pokazuje na raniji merge commit `d7bd1a9`, isti kod kao `d93ea1f`).

## Pokretanje i build (Windows)
- Python 3.11+ (min 3.10.1) s "Add Python to PATH". Dupli klik na `Avvia_OrizonViewer.bat`. Exe pravi `build_exe.bat`, a za distribuciju se nosi folder `release\OrizonViewer_v1.2.0\`.
- Testovi: `cd PYSIDE6-viewer`, `pip install pytest xlwt`, `python -m pytest tests`.

## Otvoreno / sljedeći koraci
- Ručni test na pravom Windowsu (čisti `venv`, bez Pythona, promjena `requirements.txt`, exe, SmartScreen, `Ripristina_account.bat`, dijalog greške).
- Ukloniti `mm16.xlsx` i `dist/mm16.xlsx` iz javnog repoa (`git rm --cached` + `.gitignore`) i odlučiti šta sa starim Tkinter fajlovima u rootu.
- Kartica "Generale" je spremna za nove opcije.
- Možda kasnije: Inno Setup instaler s autostartom za kiosk.
