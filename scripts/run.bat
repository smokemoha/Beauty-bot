@echo off

:: Check for Poetry
where poetry >nul 2>&1
if %errorlevel% equ 0 (
    echo Poetry detected. Setting up environment with Poetry...
    poetry install
    poetry run python app/main.py
    goto end
) else (
    echo Poetry not found. Falling back to venv or virtualenv...
)

:: Check for virtualenv
where virtualenv >nul 2>&1
if %errorlevel% equ 0 (
    echo Using virtualenv to set up the environment...
    virtualenv venv
) else (
    echo Using venv (built-in) to set up the environment...
    python -m venv venv
)

:: Activate virtual environment
call venv\Scripts\activate

:: Install dependencies
if exist requirements.txt (
    pip install -r requirements.txt
) else (
    echo requirements.txt not found!
    goto deactivate
)

:: Run the application
python app/main.py

:: Deactivate the virtual environment
:deactivate
deactivate

:end
