@echo off
chcp 65001 >nul
setlocal
title Orizon Viewer - Ripristino account
echo ============================================================
echo   ORIZON VIEWER - RIPRISTINO ACCOUNT
echo ============================================================
echo.
echo Questo programma elimina SOLO l'account locale di Orizon Viewer:
echo   - nome utente, password, PIN e codice di recupero.
echo.
echo NON vengono eliminati: impostazioni, tema, configurazioni dei file
echo (profili) e i tuoi file Excel/CSV.
echo.
echo Al prossimo avvio Orizon Viewer chiedera' di creare un nuovo account.
echo.

rem Percorso usato davvero dall'app (vedi app/auth.py, DATA_SUBDIR)
set "ACCOUNT_FILE=%APPDATA%\Orizon-AIX\OrizonViewer\account.json"

tasklist /FI "IMAGENAME eq OrizonViewer.exe" 2>nul | find /I "OrizonViewer.exe" >nul
if not errorlevel 1 (
    echo ATTENZIONE: Orizon Viewer e' in esecuzione.
    echo Chiudilo e poi avvia di nuovo questo programma.
    echo.
    pause
    exit /b 1
)

if not exist "%ACCOUNT_FILE%" (
    echo Nessun account da ripristinare: il file non esiste.
    echo   %ACCOUNT_FILE%
    echo.
    pause
    exit /b 0
)

echo File che verra' eliminato:
echo   %ACCOUNT_FILE%
echo.
set "CONFERMA="
set /p "CONFERMA=Per continuare scrivi SI e premi Invio: "
if /I not "%CONFERMA%"=="SI" (
    echo.
    echo Operazione annullata. Nessuna modifica.
    pause
    exit /b 0
)

del /F /Q "%ACCOUNT_FILE%"
if exist "%ACCOUNT_FILE%" (
    echo.
    echo ERRORE: impossibile eliminare il file. Controlla i permessi e riprova.
    pause
    exit /b 1
)

echo.
echo Fatto. Account eliminato: al prossimo avvio potrai crearne uno nuovo.
echo.
pause
endlocal
