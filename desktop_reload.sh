 #!/bin/bash

pnpm run build
sudo rm -rf "$HOME/.unofficial_homebrew/plugins/SimpleDeckyTDP/"
sudo cp -r "$HOME/Development/SimpleDeckyTDP/" ~/.unofficial_homebrew/plugins/
sudo systemctl restart unofficial_plugin_loader.service
