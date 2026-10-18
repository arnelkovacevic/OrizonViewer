@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Orizon Viewer

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

if not exist "venv\Scripts\pythonw.exe" goto :install_failed
rem --- avvia l'app senza console
start "" "venv\Scripts\pythonw.exe" main.py
exit /b 0

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
