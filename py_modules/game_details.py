import json
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import decky_plugin
from plugin_settings import settings_directory

GAME_DETAILS_PATH = Path(settings_directory) / "gamedetails.json"
NON_STEAM_APPID_THRESHOLD = 2147483648  # 0x80000000


def _load_game_details() -> Dict[str, dict]:
    if not GAME_DETAILS_PATH.exists():
        return {}
    try:
        with open(GAME_DETAILS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception as e:
        decky_plugin.logger.error(f"game_details#_load_game_details error: {e}")
        return {}


def _save_game_details(data: Dict[str, dict]) -> None:
    try:
        GAME_DETAILS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(GAME_DETAILS_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        decky_plugin.logger.error(f"game_details#_save_game_details error: {e}")


def _get_steam_roots() -> List[Path]:
    home = Path.home()
    candidates = [
        home / ".local" / "share" / "Steam",
        home / ".steam" / "steam",
        home / ".steam" / "root",
    ]
    roots: List[Path] = []
    seen = set()
    for c in candidates:
        try:
            resolved = c.resolve()
            if resolved.is_dir() and str(resolved) not in seen:
                seen.add(str(resolved))
                roots.append(resolved)
        except Exception:
            continue
    return roots


def _get_steam_library_folders() -> List[Path]:
    libraries: List[Path] = []
    seen = set()
    for root in _get_steam_roots():
        steamapps = root / "steamapps"
        if steamapps.is_dir() and str(root) not in seen:
            seen.add(str(root))
            libraries.append(root)

        vdf_path = steamapps / "libraryfolders.vdf"
        if vdf_path.is_file():
            try:
                content = vdf_path.read_text(encoding="utf-8", errors="ignore")
                for match in re.finditer(r'"path"\s+"([^"]+)"', content):
                    lib_path = Path(match.group(1).replace("\\\\", "/"))
                    if lib_path.is_dir() and str(lib_path) not in seen:
                        seen.add(str(lib_path))
                        libraries.append(lib_path)
            except Exception:
                continue
    return libraries


def _find_steam_install_dir(game_id: str) -> Optional[str]:
    for lib in _get_steam_library_folders():
        manifest = lib / "steamapps" / f"appmanifest_{game_id}.acf"
        if manifest.is_file():
            try:
                content = manifest.read_text(encoding="utf-8", errors="ignore")
                match = re.search(r'"installdir"\s+"([^"]+)"', content)
                if match:
                    install_path = lib / "steamapps" / "common" / match.group(1)
                    return str(install_path)
            except Exception:
                return str(lib / "steamapps" / "common")
    return None


def _find_proc_game_path(game_id: str) -> Optional[str]:
    """Inspect /proc for a running process matching SteamAppId or SteamGameId."""
    target_app = f"SteamAppId={game_id}".encode()
    target_game = f"SteamGameId={game_id}".encode()

    try:
        pids = [p for p in os.listdir("/proc") if p.isdigit()]
    except Exception:
        return None

    fallback_cwd: Optional[str] = None
    for pid in pids:
        proc_dir = Path("/proc") / pid
        try:
            environ = (proc_dir / "environ").read_bytes()
        except Exception:
            continue

        if target_app not in environ and target_game not in environ:
            continue

        # Check cmdline for a concrete executable (.exe or binary path)
        try:
            raw_cmd = (proc_dir / "cmdline").read_bytes()
            args = [a.decode("utf-8", errors="ignore") for a in raw_cmd.split(b"\x00") if a]
            for arg in args:
                if arg.lower().endswith(".exe") and ("/" in arg or "\\" in arg):
                    return arg
        except Exception:
            pass

        # Check /proc/<pid>/exe if it's not a generic wrapper/wine binary
        try:
            exe = os.readlink(proc_dir / "exe")
            exe_name = os.path.basename(exe).lower()
            if exe_name not in {
                "reaper",
                "steam-launch-wrapper",
                "pressure-vessel-wrap",
                "pv-adverb",
                "wine64-preloader",
                "wine-preloader",
                "wineserver",
                "python3",
                "bash",
                "sh",
            }:
                return exe
        except Exception:
            pass

        if fallback_cwd is None:
            try:
                fallback_cwd = os.readlink(proc_dir / "cwd")
            except Exception:
                pass

    return fallback_cwd


def _detect_is_steam_and_path(game_id: str) -> Tuple[bool, str]:
    steam_install_dir = _find_steam_install_dir(game_id)
    if steam_install_dir is not None:
        is_steam = True
    else:
        try:
            is_steam = int(game_id) < NON_STEAM_APPID_THRESHOLD
        except ValueError:
            is_steam = False

    proc_path = _find_proc_game_path(game_id)
    path = proc_path or steam_install_dir or ""
    return is_steam, path


def record_game_details(game_id: str, title: str) -> dict:
    """Detect and persist game title, Steam/Non-Steam status, and execution path."""
    if not game_id or game_id == "default" or game_id.startswith("default-"):
        return {}

    clean_id = game_id.removesuffix("-ac-power").removesuffix("-egpu")
    is_steam, path = _detect_is_steam_and_path(clean_id)

    details = _load_game_details()
    existing = details.get(clean_id, {})

    final_title = title if title and title != "default" else existing.get("title", "")
    final_path = path or existing.get("path", "")

    entry = {
        "title": final_title,
        "isSteam": is_steam,
        "path": final_path,
    }

    if existing != entry:
        details[clean_id] = entry
        _save_game_details(details)

    return entry
