# 🤖 Jarvis-Bud: Hardware-First AI Companion

**Project Jarvis-Bud is a modular, voice-activated AI Agent for Raspberry Pi Zero 2 W** featuring the Whisplay HAT and PiSugar 3 battery management. It transforms your Pi into a sentient handheld AI companion with personality selection, emoji-rich UI, and seamless switching between local Ollama and cloud OpenRouter models.

> Designed for **makers**, **hikers**, and **tech-heads** who want AI intelligence in their pocket.

---

## 🎯 Features

- ✅ **First-Boot Wizard** - Interactive 4-step setup (Hardware > Connectivity > Personality > API)
- ✅ **Dual-Route Intelligence** - Switch between local Ollama and cloud OpenRouter
- ✅ **Personality System** - 4 pre-built "Buds" with unique system prompts and UI themes
  - 🤖 Tech-Support Bud - Patient, knowledgeable, helpful mentor
  - 🏃 Trail-Runner Bud - Adventurous, outdoor-focused companion
  - 🖥️ Snarky Hacker Bud - Witty, irreverent code enthusiast
  - 🧘 Zen-Guide Bud - Calm, philosophical, mindfulness-focused
- ✅ **Terminal-Dark UI** - Retro-futuristic aesthetic with neon accents (Green/Blue/Magenta)
- ✅ **Emoji Integration** - All UI strings include contextual emojis
- ✅ **Real-Time Waveform** - Smooth audio visualization during capture/processing
- ✅ **60fps Animation** - Responsive GUI powered by asyncio event loop
- ✅ **Battery Management** - Real-time PiSugar 3 monitoring with critical alerts
- ✅ **GPIO Buttons** - Button A for Listen/Wake, Button B to Cycle Personalities
- ✅ **Safety Core** - SHA-256 chained audit log + high-risk action confirmation
- ✅ **Emergency Stop** - Long-press Button B terminates tracked tool process groups
- ✅ **Export Pipeline** - `python main.py export` creates single-file HTML + encrypted USB package
- ✅ **Cyberpunk Runtime Profiles** - `stealth` / `aggressive` / `cinematic` vibe levels
- ✅ **God Mode + Legendary Demo** - instant simulation mode for presentations

### 🎙️ Full voice command list

- `status`
- `stop`
- `export`
- `target add X`
- `crack wifi`
- `full auto`
- `god mode`
- `make legendary`

---

## 📋 Hardware Requirements

| Component | Specs | Purpose |
|-----------|-------|---------|
| **Raspberry Pi Zero 2 W** | 1.9 GHz ARM, 512 MB RAM | Main processor |
| **Whisplay HAT** | WM8960 codec + audio I/O | Voice capture & playback |
| **ST7789 LCD Display** | 240x280, SPI interface | UI rendering & animations |
| **PiSugar 3** | 5000 mAh battery + UPS | Power + monitoring via `/tmp/pisugar-server.sock` |
| **GPIO Buttons** | GPIO 17 (A), GPIO 27 (B) | Physical input controls |

---

## 🏗️ Architecture

```
jarvis_bud/
├── hardware/               # Hardware drivers
│   ├── lcd.py             # ST7789 display (PIL-based)
│   ├── audio.py           # WM8960 codec (alsaaudio/pyaudio)
│   ├── battery.py         # PiSugar 3 monitoring
│   └── buttons.py         # GPIO button handlers
├── ui/                    # UI rendering & animations
│   ├── renderer.py        # PIL frame rendering engine
│   ├── animations.py      # Waveform & transition animations
│   └── themes.py          # Terminal-Dark color scheme
├── ai/                    # Dual-route AI intelligence
│   ├── ollama_client.py   # Local LLM backend
│   ├── openrouter_client.py # Cloud LLM backend
│   └── router.py          # Intelligent routing logic
├── wizard/                # First-boot setup
│   └── setup_wizard.py   # Interactive 4-step wizard
├── buds.json              # Personality definitions
├── config.py              # Configuration management
└── main.py                # Async event loop & app controller
```

### Event Loop Design

