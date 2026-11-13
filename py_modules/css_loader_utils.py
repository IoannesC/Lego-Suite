import os
import json
import urllib.request
import socket
import base64

def get_theme_candidates() -> list:
    candidates = []
    # 1. Decky env var
    env_dir = os.environ.get("DECKY_PLUGIN_SETTINGS_DIR")
    if env_dir:
        # e.g. /home/deck/homebrew/settings/LeGO Suite -> /home/deck/homebrew/themes
        homebrew_root = os.path.abspath(os.path.join(env_dir, "..", ".."))
        candidates.append(os.path.join(homebrew_root, "themes", "Colored Toggles"))
    
    # 2. Standard system locations
    candidates.extend([
        os.path.expanduser("~/homebrew/themes/Colored Toggles"),
        os.path.expanduser("~/.local/share/Steam/steamui/themes/Colored Toggles"),
    ])
    return [c for c in candidates if c]

def get_installed_theme_dir() -> str:
    for path in get_theme_candidates():
        if os.path.isdir(path):
            return path
    return ""

def is_colored_toggles_installed() -> bool:
    return bool(get_installed_theme_dir())

def _send_ws_evaluate(ws_url: str, expression: str) -> bool:
    try:
        host, port_path = ws_url.replace("ws://", "").split(":", 1)
        port, path = port_path.split("/", 1)
        port = int(port)
        path = "/" + path

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.6)
        s.connect((host, port))

        sec_key = base64.b64encode(os.urandom(16)).decode('utf-8')
        handshake = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {host}:{port}\r\n"
            f"Upgrade: websocket\r\n"
            f"Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {sec_key}\r\n"
            f"Sec-WebSocket-Version: 13\r\n\r\n"
        )
        s.sendall(handshake.encode('utf-8'))
        resp = s.recv(1024)
        if b"101 " not in resp:
            s.close()
            return False

        msg = json.dumps({
            "id": 1,
            "method": "Runtime.evaluate",
            "params": {"expression": expression}
        })
        payload = msg.encode('utf-8')
        mask = os.urandom(4)
        frame = bytearray([0x81])
        length = len(payload)
        if length < 126:
            frame.append(0x80 | length)
        elif length < 65536:
            frame.append(0x80 | 126)
            frame.extend(length.to_bytes(2, 'big'))
        else:
            frame.append(0x80 | 127)
            frame.extend(length.to_bytes(8, 'big'))
        frame.extend(mask)
        masked_payload = bytearray(b ^ mask[i % 4] for i, b in enumerate(payload))
        frame.extend(masked_payload)
        s.sendall(frame)
        s.recv(1024)
        s.close()
        return True
    except Exception:
        try:
            s.close()
        except:
            pass
        return False

def sync_colored_toggles_color(hue: int) -> bool:
    """
    1. Writes to Colored Toggles config_USER.json for persistent state.
    2. Injects the style directly into all open Steam CEF tabs for INSTANT live rendering.
    """
    color_val = f"hsla({int(hue) % 360}, 100%, 50%, 1)"

    # 1. Persistent write across any found candidate folder
    for theme_dir in get_theme_candidates():
        if not os.path.isdir(theme_dir):
            continue
        config_path = os.path.join(theme_dir, "config_USER.json")
        try:
            data = {}
            if os.path.isfile(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    try:
                        data = json.load(f)
                    except Exception:
                        data = {}
            if not isinstance(data, dict):
                data = {}
            data["active"] = True
            if "Theme Color" not in data or not isinstance(data["Theme Color"], dict):
                data["Theme Color"] = {}
            data["Theme Color"]["value"] = "Custom"
            if "components" not in data["Theme Color"] or not isinstance(data["Theme Color"]["components"], dict):
                data["Theme Color"]["components"] = {}
            data["Theme Color"]["components"]["Main Color"] = color_val
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(data, f)
        except Exception:
            pass

    # 2. Instant live injection into Steam CEF (QuickAccess, MainMenu, SP)
    js_inject = f"""
    (function() {{
        let s = document.getElementById('lego-colored-toggles-live');
        if (!s) {{
            s = document.createElement('style');
            s.id = 'lego-colored-toggles-live';
            document.head.appendChild(s);
        }}
        s.textContent = `:root {{ --colored-toggles-main-color: {color_val} !important; --colored-toggles-static-color: {color_val} !important; --gpColor-Blue: {color_val} !important; }}`;
    }})();
    """
    try:
        req = urllib.request.urlopen("http://127.0.0.1:8080/json/list", timeout=0.8)
        tabs = json.loads(req.read().decode())
        for t in tabs:
            ws = t.get("webSocketDebuggerUrl")
            if ws:
                _send_ws_evaluate(ws, js_inject)
    except Exception:
        pass

    return True
