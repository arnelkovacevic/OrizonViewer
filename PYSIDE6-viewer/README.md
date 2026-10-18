# 🇮🇹 Orizon Viewer 1.2.0 (PySide6)

Visualizzatore di tabelle in modalità kiosk (schermo intero) con ricerca dinamica, dettaglio articolo e codice a barre.

## Funzioni
- Account locale per computer: registrazione al primo avvio, PIN personale, codice di recupero, blocco dopo 5 tentativi errati
- Schermo intero adattato a qualsiasi risoluzione; Esc, Alt+F4 e X non chiudono l'app (serve il PIN)
- Formati: .xlsx .xlsm .xls .xlsb .ods .csv .tsv .txt (file di testo: separatore e codifica rilevati automaticamente e modificabili)
- La procedura guidata «Configurazione file» fa scegliere foglio, colonne (e ordine) e dettagli del popup
- Configurazioni salvate per struttura del file (non serve riconfigurare lo stesso file); caricamento in background
- Popup articolo configurabile: Code128, Code39, EAN-13, EAN-8, UPC-A, ITF, QR Code, testo sopra e testo evidenziato
- Ricerca istantanea: parole separate da `%` o spazio, in qualsiasi ordine (es. `banco%vite`)
- Tema scuro / chiaro, ultimo file riaperto all'avvio (opzione in Impostazioni)

## Avvio rapido (doppio clic su Avvia_OrizonViewer.bat)
1. Installa Python 3.9 o superiore da <https://www.python.org/downloads/> e **spunta «Add Python to PATH»**.
2. Fai doppio clic su **`Avvia_OrizonViewer.bat`** (nella cartella `PYSIDE6-viewer`).
   - Al primo avvio crea l'ambiente `venv` e installa le dipendenze («Prima installazione in corso, attendere...»): serve Internet, ci vuole qualche minuto.
   - Se `requirements.txt` cambia, le dipendenze si aggiornano da sole al prossimo avvio.
   - Poi l'app si apre senza finestra nera.

Da terminale (qualsiasi sistema): `python -m venv .venv`, attivare l'ambiente, `pip install -r requirements.txt`, `python main.py`.

## Creare l'exe (build_exe.bat)
Fai doppio clic su **`build_exe.bat`**: usa lo stesso `venv`, installa PyInstaller e crea `dist\OrizonViewer.exe`
(un solo file, senza console, con l'icona `assets\orizon.ico`). Al termine prepara la cartella di distribuzione e ne mostra il percorso.
L'exe va creato su Windows: PyInstaller non fa build incrociate.

## Distribuzione (cartella release)
`build_exe.bat` crea `release\OrizonViewer_v<versione>\` con:
- `OrizonViewer.exe`
- `Ripristina_account.bat`
- `LEGGIMI.txt` (come avviare, primo avvio, SmartScreen, dove sono i dati, reset dell'account)

Copia l'intera cartella sul computer di destinazione: non serve installare né Python né altro.
Al primo avvio Windows può mostrare l'avviso SmartScreen (l'exe non è firmato): **«Ulteriori informazioni» → «Esegui comunque»**.
`Ripristina_account.bat` deve restare nella stessa cartella dell'exe.

## Requisiti
- Windows 10/11 (l'exe) oppure Windows/macOS/Linux per l'esecuzione da sorgente
- Python 3.9+ (provato con 3.10) solo per `Avvia_OrizonViewer.bat` e per creare l'exe
- Librerie: vedi `requirements.txt` (versioni minime: PySide6, pandas, openpyxl, xlrd, pyxlsb, odfpy, python-barcode, qrcode, pillow)

## Dove vengono salvati i dati
Windows: `%APPDATA%\Orizon-AIX\OrizonViewer` (macOS: `~/Library/Application Support/Orizon-AIX/OrizonViewer`)

| File | Contenuto |
|---|---|
| `account.json` | account locale: solo hash PBKDF2, nessuna password o PIN in chiaro |
| `profiles.json` | configurazioni dei file (fogli, colonne, popup) |
| `orizon.log` | registro eventi ed errori imprevisti (da inviare all'assistenza) |

Le impostazioni (tema, ultimo file) sono nel registro di Windows (`HKCU\Software\Orizon-AIX`). I file Excel/CSV non vengono mai modificati.

## Reimpostare l'account
Se password, PIN **e** codice di recupero sono andati persi, l'amministratore del computer può eseguire da Windows
`Ripristina_account.bat` (nella cartella del programma). Lo script:
1. chiede conferma (scrivere `SI`) e verifica che Orizon Viewer sia chiuso;
2. elimina **solo** `account.json` (utente, password, PIN, codice di recupero);
3. lascia intatti impostazioni, tema, configurazioni dei file e i file Excel/CSV.

Al prossimo avvio si crea un nuovo account. Con il codice di recupero basta invece «Password dimenticata?» nella schermata di accesso.

## Problemi comuni
| Problema | Soluzione |
|---|---|
| «Python non è installato» | Installa Python da python.org e spunta **Add Python to PATH**, poi riavvia `Avvia_OrizonViewer.bat` |
| «Installazione non riuscita» | Controlla Internet; se persiste elimina la cartella `venv` e riavvia |
| Windows SmartScreen blocca l'exe | «Ulteriori informazioni» → «Esegui comunque» |
| «File aperto in un altro programma» | Chiudi il file in Excel e riprova |
| «File danneggiato o non supportato» | Il file non corrisponde alla sua estensione o è rovinato: riapri e risalva da Excel |
| «Si è verificato un errore imprevisto» | Invia il file `orizon.log` (percorso indicato nel messaggio) all'assistenza |
| Password, PIN e codice persi | Vedi «Reimpostare l'account» |
| Accesso bloccato 30 secondi | Dopo 5 tentativi errati: attendere il termine del conto alla rovescia |

## Test
```
pip install pytest xlwt
python -m pytest tests
```

## Licenza / contatti
Orizon-AIX — orizon-aix.com — info@orizon-aix.com

---

# 🇬🇧 English (short)

Orizon Viewer 1.2.0 is a kiosk-mode table viewer built with PySide6 (Qt6): local admin account with recovery code, fullscreen that cannot be exited without the PIN, fast multi-term search, article detail dialog with barcode, files: xlsx/xlsm/xls/xlsb/ods/csv/tsv/txt.

- Quick start (Windows): install Python 3.9+ (tick *Add Python to PATH*), double-click `Avvia_OrizonViewer.bat`
- Build the exe: double-click `build_exe.bat` → `release\OrizonViewer_v<version>\`
- Run from source: `pip install -r requirements.txt` then `python main.py`
- Tests: `python -m pytest tests`
- Data folder: `%APPDATA%\Orizon-AIX\OrizonViewer` (`account.json`, `profiles.json`, `orizon.log`)
