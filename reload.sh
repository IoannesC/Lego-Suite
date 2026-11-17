#!/bin/bash
set -e

PLUGIN_DIR="$HOME/homebrew/plugins/LeGO Suite"

echo "[1/4] Generando traducciones i18n..."
./scripts/build_i18n_json.sh
if [ -e "./i18n" ]; then
  echo "The ./i18n path exists."
else
  ln -s ./defaults/i18n ./i18n
fi

echo "[2/4] Compilando frontend (pnpm run build)..."
pnpm run build

echo "[3/4] Copiando plugin a $PLUGIN_DIR..."
sudo mkdir -p "$PLUGIN_DIR"
if command -v rsync >/dev/null 2>&1; then
  sudo rsync -a --delete \
    --exclude='node_modules' \
    --exclude='.git' \
    --exclude='.vscode' \
    --exclude='__pycache__' \
    --exclude='Gitsinc' \
    ./ "$PLUGIN_DIR/"
else
  sudo rm -rf "$PLUGIN_DIR"
  sudo mkdir -p "$PLUGIN_DIR"
  sudo tar --exclude='node_modules' --exclude='.git' --exclude='.vscode' --exclude='__pycache__' --exclude='Gitsinc' -cf - . | sudo tar -xf - -C "$PLUGIN_DIR"
fi

echo "[4/4] Reiniciando plugin_loader.service..."
sudo systemctl restart plugin_loader.service

echo "✅ Reload completado."
