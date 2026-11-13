#!/usr/bin/bash

if [ "$EUID" -eq 0 ]
  then echo "Please do not run as root"
  exit
fi

if [ ! -f "/etc/udev/rules.d/90-legion-go-remapper.rules" ]; then
cat << EOF | sudo tee -a "/etc/udev/rules.d/90-legion-go-remapper.rules"
SUBSYSTEMS=="usb", ATTRS{idVendor}=="17ef", TAG+="uaccess"
SUBSYSTEMS=="usb", ATTRS{idVendor}=="17ef", MODE="0666"
EOF
fi

echo "udev rules configured for Legion Go controllers."
