@echo off
REM Build a single-file Windows executable of CSV_Tools.
REM
REM Requirements (developer machine only):
REM   * Python 3.10+ on PATH
REM   * PyInstaller is installed automatically into .venv\
REM   * optional: Inno Setup 6 (for dist\CSV_Tools_Setup.exe)
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

rem Build inside a private venv so the system Python stays untouched.
if not exist .venv\Scripts\python.exe (
    echo [build] Creating .venv ...
    python -m venv .venv || goto :err
)
set "PY=.venv\Scripts\python.exe"
"%PY%" -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo [build] Installing PyInstaller into .venv ...
    "%PY%" -m pip install --disable-pip-version-check --quiet pyinstaller || goto :err
)

echo [build] Cleaning previous build output...
if exist build  rmdir /s /q build
if exist dist   rmdir /s /q dist

echo [build] Running PyInstaller...
"%PY%" -m PyInstaller CSV_Tools.spec --noconfirm || goto :err

rem Optional installer: built only if Inno Setup's ISCC.exe is available.
set "ISCC="
for %%I in (ISCC.exe) do if not "%%~$PATH:I"=="" set "ISCC=%%~$PATH:I"
if not defined ISCC if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if defined ISCC (
    echo [build] Building installer with Inno Setup...
    "%ISCC%" /Q installer.iss || goto :err
    echo [build] Installer: dist\CSV_Tools_Setup.exe
) else (
    echo [build] Inno Setup not found - skipping installer ^(winget install JRSoftware.InnoSetup^).
)

echo.
echo [build] Done.  Executable: dist\CSV_Tools.exe
echo [build] Copy it anywhere; it will create input\ and output\ on first run.
exit /b 0

:err
echo [build] BUILD FAILED.
exit /b 1
