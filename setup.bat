echo off

rem ==========================================
rem This is a simple script to speed up the setup process on Windows.
rem It assumes you have Python and pip installed and added to your PATH.
rem It also assumes you have your .env already set up.
rem ==========================================

rem Check for Python 3.8.10
python --version | findstr /R "^Python 3\.8\.10" >nul
if errorlevel 1 (
    echo Python 3.8.10 is required. Please install it and ensure it's in your PATH.
    pause
    exit /b 1
)

rem Create virtual environment if it doesn't exist
if not exist ".venv" (
    python -m venv .venv
    if errorlevel 1 (
        echo Failed to create virtual environment.
        pause
        exit /b 1
    )
)

rem Activate virtual environment
if not exist ".venv\Scripts\activate.bat" (
    echo Virtual environment activation script not found.
    pause
    exit /b 1
)
call .venv\Scripts\activate.bat

rem Upgrade pip
python -m pip install --upgrade pip
if errorlevel 1 (
    echo Failed to upgrade pip.
    pause
    exit /b 1
)

rem Install dependencies
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo Failed to install dependencies.
    pause
    exit /b 1
)

rem Apply Django migrations
python manage.py migrate
if errorlevel 1 (
    echo Migration failed.
    pause
    exit /b 1
)

rem Collect static files
python manage.py collectstatic
if errorlevel 1 (
    echo Failed to collect static files.
    pause
    exit /b 1
)

echo ==========================================
echo Setup complete! You can now run the server with:
echo python manage.py runserver
echo ==========================================
pause

endlocal