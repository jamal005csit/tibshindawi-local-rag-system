#!/bin/bash

# Zero Cost Local RAG PDF System - Quick Start Script
# This script starts the backend server

set -e

echo "============================================================"
echo "Zero Cost Local RAG PDF System"
echo "============================================================"
echo ""

# Check if we're in the right directory
if [ ! -f "backend/main.py" ]; then
    echo "ERROR: Please run this script from the project root directory"
    echo "Usage: ./start.sh"
    exit 1
fi

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed"
    echo "Please install Python 3.8 or higher"
    exit 1
fi

echo "✓ Python found: $(python3 --version)"

# Check if dependencies are installed
echo ""
echo "Checking dependencies..."
if ! python3 -c "import fastapi" 2>/dev/null; then
    echo ""
    echo "Dependencies not installed. Installing now..."
    echo ""
    cd backend
    pip3 install -r requirements.txt --break-system-packages
    cd ..
    echo ""
    echo "✓ Dependencies installed"
else
    echo "✓ Dependencies already installed"
fi

# Check for PDFs
pdf_count=$(find data/pdfs -name "*.pdf" 2>/dev/null | wc -l)
echo ""
echo "PDFs found: $pdf_count"
if [ "$pdf_count" -eq 0 ]; then
    echo "WARNING: No PDFs found in data/pdfs/"
    echo "Add PDFs to the data/pdfs/ directory before querying"
fi

echo ""
echo "============================================================"
echo "Starting Backend Server..."
echo "============================================================"
echo ""
echo "The server will be available at: http://localhost:8000"
echo "Open frontend/index.html in your browser to use the chat interface"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start the server
cd backend
python3 main.py
