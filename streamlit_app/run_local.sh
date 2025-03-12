#!/bin/bash

# Local setup script for Sales Call Simulator

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is required but not installed. Please install Python 3 and try again."
    exit 1
fi

# Check if virtual environment exists, create if not
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install requirements
echo "Installing dependencies..."
pip install -r requirements.txt

# Check if secrets file has been configured
if grep -q 'Your Anthropic API key' .streamlit/secrets.toml; then
    echo "WARNING: You need to configure your API keys in .streamlit/secrets.toml before running the app."
    echo "Please edit that file and fill in your API keys."
else
    echo "Secrets file appears to be configured."
fi

# Run Streamlit app
echo "Starting Streamlit app..."
streamlit run app.py

# Deactivate virtual environment when done
deactivate