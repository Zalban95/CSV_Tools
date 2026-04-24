@echo off
REM Build a single-file Windows executable of CSV_Tools.
REM
REM Requirements (developer machine only):
REM   * Python 3.10+ on PATH
REM   * pip install pyinstaller
REM
REM The resulting .exe lands in dist\CSV_Tools.exe and has no runtime
REM dependencies -- users just double-click it. The exe looks for input\ and
REM output\ folders next to itself (they will be created on first run).

setlocal
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo [build] ERROR: Python is not on PATH. Install Python 3.10+ first.
    exit /b 1
)

python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo [build] Installing PyInstaller into the current Python environment...
    python -m pip install --disable-pip-version-check --quiet pyinstaller || goto :err
)

echo [build] Cleaning previous build output...
if exist build  rmdir /s /q build
if exist dist   rmdir /s /q dist

echo [build] Running PyInstaller...
python -m PyInstaller CSV_Tools.spec --noconfirm || goto :err

echo.
echo [build] Done.  Executable: dist\CSV_Tools.exe
echo [build] Copy it anywhere; it will create input\ and output\ on first run.
exit /b 0

:err
echo [build] BUILD FAILED.
exit /b 1
