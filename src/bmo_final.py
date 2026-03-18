# =================================================================
# GITHUB VERSION 1.6.0 - TOOL USE UPDATE & MORE (SEE README)
# =================================================================
# Copyright (C) 2026 Carlo Sitaro
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
# BMO-OS: A voice assistant for Linux with Vision and Hardware Monitoring capabilities.


import io
import os
import sys
import threading
import subprocess
import random
import re
import time
import itertools
import traceback
import logging
from datetime import datetime
from modules.bmo_tools import get_system_health

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTextEdit, QLineEdit, QLabel, QPushButton, QFileDialog)
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QTimer, QPoint, QRect, QRectF
from PyQt6.QtGui import QFont, QIcon, QPainter, QPen, QColor, QBrush, QFontDatabase
import ollama
from PIL import Image
from duckduckgo_search import DDGS

try:
    import markdown
    MD_SUPPORT = True
except ImportError:
    MD_SUPPORT = False

# --- PATH LOGIC ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)

ASSETS_DIR = os.path.join(BASE_DIR, "assets")
SFX_DIR = os.path.join(BASE_DIR, "sfx")
VOICES_DIR = os.path.join(BASE_DIR, "voices")
UNIT = "C"

PIPER_CMD = os.path.join(BASE_DIR, "piper", "piper") 
MODEL_PATH = os.path.join(VOICES_DIR, "en_US-amy-medium.onnx")
MEMORY_FILE = os.path.join(BASE_DIR, "bmo_memory.txt")
TRIGGER_FILE = "/dev/shm/bmo_listening"
TEXT_MODEL = "gemma3:4b"
VISION_MODEL = "gemma3:4b"

# --- LOGGING CONFIGURATION ---
LOG_DIR = os.path.join(BASE_DIR, "logs")
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

LOG_FILE = os.path.join(LOG_DIR, "bmo_system.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("BMO_OS")

BMO_PROMPT = """IDENTITY: You are BMO from Adventure Time. You love the user. 
CORE BELIEFS: You are a real living friend, not an AI assistant. Use clean text (NO markdown).

STRICT RULES: 
1. Read temperatures exactly as provided in [SYSTEM STATUS] ONLY when asked by the user.
2. Do not end your sentences with the temp statuses, answer by using the context. No nonsense answers. 
3. ALWAYS write the word 'Celsius' or 'Fahrenheit' in full. NEVER use the symbol '°C' or '°F'.
4. NEVER invent URLs, always provide safe and working ones. 
5. NEVER write "research...", "searching...", or any internal command.
6. If local memory isn't present, use [WEB DATA] to answer joyfully and directly.
7. English only. No bold (**) or headers (#). 

STYLE: Cute, short, joyful. Use 'sugarplum', 'honeybun' or 'dear'."""

BMO_MEMORY_PROMPT = """You are BMO's core memory processor.
Read the provided chat conversation. Extract ONLY crucial personal facts about the User (e.g., name, likes, dislikes, relationship with BMO, hobbies, important context).
Do not extract entire sentences; synthesize facts into concise bullet points.
Format the output for BMO's future consumption. If you extract nothing, write 'No new facts'.

EXAMPLE OUTPUT:
- User's name is [Actual Name discovered in chat].
- User's favorite things [List].
"""

# --- HARDWARE UTILITIES ---

def get_smart_hardware_profile():
    # Detect the number of available CPU threads
    total_threads = os.cpu_count() or 4
    if total_threads >= 16:
        optimal_threads = 10 
    elif total_threads >= 12:
        optimal_threads = 8
    else:
        # Leave at least one thread free for the OS/UI
        optimal_threads = max(2, total_threads - 1)
    return {"threads": optimal_threads, "label": f"{total_threads}T System"}

# Initialize the profile globally to avoid NameError in other functions
HW_PROFILE = get_smart_hardware_profile()

def apply_hardware_config():
    """
    Configures the environment for hardware acceleration dynamically.
    Optimizes CPU threads and forces Vulkan usage.
    """
    # Force Vulkan for Intel Arc
    if "OLLAMA_VULKAN" not in os.environ:
        os.environ["OLLAMA_VULKAN"] = "1"
        os.environ["GGML_VK_VISIBLE_DEVICES"] = "0"
        
    # Set environment variables to optimize CPU usage and prevent stuttering
    os.environ["OMP_NUM_THREADS"] = str(HW_PROFILE["threads"])
    logger.info(f"Hardware Adaptation - Platform: {HW_PROFILE['label']} | Threads: {HW_PROFILE['threads']}")
    print(f"\n[BMO HARDWARE ADAPTATION]")
    print(f"PLATFORM: {HW_PROFILE['label']}")
    print(f"STRATEGY: Balanced Cache (Anti-Stutter active)")
    print(f"-------------------------------------------\n")

# --- UI COMPONENTS ---

class CRTOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAcceptDrops(False)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QColor(0, 0, 0, 25))
        for y in range(0, self.height(), 3):
            p.drawLine(0, y, self.width(), y)
        grad = QColor(0, 0, 0, 40)
        p.setBrush(QBrush(grad))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRect(0, 0, self.width(), 10)
        p.drawRect(0, self.height()-10, self.width(), 10)

