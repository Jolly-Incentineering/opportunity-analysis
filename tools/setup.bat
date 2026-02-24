@echo off
setlocal
echo.
echo  Jolly Claude Setup
echo  ==================
echo.

REM Check Python is installed and on PATH
python --version >nul 2>&1
if errorlevel 1 (
    echo  Python was not found on your system.
    echo.
    echo  Please do the following:
    echo    1. Go to https://www.python.org/downloads/
    echo    2. Click "Download Python"
    echo    3. Run the installer
    echo    4. IMPORTANT: on the first screen, check "Add Python to PATH"
    echo    5. Click "Install Now" and wait for it to finish
    echo    6. Run this setup file again
    echo.
    echo  Opening the Python download page now...
    start "" "https://www.python.org/downloads/"
    pause
    exit /b 1
)

echo  Python found:
python --version
echo.

REM Upgrade pip silently
echo  Upgrading pip...
python -m pip install --upgrade pip --quiet

REM Install required packages
echo  Installing required packages (this may take 1-3 minutes)...
echo.
python -m pip install openpyxl python-pptx playwright requests edgartools pypdf

if errorlevel 1 (
    echo.
    echo  ERROR: Package installation failed. Check the output above for details.
    echo  If you see a permissions error, try right-clicking this file and
    echo  selecting "Run as administrator".
    pause
    exit /b 1
)

REM Install Playwright browser
echo.
echo  Installing Playwright browser (used for PDF generation)...
playwright install chromium

echo.
echo  ==================
echo  Setup complete!
echo.
echo  Next steps in Claude Code:
echo    /deck-setup   ^<-- run once to configure your workspace
echo    /deck-auto [Company Name]   ^<-- start an Opportunity Analysis
echo.
pause
endlocal
