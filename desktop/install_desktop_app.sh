#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TARGET_DIR="$HOME/.local/share/lego-suite-desktop"

echo "Instalando LeGO Suite Desktop en $TARGET_DIR..."
rm -rf "$TARGET_DIR"
mkdir -p "$TARGET_DIR"
cp -r "$PROJECT_ROOT/desktop" "$PROJECT_ROOT/py_modules" "$PROJECT_ROOT/bin" "$PROJECT_ROOT/assets" "$PROJECT_ROOT/main.py" "$PROJECT_ROOT/plugin.json" "$TARGET_DIR/"
chmod +x "$TARGET_DIR/desktop/lego_suite_desktop.py"
chmod +x "$TARGET_DIR/bin/ryzenadj" 2>/dev/null || true

mkdir -p "$HOME/.local/share/applications"
cat > "$HOME/.local/share/applications/lego-suite-desktop.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=LeGO Suite
Comment=Control de TDP, Ventilación, Batería y Mandos para Legion Go
Exec=env QT_QPA_PLATFORM=xcb /usr/bin/python3 "$TARGET_DIR/desktop/lego_suite_desktop.py"
Icon=$TARGET_DIR/assets/logo.jpg
Terminal=false
Categories=Utility;HardwareSettings;
StartupNotify=false
EOF
chmod +x "$HOME/.local/share/applications/lego-suite-desktop.desktop"

mkdir -p "$HOME/.config/autostart"
cat > "$HOME/.config/autostart/lego-suite-desktop.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=LeGO Suite Tray
Comment=LeGO Suite en bandeja del sistema
Exec=env QT_QPA_PLATFORM=xcb /usr/bin/python3 "$TARGET_DIR/desktop/lego_suite_desktop.py" --tray
Icon=$TARGET_DIR/assets/logo.jpg
Terminal=false
Categories=Utility;HardwareSettings;
StartupNotify=false
EOF

for DESK_DIR in "$HOME/Escritorio" "$HOME/Desktop"; do
  if [ -d "$DESK_DIR" ]; then
    cp -f "$HOME/.local/share/applications/lego-suite-desktop.desktop" "$DESK_DIR/LeGO Suite.desktop"
    chmod +x "$DESK_DIR/LeGO Suite.desktop"
  fi
done

KWIN_RULES="$HOME/.config/kwinrulesrc"
if [ -f "$KWIN_RULES" ] || [ -d "$HOME/.config" ]; then
  cat > "$KWIN_RULES" << 'EOF'
[General]
count=1
rules=1

[1]
Description=LeGO Suite Top Right
above=true
aboverule=2
noborder=true
noborderrule=2
wmclass=lego-suite-desktop
wmclassmatch=1
EOF
  qdbus6 org.kde.KWin /KWin reconfigure 2>/dev/null || true
fi

echo "¡LeGO Suite Desktop instalado correctamente!"
