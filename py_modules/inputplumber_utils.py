import os
import re
import subprocess
import time
import json
import yaml

try:
    import decky_plugin
except ImportError:
    class _DummyDecky:
        class logger:
            @staticmethod
            def info(*args): print("[INFO]", *args)
            @staticmethod
            def error(*args): print("[ERROR]", *args)
            @staticmethod
            def warning(*args): print("[WARN]", *args)
            @staticmethod
            def debug(*args): pass
    decky_plugin = _DummyDecky()

STATE_FILE = f"/tmp/.inputplumber_{os.getuid()}.state"
ACTIVE_PROFILE_TMP = f"/tmp/legosuite_active_profile_{os.getuid()}.yaml"
DEFAULT_SYSTEM_PROFILE = "/usr/share/inputplumber/profiles/default.yaml"
PROFILES_DIR = os.path.join(os.path.dirname(__file__), "inputplumber_profiles")

_BUSCTL_DEST = "org.shadowblip.InputPlumber"
_BUSCTL_PATH_DEFAULT = "/org/shadowblip/InputPlumber/CompositeDevice0"
_BUSCTL_IFACE = "org.shadowblip.Input.CompositeDevice"

CONTROLLER_MODES = [
    {"data": "default", "label_es": "Por Defecto (Nativo Legion Go)", "label_en": "Default (Native Legion Go)"},
    {"data": "xbox-elite", "label_es": "Xbox Elite", "label_en": "Xbox Elite"},
    {"data": "xbox-series", "label_es": "Xbox Series X|S", "label_en": "Xbox Series X|S"},
    {"data": "ds5", "label_es": "PlayStation DualSense (PS5)", "label_en": "PlayStation DualSense (PS5)"},
    {"data": "ds5-edge", "label_es": "PlayStation DualSense Edge", "label_en": "PlayStation DualSense Edge"},
    {"data": "deck-uhid", "label_es": "Steam Deck (Virtual)", "label_en": "Steam Deck (Virtual)"},
    {"data": "hori-steam", "label_es": "Hori Steam Controller", "label_en": "Hori Steam Controller"},
    {"data": "8bitdo-u2", "label_es": "8BitDo Ultimate 2", "label_en": "8BitDo Ultimate 2"},
]

def _get_env():
    env = os.environ.copy()
    env["LD_LIBRARY_PATH"] = ""
    return env

def _get_settings_candidates() -> list:
    candidates = []
    env_dir = os.environ.get("DECKY_PLUGIN_SETTINGS_DIR")
    if env_dir:
        candidates.append(os.path.join(env_dir, "settings.json"))
    candidates.extend([
        os.path.expanduser("~/homebrew/settings/LeGO Suite/settings.json"),
        os.path.expanduser("~/homebrew/settings/LeGO-Suite/settings.json"),
        os.path.expanduser("~/.config/lego-suite/settings.json"),
        "/tmp/lego-suite-settings/settings.json"
    ])
    return candidates

def _read_setting(key: str, default=None):
    try:
        import plugin_settings
        saved = plugin_settings.get_saved_settings()
        if isinstance(saved, dict) and key in saved:
            return saved.get(key)
    except Exception:
        pass

    for path in _get_settings_candidates():
        try:
            if os.path.isfile(path):
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if key in data:
                        return data.get(key)
        except Exception:
            pass
    return default

def _write_setting(key: str, value) -> bool:
    success = False
    try:
        import plugin_settings
        plugin_settings.set_setting(key, value)
        success = True
    except Exception:
        pass

    candidates = _get_settings_candidates()
    written_any = False
    for path in candidates:
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                data[key] = value
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4)
                written_any = True
                success = True
            except Exception as e:
                decky_plugin.logger.error(f"Error updating setting in {path}: {e}")

    if not written_any and candidates:
        for primary in candidates:
            try:
                os.makedirs(os.path.dirname(primary), exist_ok=True)
                data = {}
                if os.path.isfile(primary):
                    try:
                        with open(primary, "r", encoding="utf-8") as f:
                            data = json.load(f)
                    except Exception:
                        pass
                data[key] = value
                with open(primary, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4)
                success = True
                break
            except Exception as e:
                decky_plugin.logger.warning(f"Could not write to candidate {primary}: {e}")
                continue

    return success

def is_service_active() -> bool:
    try:
        res = subprocess.run(["systemctl", "is-active", "inputplumber"], capture_output=True, text=True, check=False)
        return res.stdout.strip() == "active"
    except Exception:
        return False

