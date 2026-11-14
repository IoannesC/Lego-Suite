#!/bin/bash

./scripts/build_i18n_json.sh
if [ -e "./i18n" ]; then
  echo "./i18n already exists."
else
  ln -s ./defaults/i18n ./i18n
fi
pnpm run build
sudo rm -rf "$HOME/homebrew/plugins/LeGO Suite/"
sudo cp -r "$(pwd)" "$HOME/homebrew/plugins/LeGO Suite"
sudo systemctl restart plugin_loader.service
