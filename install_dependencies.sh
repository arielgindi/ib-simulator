#!/bin/bash
# Install dependencies for IB Simulator

echo "Installing IB Simulator dependencies..."

# Create virtual environment (optional but recommended)
# python -m venv venv
# source venv/bin/activate

# Install required packages
pip install duckdb
pip install pyyaml
pip install bcrypt
pip install colorlog
pip install numpy
pip install pandas
pip install scipy
pip install python-dateutil
pip install yfinance

echo "Dependencies installed successfully!"