# 🇮🇹 Orizon Viewer 1.2.0 (PySide6)

Visualizzatore Excel in modalità kiosk (schermo intero) con ricerca dinamica, dettaglio articolo e codice a barre Code128.

## Funzioni
- Account locale per computer (registrazione al primo avvio, PIN personale, codice di recupero, blocco dopo 5 tentativi)
- Schermo intero, adattato a qualsiasi risoluzione; Esc, Alt+F4 e X non chiudono l'app
- «Esci» e «Importa Excel» richiedono il PIN
- Formati: .xlsx .xlsm .xls .xlsb .ods .csv .tsv .txt (file di testo: separatore e codifica rilevati automaticamente e modificabili)
- La procedura guidata «Configurazione file» fa scegliere foglio, colonne (e ordine) e dettagli del popup
- Configurazioni salvate per struttura del file (non serve riconfigurare lo stesso file); caricamento in background
- Popup articolo configurabile: Code128, Code39, EAN-13, EAN-8, UPC-A, ITF, QR Code, testo sopra e testo evidenziato
- Ultimo file riaperto all'avvio (opzione in Impostazioni)
- Ricerca istantanea: parole separate da `%` o spazio, in qualsiasi ordine (es. `banco%vite`), + filtri Codice / Descrizione / Layout
- Tabella veloce (oltre 26.000 righe), ordinamento, larghezze colonne salvate
- Dettaglio articolo (doppio clic o Invio) costruito dalla configurazione

## Installazione
```
python -m venv .venv
.venv\Scripts\activate        # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

## Avvio
```
python main.py
```
All'avvio viene aperto solo l'ultimo file importato (opzione in Impostazioni > Generale); altrimenti si usa «Importa file».

## Account e accesso
Al primo avvio compare «Configurazione iniziale»: si crea l'account locale (nome utente, password, PIN personale)
e si riceve un **codice di recupero** (formato XXXX-XXXX-XXXX, mostrato una sola volta). Il PIN protegge
Importa, Esci e Modifica configurazione. Dopo 5 tentativi errati (login, PIN o codice) l'accesso si blocca per 30 secondi.
I dati stanno in `account.json` (solo hash PBKDF2, nessun segreto in chiaro) nella cartella dati dell'app
(Windows: `%APPDATA%\Orizon-AIX\OrizonViewer`).

## Reimpostare l'account
Se password, PIN **e** codice di recupero sono andati persi, l'amministratore del computer può eseguire da Windows
`Ripristina_account.bat` (nella cartella del programma). Lo script:
1. chiede conferma (scrivere `SI`) e verifica che Orizon Viewer sia chiuso;
2. elimina **solo** `account.json` (utente, password, PIN, codice di recupero);
3. lascia intatti impostazioni, tema, configurazioni dei file e i file Excel/CSV.

Al prossimo avvio si crea un nuovo account.

## Test
```
pip install pytest
python -m pytest tests
```

## Creare l'exe (Windows)
```
pip install pyinstaller
pyinstaller --noconfirm OrizonViewer.spec
```
L'eseguibile è in `dist/OrizonViewer.exe`.

---

# 🇬🇧 English (short)

Orizon Viewer 1.2.0 is a kiosk-mode Excel viewer built with PySide6 (Qt6): login on start, fullscreen that cannot be exited without the PIN, fast multi-term search (`%`/space separated, any order), article detail dialog with Code128 barcode.

- Install: `pip install -r requirements.txt`
- Run: `python main.py`
- Tests: `python -m pytest tests`
- Build: `pyinstaller --noconfirm OrizonViewer.spec`
