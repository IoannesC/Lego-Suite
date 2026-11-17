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
  if [ -f "$KWIN_RULES" ]; then
    cp -f "$KWIN_RULES" "${KWIN_RULES}.bak"
  fi
  /usr/bin/python3 - "$KWIN_RULES" << 'EOF'
import configparser
import os
import sys

path = sys.argv[1]
cfg = configparser.RawConfigParser(strict=False)
cfg.optionxform = str

if os.path.exists(path):
    cfg.read(path, encoding="utf-8")

if not cfg.has_section("General"):
    cfg.add_section("General")

rules_raw = cfg.get("General", "rules", fallback="").strip()
rules_list = [r.strip() for r in rules_raw.split(",") if r.strip()]

target_sec = None
for sec in cfg.sections():
    if sec == "General":
        continue
    if (
        cfg.get(sec, "wmclass", fallback="") == "lego-suite-desktop"
        or cfg.get(sec, "Description", fallback="") == "LeGO Suite Top Right"
    ):
        target_sec = sec
        break

if target_sec is None:
    idx = 1
    while str(idx) in cfg.sections() or str(idx) in rules_list:
        idx += 1
    target_sec = str(idx)
    cfg.add_section(target_sec)
    rules_list.append(target_sec)
elif target_sec not in rules_list:
    rules_list.append(target_sec)

cfg.set(target_sec, "Description", "LeGO Suite Top Right")
cfg.set(target_sec, "above", "true")
cfg.set(target_sec, "aboverule", "2")
cfg.set(target_sec, "noborder", "true")
cfg.set(target_sec, "noborderrule", "2")
cfg.set(target_sec, "wmclass", "lego-suite-desktop")
cfg.set(target_sec, "wmclassmatch", "1")

cfg.set("General", "rules", ",".join(rules_list))
cfg.set("General", "count", str(len(rules_list)))

with open(path, "w", encoding="utf-8") as f:
    cfg.write(f, space_around_delimiters=False)
EOF
  qdbus6 org.kde.KWin /KWin reconfigure 2>/dev/null || true
fi

echo "¡LeGO Suite Desktop instalado correctamente!"
