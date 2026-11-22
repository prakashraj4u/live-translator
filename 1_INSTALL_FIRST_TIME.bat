@echo off
cd /d "%~dp0"
echo === Live Translator: pehli baar setup (internet chahiye) ===

set PYV=
py -3.12 --version >nul 2>&1 && set PYV=-3.12
if "%PYV%"=="" py -3.11 --version >nul 2>&1 && set PYV=-3.11
if "%PYV%"=="" py -3.13 --version >nul 2>&1 && set PYV=-3.13
if "%PYV%"=="" set PYV=-3

echo Python version jo use hoga: %PYV%
if "%PYV%"=="-3" echo NOTE: Sirf naya Python mila. Agar install fail ho to python.org se Python 3.12 install karo aur ye file dobara chalao.

if exist venv rmdir /s /q venv
py %PYV% -m venv venv
if errorlevel 1 (
  echo Virtual environment nahi bana. Python 3.12 install karo: python.org/downloads
  pause
  exit /b 1
)

call venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
  echo.
  echo Install fail hua. Is screen ka screenshot bhej do. Agar Python 3.14 tha to Python 3.12 install karke dobara chalao.
  pause
  exit /b 1
)

python download_models.py
echo.
echo Setup ho gaya. Ab 2_RUN.bat double-click karo.
pause