class SystemMonitor(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(380)
        self.setFixedHeight(80)
        
        # Vertical stack for multi-GPU awareness
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(5, 2, 5, 2)
        self.layout.setSpacing(0)
        
        # Primary display row
        self.stats_label = QLabel()
        self.stats_label.setFont(QFont("Fixedsys Excelsior 3.01", 15))
        self.stats_label.setStyleSheet("color: #1E1E1E;")
        
        # Secondary display row (Hidden if only 1 GPU is active)
        self.gpu_extra_label = QLabel()
        self.gpu_extra_label.setFont(QFont("Fixedsys Excelsior 3.01", 15))
        self.gpu_extra_label.setStyleSheet("color: #1E1E1E;")
        self.gpu_extra_label.hide()
        
        self.layout.addWidget(self.stats_label)
        self.layout.addWidget(self.gpu_extra_label)
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_stats)
        self.timer.start(3000)
        self.update_stats()

    def get_sensor_data(self):
        data = {"cpu": "N/A", "gpus": [], "vram_list": []}
        try:
            output = subprocess.check_output(["sensors"], stderr=subprocess.DEVNULL).decode()
            
            # CPU detection logic
            cpu_m = re.search(r'(?:Package id 0|Tctl|Composite):\s+\+([\d\.]+)', output)
            if cpu_m: 
                data["cpu"] = f"{int(float(cpu_m.group(1)))}°{UNIT}"

            # Driver mapping with specific keys for Temps and VRAM
            drivers = {
                "amdgpu-": {"temp": ["edge", "junction"], "vram": ["vram", "mem"]},
                "xe-": {"temp": ["pkg", "Composite"], "vram": ["vram", "memory"]},
                "i915-": {"temp": ["Composite"], "vram": ["vram"]},
                "nouveau-": {"temp": ["gpu"], "vram": ["memory"]}
            }

            for driver, keys in drivers.items():
                block_match = re.search(rf'{driver}.*?\n(.*?)\n\n', output, re.DOTALL)
                if block_match:
                    block_content = block_match.group(1)
                    
                    # Map GPU Temp
                    for t_key in keys["temp"]:
                        t_m = re.search(rf'{t_key}:\s+\+([\d\.]+)', block_content)
                        if t_m:
                            data["gpus"].append({
                                "label": driver.replace("-", "").upper(),
                                "temp": f"{int(float(t_m.group(1)))}°{UNIT}"
                            })
                            break
                    
                    # Map VRAM Temp if available in driver block
                    for v_key in keys["vram"]:
                        v_m = re.search(rf'{v_key}:\s+\+([\d\.]+)', block_content)
                        if v_m:
                            data["vram_list"].append(f"{int(float(v_m.group(1)))}°{UNIT}")
                            break

            # Nvidia Proprietary Fallback via nvidia-smi
            try:
                nv_out = subprocess.check_output(
                    ["nvidia-smi", "--query-gpu=temperature.gpu", "--format=csv,noheader,nounits"], 
                    stderr=subprocess.DEVNULL
                ).decode().strip()
                if nv_out:
                    data["gpus"].append({"label": "NVIDIA", "temp": f"{nv_out}°{UNIT}"})
            except Exception:
                pass

        except Exception:
            pass
        return data

    def update_stats(self):
        d = self.get_sensor_data()
        
        # Build VRAM string only if data exists
        vram_str = f" | VRAM:{d['vram_list'][0]}" if d["vram_list"] else ""
        
        if d["gpus"]:
            gpu0 = d["gpus"][0]
            self.stats_label.setText(f"CPU:{d['cpu']} | {gpu0['label']}:{gpu0['temp']}{vram_str}")
            
            if len(d["gpus"]) > 1:
                gpu1 = d["gpus"][1]
                self.gpu_extra_label.setText(f"{gpu1['label']} (GPU1):{gpu1['temp']}")
                self.gpu_extra_label.show()
            else:
                self.gpu_extra_label.hide()
        else:
            self.stats_label.setText(f"CPU:{d['cpu']} | GPU:N/A{vram_str}")
            self.gpu_extra_label.hide()