```
┌─────────────────────────────────────────────────────────┐
│        Async Event Loop (asyncio)                       │
├─────────────────────────────────────────────────────────┤
│ ┌─ Update Display (60fps) ───────────────────────────┐  │
│ │ • Render current state                             │  │
│ │ • Update waveform animations                       │  │
│ │ • Show battery/connectivity status                 │  │
│ └────────────────────────────────────────────────────┘  │
│                                                         │
│ ┌─ Button Handler (async)  ───────────────────────────┐  │
│ │ • Wait for GPIO interrupts                         │  │
│ │ • Trigger listen/respond tasks                     │  │
│ └────────────────────────────────────────────────────┘  │
│                                                         │
│ ┌─ AI Response Generation (async) ─────────────────────┐ │
│ │ • Stream responses (local or cloud)                │ │
│ │ • Update UI with thinking animation                │ │
│ └────────────────────────────────────────────────────┘  │
│                                                         │
│ ┌─ Battery Monitor (background) ─────────────────────┐  │
│ │ • Poll PiSugar socket every 10s                    │  │
│ │ • Alert on low battery                             │  │
│ └────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### 1. Flash & Boot Raspberry Pi

- Use [Raspberry Pi OS Lite](https://www.raspberrypi.com/software/) (32-bit recommended for Pi Zero)
- Enable SPI, I2C, and SSH via `raspi-config`

### 2. Clone Jarvis-Bud

```bash
git clone https://github.com/NaustudentX18/Omni-Bot.git
cd Omni-Bot
```

### 3. Run Automated Setup

```bash
bash setup.sh
```

This will:
- Update system packages
- Install Python dependencies (Pillow, requests, RPi.GPIO, pyaudio, alsaaudio)
- Enable SPI and I2C interfaces
- Create config directory

### 4. Start First-Boot Wizard

```bash
python3 -m jarvis_bud.main
```

The wizard will guide you through:

**Step 1: Hardware Check** 🔧
```
📺 Testing ST7789 LCD Display...     ✅
🎙️  Testing WM8960 Audio Codec...     ✅
🔋 Testing PiSugar 3 Battery...      ✅
🔘 Testing GPIO Buttons...           ✅
```

**Step 2: Connectivity** 📡
```
📳 Scanning WiFi networks...          ✅
🌐 Checking for local Ollama...       ✅ (http://naspi:11434)
```

**Step 3: Pick Your Bud** 🤝
```
Available personalities:
  1. Tech-Support Bud 🤖
  2. Trail-Runner Bud 🏃
  3. Snarky Hacker Bud 🖥️
  4. Zen-Guide Bud 🧘
Select: 1
```

**Step 4: API Configuration** 🔑
```
Enter OpenRouter API key (optional): sk_your_key_here
✅ OpenRouter API key is valid!
```

Configuration saved to `config/config.json`

### 5. Run Jarvis-Bud

```bash
python3 -m jarvis_bud.main
```

---

## 🎮 Usage

### Button Controls

| Button | Action | Effect |
|--------|--------|--------|
| **Button A** | Press & Hold | 🎙️ Start listening for voice input |
| **Button B** | Single Press | 💫 Cycle through available Buds |

### Voice Interaction

1. Press Button A to wake Jarvis-Bud
2. Speak your question or command
3. Release Button A when done
4. Watch the waveform animate while processing
5. Response plays through audio output

### Status Bar

```
🔋 85%  <─ Battery Level          Connectivity ─→  🏠
────────────────────────────────────────────────────
                    📍 Tech-Support Bud 🤖
                         
              [Waveform Animation Here]
                         
────────────────────────────────────────────────────
              Local Ollama (or OpenRouter)
```

---

## 🔧 Configuration Reference

### `config/config.json` Structure

```json
{
  "bud": {
    "id": "tech-support",
    "name": "Tech-Support Bud 🤖",
    "system_prompt": "You are a friendly, patient tech-support assistant...",
    "ui_accent_color": "#00FF00"
  },
  "hardware": {
    "lcd": "✅",
    "audio": "✅",
    "battery": "✅",
    "buttons": "✅"
  },
  "connectivity": {
    "wifi": "✅",
    "ollama": "http://naspi:11434"
  },
  "openrouter": {
    "api_key": "sk_your_key...",
    "model": "google/gemini-2.0-flash-lite:free"
  }
}
```

### Adding Custom Buds

Edit `jarvis_bud/buds.json`:

```json
{
  "buds": [
    {
      "id": "your-bud",
      "name": "Your Bud 🎯",
      "emoji": "🎯",
      "description": "Custom personality",
      "system_prompt": "Your custom system prompt here...",
      "personality_traits": ["trait1", "trait2"],
      "ui_accent_color": "#FFAA00",
      "response_style": "Your style here"
    }
  ]
}
```

---

## 🌐 AI Backend Setup

### Option A: Local Ollama (Recommended for Home Use)

#### On your home server or PC:

1. **Install Ollama:**
   ```bash
   curl https://ollama.ai/install.sh | sh
   ```

2. **Run Ollama server:**
   ```bash
   ollama serve
   ```

3. **Pull lightweight models:**
   ```bash
   ollama pull mistral        # 4.1B parameters
   ollama pull neural-chat    # Optimized for chat
   ollama pull starling-lm    # 7B, highly capable
   ```

4. **Access from Pi Zero:**
   - Make sure Pi and server are on same network
   - Ollama listens on `http://localhost:11434`
   - Wizard will auto-detect at common addresses (naspi, pironman, local network IPs)

**Advantages:**
- ✅ Zero cost (no API keys)
- ✅ Instant local responses
- ✅ Works offline
- ✅ Privacy-first

### Option B: OpenRouter Cloud (Recommended for Mobile Use)

1. **Get Free API Key:**
   - Visit https://openrouter.ai/keys
   - Sign up (free tier available)
   - Copy your API key

2. **Add to Jarvis-Bud:**
   - Run setup wizard and paste key at Step 4
   - Or edit `config/config.json` manually

3. **Available Free Models:**
   - `google/gemini-2.0-flash-lite:free` (Recommended - fast, capable)
   - `meta-llama/llama-3.3-70b-instruct:free` (Most powerful)
   - `mistralai/mixtral-8x7b-instruct:free` (Balanced)

**Advantages:**
- ✅ Cloud-based (works anywhere with WiFi)
- ✅ Cutting-edge models (Gemini 2.0, Llama 3.3)
- ✅ No setup required
- ✅ Free tier generous for casual use

---

## 🎨 UI Customization

### Terminal-Dark Theme Colors

| Component | Color | Hex |
|-----------|-------|-----|
| Background | Deep Blue-Black | `#0A0A0F` |
| Surface | Dark Purple | `#141428` |
| Text Primary | Light Gray | `#D2DCE6` |
| Text Secondary | Medium Gray | `#7882961` |
| Neon Green | Accent | `#00FF64` |
| Neon Blue | Accent | `#0096FF` |
| Neon Magenta | Accent | `#FF0096` |
| Neon Cyan | Progress | `#00FFFF` |

### Personalize Accent Color

Edit personality in `buds.json`:

```json
"ui_accent_color": "#FF0096"  // Your hex color
```

This color will appear in:
- Bud name header
- Button text
- Status indicators
- Waveform visualization (on select screens)

---

## 🐛 Troubleshooting

### Hardware Issues

| Problem | Cause | Solution |
|---------|-------|----------|
| LCD not displaying | SPI not enabled | Run `sudo raspi-config` → SPI → Enable |
| Audio not working | Audio codec not initialized | Check: `i2cdetect -y 1` (should show WM8960 address) |
| No audio input | Microphone muted | Check ALSA: `alsamixer` (unmute inputs) |
| Buttons not responsive | GPIO not initialized | Check: `gpio readall` (verify GPIO modes) |
| Battery not detected | PiSugar socket missing | Verify PiSugar running: `ls -la /tmp/pisugar-server.sock` |

### Connectivity Issues

| Problem | Cause | Solution |
|---------|-------|----------|
| Can't reach Ollama | Server offline/wrong IP | Check server IP in config; verify on same network |
| OpenRouter fails | Invalid API key | Generate new key at https://openrouter.ai/keys |
| WiFi disconnects | Weak signal | Move closer to router; check signal strength |
| Stuck in setup wizard | Pi frozen | Hold Button A for 10s to force restart |

### Performance Issues

| Problem | Cause | Solution |
|---------|-------|----------|
| Lag/stuttering | Low memory | Kill other processes; reboot |
| Display tearing | SPI bandwidth | Reduce refresh rate in code; upgrade SD card |
| AI responses slow | Model too large | Switch to lighter model (mistral vs llama-70b) |
| Frequent crashes | Overheating | Add heatsink to Pi; ensure good ventilation |

---

## 📚 API Documentation

### Hardware Module

```python
from jarvis_bud.hardware import ST7789Display, AudioCodec, Battery, ButtonHandler

# Display
lcd = ST7789Display(width=240, height=280)
lcd.init()
lcd.clear((0, 0, 0))
lcd.draw_text(120, 50, "Hello!", color=(0, 255, 0), center=True)
lcd.update()

# Audio
audio = AudioCodec(sample_rate=16000)
audio.init()
audio.start_recording()
# ... record for a bit ...
audio_data = audio.stop_recording()
level = audio.get_audio_level()

# Battery
battery = Battery()
battery.connect()
status = battery.get_status()  # {"percentage": 85, "voltage": 4.2, "charging": False}
if battery.is_low_battery(threshold=15):
    print("Low battery!")

# Buttons
buttons = ButtonHandler()
buttons.on_button_a(my_callback_function)
buttons.on_button_b(another_callback)
```

### UI Module

```python
from jarvis_bud.ui import FrameRenderer, WaveformAnimator, TerminalDarkTheme

# Renderer
renderer = FrameRenderer()
renderer.render_status_hud(
    lcd_display,
    bud_name="Tech-Support Bud 🤖",
    battery_level=85,
    is_charging=False,
    connectivity_status="local",
    animation_frame=animation_frame
)

# Animations
animator = WaveformAnimator(sample_count=60, animation_fps=60)
frame = animator.get_frame("idle")  # "idle", "listening", "thinking", "loading"
samples = frame.samples  # List of normalized values 0.0-1.0

# Themes
color = TerminalDarkTheme.NEON_GREEN
personality_color = TerminalDarkTheme.get_personality_color("tech-support")
```

### AI Module

```python
from jarvis_bud.ai import OllamaClient, OpenRouterClient, AIRouter

# Local Ollama
ollama = OllamaClient(base_url="http://localhost:11434", model="mistral")
response = ollama.generate("What is Python?", system_prompt="You are helpful")

# Cloud OpenRouter
openrouter = OpenRouterClient(api_key="sk_...", model="gemini")
response = openrouter.generate("Hello!")

# Intelligent Router
router = AIRouter(
    ollama_url="http://naspi:11434",
    openrouter_key="sk_..."
)
response = router.generate(
    "Complex query",
    system_prompt="System prompt",
    prefer="auto"  # auto-selects best route
)

# Async streaming
async for chunk in router.generate_async(prompt, system_prompt):
    print(chunk, end="", flush=True)
```

### Configuration Module

```python
from jarvis_bud.config import ConfigManager

config = ConfigManager("config/config.json")
bud_name = config.get("bud.name")
system_prompt = config.get_bud_system_prompt()
ollama_url = config.get_ollama_url()
api_key = config.get_openrouter_key()

# Modify and save
config.set("bud.id", "snarky-hacker")
config.save()
```

---

## 🤝 Contributing

We welcome contributions! Areas where help is appreciated:

- **New Buds** - Add personality definitions to `buds.json`
- **UI Themes** - Create new color schemes in `ui/themes.py`
- **Hardware Support** - Add drivers for additional HATs/sensors
- **Animations** - Expand waveform and transition animations
- **Documentation** - Improve guides and API docs
- **Testing** - Report bugs and edge cases

### Development Setup

```bash
# Clone repo
git clone https://github.com/NaustudentX18/Omni-Bot.git
cd Omni-Bot

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install in dev mode
pip install -e .
pip install -r requirements.txt

# Run tests
python3 -m pytest tests/

# Format code
black jarvis_bud/
pylint jarvis_bud/
```

---

## 📜 License

MIT License - See `LICENSE` file

---

## 🎓 Credits

**Project Jarvis-Bud** was designed and developed as a comprehensive IoT/AI project for makers.

- **Hardware Integration**: Whisplay HAT, PiSugar 3, ST7789 LCD
- **AI Backends**: Ollama (local), OpenRouter (cloud)
- **UI/UX**: Terminal-dark theme with neon accents, PIL-based rendering
- **Architecture**: Async-first design with concurrent event handling

---

## 📞 Support & Links

- **GitHub**: https://github.com/NaustudentX18/Omni-Bot
- **Ollama**: https://ollama.ai
- **OpenRouter**: https://openrouter.ai
- **RPi Documentation**: https://www.raspberrypi.com/documentation/

### Getting Started Resources

1. **First-time setup**: Run `python3 -m jarvis_bud.main` and follow the wizard
2. **Configuration**: See `config/example_config.json`
3. **API Keys**: Get OpenRouter free tier at https://openrouter.ai
4. **Ollama Setup**: Follow https://ollama.ai/library for model selection

---

**🚀 Ready to make your AI companion? Let's go!**

```
    / \__
   (    @\___
   /         O
  /   (_____/
/_____/   U
```

*Jarvis-Bud: Where hardware meets intelligence. Edge AI for everyone. 🤖✨*