def get_composite_device_paths() -> list:
    paths = []
    try:
        res = subprocess.run(
            ["busctl", "tree", _BUSCTL_DEST, "--no-pager"],
            capture_output=True, text=True, check=False, timeout=1.5, env=_get_env()
        )
        if res.returncode == 0:
            for line in res.stdout.splitlines():
                idx = line.find("/org/shadowblip/InputPlumber/CompositeDevice")
                if idx != -1:
                    clean_path = line[idx:].strip()
                    if clean_path and clean_path not in paths:
                        paths.append(clean_path)
    except Exception:
        pass
    if not paths:
        paths = [_BUSCTL_PATH_DEFAULT]
    return paths

def is_dbus_ready() -> bool:
    paths = get_composite_device_paths()
    path = paths[0] if paths else _BUSCTL_PATH_DEFAULT
    try:
        res = subprocess.run(
            ["busctl", "get-property", _BUSCTL_DEST, path, _BUSCTL_IFACE, "ProfileName"],
            capture_output=True, text=True, check=False, timeout=1.5, env=_get_env()
        )
        return res.returncode == 0
    except Exception:
        return False

def get_current_mode() -> str:
    mode = _read_setting("inputPlumberMode")
    if mode:
        return mode

    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                m = f.read().strip()
                if m:
                    return m
        except Exception:
            pass
    return "default"

def set_controller_mode(mode: str) -> bool:
    try:
        decky_plugin.logger.info(f"Setting InputPlumber controller mode: {mode}")
        _write_setting("inputPlumberMode", mode)

        target_gamepad = "xbox-elite" if mode == "default" else mode
        ok = False

        if os.path.isfile("/usr/bin/inputplumber"):
            try:
                paths = get_composite_device_paths()
                for idx in range(max(1, len(paths))):
                    res = subprocess.run(
                        ["/usr/bin/inputplumber", "device", str(idx), "targets", "set", target_gamepad, "mouse", "keyboard", "touchpad"],
                        capture_output=True, text=True, check=False, timeout=3.0, env=_get_env()
                    )
                    if res.returncode == 0:
                        ok = True
            except Exception as e:
                decky_plugin.logger.warning(f"CLI targets set note: {e}")

        if not ok:
            paths = get_composite_device_paths()
            args = f'4 "{target_gamepad}" mouse keyboard touchpad'
            for path in paths:
                cmd = f'busctl call {_BUSCTL_DEST} {path} {_BUSCTL_IFACE} SetTargetDevices "as" {args}'
                res = subprocess.run(cmd, shell=True, check=False, capture_output=True, text=True, env=_get_env())
                if res.returncode == 0:
                    ok = True
                else:
                    decky_plugin.logger.error(f"busctl error setting mode on {path}: {res.stderr}")

        if mode == "default":
            if os.path.exists(STATE_FILE):
                try:
                    os.remove(STATE_FILE)
                except Exception:
                    pass
        else:
            try:
                with open(STATE_FILE, "w") as f:
                    f.write(mode)
            except Exception:
                pass

        apply_active_profiles()
        return ok
    except Exception as e:
        decky_plugin.logger.error(f"Error set_controller_mode {mode}: {e}")
        return False

def load_preset_profiles() -> list:
    profiles = []
    if not os.path.isdir(PROFILES_DIR):
        return profiles
    for filename in sorted(os.listdir(PROFILES_DIR)):
        if not filename.endswith(".yaml"):
            continue
        p_id = filename.replace(".yaml", "")
        p_path = os.path.join(PROFILES_DIR, filename)
        try:
            with open(p_path, "r") as f:
                data = yaml.safe_load(f)
            name = data.get("name", p_id)
            desc = data.get("description", "")
            profiles.append({
                "id": p_id,
                "name": name,
                "name_es": data.get("name_es", name),
                "name_en": data.get("name_en", name),
                "description": desc,
                "description_es": data.get("description_es", desc),
                "description_en": data.get("description_en", desc),
                "isPreset": True,
            })
        except Exception as e:
            decky_plugin.logger.error(f"Failed loading profile {filename}: {e}")
    return profiles

def get_active_profiles() -> list:
    active = _read_setting("inputPlumberActiveProfiles")
    if isinstance(active, list):
        return active
    return []

def set_active_profiles(active_profile_ids: list) -> bool:
    profile_list = list(active_profile_ids) if active_profile_ids is not None else []
    decky_plugin.logger.info(f"Setting active profiles: {profile_list}")
    _write_setting("inputPlumberActiveProfiles", profile_list)
    return apply_active_profiles(profile_list)