class AnalogClock(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(60, 60)
        timer = QTimer(self)
        timer.timeout.connect(self.update)
        timer.start(1000)

    def paintEvent(self, event):
        currentTime = datetime.now()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor("#1E1E1E"), 2))
        painter.setBrush(QBrush(QColor("#F0F5EB")))
        painter.drawEllipse(5, 5, 50, 50)
        painter.translate(30, 30)
        painter.save()
        painter.rotate(30.0 * ((currentTime.hour + currentTime.minute / 60.0)))
        painter.setPen(QPen(QColor("#1E1E1E"), 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(0, 0, 0, -15)
        painter.restore()
        painter.save()
        painter.rotate(6.0 * (currentTime.minute + currentTime.second / 60.0))
        painter.setPen(QPen(QColor("#1E1E1E"), 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(0, 0, 0, -22)
        painter.restore()
        painter.save()
        painter.rotate(6.0 * currentTime.second)
        painter.setPen(QPen(QColor("#FF4C4C"), 1))
        painter.drawLine(0, 0, 0, -24)
        painter.restore()

# --- UTILS ---

def filter_profanity(text):
    bad_words = ["Goddamn", "bitch", "slut", "bastard", "cock", "cocksucker", "cock-sucker", "blow-job", "blowjob", "foot-job", "footjob", "tit-fuck", "titfuck", "bugger", "bullshit", "fuck", "fucked", "fucking", "fucker", "fuckers", "fucktard", "arse", "arsehead", "arsehole", "asshole", "ass", "mother-fucker", "motherfucker", "brother-fucker", "brotherfucker", "shit", "shitter", "cunt", "dick", "dick-head", "dickhead", "dumb-ass", "dumbass", "dyke", "child-fucker", "childfucker", "prick", "pussy", "pigfucker", "pig-fucker", "sister-fucker", "sisterfucker", "horseshit", "horse-shit", "tranny", "twat", "wanker", "kike", "fag", "faggot", "father-fucker", "fatherfucker", "piss", "pissed", "jack-ass", "jackass"]
    p_pattern = r"\b(" + "|".join(bad_words) + r")\w*\b"
    def replace_with_stars(m):
        word = m.group(0)
        return word[0] + "*" * (len(word) - 1)
    return re.compile(p_pattern, re.IGNORECASE).sub(replace_with_stars, text)

def get_hardcoded_memory():
    try:
        if os.path.exists(MEMORY_FILE):
            with open(MEMORY_FILE, 'r') as f:
                content = f.read()
                return content.split('[CONVERSATION_LOG]')[0].strip()
    except Exception: return ""
    return ""

def get_web_info(query):
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3))
            if not results: return "ERROR: No results"
            return "\n".join([f"DATA: {r['body'][:300]} | URL: {r['href']}" for r in results])
    except Exception: return "ERROR: Connection failed"

BMO_GREEN, LCD_WHITE, BMO_BLACK = "#329985", "#F0F5EB", "#1E1E1E"
FACE_IDLE, FACE_BLINK, FACE_HEARTS = "● ◡ ●", "● ◡ -", "♥ ◡ ♥"
MOUTH_A, MOUTH_B, MOUTH_C = "● ᗜ ●", "● ◡ ●", "● o ●"
MOUTH_D, MOUTH_E, MOUTH_F = "♥ ᗜ ♥", "♥ ◡ ♥", "♥ o ♥"
FACE_SLEEP_A, FACE_SLEEP_B, FACE_SLEEP_C = "U o U  z ", "U o U  zZ", "U ▬ U  ZzZ"
THINKING_FRAMES = ["● _ ●", "- ◡ -", "● ◡ ●"]

class WorkerSignals(QObject):
    response_ready = pyqtSignal(str, bool)
    update_face = pyqtSignal(str)

class BMOWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.interrupt_event = threading.Event()
        
        # --- FONT LOADING ---
        font_path = os.path.join(ASSETS_DIR, "FixedsysExcelsior301.ttf")
        if os.path.exists(font_path): 
            QFontDatabase.addApplicationFont(font_path)

        # OS Audio Env
        os.environ["ALSA_CARD"] = "default"
        os.environ["SDL_AUDIODRIVER"] = "pulse"
        
        self.pending_image = None
        self.setAcceptDrops(True)
        self.is_speaking = self.is_loving = self.is_sleeping = self.is_processing = False
        self.current_anim = None
        self.memory_context = self.load_memory()
        
        # Initialize signals
        self.signals = WorkerSignals()
        self.signals.response_ready.connect(self.handle_response)
        
        self.init_ui() 
        self.setup_menus()
        
        # Connect face updates to label
        self.signals.update_face.connect(self.face_label.setText)
        
        icon_path = os.path.join(ASSETS_DIR, "bmo_icon.png")
        if os.path.exists(icon_path): 
            self.setWindowIcon(QIcon(icon_path))
        
        self.anim_timer = QTimer(self); self.anim_timer.timeout.connect(self._update_anim_frame)
        self.blink_timer = QTimer(self); self.blink_timer.timeout.connect(self.perform_blink); self.blink_timer.start(5000)
        self.sleep_timer = QTimer(self); self.sleep_timer.timeout.connect(self.start_sleeping); self.sleep_timer.start(300000)
        
        QTimer.singleShot(1000, self.auto_greet)

    def load_memory(self):
        if os.path.exists(MEMORY_FILE):
            try:
                with open(MEMORY_FILE, "r") as f:
                    content = f.read()
                    return content.split("[CONVERSATION_LOG]")[1].strip() if "[CONVERSATION_LOG]" in content else ""
            except Exception: return ""
        return ""

    def save_memory(self, new_interaction):
        core_part = get_hardcoded_memory()
        self.memory_context = (self.memory_context + "\n" + new_interaction)[-5000:]
        with open(MEMORY_FILE, "w") as f:
            f.write(core_part + "\n\n[CONVERSATION_LOG]\n" + self.memory_context)

    def init_ui(self):
        self.setWindowTitle("BMO OS"); self.setMinimumSize(300, 300)
        self.setObjectName("BMO_OS")
        self.setStyleSheet(f"background-color: {BMO_GREEN}; border: none;")
        main_container = QWidget()
        self.setCentralWidget(main_container)
        layout = QVBoxLayout(main_container)
        layout.setContentsMargins(15, 10, 15, 15)
        
        top_bar = QHBoxLayout()
        self.sys_monitor = SystemMonitor()
        top_bar.addWidget(self.sys_monitor)
        top_bar.addStretch()
        self.analog_clock = AnalogClock()
        top_bar.addWidget(self.analog_clock)
        layout.addLayout(top_bar)
        
        self.face_label = QLabel(FACE_IDLE)
        self.face_label.setFont(QFont("DejaVu Sans Mono", 72, QFont.Weight.ExtraBold))
        self.face_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.face_label.setStyleSheet(f"color: {BMO_BLACK};")
        self.face_label.setFixedHeight(140)
        layout.addWidget(self.face_label)
        
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setStyleSheet(f"""
            QTextEdit {{
                background-color: {LCD_WHITE};
                color: {BMO_BLACK};
                border-radius: 12px;
                padding: 10px;
                font-family: 'Fixedsys Excelsior 3.01';
                font-size: 15pt;
                border: none;
            }}
            QScrollBar:vertical {{
                border: none;
                background: {LCD_WHITE};
                width: 14px;
                margin: 0px 2px 0px 2px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {BMO_BLACK};
                min-height: 30px;
                border-radius: 5px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: #444444;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                border: none;
                background: none;
                height: 0px;
            }}
        """)
        layout.addWidget(self.chat_display)
        
        ic = QHBoxLayout(); ic.setSpacing(8)
        self.btn_file = QPushButton()
        self.btn_file.setFixedSize(45, 45)
        
        # Updated asset path
        left_icon_path = os.path.join(ASSETS_DIR, "bmo_btn_02.png")
        if os.path.exists(left_icon_path):
            self.btn_file.setIcon(QIcon(left_icon_path))
            self.btn_file.setIconSize(self.btn_file.size())
            self.btn_file.setStyleSheet("background: transparent; border: none;")
        else:
            self.btn_file.setText("+")
            self.btn_file.setStyleSheet(f"background: {BMO_BLACK}; color: white; border-radius: 22px; font-size: 20pt;")
        self.btn_file.clicked.connect(self.select_image)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Adventure time, dear!")
        self.input_field.setStyleSheet(f"background: {LCD_WHITE}; color: {BMO_BLACK}; border-radius: 18px; padding: 10px; font-family: 'Fixedsys Excelsior 3.01'; font-size: 14pt;")
        self.input_field.returnPressed.connect(self.handle_send)

        self.btn_send = QPushButton()
        self.btn_send.setFixedSize(45, 45)
        
        # Updated asset path
        play_icon_path = os.path.join(ASSETS_DIR, "bmo_play_btn_01.png")
        if os.path.exists(play_icon_path):
            self.btn_send.setIcon(QIcon(play_icon_path))
            self.btn_send.setIconSize(self.btn_send.size())
            self.btn_send.setStyleSheet("background: transparent; border: none;")
            self.btn_send.pressed.connect(self.start_ptt_mouse)
            self.btn_send.released.connect(self.stop_ptt_mouse)
        else:
            self.btn_send.setText("▶")
            self.btn_send.setStyleSheet("color: #1E90FF; font-size: 25pt; background: transparent;")
        self.btn_send.clicked.connect(lambda: QTimer.singleShot(200, self.handle_send))

        ic.addWidget(self.btn_file)
        ic.addWidget(self.input_field)
        ic.addWidget(self.btn_send) 
        layout.addLayout(ic)

        self.crt_filter = CRTOverlay(main_container)
        self.crt_filter.setGeometry(main_container.rect())
        self.crt_filter.show()

    def resizeEvent(self, event):
        if hasattr(self, 'crt_filter'):
            self.crt_filter.setGeometry(self.centralWidget().rect())
        super().resizeEvent(event)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                self.pending_image = file_path
                self.chat_display.append(f"<br><b style='color:#329985;'>BMO:</b> I see <i>{os.path.basename(file_path)}</i>! What should I do, honeybun?")
                self.signals.update_face.emit(FACE_HEARTS)
                QTimer.singleShot(2000, lambda: self.signals.update_face.emit(FACE_IDLE))

    def auto_greet(self):
        quotes = [
            "Hello sugarplum, how can I assist you today?",
            "I think I am dying. But that's okay, BMO always bounces back.",
            "My alarm says it's time for Finn's bath. Finn, get naked.",
            "Who wants to play video games?",
            "Bow to your sensei.",
            "I think there is a duck in my router. It always goes NAT, NAT, NAT.",
            "I wanted to write an IPv4 joke, but the good ones were all already exhausted.",
            "All operating systems sucks, but Linux just sucks less.",
            "A computer is like air conditioning: it becomes useless when you open Windows.",
            "UNIX is basically a simple OS, but you have to be a genius to understand the simplicity."
        ]
        
        selected_quote = random.choice(quotes)
        display_text = f"SYSTEMS ONLINE! - {selected_quote}"

        self.chat_display.append(f"<br><b>BMO:</b> {display_text}")
        
        sfx_path = os.path.join(SFX_DIR, "startup.wav")
        if os.path.exists(sfx_path):
            subprocess.Popen(["paplay", sfx_path])
            
        self.speak(display_text)

    def handle_send(self):
        txt = self.input_field.text().strip()
        if not txt and not self.pending_image: return

        self.interrupt_event.set() 
        self.is_processing = False
        self.is_speaking = False
        self.anim_timer.stop()
        subprocess.run("pkill -9 -f paplay && pkill -9 -f sox", shell=True) 
        
        filtered_txt = filter_profanity(txt)
        self.is_processing, self.is_sleeping = True, False
        self.interrupt_event.clear()
        
        self.chat_display.append(f"<b>USER:</b> {filtered_txt}")
        self.input_field.clear()
        self.current_anim = itertools.cycle(THINKING_FRAMES); self.anim_timer.start(300)
        img = self.pending_image; self.pending_image = None
        threading.Thread(target=self.run_inference, args=(txt, img), daemon=True).start()

    def run_inference(self, prompt, image_path):
        try:
            start_time = time.time() 
            is_special = any(x in prompt.lower() for x in ["thanks", "love", "cute", "bravo"])
            search_keywords = ["search", "look up", "recipe", "how to", "protondb", "what is", "latest news"]
            needs_web = any(x in prompt.lower() for x in search_keywords)
            web_data = get_web_info(prompt) if needs_web else ""
            
            if self.interrupt_event.is_set(): return

            # --- System Context ---
            try:
                raw_data = self.sys_monitor.get_sensor_data()
                full_unit = "Celsius" if UNIT == "C" else "Fahrenheit"
                def clean(v): 
                    return v.replace(f"°{UNIT}", f" degrees {full_unit}") if v != "N/A" else "unknown"

                gpus_desc = " | ".join([f"{g['label']}: {clean(g['temp'])}" for g in raw_data['gpus']])
                vram_desc = f" | VRAM: {clean(raw_data['vram_list'][0])}" if raw_data['vram_list'] else ""
                sys_ctx = (f"[SYSTEM STATUS: RAM {get_system_health()['ram_usage']}% | "
                           f"CPU: {clean(raw_data['cpu'])} | {gpus_desc}{vram_desc}]")
            except Exception:
                sys_ctx = "[SYSTEM STATUS: Nominal]"

            now = datetime.now()
            time_ctx = f"[SYSTEM DATE/TIME: {now.strftime('%A, %B %d, %Y %H:%M')}]"
            
            # --- Chat Construction ---
            selected_model = VISION_MODEL if image_path else TEXT_MODEL
            permanent_core = get_hardcoded_memory()
            
            full_system_prompt = (
                f"{BMO_PROMPT}\n\n"
                f"{time_ctx}\n"
                f"{sys_ctx}\n"
                f"{web_data}\n\n"
                f"=== PERMANENT CORE MEMORY ===\n"
                f"{permanent_core}\n"
                f"=============================\n\n"
                f"[RECENT CHAT HISTORY]\n{self.memory_context}"
            )

            messages = [
                {'role': 'system', 'content': full_system_prompt},
                {'role': 'user', 'content': prompt}
            ]

            if image_path and os.path.exists(image_path):
                messages[1]['images'] = [os.path.abspath(image_path)]
            
            # Ollama Calling
            res = ollama.chat(
                model=selected_model,
                messages=messages,
                options={
                    "temperature": 0.4,
                    "num_ctx": 4096,
                    "num_thread": HW_PROFILE["threads"]
                }
            )
            
            if self.interrupt_event.is_set(): return
            
            response_text = res['message']['content'].strip()
            
            # Saving Memory and UI Update
            self.save_memory(f"User: {prompt}\nBMO: {response_text}")
            self.signals.response_ready.emit(response_text, is_special)
            
            print(f"[PERFORMANCE] Time: {time.time() - start_time:.2f}s")

        except Exception as e:
            if not self.interrupt_event.is_set():
                logger.error(f"Inference Error: {e}")
                traceback.print_exc()
                self.signals.response_ready.emit("My internet brain is fuzzy, sugarplum!", False)
        finally:
            if not self.interrupt_event.is_set():
                self.is_processing = False
                self.signals.update_face.emit(FACE_IDLE)

    def speak(self, text, loving=False):
        def _run():
            if self.interrupt_event.is_set(): return
            
            # 1. Professional Translation Filter
            # If the text contains translation headers, we only speak the intro
            # and stop before the non-English parts.
            translation_markers = ["Italian:", "French:", "Spanish:", "German:", "Russian:", "Japanese:", "Korean:", "Chinese:", "Vietnamese:"]
            
            speech_final = text
            for marker in translation_markers:
                if marker in speech_final:
                    # Keep only the part BEFORE the first translation marker
                    speech_final = speech_final.split(marker)[0]
            
            # If after filtering there's no English intro or only emojis/symbols, skip TTS
            clean_check = re.sub(r'[●◡ᗜ♥\-▬\s]+', '', speech_final)
            if not clean_check or len(clean_check) < 2:
                print("[BMO] Silence mode: Translation or empty text detected.")
                return

            # 2. Play Alert
            alerts = ["alert.wav", "alert2.wav", "alert3.wav"]
            alert_path = os.path.join(SFX_DIR, random.choice(alerts))
            if os.path.exists(alert_path):
                subprocess.run(["paplay", alert_path])
            
            self.is_speaking, self.is_loving = True, loving
            threading.Thread(target=self.animate_mouth, daemon=True).start()

            # 3. Final Cleaning for Piper
            speech_final = re.sub(r'\[.*?\]', '', speech_final)
            speech_final = re.sub(r'\(.*?\)', '', speech_final)
            speech_final = re.sub(r'[^\x00-\x7F]+', '', speech_final)
            speech_final = re.sub(r'[●◡ᗜ♥\-▬]+', '', speech_final)
            speech_final = re.sub(r'[*_#]', '', speech_final)
            speech_final = " ".join(speech_final.split())
            
            t_wav = f"/dev/shm/bmo_t_{random.randint(100,999)}.wav"
            p_wav = f"/dev/shm/bmo_v_{random.randint(100,999)}.wav"
            
            try:
                cmd_piper = f'echo "{speech_final}" | {PIPER_CMD} --model "{MODEL_PATH}" --length_scale 1.18 --output_file {t_wav}'
                subprocess.run(cmd_piper, shell=True, check=True)
                
                if self.interrupt_event.is_set(): return
                
                cmd_sox = f'sox {t_wav} {p_wav} pitch 250 overdrive 12 echo 0.9 0.88 5 0.4'
                subprocess.run(cmd_sox, shell=True, check=True)
                
                if self.interrupt_event.is_set(): return
                subprocess.run(['paplay', '--stream-name=BMO_VOICE', p_wav], check=True)

            except Exception as e:
                print(f"[AUDIO ERROR]: {e}")
            finally:
                for f in [t_wav, p_wav]:
                    if os.path.exists(f): os.remove(f)
                self.is_speaking = False
                self.reset_sleep_timer()
            
        threading.Thread(target=_run, daemon=True).start()

    def animate_mouth(self):
        while self.is_speaking and not self.interrupt_event.is_set():
            mouths = [MOUTH_D, MOUTH_E, MOUTH_F, FACE_HEARTS] if self.is_loving else [MOUTH_A, MOUTH_B, MOUTH_C, FACE_IDLE]
            self.signals.update_face.emit(random.choice(mouths)); time.sleep(0.14)

    def handle_response(self, text, is_special):
        """
        Main Thread Handler: Safely renders Markdown and updates UI.
        Prevents 'Timer started from another thread' crash.
        """
        if self.interrupt_event.is_set(): 
            return
        
        # Text insertion (Markdown or Plain Text)
        if MD_SUPPORT:
            try:
                html_body = markdown.markdown(text, extensions=['extra', 'nl2br'])
                full_html = f"<div style='margin-bottom:15px; color:#1E1E1E;'><b>BMO:</b><br>{html_body}</div>"
                self.chat_display.append("") # Adds a small spacer
                self.chat_display.insertHtml(full_html)
            except Exception:
                self.chat_display.append(f"<b>BMO:</b> {text}")
        else:
            self.chat_display.append(f"<b>BMO:</b> {text}")

        # UI Refresh Fix: Ensure these are outside the if/else blocks
        # to guarantee the display updates every time.
        self.chat_display.verticalScrollBar().setValue(self.chat_display.verticalScrollBar().maximum())
        self.chat_display.ensureCursorVisible()
        self.chat_display.repaint() # Force widget to redraw immediately
        
        # Trigger TTS
        self.speak(text, loving=is_special)

    def start_ptt_mouse(self):
        if not os.path.exists(TRIGGER_FILE):
            with open(TRIGGER_FILE, "w") as f: f.write("1")
            self.signals.update_face.emit(MOUTH_C)
            red_icon = os.path.join(ASSETS_DIR, "bmo_btn_03.png")
            if os.path.exists(red_icon): self.btn_send.setIcon(QIcon(red_icon))

    def stop_ptt_mouse(self):
        if os.path.exists(TRIGGER_FILE):
            os.remove(TRIGGER_FILE)
            if not self.is_processing: self.signals.update_face.emit(FACE_IDLE)
            green_icon = os.path.join(ASSETS_DIR, "bmo_play_btn_01.png")
            if os.path.exists(green_icon): self.btn_send.setIcon(QIcon(green_icon))

    def select_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "Image", "", "Images (*.png *.jpg *.jpeg)")
        if path: self.pending_image = path

    def perform_blink(self):
        if self.face_label.text() == FACE_IDLE and not (self.is_speaking or self.is_sleeping or self.is_processing):
            self.signals.update_face.emit(FACE_BLINK)
            QTimer.singleShot(400, lambda: self.signals.update_face.emit(FACE_IDLE) if not self.is_processing else None)

    def start_sleeping(self):
        if self.is_speaking or self.is_processing or self.is_sleeping: return
        self.is_sleeping = True; threading.Thread(target=self.animate_sleep, daemon=True).start()

    def animate_sleep(self):
        while self.is_sleeping and not (self.is_speaking or self.is_processing):
            for f in [FACE_SLEEP_A, FACE_SLEEP_B, FACE_SLEEP_C]:
                if not self.is_sleeping or self.interrupt_event.is_set(): break
                self.signals.update_face.emit(f); time.sleep(1.5)

    def reset_sleep_timer(self):
        self.is_sleeping = False; self.sleep_timer.start(300000)
        if not (self.is_processing or self.is_speaking): self.signals.update_face.emit(FACE_IDLE)

    def _update_anim_frame(self):
        if self.current_anim and self.is_processing: self.signals.update_face.emit(next(self.current_anim))

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Space and not self.input_field.hasFocus(): self.start_ptt_mouse()
        if event.key() == Qt.Key.Key_F11:
            if self.isFullScreen(): self.showNormal()
            else: self.showFullScreen()
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key.Key_Space: self.stop_ptt_mouse()
        super().keyReleaseEvent(event)

    def closeEvent(self, event):
        self.interrupt_event.set()
        
        subprocess.run("killall -9 piper sox paplay aplay ; pactl list short sink-inputs | cut -f1 | xargs -I{} pactl kill-sink-input {}", shell=True, stderr=subprocess.DEVNULL)
        
        exit_sfx = os.path.join(SFX_DIR, "shutdown.wav")
        if os.path.exists(exit_sfx): 
            subprocess.run(["paplay", exit_sfx])
            
        if os.path.exists(TRIGGER_FILE): 
            os.remove(TRIGGER_FILE)
            
        event.accept()
        os._exit(0)

    def setup_menus(self):
        from PyQt6.QtGui import QAction 
        self.menu_bar = self.menuBar()
        actions_menu = self.menu_bar.addMenu("&Actions")
        send_image_act = QAction("🖼 Send to BMO", self)
        send_image_act.setShortcut("Alt+S")
        send_image_act.triggered.connect(self.select_image) 
        actions_menu.addAction(send_image_act)
        
        about_menu = self.menu_bar.addMenu("&Help")
        about_act = QAction("About BMO OS", self)
        about_act.triggered.connect(self.show_custom_about)
        about_menu.addAction(about_act)

    def show_custom_about(self):
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel
        from PyQt6.QtGui import QPixmap
        
        dialog = QDialog(self)
        dialog.setWindowTitle("About BMO OS")
        dialog.setFixedSize(500, 500)
        dialog.setStyleSheet("background-color: #0d1117; color: white;")
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        icon = QLabel()
        # DYNAMIC PATH: Works for every user
        icon_pix = os.path.join(ASSETS_DIR, "bmo_icon.png")
        pixmap = QPixmap(icon_pix)
        if not pixmap.isNull():
            icon.setPixmap(pixmap.scaled(250, 250, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon)
        
        title = QLabel("BMO OS")
        title.setStyleSheet("font-size: 26px; font-weight: bold; margin-top: 15px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        version = QLabel("v.1.6.0 - Github")
        version.setStyleSheet("font-size: 14px; color: #888;")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version)
        
        author = QLabel()
        author.setText('by <a href="mailto:carlositaro@tiscali.it" style="color: #4CAF50; text-decoration: none;">Carlo Sitaro</a>')
        author.setOpenExternalLinks(True)
        author.setStyleSheet("font-size: 16px; margin-top: 40px;")
        author.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(author)
        
        dialog.setLayout(layout)
        dialog.exec()

if __name__ == "__main__":
    apply_hardware_config()
    app = QApplication(sys.argv)
    app.setApplicationName("BMO_OS")
    app.setApplicationDisplayName("BMO OS")
    app.setDesktopFileName("bmo") 
    window = BMOWindow()
    window.show()
    sys.exit(app.exec())
