@echo off
title Voice Paste Studio - Electron
echo.
echo  Voice Paste Studio baslatiliyor...
echo.

cd /d "%~dp0"

set "PYTHON_EXE=python"
if exist "%~dp0.venv\Scripts\python.exe" (
    set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"
)

:: Python kontrolu (backend icin)
"%PYTHON_EXE%" --version >nul 2>&1
if errorlevel 1 (
    echo [HATA] Python bulunamadi! Lutfen Python yukleyin.
    pause
    exit /b 1
)

:: Backend bagimliliklari kontrol et ve kur
"%PYTHON_EXE%" -m pip show faster-whisper >nul 2>&1
if errorlevel 1 (
    echo [*] Python bagimliliklari kuruluyor...
    "%PYTHON_EXE%" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [HATA] Python bagimlilik kurulumu basarisiz.
        pause
        exit /b 1
    )
    echo.
)

:: Node/NPM kontrolu
node --version >nul 2>&1
if errorlevel 1 (
    echo [HATA] Node.js bulunamadi! Lutfen Node.js 20+ yukleyin.
    pause
    exit /b 1
)

npm --version >nul 2>&1
if errorlevel 1 (
    echo [HATA] npm bulunamadi!
    pause
    exit /b 1
)

cd /d "%~dp0desktop"
set ELECTRON_RUN_AS_NODE=

:: Frontend bagimliliklari
if not exist node_modules (
    echo [*] Node bagimliliklari kuruluyor...
    call npm install
    if errorlevel 1 (
        echo [HATA] npm install basarisiz.
        pause
        exit /b 1
    )
)

:: Electron + React gelistirme modu
call npm run dev
