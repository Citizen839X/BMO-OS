# 📟 BMO OS - "Adventure Time" Project (v1.5.8 GOLD)

**Developer:** Carlo Sitaro
**Host System:** openSUSE Tumbleweed/Leap (GNOME 49 Wayland / Xfce X11)
**Core:** Python 3.11+ / PyQt6 / Ollama (Gemma 3:4b)

---

## 📜 Version History (Changelog)

### 🚀 v1.5.8 - "Native System Integration" (Final Release)
* **Universal Linux Installer:** Rewritten `setup_bmo.sh` with auto-detection for **openSUSE, Fedora, Debian, and Arch Linux** (including all major derivatives).
* **Self-Contained Voice Engine:** Integrated **Piper TTS** directly into the project structure. No global installation required.
* **XFCE & GNOME Parity:** Finalized `.desktop` entry with `StartupWMClass=BMO_OS` synchronization for perfect dock/panel pinning.
* **Global Menu Architecture:** Implemented `QMenuBar` support for Xfce Top Panel integration.
* **Hotkey Engine:** Added `Alt+S` for image injection and `Alt+H` for Help/About.
* **Robotic Voice Refinement:** Adjusted **Sox** filters for a clearer, authentically electronic tone.

### 💎 v1.5.7 - "Stability & Professionalism"
* **Thread-Safe Architecture:** Rewrote response handler using `pyqtSignals` to eliminate UI freezing during long AI inferences.
* **Markdown UI:** Integrated `python-markdown`. BMO now renders bold text, lists, and code blocks natively.
* **Hardware Adaptation:** Added smart hardware profiler (optimized for **16T systems**) to balance AI speed and system stability.
* **Phonetic Engine Patch:** Implemented a phonetic override in the TTS pipeline to fix "Italian-style" vowel mispronunciations (e.g., "I" to "eye" conversion).

### 🏆 v1.5 - "The Gold Master"
* **Full Refactoring:** Code cleanup and removal of redundant modules.
* **Wayland Optimization:** Fixed for **GNOME 49**. Corrected window-to-launcher binding via `app.setDesktopFileName()`.
* **Enhanced Safety:** Reinforced `filter_profanity`. BMO is now a Child-Safe environment.

### 🟣 v1.4 - "Life & Presence"
* **ASCII Animations:** Added dynamic facial expressions (Idle, Blink, Processing).
* **Deep Sleep:** Introduced an automatic power-save state after 5 minutes of inactivity with a "zZz" animation.
* **Push-To-Talk (PTT) Ready:** Implemented listening trigger logic via `/dev/shm/bmo_listening`.

*(... v1.0 through v1.3 archived in legacy documentation ...)*

---

## 🛠️ Automated Installation

BMO now features an intelligent, multi-distro setup script. It will automatically detect your package manager, install system dependencies, and organize the environment.

## 🛠️ Run the Installer

Clone the repository and execute the setup script:

chmod +x scripts/setup_bmo.sh
./scripts/setup_bmo.sh

## 🐧 OS Compatibility Matrix

openSUSE Tumbleweed - Native (Primary) 
Fedora - Supported 
Debian & Derivatives (Ubuntu, Mint, Pop!_OS) - Supported 
Arch Linux & Derivatives (EndeavourOS, CachyOS) - Supported

PS - If you are on openSUSE, you can also install dependencies via:

sudo zypper in python3-PyQt6 python3-Pillow python3-markdown

💎 Note for Bazzite / Fedora Silverblue Users

Since Bazzite is an atomic/immutable distribution, the standard dnf commands inside the script may not modify the base system. 

---

📋 Appendix: Required System Components

1. System Packages (Managed by Installer)

    PyQt6: GUI Framework.

    python-markdown: For rich-text chat rendering.

    sox & alsa-utils: Audio processing and playback.

    gcc-c++: Required for certain Python extensions.

2. AI Stack & Models

    Ollama Runtime: Must be running locally.

    Text Model: Custom model named BMO (Gemma 3 based).

    Vision Model: gemma3:4b.

    Piper TTS: Binary executable located in ~/BMO/piper/ with the en_US-amy-medium.onnx voice model.

## 🤝 Special Contributor's Note: PTT (Push To Talk) Implementation

**Current Challenge:** The UI and trigger logic are fully architected. The system features a robust trigger based on a shared memory file (`/dev/shm/bmo_listening`).

However, I am seeking expertise in **PipeWire/PulseAudio** integration for a seamless, low-latency audio capture bridge that won't block the PyQt6 event loop. If you are an expert in real-time STT buffering, help me give BMO his "ears"!

---
**"BMO is more than a computer. BMO is family."** 💚

## 🖥️ BMO in Action (XFCE + Cortile)

BMO is perfectly integrated into the **openSUSE Tumbleweed** environment using **XFCE (X11)**. 
The following screenshots showcase the seamless integration with the **Cortile Tile Manager**, 
the **Global Menu** support, and BMO's advanced interaction capabilities.

## Screenshots

| | | |
|:---:|:---:|:---:|
| ![sc_01](screenshots/sc_01.png) | ![sc_02](screenshots/sc_02.png) | ![sc_03](screenshots/sc_03.png) |
| ![sc_04](screenshots/sc_04.png) | ![sc_05](screenshots/sc_05.png) | ![sc_06](screenshots/sc_06.png) |
