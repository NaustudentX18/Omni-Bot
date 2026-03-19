# 🤖 Omni-Bot: Multi-Modal AI Companion

**Omni-Bot** is a comprehensive AI companion platform featuring modular, hardware-first AI agents designed for edge devices.

## 📂 Projects

### [Jarvis-Bud 🤖](README_JARVIS_BUD.md)
*Type: Raspberry Pi Voice Assistant | Status: Active Development*

A modular, voice-activated AI Agent for **Raspberry Pi Zero 2 W** with Whisplay HAT and PiSugar 3.

**Features:**
- ✅ Interactive First-Boot Wizard (Hardware > Connectivity > Personality > API)
- ✅ 4 Pre-built "Bud" personalities (Tech-Support, Trail-Runner, Hacker, Zen)
- ✅ Dual-Route Intelligence (Local Ollama + Cloud OpenRouter)
- ✅ Terminal-Dark UI with neon accents & 60fps animations
- ✅ Real-time waveform visualization during voice capture
- ✅ Battery management with PiSugar 3 monitoring
- ✅ Physical GPIO buttons for Wake/Control
- ✅ Fully async event loop for responsive UI

**Quick Start:**
```bash
cd Omni-Bot
bash setup.sh
python3 -m jarvis_bud.main
```

[📖 Full Jarvis-Bud Documentation →](README_JARVIS_BUD.md)

---

## ⚡ Final Deployment Mode (Pi Zero 2 W)

This branch ships a hardened offline deployment stack with:

- 🔐 Tamper-evident audit chain (`logs/audit_chain.jsonl`)
- 🛑 Long-press **Button B** emergency stop (kills tracked process groups)
- ⚠️ High-risk action gating (risk >= 6 requires explicit button confirmation)
- 🧠 Offline brain planner + reflection loop with GGUF model fallback chain
- 🧵 Tiny memory layer (FAISS/MiniLM optional, JSONL fallback always available)
- 📦 `python main.py export` for single-file HTML + encrypted USB package export
- 🎛️ Runtime `config/config.ini` control for `vibe_level` + `god_mode` + `dry_run`

### Voice command list (offline parser)

- `status`
- `stop`
- `export`
- `target add <X>`
- `crack wifi`
- `full auto`
- `god mode`
- `make legendary`

### Vibe levels

Set in `config/config.ini`:

```ini
[runtime]
vibe_level = stealth     ; stealth | aggressive | cinematic
god_mode = false
dry_run = true
```

### God mode

`god mode` switches to simulation-first flow for demos:

- fake rapid results
- matrix/glitch OLED visuals
- safety-preserving no-live-aggression defaults

### Physical hardware checklist

- [ ] Raspberry Pi Zero 2 W boots and reaches shell
- [ ] Whisplay OLED active + matrix boot animation visible
- [ ] Button A triggers listen cycle
- [ ] Button B short press cycles Bud personality
- [ ] Button B long press performs emergency stop
- [ ] PiSugar battery values visible in HUD
- [ ] `python main.py export` writes encrypted package to mounted USB

**Built 2026 by madman + Cursor.**

---

## 🏗️ Project Structure

```
Omni-Bot/
├── README.md                    # This file
├── README_JARVIS_BUD.md        # Comprehensive Jarvis-Bud guide
├── LICENSE                      # MIT License
├── requirements.txt             # Python dependencies
├── setup.sh                     # Automated RPi setup script
│
├── jarvis_bud/                 # Main application
│   ├── main.py                # Entry point with async loop
│   ├── config.py              # Configuration management
│   ├── buds.json              # Personality definitions
│   │
│   ├── hardware/
│   │   ├── lcd.py            # ST7789 display driver
│   │   ├── audio.py          # WM8960 codec driver
│   │   ├── battery.py        # PiSugar 3 battery manager
│   │   └── buttons.py        # GPIO button handler
│   │
│   ├── ui/
│   │   ├── renderer.py       # PIL frame renderer
│   │   ├── animations.py     # Waveform animations
│   │   └── themes.py         # UI color schemes
│   │
│   ├── ai/
│   │   ├── ollama_client.py      # Local LLM (Ollama)
│   │   ├── openrouter_client.py  # Cloud LLM (OpenRouter)
│   │   └── router.py             # Intelligent routing
│   │
│   └── wizard/
│       └── setup_wizard.py      # First-boot setup
│
└── config/
    └── example_config.json      # Config template
```

---

## 🎯 Core Architecture

