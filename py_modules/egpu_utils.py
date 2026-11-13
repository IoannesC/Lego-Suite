import os
import glob
import re
import subprocess

try:
    import decky_plugin
    _logger = decky_plugin.logger
except ImportError:
    import logging
    _logger = logging.getLogger("egpu_utils")

ALL_WAYS_EGPU_DIRS = [
    "/usr/share/all-ways-egpu",
    "/etc/all-ways-egpu",
    os.path.expanduser("~/.config/all-ways-egpu"),
]

def is_pci_device_alive(dev_dir):
    """
    Check if a PCI device in sysfs is actually responding and alive,
    not a disconnected ghost entry lingering before kernel bus cleanup.
    """
    try:
        if not os.path.isdir(dev_dir):
            return False
        config_path = os.path.join(dev_dir, "config")
        if not os.path.exists(config_path):
            return False
        with open(config_path, "rb") as f:
            data = f.read(4)
            if not data or len(data) < 4 or data == b"\xff\xff\xff\xff":
                return False
        return True
    except Exception:
        return False

def get_configured_egpu_bus_ids():
    """Retrieve bus IDs explicitly configured as eGPU in all-ways-egpu files."""
    bus_ids = set()
    for d in ALL_WAYS_EGPU_DIRS:
        egpu_file = os.path.join(d, "egpu-bus-ids")
        if os.path.exists(egpu_file):
            try:
                with open(egpu_file, "r") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            parts = line.split()
                            bus_ids.add(parts[0].lower())
            except Exception as e:
                _logger.error(f"egpu_utils: error reading {egpu_file}: {e}")
    return bus_ids

def get_configured_igpu_bus_ids():
    """Retrieve bus IDs configured as internal GPU in all-ways-egpu files."""
    bus_ids = set()
    for d in ALL_WAYS_EGPU_DIRS:
        user_file = os.path.join(d, "user-bus-ids")
        if os.path.exists(user_file):
            try:
                with open(user_file, "r") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            parts = line.split()
                            bus_ids.add(parts[0].lower())
            except Exception as e:
                _logger.error(f"egpu_utils: error reading {user_file}: {e}")
    return bus_ids

def get_pci_gpus():
    """Enumerate all active, responsive VGA, 3D, and Display controller PCI devices."""
    gpus = []
    display_classes = ("0x0300", "0x0301", "0x0302", "0x0380")
    for dev_dir in glob.glob("/sys/bus/pci/devices/*"):
        try:
            if not is_pci_device_alive(dev_dir):
                continue

            class_file = os.path.join(dev_dir, "class")
            if os.path.exists(class_file):
                with open(class_file, "r") as f:
                    cls = f.read().strip()
                if any(cls.startswith(dc) for dc in display_classes):
                    bus_id = os.path.basename(dev_dir).lower()
                    real_path = os.path.realpath(dev_dir)
                    boot_vga_file = os.path.join(dev_dir, "boot_vga")
                    boot_vga = 0
                    if os.path.exists(boot_vga_file):
                        try:
                            with open(boot_vga_file, "r") as f:
                                boot_vga = int(f.read().strip())
                        except Exception:
                            boot_vga = 0
                    gpus.append({
                        "bus_id": bus_id,
                        "path": real_path,
                        "boot_vga": boot_vga,
                        "dir": dev_dir
                    })
        except Exception:
            continue
    return gpus

