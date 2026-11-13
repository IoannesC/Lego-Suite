import os
import subprocess
import decky_plugin

def find_backlight_dir():
    base = "/sys/class/backlight"
    if not os.path.exists(base):
        return None
    preferred = os.path.join(base, "amdgpu_bl1")
    if os.path.exists(preferred):
        return preferred
    for name in os.listdir(base):
        p = os.path.join(base, name)
        if os.path.exists(os.path.join(p, "brightness")):
            return p
    return None

def get_screen_brightness() -> int:
    bl_dir = find_backlight_dir()
    if not bl_dir:
        return 80
    try:
        with open(os.path.join(bl_dir, "brightness"), "r") as f:
            cur = int(f.read().strip())
        with open(os.path.join(bl_dir, "max_brightness"), "r") as f:
            mx = int(f.read().strip())
        if mx <= 0:
            return 80
        return max(1, min(100, int(round((cur / mx) * 100.0))))
    except Exception as e:
        decky_plugin.logger.error(f"get_screen_brightness error: {e}")
        return 80

def set_screen_brightness(pct: int) -> bool:
    pct = max(1, min(100, int(pct)))
    bl_dir = find_backlight_dir()
    if bl_dir:
        try:
            with open(os.path.join(bl_dir, "max_brightness"), "r") as f:
                mx = int(f.read().strip())
            target_val = max(1, min(mx, int(round((pct / 100.0) * mx))))
            with open(os.path.join(bl_dir, "brightness"), "w") as f:
                f.write(str(target_val))
            return True
        except Exception as e:
            decky_plugin.logger.error(f"set_screen_brightness error: {e}")
    return False

def set_screen_contrast(pct: int) -> bool:
    return True
