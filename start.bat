@echo off
chcp 65001 >nul
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
    py -3 auto_mfg_gui.py
    goto :eof
)

where python >nul 2>nul
if %errorlevel%==0 (
    python auto_mfg_gui.py
    goto :eof
)

echo Python не найден.
echo Установите Python 3 с https://www.python.org/downloads/
echo При установке отметьте пункт "Add python.exe to PATH".
pause
