@echo off
REM This script automates the setup and execution of the bot for Windows.

REM Check if a virtual environment directory exists
IF NOT EXIST "venv\" (
    ECHO Sozdayu virtual'noe okruzhenie...
    python -m venv venv
    IF %ERRORLEVEL% NEQ 0 (
        ECHO Oshibka: Ne udalos' sozdat' virtual'noe okruzhenie. Ubedites', chto u vas ustanovlen python.
        PAUSE
        EXIT /B 1
    )
)

REM Activate the virtual environment
ECHO Aktiviruyu virtual'noe okruzhenie...
CALL "venv\Scripts\activate.bat"

REM Install/update dependencies
ECHO Ustanavlivayu/obnovlyayu zavisimosti iz requirements.txt...
pip install -r requirements.txt
IF %ERRORLEVEL% NEQ 0 (
    ECHO Oshibka: Ne udalos' ustanovit' zavisimosti.
    PAUSE
    EXIT /B 1
)

REM Run the bot
ECHO Zapuskayu bota... Nazhmite CTRL+C dlya ostanovki.
python main.py

REM The environment will be deactivated when the command prompt is closed.
PAUSE