def is_egpu_connected():
    """
    Check if an eGPU is currently connected and actively responding:
    1. Check configured egpu-bus-ids in sysfs and confirm they are alive
    2. Check all-ways-egpu bind-paths overrides
    3. Check active PCI display adapters
    4. Check Thunderbolt / USB4 connected GPUs
    5. Check multiple active DRM cards
    """
    try:
        configured_egpu_ids = get_configured_egpu_bus_ids()
        configured_igpu_ids = get_configured_igpu_bus_ids()

        for egpu_id in configured_egpu_ids:
            pci_path = f"/sys/bus/pci/devices/{egpu_id}"
            if is_pci_device_alive(pci_path):
                return True

        bind_paths_file = "/etc/all-ways-egpu/bind-paths"
        if os.path.exists(bind_paths_file):
            try:
                with open(bind_paths_file, "r") as f:
                    content = f.read().strip()
                    if content:
                        return True
            except Exception:
                pass

        pci_gpus = get_pci_gpus()

        for gpu in pci_gpus:
            if gpu["bus_id"] in configured_egpu_ids:
                return True

        if configured_igpu_ids:
            for gpu in pci_gpus:
                if gpu["bus_id"] not in configured_igpu_ids:
                    return True

        if len(pci_gpus) > 1:
            return True

        for gpu in pci_gpus:
            p = gpu["path"].lower()
            if any(key in p for key in ("thunderbolt", "usb4", "usb-")):
                return True

        alive_drm_cards = 0
        for c in glob.glob("/sys/class/drm/card[0-9]*"):
            if "-" not in os.path.basename(c):
                dev_link = os.path.join(c, "device")
                if os.path.exists(dev_link) and is_pci_device_alive(dev_link):
                    alive_drm_cards += 1
        if alive_drm_cards > 1:
            return True

    except Exception as e:
        _logger.error(f"egpu_utils: is_egpu_connected error {e}")

    return False

def get_egpu_model_name():
    """Detect the hardware model/name of the connected eGPU."""
    configured_egpu_ids = get_configured_egpu_bus_ids()
    configured_igpu_ids = get_configured_igpu_bus_ids()

    pci_gpus = get_pci_gpus()
    target_bus = None

    for gpu in pci_gpus:
        if gpu["bus_id"] in configured_egpu_ids:
            target_bus = gpu["bus_id"]
            break

    if not target_bus:
        for gpu in pci_gpus:
            p = gpu["path"].lower()
            if any(k in p for k in ("thunderbolt", "usb4", "usb-")):
                target_bus = gpu["bus_id"]
                break

    if not target_bus and configured_igpu_ids:
        for gpu in pci_gpus:
            if gpu["bus_id"] not in configured_igpu_ids:
                target_bus = gpu["bus_id"]
                break

    if not target_bus and len(pci_gpus) > 1:
        for gpu in pci_gpus:
            if gpu.get("boot_vga", 0) == 0:
                target_bus = gpu["bus_id"]
                break
        if not target_bus:
            target_bus = pci_gpus[-1]["bus_id"]

    if not target_bus and pci_gpus:
        target_bus = pci_gpus[0]["bus_id"]

    if target_bus:
        slot = target_bus
        if slot.startswith("0000:"):
            slot = slot[5:]
        try:
            out = subprocess.check_output(["lspci", "-s", slot], text=True, stderr=subprocess.DEVNULL).strip()
            cleaned = re.sub(r"^[0-9a-fA-F:\.]+\s+", "", out)
            cleaned = re.sub(r"^(VGA compatible controller|3D controller|Display controller):\s+", "", cleaned, flags=re.I)
            cleaned = re.sub(r"\(rev [0-9a-fA-F]+\)", "", cleaned).strip()
            brackets = re.findall(r"\[(.*?)\]", cleaned)
            if brackets:
                for b in reversed(brackets):
                    if any(k in b for k in ("Radeon", "GeForce", "RTX", "GTX", "Arc", "Intel", "AMD", "NVIDIA")):
                        return b
                return brackets[-1]
            if cleaned:
                return cleaned
        except Exception as e:
            _logger.error(f"egpu_utils: error querying lspci for {slot}: {e}")

    return "eGPU"

def get_egpu_status():
    """Returns detailed eGPU status for Decky UI and Desktop App."""
    connected = is_egpu_connected()
    name = get_egpu_model_name() if connected else None
    method = "all-ways-egpu / hardware" if connected else None
    return {
        "connected": connected,
        "name": name,
        "method": method
    }
