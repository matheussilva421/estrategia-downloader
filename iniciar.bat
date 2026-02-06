@echo off
cd /d "%~dp0"
echo Iniciando Estrategia Downloader Pro...
python app.py
if %errorlevel% neq 0 (
    echo.
    echo Ocorreu um erro ao executar o programa.
    pause
)
