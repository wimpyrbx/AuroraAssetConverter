@echo off
REM Get the project name from the directory
for %%i in ("%cd%") do set "projectName=%%~nxi"
set "venvName=%projectName%_env"

REM Check if virtual environment is already active
echo %VIRTUAL_ENV% | findstr /i "%venvName%" >nul 2>&1
if %errorlevel% equ 0 (
    echo Virtual environment is already active.
    goto :run
)

REM Activate virtual environment
if exist "%venvName%\Scripts\activate.bat" (
    echo Attempting to activate virtual environment in %venvName%...
    call "%venvName%\Scripts\activate.bat"
    if %errorlevel% neq 0 (
        echo.
        echo Failed to activate virtual environment. Possible reasons:
        echo 1. Virtual environment is corrupted
        echo 2. Python installation is incomplete
        echo 3. System permissions issue
        echo.
        echo Try running install.bat again to recreate the environment.
        pause
        exit /b 1
    )
    goto :run
) else (
    echo Virtual environment not found in %venvName%.
    echo Please run install.bat first to create the environment.
    pause
    exit /b 1
)

:run
REM Run the converter
echo Running Aurora Asset Converter...
python -m aurora_converter.cli %*
if %errorlevel% neq 0 (
    echo.
    echo Converter failed with error code %errorlevel%
    pause
    exit /b %errorlevel%
) 