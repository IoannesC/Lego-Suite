#!/usr/bin/env bash
set -e

echo "Desinstalando el plugin LeGO Suite de Decky Loader..."
sudo rm -rf "$HOME/homebrew/plugins/LeGO Suite" "$HOME/homebrew/plugins/LeGO-Suite" "$HOME/homebrew/settings/LeGO-Suite"
sudo systemctl restart plugin_loader.service
echo "¡Plugin LeGO Suite desinstalado correctamente!"
