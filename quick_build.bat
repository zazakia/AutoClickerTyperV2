@echo off
REM Quick build script for Windows
REM This script builds the executable and creates the installer

echo ============================================================
echo AutoClickerTyper - Quick Build Script
echo ============================================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found in PATH
    echo Please install Python 3.10+ and try again
    pause
    exit /b 1
)

echo Step 1: Installing dependencies...
pip install -r requirements.txt
pip install -r requirements-dev.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo Step 2: Building executable...
python build.py
if errorlevel 1 (
    echo ERROR: Build failed
    pause
    exit /b 1
)

echo.
echo Step 3: Checking for Inno Setup...
where iscc >nul 2>&1
if errorlevel 1 (
    echo WARNING: Inno Setup not found in PATH
    echo Skipping installer creation
    echo.
    echo To create installer:
    echo   1. Install Inno Setup from https://jrsoftware.org/isinfo.php
    echo   2. Run: iscc installer.iss
    goto :done
)

echo.
echo Step 4: Creating installer...
iscc installer.iss
if errorlevel 1 (
    echo ERROR: Installer creation failed
    pause
    exit /b 1
)

:done
echo.
echo ============================================================
echo BUILD COMPLETE!
echo ============================================================
echo.
echo Executable: dist\ZapwebPromptAssist.exe
if exist installer_output (
    echo Installer:  installer_output\ZapwebPromptAssist_Setup_v*.exe
)
echo.
pause
