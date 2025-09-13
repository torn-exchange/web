#!/usr/bin/env bash

# ==========================================
# This is a simple script to speed up the setup process on Linux.
# It assumes you have Python and pip installed and added to your PATH.
# It also assumes you have your .env already set up.
# ==========================================

# WARNING: THIS SCRIPT IS UNTESTED AND MAY NEED MODIFICATIONS TO WORK IN YOUR ENVIRONMENT OR YOUR SPESIFIC DISTRO.

set -e  # Exit immediately if a command fails
set -u  # Treat unset variables as an error

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1)
if [[ ! $PYTHON_VERSION =~ ^Python\ 3\.8\.10 ]]; then
    echo "Python 3.8.10 is required. Detected: $PYTHON_VERSION"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    if [ $? -ne 0 ]; then
        echo "Failed to create virtual environment."
        exit 1
    fi
fi

# Activate virtual environment
source .venv/bin/activate
if [ $? -ne 0 ]; then
    echo "Failed to activate virtual environment."
    exit 1
fi

# Upgrade pip
python3 -m pip install --upgrade pip
if [ $? -ne 0 ]; then
    echo "Failed to upgrade pip."
    exit 1
fi

# Install dependencies
python3 -m pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "Failed to install dependencies."
    exit 1
fi

# Apply Django migrations
python3 manage.py migrate
if [ $? -ne 0 ]; then
    echo "Migration failed."
    exit 1
fi

# Collect static files
python3 manage.py collectstatiC
if [ $? -ne 0 ]; then
    echo "Failed to collect static files."
    exit 1
fi

echo "=========================================="
echo "Setup complete! You can now run the server with:"
echo "python3 manage.py runserver"
echo "=========================================="