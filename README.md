# 📟 BMO OS - "Adventure Time" Project (v1.5.8 GOLD)

**Developer:** Carlo Sitaro
**Host System:** openSUSE Tumbleweed/Leap (GNOME 49 Wayland / Xfce X11)
**Core:** Python 3.11+ / PyQt6 / Ollama (Gemma 3:4b)

---

BMO-OS is a voice assistant for Linux, specifically designed for Wayland/Sway environments. It integrates local LLMs via Ollama with fast text-to-speech using Piper.

## 🛠 Current State
* **Version:** 1.5.8
* **Core:** Python integration between Ollama and Piper TTS.
* **Compatibility:** Optimized for RPM-based systems (OpenSUSE/Fedora).

## 📦 Installation & Setup
> **Current Status:** The installation script is functional but currently optimized for `zypper`. Robust error handling and multi-distro support are priority targets for upcoming 1.6.x updates.

## 🛠️ Run the Installer

Clone the repository and execute the setup script:

1. git clone https://github.com/Citizen839X/BMO-OS.git
2. cd BMO-OS
3. chmod +x scripts/setup_bmo.sh
4. ./scripts/setup_bmo.sh

---

## 🤝 Special Contributor's Note: PTT (Push To Talk) Implementation

**Current Challenge:** The UI and trigger logic are fully architected. The system features a robust trigger based on a shared memory file (`/dev/shm/bmo_listening`).

However, I am seeking expertise in **PipeWire/PulseAudio** integration for a seamless, low-latency audio capture bridge that won't block the PyQt6 event loop. If you are an expert in real-time STT buffering, help me give BMO his "ears"!

---

**"BMO is more than a computer. BMO is family."** 💚

## 📸 Gallery
Check out BMO-OS in action:

![BMO Screen 01](screenshots/sc_01.png)
![BMO Screen 02](screenshots/sc_02.png)
![BMO Screen 03](screenshots/sc_03.png)
![BMO Screen 04](screenshots/sc_04.png)
![BMO Screen 05](screenshots/sc_05.png)
![BMO Screen 06](screenshots/sc_06.png)
