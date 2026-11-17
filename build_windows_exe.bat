@echo off
echo ============================================
echo Building Just One More Try Windows Executable (.exe)
echo ============================================

REM Check Python installation
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.10+ from https://www.python.org/
    pause
    exit /b 1
)

echo Installing dependencies...
python -m pip install --upgrade pip
python -m pip install -r src\requirements.txt
python -m pip install pyinstaller

echo.
echo Compiling executable with PyInstaller...
pyinstaller JustOneMoreTry.spec --clean --noconfirm

if %ERRORLEVEL% equ 0 (
    echo.
    echo ============================================
    echo SUCCESS! Standalone executable created at:
    echo dist\JustOneMoreTry.exe
    echo ============================================
) else (
    echo.
    echo [ERROR] Build failed. Please inspect logs above.
)

pause