### Event Loop Design (60fps)
```
┌─ Async Main Loop ──────────────────────────────┐
├─ Display Update (60fps)                        │
├─ Button Event Handler                          │
├─ AI Response Generation (streaming)            │
├─ Battery Monitoring                            │
└────────────────────────────────────────────────┘
```

### Dual-Route AI
```
User Input
    ↓
AIRouter decides:
    ├─ Local Ollama (fast, offline)      [home/office]
    └─ Cloud OpenRouter (powerful)       [mobile/outdoor]
    ↓
AI Response → Waveform Animation → Output
```

### Hardware Stack
| Component | Driver | Purpose |
|-----------|--------|---------|
| RPi Zero 2W | Custom | Main CPU |
| ST7789 LCD | PIL-based | User Interface |
| WM8960 Codec | alsaaudio/pyaudio | Audio I/O |
| PiSugar 3 | Socket IPC | Battery + UPS |
| GPIO Buttons | RPi.GPIO | Physical Input |

---

## 🚀 Getting Started

### Prerequisites
- Raspberry Pi Zero 2 W (or any RPi with SPI/I2C support)
- Whisplay HAT with WM8960 codec
- ST7789 LCD display (240x280)
- PiSugar 3 battery management
- Python 3.8+
- WiFi/Ethernet for cloud AI (optional)

### Installation (5 min)

1. **Clone this repo:**
   ```bash
   git clone https://github.com/NaustudentX18/Omni-Bot.git
   cd Omni-Bot
   ```

2. **Run automated setup:**
   ```bash
   bash setup.sh
   ```
   This handles: system updates, Python dependencies, SPI/I2C enabling, config directory creation

3. **Start Jarvis-Bud:**
   ```bash
   python3 -m jarvis_bud.main
   ```

4. **Follow the interactive wizard:**
   - Step 1: Hardware Check ✅
   - Step 2: WiFi & Ollama auto-detection 📡
   - Step 3: Pick your personality 🤝
   - Step 4: Add OpenRouter API (optional) 🔑

5. **Done!** Your AI companion is ready 🎉

---

## 💡 Usage

### Physical Controls
- **Button A (GPIO 17)**: Press to activate Listen mode 🎙️
- **Button B (GPIO 27)**: Press to cycle through Buds 💫

### Voice Interaction
```
1. Press Button A
2. Speak your question
3. Release Button A
4. Watch waveform animate while thinking
5. Hear AI response through speaker
```

### LCD Display
```
🔋 85%                    🏠  ← Battery & Connectivity Status
─────────────────────────────
    📍 Tech-Support Bud 🤖
    
    ▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄  ← Waveform Animation
    
─────────────────────────────
    Local Ollama
```

---

## 🔧 Configuration

### First-Time Setup
The wizard creates `config/config.json` with your preferred settings

### Manual Configuration
Edit `config/config.json`:

```json
{
  "bud": {
    "id": "tech-support",
    "name": "Tech-Support Bud 🤖",
    "system_prompt": "You are a friendly tech-support assistant...",
    "ui_accent_color": "#00FF00"
  },
  "connectivity": {
    "ollama": "http://naspi:11434"
  },
  "openrouter": {
    "api_key": "sk_your_key_here",
    "model": "google/gemini-2.0-flash-lite:free"
  }
}
```

### Adding AI Backends

**Local Ollama (Free, Offline):**
```bash
# On your home server
ollama pull mistral
ollama serve
# Pi will auto-detect at common addresses
```

**Cloud OpenRouter (Powerful, Mobile):**
```
1. Get free API key: https://openrouter.ai/keys
2. Add to wizard at setup or config.json
3. Enjoy cloud AI models (Gemini, Llama, etc.)
```

---

## 🎨 UI & Personality

### Built-In Personalities
1. **Tech-Support Bud 🤖** - Green neon, patient & knowledgeable
2. **Trail-Runner Bud 🏃** - Blue neon, adventurous & motivational
3. **Snarky Hacker Bud 🖥️** - Magenta neon, witty & irreverent
4. **Zen-Guide Bud 🧘** - Orange neon, calm & philosophical

### Customize Appearance
Edit `jarvis_bud/buds.json` to add new personalities with custom:
- System prompts (behavior)
- UI accent colors
- Response styles
- Personality traits

### Theme Colors
Terminal-Dark with Neon Accents:
- Background: `#0A0A0F` (deep blue-black)
- Text: `#D2DCE6` (light gray)
- Neon Green: `#00FF64` (primary accent)
- Neon Blue: `#0096FF` (secondary accent)

