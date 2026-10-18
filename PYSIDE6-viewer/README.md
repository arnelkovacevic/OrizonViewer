# 🇮🇹 Orizon Viewer 1.0.1 (PySide6)

Visualizzatore Excel in modalità kiosk (schermo intero) con ricerca dinamica, dettaglio articolo e codice a barre Code128.

## Funzioni
- Accesso all'avvio (utente/password salvati solo come hash SHA-256)
- Schermo intero, adattato a qualsiasi risoluzione; Esc, Alt+F4 e X non chiudono l'app
- «Esci» e «Importa Excel» richiedono il PIN
- Caricamento Excel in background (foglio «Foglio1», altrimenti il primo); ultimo file riaperto all'avvio
- Ricerca istantanea: parole separate da `%` o spazio, in qualsiasi ordine (es. `banco%vite`), + filtri Codice / Descrizione / Layout
- Tabella veloce (oltre 26.000 righe), ordinamento, larghezze colonne salvate
- Dettaglio articolo (doppio clic o Invio) con LAYOUT e codice a barre

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

Orizon Viewer 1.0.1 is a kiosk-mode Excel viewer built with PySide6 (Qt6): login on start, fullscreen that cannot be exited without the PIN, fast multi-term search (`%`/space separated, any order), article detail dialog with Code128 barcode.

- Install: `pip install -r requirements.txt`
- Run: `python main.py`
- Tests: `python -m pytest tests`
- Build: `pyinstaller --noconfirm OrizonViewer.spec`
