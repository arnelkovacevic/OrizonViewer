@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Orizon Viewer - Creazione exe
echo ============================================================
echo   ORIZON VIEWER - CREAZIONE DELL'EXE
echo ============================================================
echo.

rem --- cerca Python 3 (py launcher, poi python)
set "PY="
py -3 --version >nul 2>&1
if not errorlevel 1 set "PY=py -3"
if not defined PY (
    python --version >nul 2>&1
    if not errorlevel 1 set "PY=python"
)
if not defined PY goto :no_python
%PY% -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)" >nul 2>&1
if errorlevel 1 goto :old_python

rem --- ambiente virtuale e dipendenze
set "REQ_HASH="
for /f "skip=1 delims=" %%H in ('certutil -hashfile "requirements.txt" SHA256') do if not defined REQ_HASH set "REQ_HASH=%%H"
set "REQ_HASH=%REQ_HASH: =%"
set "OLD_HASH="
if exist "venv\req.sha" set /p OLD_HASH=<"venv\req.sha"
set "OLD_HASH=%OLD_HASH: =%"
set "NEED_INSTALL="
if not exist "venv\Scripts\python.exe" (
    set "NEED_INSTALL=1"
    echo Prima installazione in corso, attendere...
) else if not "%REQ_HASH%"=="%OLD_HASH%" (
    set "NEED_INSTALL=1"
    echo Aggiornamento delle dipendenze in corso, attendere...
)
if not defined NEED_INSTALL goto :venv_ready
if not exist "venv\Scripts\python.exe" (
    %PY% -m venv venv
    if errorlevel 1 goto :install_failed
)
"venv\Scripts\python.exe" -m pip install --upgrade pip
"venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :install_failed
(echo %REQ_HASH%)>"venv\req.sha"
:venv_ready

rem --- PyInstaller nello stesso ambiente
echo Installazione di PyInstaller...
"venv\Scripts\python.exe" -m pip install pyinstaller
if errorlevel 1 goto :install_failed

rem --- versione dall'app (APP_VERSION in app\config.py)
set "VER="
for /f "delims=" %%V in ('venv\Scripts\python.exe tools\print_version.py') do set "VER=%%V"
if not defined VER (
    echo ERRORE: impossibile leggere APP_VERSION da app\config.py.
    pause
    exit /b 1
)

echo Creazione di OrizonViewer.exe, attendere...
echo.
"venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean OrizonViewer.spec
if errorlevel 1 goto :build_failed
if not exist "dist\OrizonViewer.exe" goto :build_failed

rem --- cartella di distribuzione
set "REL=release\OrizonViewer_v%VER%"
if exist "%REL%" rmdir /s /q "%REL%"
mkdir "%REL%"
if errorlevel 1 goto :build_failed
copy /Y "dist\OrizonViewer.exe" "%REL%\" >nul
if errorlevel 1 goto :build_failed
copy /Y "Ripristina_account.bat" "%REL%\" >nul
if errorlevel 1 goto :build_failed
copy /Y "tools\LEGGIMI.txt" "%REL%\LEGGIMI.txt" >nul
if errorlevel 1 goto :build_failed

echo.
echo ============================================================
echo   FATTO. Cartella pronta per la distribuzione:
echo   %CD%\%REL%
echo ============================================================
echo.
pause
exit /b 0

:build_failed
echo.
echo ERRORE: creazione dell'exe non riuscita.
echo Leggi i messaggi qui sopra: di solito manca una libreria o un file.
echo Prova a eliminare le cartelle "build" e "dist" e a rilanciare.
echo.
pause
exit /b 1

:no_python
echo.
echo ERRORE: Python non e' installato su questo computer.
echo.
echo Scaricalo da https://www.python.org/downloads/ e durante l'installazione
echo spunta la casella "Add Python to PATH". Poi riavvia questo programma.
echo.
pause
exit /b 1

:old_python
echo.
echo ERRORE: serve Python 3.9 o superiore.
echo Scarica una versione recente da https://www.python.org/downloads/
echo e spunta "Add Python to PATH" durante l'installazione.
echo.
pause
exit /b 1

:install_failed
echo.
echo ERRORE: installazione non riuscita.
echo Controlla la connessione a Internet e riprova.
echo Se il problema continua, elimina la cartella "venv" e avvia di nuovo.
echo.
pause
exit /b 1
