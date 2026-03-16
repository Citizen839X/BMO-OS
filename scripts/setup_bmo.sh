#!/bin/bash

# Target directory in User Home
TARGET_DIR="$HOME/BMO"
SCRIPT_PATH=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)
CURRENT_PROJECT_ROOT=$(dirname "$SCRIPT_PATH")

echo "● ◡ ● Configuring BMO in $TARGET_DIR..."

# Move files to ~/BMO if executed from elsewhere
if [ "$CURRENT_PROJECT_ROOT" != "$TARGET_DIR" ]; then
    echo "[0/5] Relocating files to $TARGET_DIR..."
    mkdir -p "$TARGET_DIR"
    cp -af "$CURRENT_PROJECT_ROOT/." "$TARGET_DIR/"
fi

# Define paths for the launcher and binaries
PIPER_BIN="$TARGET_DIR/piper/piper"
MAIN_PY="$TARGET_DIR/src/bmo_final.py"
ICON_PATH="$TARGET_DIR/assets/bmo_icon.png"
DESKTOP_FILE="$HOME/.local/share/applications/bmo.desktop"

# [1/5] System dependencies
echo "[1/5] Installing system dependencies..."
sudo zypper in -y espeak-ng libasound2 pulseaudio-utils sox python311-PyQt6 python311-Pillow

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
Version=1.5.9
Type=Application
Name=BMO OS
Comment=Adventure time AI Assistant
Exec=python3 $MAIN_PY
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
echo "Version: 1.5.9 GitHub Fix"
echo "🚀 Search for 'BMO' or 'Adventure time' in your dashboard!"
echo "-------------------------------------------------------"
echo "⚠️  IMPORTANT: Remember to start Ollama before running BMO!"
echo "Run: 'ollama serve' in a separate terminal."
echo "-------------------------------------------------------"