def apply_active_profiles(active_profile_ids: list = None) -> bool:
    if active_profile_ids is None:
        active_profile_ids = get_active_profiles()

    decky_plugin.logger.info(f"Applying active profiles to InputPlumber: {active_profile_ids}")
    paths = get_composite_device_paths()

    if not active_profile_ids:
        default_path = DEFAULT_SYSTEM_PROFILE if os.path.isfile(DEFAULT_SYSTEM_PROFILE) else None
        overall_ok = False
        for path in paths:
            if default_path:
                try:
                    cmd = ["busctl", "call", _BUSCTL_DEST, path, _BUSCTL_IFACE, "LoadProfilePath", "s", default_path]
                    res = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=2.0, env=_get_env())
                    if res.returncode == 0:
                        decky_plugin.logger.info(f"Restored default profile on {path}")
                        overall_ok = True
                except Exception as e:
                    decky_plugin.logger.error(f"Error restoring default profile on {path}: {e}")

            if not overall_ok:
                try:
                    fallback_yaml = yaml.dump({
                        "version": 1,
                        "kind": "DeviceProfile",
                        "name": "Default",
                        "mapping": []
                    }, default_flow_style=False)
                    cmd = ["busctl", "call", _BUSCTL_DEST, path, _BUSCTL_IFACE, "LoadProfileFromYaml", "s", fallback_yaml]
                    res = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=2.0, env=_get_env())
                    if res.returncode == 0:
                        overall_ok = True
                except Exception:
                    pass

        if os.path.isfile("/usr/bin/inputplumber") and default_path:
            for idx in range(len(paths)):
                subprocess.run(["/usr/bin/inputplumber", "device", str(idx), "profile", "load", default_path],
                               capture_output=True, check=False, env=_get_env())

        return overall_ok

    all_mappings = []
    if os.path.isfile(DEFAULT_SYSTEM_PROFILE):
        try:
            with open(DEFAULT_SYSTEM_PROFILE, "r") as f:
                base_data = yaml.safe_load(f)
                if isinstance(base_data, dict) and "mapping" in base_data:
                    all_mappings.extend(base_data["mapping"])
        except Exception as e:
            decky_plugin.logger.warning(f"Could not read default profile base mappings: {e}")

    for pid in active_profile_ids:
        p_path = os.path.join(PROFILES_DIR, f"{pid}.yaml")
        if os.path.isfile(p_path):
            try:
                with open(p_path, "r") as f:
                    data = yaml.safe_load(f)
                if isinstance(data, dict) and "mapping" in data:
                    all_mappings.extend(data["mapping"])
            except Exception as e:
                decky_plugin.logger.error(f"Error reading profile {pid}: {e}")

    combined = {
        "version": 1,
        "kind": "DeviceProfile",
        "name": "LeGO Suite Active Profile",
        "mapping": all_mappings,
    }
    yaml_str = yaml.dump(combined, default_flow_style=False, sort_keys=False)

    try:
        with open(ACTIVE_PROFILE_TMP, "w", encoding="utf-8") as f:
            f.write(yaml_str)
    except Exception as e:
        decky_plugin.logger.error(f"Failed writing {ACTIVE_PROFILE_TMP}: {e}")

    overall_ok = False
    for path in paths:
        try:
            cmd = ["busctl", "call", _BUSCTL_DEST, path, _BUSCTL_IFACE, "LoadProfilePath", "s", ACTIVE_PROFILE_TMP]
            res = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=2.0, env=_get_env())
            if res.returncode == 0:
                decky_plugin.logger.info(f"Loaded profile via LoadProfilePath on {path}")
                overall_ok = True
                continue
        except Exception:
            pass

        try:
            cmd = ["busctl", "call", _BUSCTL_DEST, path, _BUSCTL_IFACE, "LoadProfileFromYaml", "s", yaml_str]
            res = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=2.0, env=_get_env())
            if res.returncode == 0:
                decky_plugin.logger.info(f"Loaded profile via LoadProfileFromYaml on {path}")
                overall_ok = True
            else:
                decky_plugin.logger.error(f"LoadProfileFromYaml failed on {path}: {res.stderr}")
        except Exception as e:
            decky_plugin.logger.error(f"Error calling LoadProfileFromYaml on {path}: {e}")

    if os.path.isfile("/usr/bin/inputplumber") and os.path.isfile(ACTIVE_PROFILE_TMP):
        for idx in range(len(paths)):
            subprocess.run(["/usr/bin/inputplumber", "device", str(idx), "profile", "load", ACTIVE_PROFILE_TMP],
                           capture_output=True, check=False, env=_get_env())

    return overall_ok

def get_inputplumber_info() -> dict:
    return {
        "serviceActive": is_service_active(),
        "dbusReady": is_dbus_ready(),
        "currentMode": get_current_mode(),
        "modes": CONTROLLER_MODES,
        "presetProfiles": load_preset_profiles(),
        "activeProfiles": get_active_profiles(),
    }
