#!/bin/bash
# NXTGENAI / Jarvis-Bud Setup Script for Raspberry Pi Zero 2 W
# Usage: bash setup.sh

set -e

echo "╔════════════════════════════════════════════════════╗"
echo "║   NXTGENAI CYBERPUNK PI DEPLOYMENT INITIALIZER     ║"
echo "╚════════════════════════════════════════════════════╝"
echo ""

# ── Python version guard ──────────────────────────────────────────────────────
python3 -c "import sys; assert sys.version_info >= (3, 10)" 2>/dev/null || {
    echo "❌ Python 3.10 or newer is required."
    echo "   Current: $(python3 --version 2>&1)"
    exit 1
}
echo "✅ Python $(python3 -c 'import sys; print(*sys.version_info[:2], sep=".")')"

# Update system
echo "📦 Updating system packages..."
sudo apt-get update
sudo apt-get upgrade -y

# ── Required system packages ──────────────────────────────────────────────────
echo "📥 Installing system dependencies..."
sudo apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    python3-venv \
    git \
    curl \
    aria2 \
    unzip \
    nmap \
    aircrack-ng \
    hcxtools \
    dnsrecon \
    nikto \
    hydra \
    sqlmap \
    espeak-ng \
    libportaudio2 \
    libasound2-dev \
    portaudio19-dev \
    python3-alsaaudio \
    spi-tools \
    i2c-tools \
    libatlas-base-dev \
    libopenjp2-7 \
    libopenblas0

# ── Optional security tools (not in all distro repos — non-fatal) ─────────────
echo "🔧 Installing optional security tools (failures are non-fatal)..."
for pkg in gobuster feroxbuster theharvester; do
    sudo apt-get install -y "$pkg" 2>/dev/null \
        && echo "  ✅ $pkg" \
        || echo "  ⚠️  $pkg not found in repos — install manually if needed"
done

# Enable SPI and I2C
echo "⚙️  Enabling SPI and I2C..."
sudo raspi-config nonint do_spi 0
sudo raspi-config nonint do_i2c 0

# ── Python virtual environment ────────────────────────────────────────────────
echo "🐍 Setting up Python virtual environment..."
python3 -m venv venv
# shellcheck source=/dev/null
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Create runtime directories
mkdir -p config models logs reports

# Safe default runtime profile for first boot
if [ ! -f config/config.ini ]; then
cat > config/config.ini << 'EOF'
[runtime]
vibe_level = cinematic
god_mode = false
dry_run = true
EOF
fi

echo "🧠 Downloading GGUF models (resumable aria2)..."
MODEL_DIR="models"
mkdir -p "$MODEL_DIR"

# Priority model: Gemma-2 2B Q4_K_M
aria2c -c -x 8 -s 8 \
  -d "$MODEL_DIR" \
  -o "gemma-2-2b-it-Q4_K_M.gguf" \
  "https://huggingface.co/bartowski/gemma-2-2b-it-GGUF/resolve/main/gemma-2-2b-it-Q4_K_M.gguf" || true

# Fallback model: Phi-3.5-mini Q4_K_M
aria2c -c -x 8 -s 8 \
  -d "$MODEL_DIR" \
  -o "phi-3.5-mini-instruct-Q4_K_M.gguf" \
  "https://huggingface.co/bartowski/Phi-3.5-mini-instruct-GGUF/resolve/main/Phi-3.5-mini-instruct-Q4_K_M.gguf" || true

# Ultra-lean fallback: TinyLlama Q4_K_M
aria2c -c -x 8 -s 8 \
  -d "$MODEL_DIR" \
  -o "tinyllama-1.1b-chat-v1.0-Q4_K_M.gguf" \
  "https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf" || true

echo "🗣️ Downloading Piper voice pack (optional fallback to espeak-ng)..."
aria2c -c -x 4 -s 4 \
  -d "$MODEL_DIR/piper" \
  -o "en_US-lessac-medium.onnx" \
  "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx" || true
aria2c -c -x 4 -s 4 \
  -d "$MODEL_DIR/piper" \
  -o "en_US-lessac-medium.onnx.json" \
  "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json" || true

# Download Ollama setup (optional)
echo ""
echo "🌐 Optional: Install Ollama for local LLM support"
echo "   Visit https://ollama.ai to install Ollama on your server"
echo "   Or on this Pi: curl https://ollama.ai/install.sh | sh"
echo ""

echo "✅ Jarvis-Bud setup complete!"
echo ""
echo "🚀 To start Jarvis-Bud, activate the venv first:"
echo "   source venv/bin/activate"
echo "   python3 -m jarvis_bud.main"
echo ""
echo "   Or if installed via pip:"
echo "   jarvis-bud"
echo ""
echo "📦 To export encrypted report package to USB:"
echo "   source venv/bin/activate && python3 main.py export"
echo ""
echo "📖 For more information, see README.md"
