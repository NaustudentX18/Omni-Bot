#!/bin/bash
# Jarvis-Bud Setup Script for Raspberry Pi Zero 2 W
# Usage: bash setup.sh

set -e

echo "╔════════════════════════════════════════════════════╗"
echo "║     JARVIS-BUD RASPBERRY PI SETUP SCRIPT           ║"
echo "╚════════════════════════════════════════════════════╝"
echo ""

# Update system
echo "📦 Updating system packages..."
sudo apt-get update
sudo apt-get upgrade -y

# Install dependencies
echo "📥 Installing system dependencies..."
sudo apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    git \
    libportaudio2 \
    libasound2-dev \
    portaudio19-dev \
    python3-alsaaudio \
    spi-tools \
    i2c-tools \
    libatlas-base-dev \
    libjasper-dev \
    libtiff5 \
    libjasper1 \
    libharfbuzz0b \
    libwebp6 \
    libtiff5 \
    libopenjp2-7 \
    libopenblas0

# Enable SPI and I2C
echo "⚙️  Enabling SPI and I2C..."
sudo raspi-config nonint do_spi 0
sudo raspi-config nonint do_i2c 0

# Install Python dependencies
echo "🐍 Installing Python packages..."
pip3 install --upgrade pip
pip3 install -r requirements.txt

# Create config directory
mkdir -p config

# Download Ollama setup (optional)
echo ""
echo "🌐 Optional: Install Ollama for local LLM support"
echo "   Visit https://ollama.ai to install Ollama on your server"
echo "   Or on this Pi: curl https://ollama.ai/install.sh | sh"
echo ""

echo "✅ Jarvis-Bud setup complete!"
echo ""
echo "🚀 To start Jarvis-Bud, run:"
echo "   python3 -m jarvis_bud.main"
echo ""
echo "📖 For more information, see README.md"
