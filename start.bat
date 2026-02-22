@echo off
title Voice Paste - Sesli Yapistirma
echo.
echo  Voice Paste baslatiliyor...
echo.

cd /d "%~dp0"

:: Python kontrolu
python --version >nul 2>&1
if errorlevel 1 (
    echo [HATA] Python bulunamadi! Lutfen Python yukleyin.
    pause
    exit /b 1
)

:: Bagimliliklari kontrol et ve kur
pip show SpeechRecognition >nul 2>&1
if errorlevel 1 (
    echo [*] Bagimliliklar kuruluyor...
    pip install -r requirements.txt
    echo.
)

:: Uygulamayi baslat (GUI)
start "" pythonw voice_paste_gui.py
