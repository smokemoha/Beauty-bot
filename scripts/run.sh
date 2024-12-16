#!/bin/bash

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check for Poetry
if command_exists poetry; then
    echo "Poetry detected. Setting up environment with Poetry..."
    
    # Install dependencies with Poetry
    poetry install --no-root
    
    # Run the application
    poetry run python app/main.py
else
    echo "Poetry not found. Falling back to venv or virtualenv..."
    
    # Check if virtualenv or venv is available
    if command_exists virtualenv; then
        echo "Using virtualenv to set up the environment..."
        virtualenv venv
    elif command_exists python3; then
        echo "Using venv (built-in) to set up the environment..."
        python3 -m venv venv
    else
        echo "Python 3 or virtualenv is not installed. Please install Python 3 to continue."
        exit 1
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Install dependencies
    if [ -f requirements.txt ]; then
        pip install -r requirements.txt
    else
        echo "requirements.txt not found!"
        deactivate
        exit 1
    fi
    
    # Run the application
    python app/main.py
    
    # Deactivate the virtual environment
    deactivate
fi
