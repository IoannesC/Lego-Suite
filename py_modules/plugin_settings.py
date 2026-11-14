import os
import json
from pathlib import Path
from collections import deque 

class SettingsManager:
    def __init__(self, name="settings", settings_directory=""):
        self.name = name
        self.settings_directory = str(settings_directory)
        self.filepath = Path(settings_directory) / f"{name}.json"
        self.settings = {}
        self.read()

    def read(self):
        try:
            if self.filepath.exists():
                with open(self.filepath, "r", encoding="utf-8") as f:
                    self.settings = json.load(f)
        except Exception:
            pass

    def setSetting(self, k, v):
        if k == 'tdpProfiles':
            return
        self.settings[k] = v
        self.commit()

    def commit(self):
        try:
            if 'tdpProfiles' in self.settings:
                del self.settings['tdpProfiles']
            self.filepath.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.filepath.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=4)
            os.replace(tmp, self.filepath)
        except Exception:
            pass

def _detect_settings_directory():
    env_dir = os.environ.get("DECKY_PLUGIN_SETTINGS_DIR")
    if env_dir:
        return env_dir
    candidates = [
        Path.home() / "homebrew" / "settings" / "LeGO Suite",
        Path.home() / "homebrew" / "settings" / "LeGO Suite",
        Path.home() / ".config" / "lego-suite",
    ]
    for c in candidates:
        if c.is_dir() or (c / "settings.json").exists():
            return str(c)
    fb = Path.home() / "homebrew" / "settings" / "LeGO Suite"
    return str(fb)

settings_directory = _detect_settings_directory()
settings_path = os.path.join(settings_directory, 'settings.json')
setting_file = SettingsManager(name="settings", settings_directory=settings_directory)
try:
    setting_file.read()
except Exception:
    pass

tdp_path = Path(settings_directory) / "tdp.json"
tdpac_path = Path(settings_directory) / "tdpac.json"
tdpegpu_path = Path(settings_directory) / "tdpegpu.json"

def _read_json_file(file_path: Path):
    try:
        if file_path.exists():
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
    except Exception:
        pass
    return {}

def _write_json_file(file_path: Path, data: dict):
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = file_path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        os.replace(tmp, file_path)
    except Exception:
        pass

def deep_merge(origin, destination):
    for k, v in origin.items():
        if isinstance(v, dict):
            n = destination.setdefault(k, {})
            deep_merge(v, n)
        else:
            destination[k] = v
    return destination

def get_saved_settings():
    setting_file.read()
    settings = setting_file.settings

    tdp_data = _read_json_file(tdp_path)
    tdpac_data = _read_json_file(tdpac_path)
    tdpegpu_data = _read_json_file(tdpegpu_path)

    merged_profiles = {}
    merged_profiles.update(tdp_data)
    merged_profiles.update(tdpac_data)
    merged_profiles.update(tdpegpu_data)

    settings['tdpProfiles'] = merged_profiles
    return settings

def set_setting(name: str, value):
    return setting_file.setSetting(name, value)

def merge_tdp_profiles(tdp_profiles):
    if not isinstance(tdp_profiles, dict):
        return

    tdp_data = _read_json_file(tdp_path)
    tdpac_data = _read_json_file(tdpac_path)
    tdpegpu_data = _read_json_file(tdpegpu_path)

    tdp_changed = False
    tdpac_changed = False
    tdpegpu_changed = False

    for k, v in tdp_profiles.items():
        if not isinstance(v, dict):
            continue
        if str(k).endswith('-egpu'):
            tdpegpu_data.setdefault(k, {})
            deep_merge(v, tdpegpu_data[k])
            tdpegpu_changed = True
        elif str(k).endswith('-ac-power'):
            tdpac_data.setdefault(k, {})
            deep_merge(v, tdpac_data[k])
            tdpac_changed = True
        else:
            tdp_data.setdefault(k, {})
            deep_merge(v, tdp_data[k])
            tdp_changed = True

    if tdp_changed:
        _write_json_file(tdp_path, tdp_data)
    if tdpac_changed:
        _write_json_file(tdpac_path, tdpac_data)
    if tdpegpu_changed:
        _write_json_file(tdpegpu_path, tdpegpu_data)

    if 'tdpProfiles' in setting_file.settings:
        del setting_file.settings['tdpProfiles']
        setting_file.commit()

