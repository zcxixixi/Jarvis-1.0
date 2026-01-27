#!/bin/bash

# Jarvis Raspberry Pi Starter Script
echo "🥧 Starting Jarvis on Raspberry Pi..."

# Check if .env exists, if not use .env.pi
if [ ! -f .env ]; then
    echo "⚠️ .env not found, copying from .env.pi..."
    cp .env.pi .env
fi

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run Jarvis
python3 hybrid_jarvis.py
