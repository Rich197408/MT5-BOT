@echo off

REM 1. Change to this script's directory
pushd "%~dp0"

REM 2. Activate the virtual environment
if exist "venv\Scripts\activate.bat" (
    call "venv\Scripts\activate.bat"
) else (
    echo ❌ Virtual environment not found at venv\Scripts\activate.bat
    popd
    exit /b 1
)

REM 3. Run the bot once and then exit
python live_bot.py --once

REM 4. Deactivate the virtual environment (if available)
if defined VIRTUAL_ENV (
    call deactivate
)

REM 5. Return to the original directory
popd

exit /b 0