def get_tdp_profile(gameId):
    key = str(gameId)
    if key.endswith('-egpu'):
        profiles = _read_json_file(tdpegpu_path)
        return profiles.get(key, {})
    elif key.endswith('-ac-power'):
        profiles = _read_json_file(tdpac_path)
        return profiles.get(key, {})
    else:
        profiles = _read_json_file(tdp_path)
        return profiles.get(key, {})

def bootstrap_profile(game_id):
    key = str(game_id)
    if key.endswith('-egpu'):
        profiles = _read_json_file(tdpegpu_path)
        default_profile = profiles.get('default-egpu')
        if not default_profile:
            base = _read_json_file(tdp_path)
            default_profile = base.get('default')
        if default_profile and not profiles.get(key):
            merge_tdp_profiles({key: default_profile})
    elif key.endswith('-ac-power'):
        profiles = _read_json_file(tdpac_path)
        default_profile = profiles.get('default-ac-power')
        if not default_profile:
            base = _read_json_file(tdp_path)
            default_profile = base.get('default')
        if default_profile and not profiles.get(key):
            merge_tdp_profiles({key: default_profile})
    else:
        profiles = _read_json_file(tdp_path)
        default_profile = profiles.get('default')
        if default_profile and not profiles.get(key):
            merge_tdp_profiles({key: default_profile})

def per_game_profiles_enabled():
    settings = get_saved_settings()
    return settings.get("enableTdpProfiles", False)

def get_active_tdp_profile(gameId):
    settings = get_saved_settings()

    if settings.get("enableTdpProfiles", False):
        advanced = settings.get("advanced", {})
        if advanced.get("egpuPowerProfiles", False):
            try:
                from py_modules import egpu_utils
                if egpu_utils.is_egpu_connected():
                    egpu_id = f"{gameId}-egpu"
                    prof = get_tdp_profile(egpu_id)
                    if prof:
                        return prof
                    prof_def = get_tdp_profile("default-egpu")
                    if prof_def:
                        return prof_def
            except Exception:
                pass

        return get_tdp_profile(gameId)
    else:
        advanced = settings.get("advanced", {})
        if advanced.get("egpuPowerProfiles", False):
            try:
                from py_modules import egpu_utils
                if egpu_utils.is_egpu_connected():
                    prof_def = get_tdp_profile("default-egpu")
                    if prof_def:
                        return prof_def
            except Exception:
                pass
        return get_tdp_profile('default')

def get_nested_setting(path):
    if not path:
        return None

    settings = get_saved_settings()
    pathValues = deque(path.split('.'))

    result = settings

    while len(pathValues) > 0 and result:
        result = result.get(pathValues.popleft())
  
    return result

def clear_game_profiles():
    try:
        if tdp_path.exists():
            tdp_path.unlink()
    except Exception:
        pass

    if 'tdpProfiles' in setting_file.settings:
        del setting_file.settings['tdpProfiles']
        setting_file.commit()
    return True

def clear_ac_profiles():
    try:
        if tdpac_path.exists():
            tdpac_path.unlink()
    except Exception:
        pass

    if 'tdpProfiles' in setting_file.settings:
        del setting_file.settings['tdpProfiles']
        setting_file.commit()
    return True

def clear_egpu_profiles():
    try:
        if tdpegpu_path.exists():
            tdpegpu_path.unlink()
    except Exception:
        pass

    if 'tdpProfiles' in setting_file.settings:
        del setting_file.settings['tdpProfiles']
        setting_file.commit()
    return True
