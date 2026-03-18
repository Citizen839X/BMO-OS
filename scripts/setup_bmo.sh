#!/bin/bash

# Target directory in User Home
TARGET_DIR="$HOME/BMO"
SCRIPT_PATH=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)
CURRENT_PROJECT_ROOT=$(dirname "$SCRIPT_PATH")

echo "● ◡ ● Configuring BMO in $TARGET_DIR..."

# [0/5] Relocating files & Directory structure
if [ "$CURRENT_PROJECT_ROOT" != "$TARGET_DIR" ]; then
    echo "[0/5] Relocating files to $TARGET_DIR..."
    # Create the modules directory for tool-use implementation
    mkdir -p "$TARGET_DIR/src/modules"
    cp -af "$CURRENT_PROJECT_ROOT/." "$TARGET_DIR/"
    # Ensure the directory is treated as a Python package
    touch "$TARGET_DIR/src/modules/__init__.py"
fi

# Define paths for the launcher and binaries
PIPER_BIN="$TARGET_DIR/piper/piper"
MAIN_PY="$TARGET_DIR/src/bmo_final.py"
ICON_PATH="$TARGET_DIR/assets/bmo_icon.png"
DESKTOP_FILE="$HOME/.local/share/applications/bmo.desktop"

# [1/5] System dependencies (Universal Detection)
echo "[1/5] Detecting OS and installing system dependencies..."

if [ -f /etc/os-release ]; then
    . /etc/os-release
    # Check both ID and ID_LIKE to support derivatives
    case "$ID" in
        opensuse*|suse)
            # Added python311-psutil for system monitoring
            sudo zypper in -y espeak-ng libasound2 pulseaudio-utils sox python311-PyQt6 python311-Pillow python311-psutil
            ;;
        fedora|rhel)
            sudo dnf install -y espeak-ng alsa-lib pulseaudio-utils sox python3-pyqt6 python3-pillow python3-psutil
            ;;
        ubuntu|debian|pop|mint)
            sudo apt-get update && sudo apt-get install -y espeak-ng libasound2 pulseaudio-utils sox python3-pyqt6 python3-pil python3-psutil
            ;;
        arch|manjaro)
            sudo pacman -S --noconfirm espeak-ng alsa-lib libpulse sox python-pyqt6 python-pillow python-psutil
            ;;
        *)
            # Fallback check for ID_LIKE field
            if [[ "$ID_LIKE" == *"suse"* ]]; then
                sudo zypper in -y espeak-ng libasound2 pulseaudio-utils sox python311-PyQt6 python311-Pillow python311-psutil
            elif [[ "$ID_LIKE" == *"debian"* ]]; then
                sudo apt-get update && sudo apt-get install -y espeak-ng libasound2 pulseaudio-utils sox python3-pyqt6 python3-pil python3-psutil
            elif [[ "$ID_LIKE" == *"arch"* ]]; then
                sudo pacman -S --noconfirm espeak-ng alsa-lib libpulse sox python-pyqt6 python-pillow python-psutil
            else
                echo "⚠️ OS not recognized. Attempting generic install..."
                sudo zypper in -y espeak-ng libasound2 pulseaudio-utils sox python311-PyQt6 python311-Pillow python311-psutil
            fi
            ;;
    esac
else
    echo "❌ Error: Cannot detect OS. Please install dependencies manually."
fi

# [2/5] Piper execution rights
echo "[2/5] Setting permissions for Piper..."
if [ -f "$PIPER_BIN" ]; then
    chmod +x "$PIPER_BIN"
    echo "  > Piper OK!"
else
    echo "  > ❌ Error: Piper binary missing in $TARGET_DIR/piper/"
fi

# [3/5] Desktop Entry creation
echo "[3/5] Generating .desktop file..."
cat <<EOF > $DESKTOP_FILE
[Desktop Entry]
Version=1.6.0
Type=Application
Name=BMO OS
Comment=Adventure time AI Assistant with System Awareness
Exec=bash -c 'cd $TARGET_DIR && python3 $MAIN_PY'
Icon=$ICON_PATH
Terminal=false
Categories=Utility;AI;
StartupWMClass=BMO_OS
EOF

# [4/5] Desktop integration
echo "[4/5] Updating desktop database..."
chmod +x $DESKTOP_FILE
update-desktop-database ~/.local/share/applications/ 2>/dev/null

# [5/5] Final Service Check & Completion
echo "[5/5] Finalizing installation..."
echo "-------------------------------------------------------"
echo "✅ BMO Setup Complete in $TARGET_DIR"
echo "Version: 1.6.0 - GitHub"
echo "🚀 Search for 'BMO' or 'Adventure time' in your dashboard!"
echo "-------------------------------------------------------"
echo "⚠️  IMPORTANT: Remember to start Ollama before running BMO!"
echo "Run: 'ollama serve' in a separate terminal."
echo "-------------------------------------------------------"
