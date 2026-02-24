@echo off
title Voice Paste Studio - Electron
echo.
echo  Voice Paste Studio baslatiliyor...
echo.

cd /d "%~dp0"

:: Python kontrolu (backend icin)
python --version >nul 2>&1
if errorlevel 1 (
    echo [HATA] Python bulunamadi! Lutfen Python yukleyin.
    pause
    exit /b 1
)

:: Backend bagimliliklari kontrol et ve kur
pip show faster-whisper >nul 2>&1
if errorlevel 1 (
    echo [*] Python bagimliliklari kuruluyor...
    pip install -r requirements.txt
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
set ELECTRON_RUN_AS_NODE=0

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
