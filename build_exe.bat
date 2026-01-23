@echo off
REM Build script for PLC Modbus Process Simulator

REM Go to script directory
cd /d "%~dp0"

echo.
echo Building PLC Modbus Process Simulator...
echo Current directory: %cd%
echo.

REM Update pip and install requirements
python -m pip install --upgrade pip setuptools wheel -q
if errorlevel 1 (
    echo ERROR: Could not install pip/setuptools/wheel
    echo Try: python -m pip install --upgrade pip setuptools wheel
    pause
    exit /b 1
)

pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Could not install requirements
    echo If snap7 fails:
    echo  - You need Python 3.12 or lower (snap7 doesn't support 3.13+^)
    echo  - Download Python 3.12 from python.org
    echo  - Create venv: python -m venv venv
    echo  - Activate: venv\Scripts\activate
    echo  - Reinstall: pip install -r requirements.txt
    pause
    exit /b 1
)

pip install pyinstaller -q

REM Clean old builds
if exist dist rmdir /s /q dist 2>nul
if exist build rmdir /s /q build 2>nul

REM Build executable
echo Building... this may take a few minutes
python -m PyInstaller --noconfirm --clean app.spec

REM Step 7: Verify build output
echo.
echo.
if exist dist\PLC_Modbus_Proces_Simulator.exe (
    echo SUCCESS! Executable created at: %cd%\dist\PLC_Modbus_Proces_Simulator.exe
) else (
    echo Build completed, check dist folder
)
echo.
pause
