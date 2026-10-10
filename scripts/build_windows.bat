@echo off
setlocal

set "ROOT_DIR=%~dp0.."
pushd "%ROOT_DIR%" || exit /b 1

set "PYTHON_EXE=%ROOT_DIR%\.venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=python"

set "SKIP_INSTALLER="
if /I "%~1"=="--skip-installer" set "SKIP_INSTALLER=1"
if /I "%~1"=="-SkipInstaller" set "SKIP_INSTALLER=1"
if /I "%~1"=="/skip-installer" set "SKIP_INSTALLER=1"

"%PYTHON_EXE%" -m pip install -r requirements-release.txt
if errorlevel 1 goto :error

"%PYTHON_EXE%" -m pip install --no-build-isolation -e ".[packaging]"
if errorlevel 1 goto :error

"%PYTHON_EXE%" scripts\prepare_licenses.py --fetch-sources
if errorlevel 1 goto :error

"%PYTHON_EXE%" -m PyInstaller --noconfirm --clean packaging\pyinstaller\APIRestDesk.spec
if errorlevel 1 goto :error

if defined SKIP_INSTALLER (
    "%PYTHON_EXE%" scripts\prepare_release_sources.py
    if errorlevel 1 goto :error
    echo PyInstaller build completed: dist\APIRestDesk\APIRestDesk.exe
    popd
    exit /b 0
)

set "ISCC_EXE="
where iscc.exe >nul 2>nul
if not errorlevel 1 (
    for /f "delims=" %%I in ('where iscc.exe') do (
        if not defined ISCC_EXE set "ISCC_EXE=%%I"
    )
)

if not defined ISCC_EXE (
    if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC_EXE=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
)

if not defined ISCC_EXE (
    echo Inno Setup 6 was not found. Install it or rerun with --skip-installer to produce only the PyInstaller app.
    popd
    exit /b 1
)

"%ISCC_EXE%" packaging\windows\APIRestDesk.iss
if errorlevel 1 goto :error

"%PYTHON_EXE%" scripts\prepare_release_sources.py --include-installer
if errorlevel 1 goto :error

echo Installer, license documents and matching sources completed: dist\release
popd
exit /b 0

:error
echo Build failed.
popd
exit /b 1