---

## 🧠 AI Models

### Recommended Models

**Local (Ollama)** - Zero cost, instant, offline
- `mistral` — 4.1B params, lightweight
- `neural-chat` — Optimized for conversation
- `starling-lm` — 7B, highly capable

**Cloud (OpenRouter)** - Powerful, anywhere, free tier
- `google/gemini-2.0-flash-lite:free` — Fast & smart
- `meta-llama/llama-3.3-70b-instruct:free` — Most powerful
- `mistralai/mixtral-8x7b-instruct:free` — Balanced

---

## 📚 API Reference

### Hardware
```python
from jarvis_bud.hardware import ST7789Display, AudioCodec, Battery, ButtonHandler

lcd = ST7789Display()
audio = AudioCodec()
battery = Battery()
buttons = ButtonHandler()
```

### UI
```python
from jarvis_bud.ui import FrameRenderer, WaveformAnimator

renderer = FrameRenderer()
animator = WaveformAnimator()
animator.get_frame("idle")  # idle, listening, thinking, loading
```

### AI
```python
from jarvis_bud.ai import AIRouter

router = AIRouter(
    ollama_url="http://localhost:11434",
    openrouter_key="sk_..."
)
response = router.generate("Question?", prefer="auto")
```

### Configuration
```python
from jarvis_bud.config import ConfigManager

config = ConfigManager()
bud_name = config.get("bud.name")
prompt = config.get_bud_system_prompt()
config.set("bud.id", "snarky-hacker")
config.save()
```

[📖 Full API Documentation →](README_JARVIS_BUD.md#-api-documentation)

---

## 🐛 Troubleshooting

### Common Issues

**LCD not displaying?**
- Check SPI enabled: `sudo raspi-config` → SPI → Enable
- Verify backlight GPIO (usually GPIO 12)

**Audio not working?**
- Check codec: `i2cdetect -y 1` (look for WM8960)
- Unmute: `alsamixer` (space to unmute)

**Ollama not found?**
- Start Ollama server on your home PC/server
- Verify same WiFi network
- Check custom IP in config.json

**Stuck in setup wizard?**
- Hold Button A for 10 seconds to force-boot
- Delete config.json to re-run wizard: `rm config/config.json`

[📖 Full Troubleshooting Guide →](README_JARVIS_BUD.md#-troubleshooting)

---

## 🤝 Contributing

We'd love your help! Possible contributions:

- 🎭 New Bud personalities with unique system prompts
- 🎨 UI themes and visual customizations
- 🔌 Additional hardware driver support
- 🎬 Animation effects and transitions
- 📖 Documentation improvements
- 🐛 Bug reports and testing

### Development

```bash
# Clone and setup
git clone https://github.com/NaustudentX18/Omni-Bot.git
cd Omni-Bot
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Code quality
black jarvis_bud/
pylint jarvis_bud/

# Test
python3 -m pytest tests/
```

---

## 📜 License

MIT License - See [LICENSE](LICENSE) file for details

---

## 🎓 Acknowledgments

**Jarvis-Bud** brings together:
- Raspberry Pi ecosystem & community
- Ollama local LLM technology
- OpenRouter for cloud AI
- PIL/Pillow for UI rendering
- asyncio for responsive design

---

## 📞 Links & Resources

- **Jarvis-Bud Full Guide**: [README_JARVIS_BUD.md](README_JARVIS_BUD.md)
- **GitHub**: https://github.com/NaustudentX18/Omni-Bot
- **Ollama**: https://ollama.ai (Local LLM)
- **OpenRouter**: https://openrouter.ai (Cloud AI)
- **Raspberry Pi Docs**: https://www.raspberrypi.com/documentation/

---

## 🎯 Roadmap

- [x] First-boot wizard
- [x] Dual-route AI (local + cloud)
- [x] 4 built-in personalities
- [x] Waveform animations
- [ ] STT (Speech-to-Text)
- [ ] TTS (Text-to-Speech)
- [ ] Web dashboard for configuration
- [ ] OTA updates
- [ ] Custom skill/plugin system
- [ ] Multi-device sync

---

**🚀 Your AI companion awaits. Let's build the future together!**

```
     ^
    / \__
   (    @\___
   /         O
  /   (_____/
/_____/   U

Jarvis-Bud: Edge AI for makers, hikers, and tech-heads
```
