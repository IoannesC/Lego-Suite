#!/usr/bin/env bash
set -e

echo "Desinstalando LeGO Suite Desktop..."
rm -rf "$HOME/.local/share/lego-suite-desktop"
rm -f "$HOME/.local/share/applications/lego-suite-desktop.desktop"
rm -f "$HOME/.config/autostart/lego-suite-desktop.desktop"
rm -f "$HOME/Escritorio/LeGO Suite.desktop" "$HOME/Desktop/LeGO Suite.desktop"
echo "¡LeGO Suite Desktop desinstalado correctamente!"
