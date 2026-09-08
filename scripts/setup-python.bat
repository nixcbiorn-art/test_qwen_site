@echo off
REM Installs Python dependencies and Playwright browsers.
REM Run this by double-clicking it, or from cmd.

cd /d "%~dp0.."

echo === pip install -r requirements.txt ===
pip install -r requirements.txt
if errorlevel 1 (
    echo pip install failed. Check that Python and pip are on PATH.
    pause
    exit /b 1
)

echo.
echo === playwright install ===
playwright install
if errorlevel 1 (
    echo Playwright browser install failed.
    pause
    exit /b 1
)

echo.
echo Done. You can now run: python main.py
pause
