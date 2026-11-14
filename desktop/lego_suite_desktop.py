#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LeGO Suite Desktop (v0.198)
Aplicación de Modo Escritorio con icono en la bandeja del sistema (System Tray)
sincronizada en tiempo real con el plugin LeGO Suite de Decky Loader.
"""

import os
import sys

if "QT_QPA_PLATFORM" not in os.environ and "WAYLAND_DISPLAY" in os.environ:
    os.environ["QT_QPA_PLATFORM"] = "xcb"

import json
import math
import time
import socket
import asyncio
import colorsys
from pathlib import Path

from PyQt6.QtCore import (
    QProcess,
    Qt,
    QTimer,
    QRect,
    QRectF,
    QPoint,
    QPointF,
    QPropertyAnimation,
    QEasingCurve,
    QEvent,
    QThread,
    pyqtSignal,
)
from PyQt6.QtGui import (
    QIcon,
    QPixmap,
    QPainter,
    QColor,
    QBrush,
    QConicalGradient,
    QRadialGradient,
    QPainterPath,
    QAction,
)
from PyQt6.QtWidgets import (
    QMessageBox,
    QApplication,
    QMainWindow,
    QDialog,
    QColorDialog,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QCheckBox,
    QComboBox,
    QScrollArea,
    QFrame,
    QSystemTrayIcon,
    QMenu,
    QStackedWidget,
    QGridLayout,
)


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
if not (PROJECT_ROOT / "py_modules").exists() and (SCRIPT_DIR / "py_modules").exists():
    PROJECT_ROOT = SCRIPT_DIR

ASSETS_DIR = PROJECT_ROOT / "assets"
LOGO_ICON_PATH = ASSETS_DIR / "logo.jpg"
LOGO_UI_PATH = ASSETS_DIR / "logo_ui.png"
STICK_PATH = ASSETS_DIR / "stick.png"

RPC_HOST = "127.0.0.1"
RPC_PORT = 47392
SINGLE_INSTANCE_PORT = 47393

DEFAULT_BG_COLOR = "#0e1015"
DEFAULT_CONTENT_COLOR = "#181b24"
DEFAULT_CONTENT_COLOR_2 = "#1e2433"
DEFAULT_ACCENT_COLOR = "#3b82f6"
HWDB_SENSOR_FILE = Path("/etc/udev/hwdb.d/61-sensor-local.hwdb")
HWDB_SENSOR_CONTENT = "sensor:modalias:platform:HID-SENSOR-200073*\n ACCEL_MOUNT_MATRIX=1, 0, 0; 0, 1, 0; 0, 0, 1\n"


def find_settings_dir() -> Path:
    env_dir = os.environ.get("DECKY_PLUGIN_SETTINGS_DIR")
    if env_dir:
        p = Path(env_dir)
        if p.exists() or p.parent.exists():
            return p

    candidates = [
        Path.home() / "homebrew" / "settings" / "LeGO Suite",
        Path.home() / ".config" / "lego-suite",
    ]
    for c in candidates:
        if (c / "settings.json").exists():
            return c
    for c in candidates:
        if c.parent.exists():
            try:
                c.mkdir(parents=True, exist_ok=True)
                return c
            except Exception:
                pass
    fallback = Path.home() / ".config" / "lego-suite"
    try:
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback
    except OSError:
        tmp_fb = Path("/tmp/lego-suite-settings")
        tmp_fb.mkdir(parents=True, exist_ok=True)
        return tmp_fb


SETTINGS_DIR = find_settings_dir()
SETTINGS_FILE = SETTINGS_DIR / "settings.json"
TDP_FILE = SETTINGS_DIR / "tdp.json"



class _DummyLogger:
    def info(self, *a, **kw):
        pass

    def error(self, *a, **kw):
        pass

    def warning(self, *a, **kw):
        pass

    def debug(self, *a, **kw):
        pass


class _DeckyPluginShim:
    DECKY_PLUGIN_DIR = str(PROJECT_ROOT)
    DECKY_PLUGIN_SETTINGS_DIR = str(SETTINGS_DIR)
    DECKY_USER_HOME = str(Path.home())
    logger = _DummyLogger()


class _SettingsManagerShim:
    def __init__(self, name="settings", settings_directory=None):
        self.dir = Path(settings_directory or SETTINGS_DIR)
        self.path = self.dir / f"{name}.json"
        self.settings = {}
        self.read()

    def read(self):
        try:
            if self.path.exists():
                with open(self.path, "r", encoding="utf-8") as f:
                    self.settings = json.load(f)
        except Exception:
            if not isinstance(self.settings, dict):
                self.settings = {}

    def commit(self):
        try:
            self.dir.mkdir(parents=True, exist_ok=True)
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=2)
        except Exception:
            pass

    def getSetting(self, key, default=None):
        self.read()
        return self.settings.get(key, default)

    def setSetting(self, key, value):
        self.read()
        self.settings[key] = value
        self.commit()
        return value



class BackendClient:
    def __init__(self):
        self.rpc_available = False
        self._local_plugin = None
        self._loop = asyncio.new_event_loop()

    def _init_local_fallback(self):
        if self._local_plugin is not None:
            return
        os.environ.setdefault("DECKY_PLUGIN_DIR", str(PROJECT_ROOT))
        os.environ.setdefault("DECKY_PLUGIN_SETTINGS_DIR", str(SETTINGS_DIR))
        os.environ.setdefault("DECKY_USER_HOME", str(Path.home()))
        if "decky_plugin" not in sys.modules:
            sys.modules["decky_plugin"] = _DeckyPluginShim()
        if "settings" not in sys.modules:
            import types
            mod = types.ModuleType("settings")
            mod.SettingsManager = _SettingsManagerShim
            sys.modules["settings"] = mod
        py_mod_dir = str(PROJECT_ROOT / "py_modules")
        if py_mod_dir not in sys.path:
            sys.path.insert(0, py_mod_dir)
        if str(PROJECT_ROOT) not in sys.path:
            sys.path.insert(0, str(PROJECT_ROOT))
        try:
            import main as plugin_main
            self._local_plugin = plugin_main.Plugin()
        except Exception as e:
            print(f"[LeGO Suite Desktop] Local fallback init warning: {e}")

    def call(self, method: str, *args, **kwargs):
        try:
            with socket.create_connection((RPC_HOST, RPC_PORT), timeout=1.2) as sock:
                payload = json.dumps({"method": method, "args": list(args), "kwargs": kwargs}) + "\n"
                sock.sendall(payload.encode("utf-8"))
                buf = b""
                while not buf.endswith(b"\n"):
                    chunk = sock.recv(65536)
                    if not chunk:
                        break
                    buf += chunk
                if buf:
                    resp = json.loads(buf.decode("utf-8"))
                    self.rpc_available = True
                    if resp.get("ok"):
                        return resp.get("result")
        except Exception:
            self.rpc_available = False

        self._init_local_fallback()
        if self._local_plugin and hasattr(self._local_plugin, method):
            try:
                fn = getattr(self._local_plugin, method)
                return self._loop.run_until_complete(fn(*args, **kwargs))
            except Exception as e:
                print(f"[LeGO Suite Desktop] Direct call {method} error: {e}")
        return None



def _lighten_hex(hex_color: str, factor: float = 1.25) -> str:
    c = QColor(hex_color)
    if not c.isValid():
        c = QColor(DEFAULT_CONTENT_COLOR)
    r = min(255, int(c.red() * factor + 14))
    g = min(255, int(c.green() * factor + 14))
    b = min(255, int(c.blue() * factor + 14))
    return f"#{r:02x}{g:02x}{b:02x}"


def build_dynamic_stylesheet(bg_color: str, content_color: str, accent_color: str = DEFAULT_ACCENT_COLOR, content_color_2: str = "") -> str:
    bg = bg_color if QColor(bg_color).isValid() else DEFAULT_BG_COLOR
    card = content_color if QColor(content_color).isValid() else DEFAULT_CONTENT_COLOR
    card1 = card
    card2 = content_color_2 if (content_color_2 and QColor(content_color_2).isValid()) else _lighten_hex(card1, 1.15)
    accent = accent_color if QColor(accent_color).isValid() else DEFAULT_ACCENT_COLOR
    border = _lighten_hex(card1, 1.35)
    ctrl_bg = _lighten_hex(card1, 1.22)
    ctrl_hover = _lighten_hex(card1, 1.45)
    accent_border = _lighten_hex(accent, 1.2)

    return f"""
QMainWindow {{
    background-color: transparent;
}}
QWidget#RootWidget {{
    background-color: transparent;
}}
QFrame#WindowFrame {{
    background-color: {bg};
    border: 1.5px solid {border};
    border-radius: 18px;
}}
QDialog {{
    background-color: {bg};
    color: #f3f4f6;
    font-family: "Noto Sans", "Inter", "Segoe UI", sans-serif;
    font-size: 13px;
    border: 1.5px solid {border};
    border-radius: 14px;
}}
QScrollArea {{
    background-color: transparent;
    border: none;
}}
QScrollBar:vertical {{
    background: rgba(255, 255, 255, 0.04);
    width: 22px;
    margin: 4px 2px 4px 2px;
    border-radius: 8px;
}}
QScrollBar::handle:vertical {{
    background: {accent};
    min-height: 48px;
    border-radius: 8px;
    border: 2px solid rgba(255, 255, 255, 0.2);
}}
QScrollBar::handle:vertical:hover, QScrollBar::handle:vertical:pressed {{
    background: {accent_border};
    border-color: #ffffff;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
    background: none;
}}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: none;
}}
QWidget#ScrollContent {{
    background-color: transparent;
}}
QFrame.SectionCard {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {card1}, stop:1 {card2});
    border: 1px solid {border};
    border-radius: 10px;
}}
QLabel.SectionTitle {{
    color: #9ca3af;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}}
QLabel.RowLabel {{
    color: #e5e7eb;
    font-size: 13px;
    font-weight: 500;
}}
QLabel.ValueBadge {{
    color: #ffffff;
    font-size: 13px;
    font-weight: 700;
}}
QPushButton.TabBtn {{
    background-color: {card};
    color: #9ca3af;
    border: 1px solid {border};
    border-bottom: 2px solid transparent;
    border-radius: 6px;
    padding: 8px 8px;
    font-weight: 600;
    font-size: 13px;
}}
QPushButton.TabBtn:hover {{
    background-color: {ctrl_hover};
}}
QPushButton.TabBtn[active="true"] {{
    background-color: {ctrl_hover};
    color: #ffffff;
    border-bottom: 2px solid {accent};
    font-weight: 700;
}}
QPushButton.GearBtn {{
    background-color: {card};
    color: #d1d5db;
    border: 1px solid {border};
    border-radius: 14px;
    font-size: 15px;
    font-weight: 700;
}}
QPushButton.GearBtn:hover {{
    background-color: {ctrl_hover};
    color: #ffffff;
}}
QPushButton.WindowCtrlBtn {{
    background-color: {card};
    color: #9ca3af;
    border: 1px solid {border};
    border-radius: 14px;
    font-size: 12px;
    font-weight: 700;
}}
QPushButton.WindowCtrlBtn:hover {{
    background-color: {ctrl_hover};
    color: #ffffff;
}}
QPushButton.WindowCtrlBtn#BtnClose:hover {{
    background-color: #ef4444;
    color: #ffffff;
    border-color: #f87171;
}}
QPushButton.DockBtn {{
    background-color: {card};
    color: #f3f4f6;
    border: 1px solid {border};
    border-radius: 10px;
    font-size: 24px;
    font-weight: 800;
    padding-bottom: 2px;
}}
QPushButton.DockBtn:hover {{
    background-color: {ctrl_hover};
    color: #ffffff;
    border-color: {accent_border};
}}
QPushButton.DockBtn:pressed {{
    background-color: {accent};
    color: #ffffff;
}}
QFrame#DockHandle {{
    background-color: {card};
    border: 1.5px solid {border};
    border-right: none;
    border-top-left-radius: 14px;
    border-bottom-left-radius: 14px;
}}
QFrame#DockHandle:hover {{
    background-color: {ctrl_hover};
    border-color: {accent_border};
}}
QPushButton.ActionBtn {{
    background-color: {ctrl_bg};
    color: #f3f4f6;
    border: 1px solid {border};
    border-radius: 6px;
    padding: 6px 10px;
    font-weight: 600;
}}
QPushButton.ActionBtn:hover {{
    background-color: {ctrl_hover};
}}
QComboBox {{
    background-color: {ctrl_bg};
    color: #f3f4f6;
    border: 1px solid {border};
    border-radius: 6px;
    padding: 4px 8px;
    min-width: 130px;
}}
QComboBox::drop-down {{
    border: none;
}}
QComboBox QAbstractItemView {{
    background-color: {card};
    color: #f3f4f6;
    selection-background-color: {ctrl_hover};
}}
QCheckBox {{
    color: #e5e7eb;
    font-weight: 500;
    spacing: 8px;
}}
QCheckBox::indicator {{
    width: 36px;
    height: 20px;
    border-radius: 10px;
    background-color: {ctrl_bg};
    border: 1px solid {border};
}}
QCheckBox::indicator:checked {{
    background-color: {accent};
    border: 1px solid {accent_border};
}}
QSlider::groove:horizontal {{
    height: 14px;
    background: {ctrl_bg};
    border-radius: 7px;
}}
QSlider::sub-page:horizontal {{
    background: {accent};
    border-radius: 7px;
}}
QSlider::handle:horizontal {{
    background: #ffffff;
    border: 3px solid {accent};
    width: 28px;
    height: 28px;
    margin: -7px 0;
    border-radius: 14px;
}}
QSlider#HueSlider::groove:horizontal {{
    height: 16px;
    border-radius: 8px;
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0.00 hsl(0, 100%, 50%),
        stop:0.17 hsl(60, 100%, 50%),
        stop:0.33 hsl(120, 100%, 50%),
        stop:0.50 hsl(180, 100%, 50%),
        stop:0.67 hsl(240, 100%, 50%),
        stop:0.83 hsl(300, 100%, 50%),
        stop:1.00 hsl(359, 100%, 50%)
    );
}}
QCheckBox:disabled {{
    color: #6b7280;
}}
QCheckBox::indicator:disabled {{
    background-color: rgba(255, 255, 255, 0.04);
    border-color: rgba(255, 255, 255, 0.08);
}}
QLabel:disabled {{
    color: #6b7280;
}}
QPushButton:disabled {{
    color: #6b7280;
    background-color: rgba(255, 255, 255, 0.03);
    border-color: rgba(255, 255, 255, 0.08);
}}
QComboBox:disabled {{
    color: #6b7280;
    background-color: rgba(255, 255, 255, 0.03);
    border-color: rgba(255, 255, 255, 0.08);
}}
QSlider:disabled {{
    opacity: 0.35;
}}
QSlider::sub-page:horizontal:disabled {{
    background: #4b5563;
}}
QSlider::handle:horizontal:disabled {{
    background: #6b7280;
    border-color: #4b5563;
}}
"""



THEME_PRESETS = [
    ("theme_preset_0", "#0e1015", "#181b24", "#1e2433"),
    ("theme_preset_1", "#000000", "#121216", "#1a1a24"),
    ("theme_preset_2", "#091326", "#132342", "#1b345f"),
    ("theme_preset_3", "#1c0b10", "#2e141d", "#421a28"),
    ("theme_preset_4", "#081c15", "#123026", "#184234"),
    ("theme_preset_5", "#1c1e24", "#2a2e39", "#383e4d"),
]



TEXTS = {
    "es": {
        "tab_tdp": "TDP",
        "tab_controls": "Controles",
        "tab_screen": "Pantalla",
        "card_tdp_mode": "Modo Térmico",
        "mode_quiet": "Silencioso",
        "mode_balanced": "Balanceado",
        "mode_performance": "Rendimiento",
        "mode_custom": "Personalizado",
        "card_tdp": "TDP & Rendimiento",
        "lbl_tdp": "TDP (Potencia Térmica de Diseño)",
        "card_cpu": "Control de CPU",
        "chk_cpu_boost": "Activar CPU Boost",
        "chk_smt": "Activar SMT (Multithreading)",
        "lbl_governor": "Gobernador de Energía CPU",
        "lbl_epp": "Preferencia de Energía (EPP)",
        "card_bat": "Batería y Energía",
        "chk_charge_limit": "Activar Límite de Carga (80%)",
        "lbl_charge_val": "Límite de Carga",
        "card_monitor": "Monitoreo Térmico y Ventilador",
        "card_fan": "Curvas de Ventilación",
        "chk_fan_enabled": "Activar Curvas de Ventilación Personalizadas",
        "chk_full_fan": "Velocidad Máxima",
        "chk_fan_profile": "Activar Perfil de Ventilador",
        "card_range": "Rango de TDP",
        "lbl_min_tdp": "TDP Mínimo",
        "lbl_max_tdp": "TDP Máximo",
        "card_rgb": "Iluminación del Mando (RGB)",
        "chk_power_led": "Activar LED del Botón de Encendido",
        "chk_rgb_control": "Activar Control RGB de Legion Go",
        "chk_controller_led": "LED de Mandos",
        "lbl_rgb_mode": "Modo de Iluminación",
        "lbl_rgb_brightness": "Brillo de Luces RGB",
        "lbl_rgb_speed": "Velocidad de Efecto RGB",
        "chk_sync_slider_color": "Elegir color Slider/Ticks",
        "card_remap": "Reasignación de Botones Traseros",
        "chk_remap_enabled": "Activar Reasignación de Mandos",
        "lbl_rumble_intensity": "Intensidad de Vibración",
        "rumble_off": "Desactivada",
        "rumble_low": "Baja",
        "rumble_medium": "Media",
        "rumble_high": "Alta",
        "chk_touchpad": "Touchpad Derecho",
        "chk_guide_shortcut": "Abrir/Cerrar LeGO Suite con botón Guía / Select",
        "btn_y1": "Botón Trasero Y1",
        "btn_y2": "Botón Trasero Y2",
        "btn_y3": "Botón Trasero Y3",
        "btn_m2": "Botón Trasero M2",
        "btn_m3": "Botón Trasero M3",
        "remap_disabled": "Desactivado",
        "remap_lb": "Botón Superior Izq (LB)",
        "remap_lt": "Gatillo Izquierdo (LT)",
        "remap_rb": "Botón Superior Der (RB)",
        "remap_rt": "Gatillo Derecho (RT)",
        "remap_l3": "Pulsar Stick Izq (L3)",
        "remap_r3": "Pulsar Stick Der (R3)",
        "remap_dpad_up": "Cruceta Arriba",
        "remap_dpad_down": "Cruceta Abajo",
        "remap_dpad_left": "Cruceta Izquierda",
        "remap_dpad_right": "Cruceta Derecha",
        "remap_view": "Vista / Select",
        "remap_menu": "Menú / Start",
        "card_disp": "Pantalla: Brillo y Contraste",
        "lbl_screen_brightness": "Brillo de la Pantalla",
        "lbl_screen_contrast": "Contraste de la Pantalla",
        "card_sensor": "Rotación y Sensor de Orientación",
        "lbl_hwdb_status_title": "Estado del archivo hwdb:",
        "lbl_hwdb_desc": "Inyecta la matriz del acelerómetro en /etc/udev/hwdb.d/61-sensor-local.hwdb para calibrar el sensor.",
        "btn_inject_hwdb": "Reinstalar / Calibrar Sensor (Sudo)",
        "btn_inject_hwdb_clean": "Inyectar Sensor (Sudo)",
        "lbl_auto_rotate_hint": "Activa la rotación automática en configuración de pantalla",
        "card_als": "Sensor de Luz Ambiente (ALS)",
        "chk_als": "Activar Brillo Automático (Experimental)",
        "lbl_als_sens": "Sensibilidad",
        "lbl_als_poll": "Intervalo de Sondeo (ms)",
        "lbl_als_smooth": "Suavizado de Transición (s)",
        "lbl_als_offset": "Ajuste de Brillo",
        "sensor_ok": "✓ Sensor configurado",
        "sensor_missing": "✗ No configurado",
        "settings_title": "Ajustes de Interfaz - LeGO Suite",
        "theme_custom_title": "Personalizar UI y Colores",
        "lbl_language": "Idioma:",
        "lbl_bg_color": "Color de Fondo:",
        "lbl_ct_color": "Color Primario Tarjetas:",
        "lbl_ct2_color": "Color Secundario Tarjetas:",
        "lbl_ac_color": "Color Sliders / Ticks:",
        "lbl_quick_themes": "Temas Rápidos:",
        "btn_reset": "Restaurar defecto",
        "btn_accept": "Aceptar",
        "btn_color_pick_bg": "Color de Fondo",
        "btn_color_pick_ct": "Color Primario de Tarjetas",
        "btn_color_pick_ct2": "Color Secundario de Tarjetas",
        "btn_color_pick_ac": "Color de Sliders y Ticks",
        "theme_preset_0": "Oscuro Original",
        "theme_preset_1": "Negro OLED",
        "theme_preset_2": "Azul Legion",
        "theme_preset_3": "Rojo Carmesí",
        "theme_preset_4": "Verde Esmeralda",
        "theme_preset_5": "Gris Grafito",
        "saved_badge": "Guardado",
        "status_decky_rpc": "Decky RPC Activo",
        "status_local_sync": "Sincronizado (Local)",
        "status_sync": "Sincronizado",
        "btn_ip_submenu": "Configuración de Input Plumber",
        "btn_ip_back": "Volver a Controles",
        "lbl_ip_title": "Input Plumber",
        "lbl_ip_desc": "Modo de mando, emulación y perfiles de mapeo",
        "lbl_ip_status_active": "Servicio Activo / D-Bus",
        "lbl_ip_status_standby": "Inactivo / Standby",
        "lbl_ip_mode": "Objetivo de emulación",
        "lbl_ip_profiles": "Perfiles de Mapeo Rápido",
        "chk_ip_swap_menu": "Intercambiar Botones de Menú\n(Select/Guide y Start/QuickAccess)",
        "chk_ip_swap_vol": "Intercambiar Botones de Volumen\n(Invertir + / -)",
        "btn_reset_controllers": "Resetear Mandos",
        "lbl_reset_controllers_desc": "Reinicio USB y valores de fábrica (HHD). Atajo físico: Izq: Legion L + LB + LS | Der: Legion R + RB + RS",
        "msg_reset_controllers_success": "Mandos reseteados correctamente",
        "chk_dock_mode": "Barra lateral replegable al borde",
        "chk_dock_mode_desc": "Muestra un botón en la cabecera para replegar la ventana en una pestaña lateral y desplegarla al tocarla.",
        "btn_dock_collapse": "Replegar al borde derecho",
        "btn_dock_expand": "Desplegar panel",
        "btn_minimize": "Minimizar",
        "btn_close": "Cerrar",
        "gear_tooltip": "Cambiar colores e idioma de la UI",
        "tray_tooltip": "LeGO Suite v0.198 • TDP: {tdp}W • Carga: {charge}%"
    },
    "en": {
        "tab_tdp": "TDP",
        "tab_controls": "Controls",
        "tab_screen": "Screen",
        "card_tdp_mode": "Thermal Mode",
        "mode_quiet": "Quiet",
        "mode_balanced": "Balanced",
        "mode_performance": "Performance",
        "mode_custom": "Custom",
        "card_tdp": "TDP & Performance",
        "lbl_tdp": "TDP (Thermal Design Power)",
        "card_cpu": "CPU Controls",
        "chk_cpu_boost": "Enable CPU Boost",
        "chk_smt": "Enable SMT (Multithreading)",
        "lbl_governor": "CPU Power Governor",
        "lbl_epp": "Energy Preference (EPP)",
        "card_bat": "Battery & Power",
        "chk_charge_limit": "Enable Charge Limit (80%)",
        "lbl_charge_val": "Charge Limit",
        "card_monitor": "Thermal & Fan Monitor",
        "card_fan": "Fan Curves",
        "chk_fan_enabled": "Enable Custom Fan Curves",
        "chk_full_fan": "Full Speed",
        "chk_fan_profile": "Enable Fan Profile",
        "card_range": "TDP Range",
        "lbl_min_tdp": "Minimum TDP",
        "lbl_max_tdp": "Maximum TDP",
        "card_rgb": "Controller Lighting (RGB)",
        "chk_power_led": "Enable Power Button LED",
        "chk_rgb_control": "Enable Legion Go RGB Control",
        "chk_controller_led": "Controller LED",
        "lbl_rgb_mode": "Lighting Mode",
        "lbl_rgb_brightness": "RGB Brightness",
        "lbl_rgb_speed": "RGB Speed",
        "chk_sync_slider_color": "Custom Slider/Ticks Color",
        "card_remap": "Remap Back Buttons",
        "chk_remap_enabled": "Enable Controller Remapping",
        "lbl_rumble_intensity": "Vibration Intensity",
        "rumble_off": "Off",
        "rumble_low": "Low",
        "rumble_medium": "Medium",
        "rumble_high": "High",
        "chk_touchpad": "Right Touchpad",
        "chk_guide_shortcut": "Open/Close LeGO Suite with Guide / Select button",
        "btn_y1": "Back Button Y1",
        "btn_y2": "Back Button Y2",
        "btn_y3": "Back Button Y3",
        "btn_m2": "Back Button M2",
        "btn_m3": "Back Button M3",
        "remap_disabled": "Disabled",
        "remap_lb": "Left Bumper (LB)",
        "remap_lt": "Left Trigger (LT)",
        "remap_rb": "Right Bumper (RB)",
        "remap_rt": "Right Trigger (RT)",
        "remap_l3": "Left Stick Click (L3)",
        "remap_r3": "Right Stick Click (R3)",
        "remap_dpad_up": "D-Pad Up",
        "remap_dpad_down": "D-Pad Down",
        "remap_dpad_left": "D-Pad Left",
        "remap_dpad_right": "D-Pad Right",
        "remap_view": "View / Select",
        "remap_menu": "Menu / Start",
        "card_disp": "Display: Brightness & Contrast",
        "lbl_screen_brightness": "Screen Brightness",
        "lbl_screen_contrast": "Screen Contrast",
        "card_sensor": "Orientation & Auto-Rotation Sensor",
        "lbl_hwdb_status_title": "hwdb file status:",
        "lbl_hwdb_desc": "Injects the accelerometer mount matrix into /etc/udev/hwdb.d/61-sensor-local.hwdb to calibrate the sensor.",
        "btn_inject_hwdb": "Reinstall / Calibrate Sensor (Sudo)",
        "btn_inject_hwdb_clean": "Inject Sensor (Sudo)",
        "lbl_auto_rotate_hint": "Enable automatic rotation in display settings",
        "card_als": "Ambient Light Sensor (ALS)",
        "chk_als": "Enable Auto Brightness (Experimental)",
        "lbl_als_sens": "Sensitivity",
        "lbl_als_poll": "Poll Rate (ms)",
        "lbl_als_smooth": "Smooth Time (s)",
        "lbl_als_offset": "Brightness Offset",
        "sensor_ok": "✓ Sensor configured",
        "sensor_missing": "✗ Not configured",
        "settings_title": "Interface Settings - LeGO Suite",
        "theme_custom_title": "UI & Colors Customization",
        "lbl_language": "Language:",
        "lbl_bg_color": "Background Color:",
        "lbl_ct_color": "Primary Card Color:",
        "lbl_ct2_color": "Secondary Card Color:",
        "lbl_ac_color": "Sliders / Ticks Color:",
        "lbl_quick_themes": "Quick Themes:",
        "btn_reset": "Reset Default",
        "btn_accept": "Accept",
        "btn_color_pick_bg": "Background Color",
        "btn_color_pick_ct": "Primary Card Color",
        "btn_color_pick_ct2": "Secondary Card Color",
        "btn_color_pick_ac": "Sliders and Ticks Color",
        "theme_preset_0": "Original Dark",
        "theme_preset_1": "OLED Black",
        "theme_preset_2": "Legion Blue",
        "theme_preset_3": "Crimson Red",
        "theme_preset_4": "Emerald Green",
        "theme_preset_5": "Graphite Gray",
        "saved_badge": "Saved",
        "status_decky_rpc": "Decky RPC Active",
        "status_local_sync": "Synchronized (Local)",
        "status_sync": "Synchronized",
        "btn_ip_submenu": "Input Plumber Settings",
        "btn_ip_back": "Back to Controls",
        "lbl_ip_title": "Input Plumber",
        "lbl_ip_desc": "Controller target mode, emulation & mapping profiles",
        "lbl_ip_status_active": "Service Active / D-Bus",
        "lbl_ip_status_standby": "Inactive / Standby",
        "lbl_ip_mode": "Target Emulation",
        "lbl_ip_profiles": "Quick Mapping Profiles",
        "chk_ip_swap_menu": "Swap Menu Buttons\n(Select/Guide & Start/QuickAccess)",
        "chk_ip_swap_vol": "Swap Volume Buttons\n(Invert + / -)",
        "btn_reset_controllers": "Reset Controllers",
        "lbl_reset_controllers_desc": "USB reset & factory defaults (HHD). Hardware combo: Left: Legion L + LB + LS | Right: Legion R + RB + RS",
        "msg_reset_controllers_success": "Controllers reset successfully",
        "chk_dock_mode": "Collapsible sidebar edge tab",
        "chk_dock_mode_desc": "Adds a header button to collapse the window into a side tab and slide open when touched.",
        "btn_dock_collapse": "Collapse to right edge",
        "btn_dock_expand": "Expand panel",
        "btn_minimize": "Minimize",
        "btn_close": "Close",
        "gear_tooltip": "Change UI colors and language",
        "tray_tooltip": "LeGO Suite v0.198 • TDP: {tdp}W • Charge: {charge}%"
    }
}
def tr(key: str, lang: str = "es") -> str:
    dic = TEXTS.get(lang) or TEXTS["es"]
    return dic.get(key) or TEXTS["es"].get(key, key)


class ThemeSettingsDialog(QDialog):
    def __init__(self, parent, bg_color: str, content_color: str, accent_color: str, current_lang: str, on_apply_callback, dock_mode: bool = True, content_color_2: str = ""):
        super().__init__(parent)
        self.bg_color = bg_color
        self.content_color = content_color
        self.content_color_2 = content_color_2 or _lighten_hex(content_color, 1.15)
        self.accent_color = accent_color or DEFAULT_ACCENT_COLOR
        self.current_lang = current_lang or "es"
        self.dock_mode = bool(dock_mode)
        self.on_apply = on_apply_callback

        self.setWindowTitle(tr("settings_title", self.current_lang))
        self.setFixedSize(410, 520)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(11)

        self.title_lbl = QLabel(tr("theme_custom_title", self.current_lang))
        self.title_lbl.setStyleSheet("font-size: 15px; font-weight: 700; color: #ffffff;")
        layout.addWidget(self.title_lbl)

        lang_row = QHBoxLayout()
        self.lbl_lang = QLabel(tr("lbl_language", self.current_lang))
        self.lbl_lang.setStyleSheet("color: #e5e7eb; font-weight: 600; font-size: 13px;")
        self.cmb_lang = QComboBox()
        self.cmb_lang.addItem("Español", "es")
        self.cmb_lang.addItem("English", "en")
        idx = self.cmb_lang.findData(self.current_lang)
        if idx >= 0:
            self.cmb_lang.setCurrentIndex(idx)
        self.cmb_lang.currentIndexChanged.connect(self._on_lang_changed)
        lang_row.addWidget(self.lbl_lang)
        lang_row.addStretch()
        lang_row.addWidget(self.cmb_lang)
        layout.addLayout(lang_row)

        dock_box = QVBoxLayout()
        dock_box.setSpacing(2)
        self.chk_dock_mode = QCheckBox(tr("chk_dock_mode", self.current_lang))
        self.chk_dock_mode.setChecked(self.dock_mode)
        self.chk_dock_mode.setStyleSheet("color: #e5e7eb; font-weight: 600; font-size: 13px;")
        self.chk_dock_mode.toggled.connect(self._on_dock_mode_toggled)
        dock_box.addWidget(self.chk_dock_mode)

        self.lbl_dock_desc = QLabel(tr("chk_dock_mode_desc", self.current_lang))
        self.lbl_dock_desc.setStyleSheet("color: #9ca3af; font-size: 11px; margin-left: 22px;")
        self.lbl_dock_desc.setWordWrap(True)
        dock_box.addWidget(self.lbl_dock_desc)
        layout.addLayout(dock_box)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: rgba(255, 255, 255, 0.15);")
        layout.addWidget(sep)

        bg_row = QHBoxLayout()
        self.lbl_bg = QLabel(tr("lbl_bg_color", self.current_lang))
        self.btn_pick_bg = QPushButton(self.bg_color)
        self.btn_pick_bg.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_pick_bg.clicked.connect(self._pick_bg_color)
        bg_row.addWidget(self.lbl_bg)
        bg_row.addStretch()
        bg_row.addWidget(self.btn_pick_bg)
        layout.addLayout(bg_row)

        ct_row = QHBoxLayout()
        self.lbl_ct = QLabel(tr("lbl_ct_color", self.current_lang))
        self.btn_pick_ct = QPushButton(self.content_color)
        self.btn_pick_ct.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_pick_ct.clicked.connect(self._pick_content_color)
        ct_row.addWidget(self.lbl_ct)
        ct_row.addStretch()
        ct_row.addWidget(self.btn_pick_ct)
        layout.addLayout(ct_row)

        ct2_row = QHBoxLayout()
        self.lbl_ct2 = QLabel(tr("lbl_ct2_color", self.current_lang))
        self.btn_pick_ct2 = QPushButton(self.content_color_2)
        self.btn_pick_ct2.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_pick_ct2.clicked.connect(self._pick_content_color_2)
        ct2_row.addWidget(self.lbl_ct2)
        ct2_row.addStretch()
        ct2_row.addWidget(self.btn_pick_ct2)
        layout.addLayout(ct2_row)

        ac_row = QHBoxLayout()
        self.lbl_ac = QLabel(tr("lbl_ac_color", self.current_lang))
        self.btn_pick_ac = QPushButton(self.accent_color)
        self.btn_pick_ac.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_pick_ac.clicked.connect(self._pick_accent_color)
        ac_row.addWidget(self.lbl_ac)
        ac_row.addStretch()
        ac_row.addWidget(self.btn_pick_ac)
        layout.addLayout(ac_row)

        self.lbl_pre = QLabel(tr("lbl_quick_themes", self.current_lang))
        self.lbl_pre.setStyleSheet("color: #9ca3af; font-size: 11px; font-weight: 700; text-transform: uppercase;")
        layout.addWidget(self.lbl_pre)

        grid = QGridLayout()
        grid.setSpacing(6)
        self.theme_preset_btns = []
        for i, (key, p_bg, p_ct, p_ct2) in enumerate(THEME_PRESETS):
            btn = QPushButton(tr(key, self.current_lang))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(
                f"background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {p_ct}, stop:1 {p_ct2}); "
                f"color: #ffffff; border: 1px solid {_lighten_hex(p_ct, 1.4)}; "
                f"border-radius: 6px; padding: 6px; font-size: 12px; font-weight: 600;"
            )
            btn.clicked.connect(lambda checked=False, b=p_bg, c=p_ct, c2=p_ct2: self._set_colors(b, c, self.accent_color, c2))
            grid.addWidget(btn, i // 2, i % 2)
            self.theme_preset_btns.append((btn, key))
        layout.addLayout(grid)

        layout.addStretch()

        bot_row = QHBoxLayout()
        self.btn_reset = QPushButton(tr("btn_reset", self.current_lang))
        self.btn_reset.setProperty("class", "ActionBtn")
        self.btn_reset.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_reset.clicked.connect(
            lambda: self._set_colors(DEFAULT_BG_COLOR, DEFAULT_CONTENT_COLOR, DEFAULT_ACCENT_COLOR, DEFAULT_CONTENT_COLOR_2)
        )

        self.btn_accept = QPushButton(tr("btn_accept", self.current_lang))
        self.btn_accept.setProperty("class", "ActionBtn")
        self.btn_accept.setStyleSheet("font-weight: 700; padding: 6px 20px;")
        self.btn_accept.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_accept.clicked.connect(self._on_accept_clicked)

        bot_row.addWidget(self.btn_reset)
        bot_row.addStretch()
        bot_row.addWidget(self.btn_accept)
        layout.addLayout(bot_row)

        self._update_swatch_buttons()

    def _on_dock_mode_toggled(self, checked: bool):
        self.dock_mode = bool(checked)
        self.on_apply(self.bg_color, self.content_color, self.accent_color, self.current_lang, self.dock_mode, self.content_color_2)

    def _on_accept_clicked(self):
        self.dock_mode = self.chk_dock_mode.isChecked()
        self.on_apply(self.bg_color, self.content_color, self.accent_color, self.current_lang, self.dock_mode, self.content_color_2)
        self.accept()

    def _update_swatch_buttons(self):
        self.btn_pick_bg.setText(self.bg_color.upper())
        self.btn_pick_bg.setStyleSheet(
            f"background-color: {self.bg_color}; color: #ffffff; border: 1px solid #6b7280; "
            f"border-radius: 6px; padding: 4px 10px; font-weight: 700;"
        )
        self.btn_pick_ct.setText(self.content_color.upper())
        self.btn_pick_ct.setStyleSheet(
            f"background-color: {self.content_color}; color: #ffffff; border: 1px solid #6b7280; "
            f"border-radius: 6px; padding: 4px 10px; font-weight: 700;"
        )
        self.btn_pick_ct2.setText(self.content_color_2.upper())
        self.btn_pick_ct2.setStyleSheet(
            f"background-color: {self.content_color_2}; color: #ffffff; border: 1px solid #6b7280; "
            f"border-radius: 6px; padding: 4px 10px; font-weight: 700;"
        )
        self.btn_pick_ac.setText(self.accent_color.upper())
        self.btn_pick_ac.setStyleSheet(
            f"background-color: {self.accent_color}; color: #ffffff; border: 1px solid #6b7280; "
            f"border-radius: 6px; padding: 4px 10px; font-weight: 700;"
        )

    def _pick_bg_color(self):
        c = QColorDialog.getColor(QColor(self.bg_color), self, tr("btn_color_pick_bg", self.current_lang))
        if c.isValid():
            self._set_colors(c.name(), self.content_color, self.accent_color, self.content_color_2)

    def _pick_content_color(self):
        c = QColorDialog.getColor(QColor(self.content_color), self, tr("btn_color_pick_ct", self.current_lang))
        if c.isValid():
            self._set_colors(self.bg_color, c.name(), self.accent_color, self.content_color_2)

    def _pick_content_color_2(self):
        c = QColorDialog.getColor(QColor(self.content_color_2), self, tr("btn_color_pick_ct2", self.current_lang))
        if c.isValid():
            self._set_colors(self.bg_color, self.content_color, self.accent_color, c.name())

    def _pick_accent_color(self):
        c = QColorDialog.getColor(QColor(self.accent_color), self, tr("btn_color_pick_ac", self.current_lang))
        if c.isValid():
            self._set_colors(self.bg_color, self.content_color, c.name(), self.content_color_2)

    def _on_lang_changed(self, idx: int):
        new_lang = self.cmb_lang.currentData()
        if new_lang:
            self.current_lang = new_lang
            self.setWindowTitle(tr("settings_title", self.current_lang))
            self.title_lbl.setText(tr("theme_custom_title", self.current_lang))
            self.lbl_lang.setText(tr("lbl_language", self.current_lang))
            self.chk_dock_mode.setText(tr("chk_dock_mode", self.current_lang))
            self.lbl_dock_desc.setText(tr("chk_dock_mode_desc", self.current_lang))
            self.lbl_bg.setText(tr("lbl_bg_color", self.current_lang))
            self.lbl_ct.setText(tr("lbl_ct_color", self.current_lang))
            if hasattr(self, "lbl_ct2"):
                self.lbl_ct2.setText(tr("lbl_ct2_color", self.current_lang))
            self.lbl_ac.setText(tr("lbl_ac_color", self.current_lang))
            self.lbl_pre.setText(tr("lbl_quick_themes", self.current_lang))
            for p_btn, p_key in getattr(self, "theme_preset_btns", []):
                p_btn.setText(tr(p_key, self.current_lang))
            self.btn_reset.setText(tr("btn_reset", self.current_lang))
            self.btn_accept.setText(tr("btn_accept", self.current_lang))
            self.on_apply(self.bg_color, self.content_color, self.accent_color, self.current_lang, self.dock_mode, self.content_color_2)

    def _set_colors(self, bg: str, ct: str, ac: str, ct2: str = ""):
        self.bg_color = bg
        self.content_color = ct
        self.content_color_2 = ct2 or _lighten_hex(ct, 1.15)
        self.accent_color = ac
        self._update_swatch_buttons()
        self.on_apply(bg, ct, ac, self.current_lang, self.dock_mode, self.content_color_2)

class AnimatedFanWidget(QWidget):
    """Widget animado que dibuja un ventilador giratorio con aspas estilizadas y velocidad según RPM."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(22, 22)
        self._angle = 0.0
        self._rpm = 0
        self._step = 6.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._rotate_step)
        self._timer.start(35)

    def set_rpm(self, rpm: int):
        self._rpm = max(0, int(rpm))
        if self._rpm == 0:
            self._step = 0.0
        else:
            self._step = max(3.0, min(24.0, 3.0 + (self._rpm / 7000.0) * 21.0))
        self.update()

    def _rotate_step(self):
        if self._step > 0:
            self._angle = (self._angle + self._step) % 360.0
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        cx = w / 2.0
        cy = h / 2.0

        painter.save()
        painter.translate(cx, cy)
        painter.rotate(self._angle)

        blade_color = QColor("#38bdf8") if self._rpm < 4000 else (QColor("#facc15") if self._rpm < 5500 else QColor("#ef4444"))
        painter.setBrush(QBrush(blade_color))
        painter.setPen(Qt.PenStyle.NoPen)

        r = min(w, h) / 2.0 - 2.0
        for _ in range(4):
            path = QPainterPath()
            path.moveTo(0, 0)
            path.quadTo(r * 0.7, -r * 0.35, r, 0)
            path.quadTo(r * 0.5, r * 0.45, 0, 0)
            painter.drawPath(path)
            painter.rotate(90.0)

        hub_color = QColor("#1e293b")
        painter.setBrush(QBrush(hub_color))
        painter.drawEllipse(QPointF(0, 0), 3.0, 3.0)
        painter.restore()


class DualStickRgbWidget(QWidget):
    """
    Renders the two Legion Go sticks at each end of the panel ('space-between'),
    49x49px each, with the inner animated RGB halo (36px) and concave cap (29px)
    running at 30% speed to match the real Legion Go controller LEDs.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(66)
        self.stick_pixmap = QPixmap(str(STICK_PATH)) if STICK_PATH.exists() else QPixmap()

        self.enabled = False
        self.mode = "SOLID"
        self.hue = 0
        self.brightness = 50
        self.speed = 50

        self._start_time = time.monotonic()
        self._timer = QTimer(self)
        self._timer.setInterval(33)
        self._timer.timeout.connect(self.update)
        self._timer.start()

    def set_rgb_state(self, enabled: bool, mode: str, hue: int, brightness: int, speed: int):
        self.enabled = bool(enabled)
        self.mode = str(mode or "SOLID").upper()
        self.hue = int(hue or 0) % 360
        self.brightness = max(1, min(100, int(brightness or 50)))
        self.speed = max(1, min(100, int(speed or 50)))
        self.update()

    def _duration_sec(self) -> float:
        return max(0.6, 4.4 - (self.speed / 100.0) * 3.6) * 3.5

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        w = self.width()
        h = self.height()
        stick_size = 49.0
        y_center = h / 2.0
        left_center = QPointF(18.0 + stick_size / 2.0, y_center)
        right_center = QPointF(w - 18.0 - stick_size / 2.0, y_center)

        for center in (left_center, right_center):
            self._draw_single_stick(painter, center, stick_size)

    def _draw_single_stick(self, painter: QPainter, center: QPointF, stick_size: float):
        target_rect = QRectF(
            center.x() - stick_size / 2.0,
            center.y() - stick_size / 2.0,
            stick_size,
            stick_size,
        )
        if not self.stick_pixmap.isNull():
            path = QPainterPath()
            path.addEllipse(target_rect)
            painter.save()
            painter.setClipPath(path)
            painter.drawPixmap(target_rect.toRect(), self.stick_pixmap)
            painter.restore()
        else:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(55, 55, 55))
            painter.drawEllipse(target_rect)

        if not self.enabled:
            return

        elapsed = time.monotonic() - self._start_time
        dur = self._duration_sec()
        phase = (elapsed % dur) / dur
        norm_b = max(0.18, min(1.0, self.brightness / 100.0))

        halo_radius = 18.0
        scale = 1.0
        alpha = norm_b

        if self.mode == "PULSE":
            wave = 0.5 * (1.0 - math.cos(2.0 * math.pi * phase))
            min_a = max(0.12, norm_b * 0.18)
            alpha = min_a + (norm_b - min_a) * wave
            scale = 0.92 + (1.04 - 0.92) * wave

        curr_radius = halo_radius * scale

        painter.save()
        painter.setPen(Qt.PenStyle.NoPen)

        if self.mode == "SPIRAL":
            angle_deg = -phase * 360.0
            grad = QConicalGradient(center, angle_deg)
            for stop, h_deg in [
                (0.0, 0),
                (1 / 6, 60),
                (2 / 6, 120),
                (3 / 6, 180),
                (4 / 6, 240),
                (5 / 6, 300),
                (1.0, 360),
            ]:
                c = QColor.fromHslF((h_deg % 360) / 360.0, 1.0, 0.55, alpha)
                grad.setColorAt(stop, c)

            glow_grad = QRadialGradient(center, curr_radius + 4.0)
            glow_grad.setColorAt(0.7, QColor(255, 255, 255, int(alpha * 110)))
            glow_grad.setColorAt(1.0, QColor(255, 255, 255, 0))
            painter.setBrush(QBrush(glow_grad))
            painter.drawEllipse(center, curr_radius + 4.0, curr_radius + 4.0)

            painter.setBrush(QBrush(grad))
            painter.drawEllipse(center, curr_radius, curr_radius)
        else:
            if self.mode == "DYNAMIC":
                curr_hue = (phase * 360.0) % 360.0
            else:
                curr_hue = float(self.hue)

            main_color = QColor.fromHslF(curr_hue / 360.0, 1.0, 0.55, alpha)
            glow_color = QColor.fromHslF(curr_hue / 360.0, 1.0, 0.55, alpha * 0.55)
            transparent_color = QColor.fromHslF(curr_hue / 360.0, 1.0, 0.55, 0.0)

            glow_r = curr_radius + 3.0 + norm_b * 4.0
            glow_grad = QRadialGradient(center, glow_r)
            glow_grad.setColorAt(0.0, main_color)
            glow_grad.setColorAt(curr_radius / glow_r, main_color)
            glow_grad.setColorAt(min(0.95, (curr_radius + 2.0) / glow_r), glow_color)
            glow_grad.setColorAt(1.0, transparent_color)

            painter.setBrush(QBrush(glow_grad))
            painter.drawEllipse(center, glow_r, glow_r)

        painter.restore()

        cap_radius = 14.5
        cap_grad = QRadialGradient(center, cap_radius)
        cap_grad.setColorAt(0.0, QColor(22, 22, 22, 242))
        cap_grad.setColorAt(0.76, QColor(28, 28, 28, 230))
        cap_grad.setColorAt(1.0, QColor(30, 30, 30, 0))
        painter.save()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(cap_grad))
        painter.drawEllipse(center, cap_radius, cap_radius)
        painter.restore()



REMAP_OPTIONS = [
    ("remap_disabled", "DISABLED"),
    ("A", "A"),
    ("B", "B"),
    ("X", "X"),
    ("Y", "Y"),
    ("remap_lb", "LEFT_BUMPER"),
    ("remap_lt", "LEFT_TRIGGER"),
    ("remap_rb", "RIGHT_BUMPER"),
    ("remap_rt", "RIGHT_TRIGGER"),
    ("remap_l3", "LEFT_STICK_CLICK"),
    ("remap_r3", "RIGHT_STICK_CLICK"),
    ("remap_dpad_up", "DPAD_UP"),
    ("remap_dpad_down", "DPAD_DOWN"),
    ("remap_dpad_left", "DPAD_LEFT"),
    ("remap_dpad_right", "DPAD_RIGHT"),
    ("remap_view", "VIEW"),
    ("remap_menu", "MENU"),
]

RGB_MODES = ["SOLID", "DYNAMIC", "PULSE", "SPIRAL"]
CHARGE_LIMIT_STEPS = [70, 75, 80, 85, 90, 95]
FAN_TEMPS = ["40", "50", "60", "70", "80", "90", "100"]


class DockHandle(QFrame):
    def __init__(self, parent, on_click):
        super().__init__(parent)
        self.setObjectName("DockHandle")
        self.setFixedSize(54, 150)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.on_click = on_click

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 8, 4, 8)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.arrow_lbl = QLabel("‹")
        self.arrow_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.arrow_lbl.setStyleSheet("color: #ffffff; font-size: 26px; font-weight: 800; background: transparent;")
        layout.addWidget(self.arrow_lbl)

        self.hint_lbl = QLabel("LeGO")
        self.hint_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hint_lbl.setStyleSheet("color: #9ca3af; font-size: 10px; font-weight: 800; letter-spacing: 1.5px; background: transparent;")
        layout.addWidget(self.hint_lbl)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if callable(self.on_click):
                self.on_click()
            event.accept()
            return
        super().mousePressEvent(event)



class ControllerShortcutThread(QThread):
    shortcut_triggered = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = True
        self.enabled = True

    def stop(self):
        self._running = False

    def run(self):
        try:
            import evdev
            import select
        except ImportError:
            return

        last_trigger_time = 0.0

        while self._running:
            devices = {}
            try:
                for path in evdev.list_devices():
                    try:
                        d = evdev.InputDevice(path)
                        caps = d.capabilities()
                        key_caps = caps.get(evdev.ecodes.EV_KEY, [])
                        if evdev.ecodes.BTN_MODE in key_caps or evdev.ecodes.BTN_SELECT in key_caps:
                            devices[d.fd] = d
                    except Exception:
                        pass
            except Exception:
                pass

            if not devices:
                self.msleep(1500)
                continue

            while self._running:
                try:
                    r, _, _ = select.select(list(devices.keys()), [], [], 1.0)
                    if not r:
                        break

                    for fd in r:
                        dev = devices.get(fd)
                        if not dev:
                            continue
                        try:
                            for ev in dev.read():
                                if ev.type == evdev.ecodes.EV_KEY and ev.value == 1:
                                    if ev.code in (evdev.ecodes.BTN_MODE, evdev.ecodes.BTN_SELECT):
                                        now = time.time()
                                        if self.enabled and (now - last_trigger_time > 0.4):
                                            last_trigger_time = now
                                            self.shortcut_triggered.emit()
                        except (OSError, IOError):
                            devices.pop(fd, None)
                            break
                except Exception:
                    break



class LeGOSuiteMainWindow(QMainWindow):
    def __init__(self, backend: BackendClient):
        super().__init__()
        self.backend = backend
        self.settings_cache = {}
        self.power_info = {}
        self._updating_ui = False
        self._last_mtime = 0.0
        self._first_close_notified = False
        self.ui_bg_color = DEFAULT_BG_COLOR
        self.ui_content_color = DEFAULT_CONTENT_COLOR
        self.ui_content_color_2 = DEFAULT_CONTENT_COLOR_2
        self.ui_accent_color = DEFAULT_ACCENT_COLOR
        self.ui_language = "es"
        self._auto_rotate_active = False

        self.setWindowTitle("LeGO Suite v0.198")
        self.resize(430, 660)
        self.setMinimumSize(0, 0)
        self.setMaximumSize(16777215, 16777215)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.dock_mode_enabled = True
        self.is_collapsed = False
        self._drag_pos = None
        self._anim = None
        self._anim_dock = None
        self._initial_pos_set = False
        if LOGO_ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(LOGO_ICON_PATH)))

        self.setStyleSheet(build_dynamic_stylesheet(self.ui_bg_color, self.ui_content_color, self.ui_accent_color, self.ui_content_color_2))
        self._build_ui()
        self._build_tray()
        self._position_top_right()

        self.refresh_from_backend(force=True)

        self._sync_timer = QTimer(self)
        self._sync_timer.setInterval(1500)
        self._sync_timer.timeout.connect(self._check_external_sync)
        self._sync_timer.start()

        self._charge_watcher_timer = QTimer(self)
        self._charge_watcher_timer.setInterval(10000)
        self._charge_watcher_timer.timeout.connect(self._enforce_charge_limit_tick)
        self._charge_watcher_timer.start()
        self._temp_timer = QTimer(self)
        self._temp_timer.setInterval(2000)
        self._temp_timer.timeout.connect(self._update_live_temps_and_fan)
        self._temp_timer.start()

        self._controller_thread = ControllerShortcutThread(self)
        self._controller_thread.shortcut_triggered.connect(self.toggle_slide_panel)
        self._controller_thread.start()



    def _is_hwdb_sensor_installed(self) -> bool:
        if not HWDB_SENSOR_FILE.exists():
            return False
        try:
            content = HWDB_SENSOR_FILE.read_text(encoding="utf-8")
            return "ACCEL_MOUNT_MATRIX=1, 0, 0; 0, 1, 0; 0, 0, 1" in content
        except Exception:
            return False

    def _inject_hwdb_sensor(self):
        """Install hwdb sensor file as root via pkexec (native KDE polkit dialog)."""
        script_path = Path("/tmp/lego_install_sensor_root.sh")
        script_content = (
            "#!/usr/bin/env bash\n"
            "set -e\n"
            "mkdir -p /etc/udev/hwdb.d\n"
            "printf 'sensor:modalias:platform:HID-SENSOR-200073*\\n ACCEL_MOUNT_MATRIX=1, 0, 0; 0, 1, 0; 0, 0, 1\\n' > /etc/udev/hwdb.d/61-sensor-local.hwdb\n"
            "systemd-hwdb update\n"
            "udevadm trigger\n"
            "systemctl restart iio-sensor-proxy || true\n"
        )
        try:
            script_path.write_text(script_content, encoding="utf-8")
            script_path.chmod(0o755)
        except Exception as e:
            QMessageBox.warning(self, "LeGO Suite", f"Error: {e}")
            return

        self.btn_inject_hwdb.setEnabled(False)
        self.btn_inject_hwdb.setText("..." )
        self._sensor_proc = QProcess(self)
        self._sensor_proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self._sensor_proc.finished.connect(self._on_sensor_install_finished)
        self._sensor_proc.errorOccurred.connect(lambda _err: self._on_sensor_install_finished(-1, None))
        self._sensor_proc.start("pkexec", ["/usr/bin/bash", str(script_path)])

    def _on_sensor_install_finished(self, exit_code, _status=None):
        if getattr(self, "_sensor_done_handled", False) and exit_code == -1:
            return
        out = ""
        try:
            out = bytes(self._sensor_proc.readAll()).decode("utf-8", "ignore").strip()
        except Exception:
            pass
        self.btn_inject_hwdb.setEnabled(True)
        self._check_hwdb_status()
        es = self.ui_language == "es"
        if exit_code == 0:
            QMessageBox.information(
                self, "LeGO Suite",
                "Sensor instalado y calibrado correctamente." if es else "Sensor installed and calibrated successfully.")
        elif exit_code in (126, 127):
            QMessageBox.warning(
                self, "LeGO Suite",
                "Autorización cancelada o denegada." if es else "Authorization cancelled or denied.")
        else:
            QMessageBox.critical(
                self, "LeGO Suite",
                (("Error al instalar el sensor (código %s).\n\n" if es else "Sensor install failed (code %s).\n\n") % exit_code) + out[-800:])

    def _check_hwdb_status(self):
        installed = self._is_hwdb_sensor_installed()
        if hasattr(self, "lbl_auto_rotate_hint"):
            self.lbl_auto_rotate_hint.setVisible(installed)
        if installed:
            self.lbl_hwdb_status.setText(tr("sensor_ok", self.ui_language))
            self.lbl_hwdb_status.setStyleSheet("color: #10b981; font-weight: 700; font-size: 11px;")
            self.btn_inject_hwdb.setText(tr("btn_inject_hwdb", self.ui_language))
        else:
            self.lbl_hwdb_status.setText(tr("sensor_missing", self.ui_language))
            self.lbl_hwdb_status.setStyleSheet("color: #ef4444; font-weight: 700; font-size: 11px;")
            self.btn_inject_hwdb.setText(tr("btn_inject_hwdb_clean", self.ui_language))

    def _on_auto_rotate_toggled(self, checked: bool):
        self._auto_rotate_active = checked
        if checked:
            if not hasattr(self, "_rotate_timer"):
                self._rotate_timer = QTimer(self)
                self._rotate_timer.setInterval(800)
                self._rotate_timer.timeout.connect(self._check_screen_orientation_tick)
            self._rotate_timer.start()
        else:
            if hasattr(self, "_rotate_timer"):
                self._rotate_timer.stop()

    def _check_screen_orientation_tick(self):
        if not self._auto_rotate_active:
            return
        accel_x_file = None
        for dev_path in (Path("/sys/bus/iio/devices/iio:device2"), Path("/sys/bus/iio/devices/iio:device0")):
            if (dev_path / "in_accel_x_raw").exists():
                accel_x_file = dev_path / "in_accel_x_raw"
                accel_y_file = dev_path / "in_accel_y_raw"
                break
        if accel_x_file and accel_x_file.exists() and accel_y_file.exists():
            try:
                x = int(accel_x_file.read_text().strip())
                y = int(accel_y_file.read_text().strip())
                new_rot = None
                if abs(x) > abs(y) and abs(x) > 5:
                    new_rot = "none" if x > 0 else "inverted"
                elif abs(y) > abs(x) and abs(y) > 5:
                    new_rot = "right" if y > 0 else "left"
                if new_rot and getattr(self, "_last_applied_rotation", None) != new_rot:
                    self._last_applied_rotation = new_rot
                    subprocess.run(["kscreen-doctor", f"output.1.rotation.{new_rot}"],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
            except Exception:
                pass

    def _update_ui_texts(self):
        lang = self.ui_language
        self.btn_tab_tdp.setText(tr("tab_tdp", lang))
        self.btn_tab_controls.setText(tr("tab_controls", lang))
        self.btn_tab_screen.setText(tr("tab_screen", lang))

        if hasattr(self, "card_tdp_mode_title") and self.card_tdp_mode_title:
            self.card_tdp_mode_title.setText(tr("card_tdp_mode", lang))
        if hasattr(self, "tdp_mode_buttons"):
            for m_key, btn in self.tdp_mode_buttons.items():
                btn.setText(tr('mode_' + m_key, lang))
        if hasattr(self, "card_tdp_title") and self.card_tdp_title:
            self.card_tdp_title.setText(tr("card_tdp", lang))
        if hasattr(self, "card_cpu_title") and self.card_cpu_title:
            self.card_cpu_title.setText(tr("card_cpu", lang))
        if hasattr(self, "card_bat_title") and self.card_bat_title:
            self.card_bat_title.setText(tr("card_bat", lang))
        if hasattr(self, "card_monitor_title") and self.card_monitor_title:
            self.card_monitor_title.setText(tr("card_monitor", lang))
        if hasattr(self, "card_fan_title") and self.card_fan_title:
            self.card_fan_title.setText(tr("card_fan", lang))
        if hasattr(self, "card_range_title") and self.card_range_title:
            self.card_range_title.setText(tr("card_range", lang))
        if hasattr(self, "card_rgb_title") and self.card_rgb_title:
            self.card_rgb_title.setText(tr("card_rgb", lang))
        if hasattr(self, "card_remap_title") and self.card_remap_title:
            self.card_remap_title.setText(tr("card_remap", lang))
        if hasattr(self, "card_sensor_title") and self.card_sensor_title:
            self.card_sensor_title.setText(tr("card_sensor", lang))

        if hasattr(self, "lbl_tdp_title"):
            self.lbl_tdp_title.setText(tr("lbl_tdp", lang))
        if hasattr(self, "lbl_tdp_val") and hasattr(self, "slider_tdp"):
            self.lbl_tdp_val.setText(f"{self.slider_tdp.value()} W")
            self.lbl_tdp_val.show()
        if hasattr(self, "lbl_min_tdp_title"):
            self.lbl_min_tdp_title.setText(tr("lbl_min_tdp", lang))
        if hasattr(self, "lbl_max_tdp_title"):
            self.lbl_max_tdp_title.setText(tr("lbl_max_tdp", lang))
        if hasattr(self, "chk_cpu_boost"):
            self.chk_cpu_boost.setText(tr("chk_cpu_boost", lang))
        if hasattr(self, "chk_smt"):
            self.chk_smt.setText(tr("chk_smt", lang))
        if hasattr(self, "lbl_gov"):
            self.lbl_gov.setText(tr("lbl_governor", lang))
        if hasattr(self, "lbl_epp"):
            self.lbl_epp.setText(tr("lbl_epp", lang))
        if hasattr(self, "chk_charge_limit"):
            self.chk_charge_limit.setText(tr("chk_charge_limit", lang))
        if hasattr(self, "lbl_cs"):
            self.lbl_cs.setText(tr("lbl_charge_val", lang))
        if hasattr(self, "chk_fan_profile"):
            self.chk_fan_profile.setText(tr("chk_fan_profile", lang))

        if hasattr(self, "btn_ip_nav"):
            self.btn_ip_nav.setText(f"🎮  {tr('lbl_ip_title', lang)}   ›")
        if hasattr(self, "btn_ip_back"):
            self.btn_ip_back.setText(f"‹  {tr('btn_ip_back', lang)}")
        if hasattr(self, "card_ip_title") and self.card_ip_title:
            self.card_ip_title.setText(tr("lbl_ip_title", lang))
        if hasattr(self, "lbl_ip_mode_title"):
            self.lbl_ip_mode_title.setText(tr("lbl_ip_mode", lang))
        if hasattr(self, "lbl_ip_prof_title"):
            self.lbl_ip_prof_title.setText(tr("lbl_ip_profiles", lang))
        if hasattr(self, "cmb_ip_mode") and hasattr(self, "_ip_modes_data"):
            is_es = (lang == "es")
            cur_idx = self.cmb_ip_mode.currentIndex()
            self.cmb_ip_mode.blockSignals(True)
            self.cmb_ip_mode.clear()
            for m_code, l_es, l_en in self._ip_modes_data:
                self.cmb_ip_mode.addItem(l_es if is_es else l_en, m_code)
            if cur_idx >= 0 and cur_idx < self.cmb_ip_mode.count():
                self.cmb_ip_mode.setCurrentIndex(cur_idx)
            self.cmb_ip_mode.blockSignals(False)
        if hasattr(self, "chk_ip_swap_menu"):
            self.chk_ip_swap_menu.setText(tr("chk_ip_swap_menu", lang))
        if hasattr(self, "chk_ip_swap_vol"):
            self.chk_ip_swap_vol.setText(tr("chk_ip_swap_vol", lang))
        if hasattr(self, "btn_reset_ctrl"):
            self.btn_reset_ctrl.setText("🔄  " + tr("btn_reset_controllers", lang))
        if hasattr(self, "lbl_reset_ctrl_desc"):
            self.lbl_reset_ctrl_desc.setText(tr("lbl_reset_controllers_desc", lang))
        if hasattr(self, "chk_power_led"):
            self.chk_power_led.setText(tr("chk_power_led", lang))
        if hasattr(self, "chk_rgb_control"):
            self.chk_rgb_control.setText(tr("chk_rgb_control", lang))
        if hasattr(self, "chk_controller_led"):
            self.chk_controller_led.setText(tr("chk_controller_led", lang))
        if hasattr(self, "lbl_mode"):
            self.lbl_mode.setText(tr("lbl_rgb_mode", lang))
        if hasattr(self, "lbl_rgb_b_title"):
            self.lbl_rgb_b_title.setText(tr("lbl_rgb_brightness", lang))
        if hasattr(self, "lbl_rgb_s_title"):
            self.lbl_rgb_s_title.setText(tr("lbl_rgb_speed", lang))
        if hasattr(self, "chk_sync_slider_color"):
            self.chk_sync_slider_color.setText(tr("chk_sync_slider_color", lang))

        if hasattr(self, "lbl_s_info"):
            self.lbl_s_info.setText(tr("lbl_hwdb_status_title", lang))
        if hasattr(self, "desc_hwdb_lbl"):
            self.desc_hwdb_lbl.setText(tr("lbl_hwdb_desc", lang))
        if hasattr(self, "lbl_auto_rotate_hint"):
            self.lbl_auto_rotate_hint.setText(tr("lbl_auto_rotate_hint", lang))

        if hasattr(self, "chk_fan_enabled"):
            self.chk_fan_enabled.setText(tr("chk_fan_enabled", lang))
        if hasattr(self, "chk_full_fan"):
            self.chk_full_fan.setText(tr("chk_full_fan", lang))

        if hasattr(self, "chk_remap_enabled"):
            self.chk_remap_enabled.setText(tr("chk_remap_enabled", lang))
        if hasattr(self, "lbl_rumble"):
            self.lbl_rumble.setText(tr("lbl_rumble_intensity", lang))
        if hasattr(self, "cmb_rumble"):
            cur_rumble = self.cmb_rumble.currentData()
            self.cmb_rumble.blockSignals(True)
            self.cmb_rumble.clear()
            for r_key, r_code in [("rumble_off", "OFF"), ("rumble_low", "LOW"), ("rumble_medium", "MEDIUM"), ("rumble_high", "HIGH")]:
                self.cmb_rumble.addItem(tr(r_key, lang), r_code)
            idx_r = self.cmb_rumble.findData(cur_rumble)
            if idx_r >= 0:
                self.cmb_rumble.setCurrentIndex(idx_r)
            self.cmb_rumble.blockSignals(False)
        if hasattr(self, "chk_touchpad"):
            self.chk_touchpad.setText(tr("chk_touchpad", lang))
        if hasattr(self, "chk_guide_shortcut"):
            self.chk_guide_shortcut.setText(tr("chk_guide_shortcut", lang))
        for btn_code, (lbl, key_name) in getattr(self, "remap_labels", {}).items():
            lbl.setText(tr(key_name, lang))
        for btn_code, cmb in getattr(self, "remap_combos", {}).items():
            cur_data = cmb.currentData()
            cmb.blockSignals(True)
            cmb.clear()
            for opt_key, act_code in REMAP_OPTIONS:
                display_txt = tr(opt_key, lang) if opt_key.startswith("remap_") else opt_key
                cmb.addItem(display_txt, act_code)
            idx = cmb.findData(cur_data)
            if idx >= 0:
                cmb.setCurrentIndex(idx)
            cmb.blockSignals(False)

        if hasattr(self, "version_label"):
            mode_txt = tr("status_decky_rpc" if self.backend.rpc_available else "status_local_sync", lang)
            self.version_label.setText(f"Version 0.198 • {mode_txt}")
        if hasattr(self, "tray") and hasattr(self, "slider_tdp"):
            tdp_val = self.slider_tdp.value()
            c_val = getattr(self, "_last_charge_limit_val", 80)
            c_enabled = self.chk_charge_limit.isChecked() if hasattr(self, "chk_charge_limit") else False

            charge_disp = c_val if c_enabled else 100
            self.tray.setToolTip(
                tr("tray_tooltip", lang).format(tdp=tdp_val, charge=charge_disp)
            )
        if hasattr(self, "btn_gear"):
            self.btn_gear.setToolTip(tr("gear_tooltip", lang))
        if hasattr(self, "btn_dock"):
            self.btn_dock.setToolTip(tr("btn_dock_collapse", lang))
        if hasattr(self, "btn_minimize"):
            self.btn_minimize.setToolTip(tr("btn_minimize", lang))
        if hasattr(self, "btn_close"):
            self.btn_close.setToolTip(tr("btn_close", lang))

        if hasattr(self, "btn_inject_hwdb"):
            self._check_hwdb_status()

    def _build_ui(self):
        root = QWidget(self)
        root.setObjectName("RootWidget")
        self.setCentralWidget(root)

        self.window_frame = QFrame(root)
        self.window_frame.setObjectName("WindowFrame")
        self.window_frame.setGeometry(0, 0, 430, 660)

        self.dock_handle = DockHandle(root, on_click=self.expand_from_dock)
        self.dock_handle.setGeometry(0, 0, 36, 130)
        self.dock_handle.hide()

        main_layout = QVBoxLayout(self.window_frame)
        main_layout.setContentsMargins(14, 10, 14, 12)
        main_layout.setSpacing(8)

        header_top_row = QHBoxLayout()
        header_top_row.setContentsMargins(0, 0, 0, 0)

        left_box = QHBoxLayout()
        left_box.setContentsMargins(0, 0, 0, 0)
        left_box.setSpacing(0)
        left_box.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        self.btn_dock = QPushButton("›")
        self.btn_dock.setProperty("class", "DockBtn")
        self.btn_dock.setFixedSize(56, 36)
        self.btn_dock.setToolTip(tr("btn_dock_collapse", self.ui_language))
        self.btn_dock.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_dock.clicked.connect(self.collapse_to_dock)
        left_box.addWidget(self.btn_dock)
        left_box.addSpacing(40)
        header_top_row.addLayout(left_box, 0)

        logo_box = QVBoxLayout()
        logo_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_box.setSpacing(2)

        logo_label = QLabel()
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_label.setStyleSheet("background: transparent;")
        ui_logo_file = LOGO_UI_PATH if LOGO_UI_PATH.exists() else LOGO_ICON_PATH
        if ui_logo_file.exists():
            pix = QPixmap(str(ui_logo_file)).scaled(
                185,
                68,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            logo_label.setPixmap(pix)
        else:
            logo_label.setText("LeGO Suite")
            logo_label.setStyleSheet("font-size: 22px; font-weight: 800; background: transparent;")
        logo_box.addWidget(logo_label)

        self.version_label = QLabel("Version 0.198 • Sincronizado")
        self.version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.version_label.setStyleSheet(
            "color: #9ca3af; font-size: 11px; font-weight: 600; letter-spacing: 0.05em; background: transparent;"
        )
        logo_box.addWidget(self.version_label)
        header_top_row.addLayout(logo_box, 1)

        win_ctrls = QHBoxLayout()
        win_ctrls.setSpacing(6)
        win_ctrls.setContentsMargins(0, 0, 0, 0)

        self.btn_gear = QPushButton("⚙")
        self.btn_gear.setProperty("class", "GearBtn")
        self.btn_gear.setFixedSize(28, 28)
        self.btn_gear.setToolTip(tr("gear_tooltip", self.ui_language))
        self.btn_gear.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_gear.clicked.connect(self._open_theme_dialog)
        win_ctrls.addWidget(self.btn_gear)

        self.btn_minimize = QPushButton("🗕")
        self.btn_minimize.setProperty("class", "WindowCtrlBtn")
        self.btn_minimize.setFixedSize(28, 28)
        self.btn_minimize.setToolTip(tr("btn_minimize", self.ui_language))
        self.btn_minimize.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_minimize.clicked.connect(self._slide_out)
        win_ctrls.addWidget(self.btn_minimize)

        self.btn_close = QPushButton("✕")
        self.btn_close.setObjectName("BtnClose")
        self.btn_close.setProperty("class", "WindowCtrlBtn")
        self.btn_close.setFixedSize(28, 28)
        self.btn_close.setToolTip(tr("btn_close", self.ui_language))
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.clicked.connect(self._slide_out)
        win_ctrls.addWidget(self.btn_close)
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.clicked.connect(self._slide_out)
        win_ctrls.addWidget(self.btn_close)

        header_top_row.addLayout(win_ctrls, 0)

        main_layout.addLayout(header_top_row)

        tab_bar = QHBoxLayout()
        tab_bar.setSpacing(6)

        self.btn_tab_tdp = QPushButton("TDP")
        self.btn_tab_tdp.setProperty("class", "TabBtn")
        self.btn_tab_tdp.setProperty("active", "true")
        self.btn_tab_tdp.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_tab_tdp.clicked.connect(lambda: self._switch_tab(0))

        self.btn_tab_controls = QPushButton("Controls")
        self.btn_tab_controls.setProperty("class", "TabBtn")
        self.btn_tab_controls.setProperty("active", "false")
        self.btn_tab_controls.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_tab_controls.clicked.connect(lambda: self._switch_tab(1))

        self.btn_tab_screen = QPushButton("Screen")
        self.btn_tab_screen.setProperty("class", "TabBtn")
        self.btn_tab_screen.setProperty("active", "false")
        self.btn_tab_screen.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_tab_screen.clicked.connect(lambda: self._switch_tab(2))

        tab_bar.addWidget(self.btn_tab_tdp)
        tab_bar.addWidget(self.btn_tab_controls)
        tab_bar.addWidget(self.btn_tab_screen)
        main_layout.addLayout(tab_bar)

        self.stack = QStackedWidget()
        self.stack.addWidget(self._create_scrollable_page(self._build_tdp_tab()))
        self.stack.addWidget(self._create_scrollable_page(self._build_controls_tab()))
        self.stack.addWidget(self._create_scrollable_page(self._build_screen_tab()))
        self.stack.addWidget(self._create_scrollable_page(self._build_inputplumber_page()))
        main_layout.addWidget(self.stack, 1)

    def _create_scrollable_page(self, content_widget: QWidget) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content_widget.setObjectName("ScrollContent")
        scroll.setWidget(content_widget)
        return scroll

    def _make_card(self, title: str):
        frame = QFrame()
        frame.setProperty("class", "SectionCard")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 10, 12, 12)
        layout.setSpacing(8)
        lbl = None
        if title:
            lbl = QLabel(title)
            lbl.setProperty("class", "SectionTitle")
            layout.addWidget(lbl)
        return frame, layout, lbl


    def _build_tdp_tab(self) -> QWidget:
        page = QWidget()
        vbox = QVBoxLayout(page)
        vbox.setContentsMargins(2, 4, 6, 8)
        vbox.setSpacing(10)

        card_mode, l_mode, self.card_tdp_mode_title = self._make_card(tr("card_tdp_mode", self.ui_language))

        self.tdp_mode_buttons = {}
        self.tdp_mode_colors = {
            "quiet": "#0019ff",
            "balanced": "#f3f4f6",
            "performance": "#ff0004",
            "custom": "#ff00d9"
        }
        modes_grid = QHBoxLayout()
        modes_grid.setSpacing(6)

        mode_defs = [
            ("quiet", "mode_quiet"),
            ("balanced", "mode_balanced"),
            ("performance", "mode_performance"),
            ("custom", "mode_custom")
        ]

        for m_key, m_tr_key in mode_defs:
            btn = QPushButton(tr(m_tr_key, self.ui_language))
            btn.setProperty("class", "ActionBtn")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("font-size: 11px; font-weight: 700; text-align: center; padding: 7px 4px; border-radius: 6px;")
            btn.clicked.connect(lambda checked=False, k=m_key: self._on_tdp_mode_selected(k))
            self.tdp_mode_buttons[m_key] = btn
            modes_grid.addWidget(btn)

        l_mode.addLayout(modes_grid)
        vbox.addWidget(card_mode)

        self.custom_tdp_container = QWidget()
        custom_vbox = QVBoxLayout(self.custom_tdp_container)
        custom_vbox.setContentsMargins(0, 0, 0, 0)
        custom_vbox.setSpacing(10)

        card_tdp, l_tdp, self.card_tdp_title = self._make_card(tr("card_tdp", self.ui_language))

        tdp_top = QHBoxLayout()
        self.lbl_tdp_title = QLabel(tr("lbl_tdp", self.ui_language))
        self.lbl_tdp_title.setProperty("class", "RowLabel")
        self.lbl_tdp_val = QLabel("15 W")
        self.lbl_tdp_val.setProperty("class", "ValueBadge")
        self.lbl_tdp_val.setStyleSheet("color: #60a5fa; font-weight: 800; font-size: 14px; min-width: 55px; text-align: right;")
        self.lbl_tdp_val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        tdp_top.addWidget(self.lbl_tdp_title)
        tdp_top.addStretch()
        tdp_top.addWidget(self.lbl_tdp_val)
        l_tdp.addLayout(tdp_top)

        self.slider_tdp = QSlider(Qt.Orientation.Horizontal)
        self.slider_tdp.setRange(4, 40)
        self.slider_tdp.setValue(15)
        self.slider_tdp.valueChanged.connect(self._on_tdp_slider_preview)
        self.slider_tdp.sliderReleased.connect(self._on_tdp_slider_commit)
        l_tdp.addWidget(self.slider_tdp)

        preset_row = QHBoxLayout()
        for w_val, w_name in [(8, "8W"), (15, "15W"), (20, "20W"), (25, "25W"), (30, "30W")]:
            btn = QPushButton(w_name)
            btn.setProperty("class", "ActionBtn")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked=False, v=w_val: self._set_quick_tdp(v))
            preset_row.addWidget(btn)
        l_tdp.addLayout(preset_row)

        custom_vbox.addWidget(card_tdp)

        card_cpu, l_cpu, self.card_cpu_title = self._make_card(tr("card_cpu", self.ui_language))

        self.chk_cpu_boost = QCheckBox(tr("chk_cpu_boost", self.ui_language))
        self.chk_cpu_boost.toggled.connect(self._on_cpu_boost_toggled)
        l_cpu.addWidget(self.chk_cpu_boost)

        self.chk_smt = QCheckBox(tr("chk_smt", self.ui_language))
        self.chk_smt.toggled.connect(self._on_smt_toggled)
        l_cpu.addWidget(self.chk_smt)

        gov_row = QHBoxLayout()
        self.lbl_gov = QLabel(tr("lbl_governor", self.ui_language))
        self.lbl_gov.setProperty("class", "RowLabel")
        self.cmb_governor = QComboBox()
        self.cmb_governor.addItems(["powersave", "performance"])
        self.cmb_governor.currentTextChanged.connect(self._on_governor_changed)
        gov_row.addWidget(self.lbl_gov)
        gov_row.addStretch()
        gov_row.addWidget(self.cmb_governor)
        l_cpu.addLayout(gov_row)

        epp_row = QHBoxLayout()
        self.lbl_epp = QLabel(tr("lbl_epp", self.ui_language))
        self.lbl_epp.setProperty("class", "RowLabel")
        self.cmb_epp = QComboBox()
        self.cmb_epp.addItems(["power", "balance_power", "balance_performance", "performance"])
        self.cmb_epp.currentTextChanged.connect(self._on_epp_changed)
        epp_row.addWidget(self.lbl_epp)
        epp_row.addStretch()
        epp_row.addWidget(self.cmb_epp)
        l_cpu.addLayout(epp_row)

        custom_vbox.addWidget(card_cpu)

        vbox.addWidget(self.custom_tdp_container)

        card_bat, l_bat, self.card_bat_title = self._make_card(tr("card_bat", self.ui_language))

        self.chk_charge_limit = QCheckBox(tr("chk_charge_limit", self.ui_language))
        self.chk_charge_limit.toggled.connect(self._on_charge_limit_toggled)
        l_bat.addWidget(self.chk_charge_limit)
        vbox.addWidget(card_bat)

        card_monitor, l_monitor, self.card_monitor_title = self._make_card(tr("card_monitor", self.ui_language))

        temp_row = QHBoxLayout()
        temp_row.setContentsMargins(4, 2, 4, 2)
        temp_row.setSpacing(8)

        cpu_box = QHBoxLayout()
        cpu_box.setSpacing(5)
        self.lbl_cpu_temp_title = QLabel("Temp CPU:")
        self.lbl_cpu_temp_title.setStyleSheet("font-weight: 700; font-size: 11px; color: #9ca3af;")
        self.lbl_cpu_temp_val = QLabel("-- °C")
        self.lbl_cpu_temp_val.setStyleSheet("color: #38bdf8; font-weight: 800; font-size: 12px; background: rgba(56, 189, 248, 0.12); padding: 2px 6px; border-radius: 5px;")
        cpu_box.addWidget(self.lbl_cpu_temp_title)
        cpu_box.addWidget(self.lbl_cpu_temp_val)
        temp_row.addLayout(cpu_box)

        temp_row.addStretch()

        fan_center_box = QHBoxLayout()
        fan_center_box.setSpacing(5)
        self.fan_anim_widget = AnimatedFanWidget()
        self.lbl_fan_rpm_val = QLabel("-- RPM")
        self.lbl_fan_rpm_val.setStyleSheet("color: #38bdf8; font-weight: 800; font-size: 12px; background: rgba(56, 189, 248, 0.12); padding: 2px 6px; border-radius: 5px;")
        fan_center_box.addWidget(self.fan_anim_widget)
        fan_center_box.addWidget(self.lbl_fan_rpm_val)
        temp_row.addLayout(fan_center_box)

        temp_row.addStretch()

        gpu_box = QHBoxLayout()
        gpu_box.setSpacing(5)
        self.lbl_gpu_temp_title = QLabel("Temp GPU:")
        self.lbl_gpu_temp_title.setStyleSheet("font-weight: 700; font-size: 11px; color: #9ca3af;")
        self.lbl_gpu_temp_val = QLabel("-- °C")
        self.lbl_gpu_temp_val.setStyleSheet("color: #38bdf8; font-weight: 800; font-size: 12px; background: rgba(56, 189, 248, 0.12); padding: 2px 6px; border-radius: 5px;")
        gpu_box.addWidget(self.lbl_gpu_temp_title)
        gpu_box.addWidget(self.lbl_gpu_temp_val)
        temp_row.addLayout(gpu_box)

        l_monitor.addLayout(temp_row)
        custom_vbox.addWidget(card_monitor)

        card_fan, l_fan, self.card_fan_title = self._make_card(tr("card_fan", self.ui_language))

        self.chk_fan_enabled = QCheckBox(tr("chk_fan_enabled", self.ui_language))
        self.chk_fan_enabled.toggled.connect(self._on_fan_enabled_toggled)
        l_fan.addWidget(self.chk_fan_enabled)

        self.fan_controls_container = QWidget()
        fc_layout = QVBoxLayout(self.fan_controls_container)
        fc_layout.setContentsMargins(0, 4, 0, 0)
        fc_layout.setSpacing(6)

        self.chk_full_fan = QCheckBox(tr("chk_full_fan", self.ui_language))
        self.chk_full_fan.toggled.connect(self._on_full_fan_toggled)
        fc_layout.addWidget(self.chk_full_fan)

        self.fan_sliders = {}
        self.fan_labels = {}
        grid_fan = QGridLayout()
        grid_fan.setSpacing(6)
        for idx, temp in enumerate(FAN_TEMPS):
            lbl_t = QLabel(f"{temp}°C")
            lbl_t.setStyleSheet("color: #9ca3af; font-size: 12px; font-weight: 600;")
            sl = QSlider(Qt.Orientation.Horizontal)
            sl.setRange(0, 100)
            sl.setValue(50)
            lbl_v = QLabel("50%")
            lbl_v.setFixedWidth(38)
            lbl_v.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            lbl_v.setStyleSheet("color: #e5e7eb; font-size: 12px; font-weight: 600;")

            sl.valueChanged.connect(lambda val, t=temp: self._on_fan_point_preview(t, val))
            sl.sliderReleased.connect(self._on_fan_curve_commit)

            self.fan_sliders[temp] = sl
            self.fan_labels[temp] = lbl_v

            grid_fan.addWidget(lbl_t, idx, 0)
            grid_fan.addWidget(sl, idx, 1)
            grid_fan.addWidget(lbl_v, idx, 2)

        fc_layout.addLayout(grid_fan)
        l_fan.addWidget(self.fan_controls_container)
        custom_vbox.addWidget(card_fan)

        card_range, l_range, self.card_range_title = self._make_card(tr("card_range", self.ui_language))
        min_row = QHBoxLayout()
        self.lbl_min_tdp_title = QLabel(tr("lbl_min_tdp", self.ui_language))
        min_row.addWidget(self.lbl_min_tdp_title)
        self.lbl_min_tdp = QLabel("4 W")
        self.lbl_min_tdp.setProperty("class", "ValueBadge")
        min_row.addStretch()
        min_row.addWidget(self.lbl_min_tdp)
        l_range.addLayout(min_row)

        self.slider_min_tdp = QSlider(Qt.Orientation.Horizontal)
        self.slider_min_tdp.setRange(3, 12)
        self.slider_min_tdp.valueChanged.connect(lambda v: self.lbl_min_tdp.setText(f"{v} W"))
        self.slider_min_tdp.sliderReleased.connect(self._on_tdp_range_commit)
        l_range.addWidget(self.slider_min_tdp)

        max_row = QHBoxLayout()
        self.lbl_max_tdp_title = QLabel(tr("lbl_max_tdp", self.ui_language))
        max_row.addWidget(self.lbl_max_tdp_title)
        self.lbl_max_tdp = QLabel("40 W")
        self.lbl_max_tdp.setProperty("class", "ValueBadge")
        max_row.addStretch()
        max_row.addWidget(self.lbl_max_tdp)
        l_range.addLayout(max_row)

        self.slider_max_tdp = QSlider(Qt.Orientation.Horizontal)
        self.slider_max_tdp.setRange(15, 45)
        self.slider_max_tdp.valueChanged.connect(lambda v: self.lbl_max_tdp.setText(f"{v} W"))
        self.slider_max_tdp.sliderReleased.connect(self._on_tdp_range_commit)
        l_range.addWidget(self.slider_max_tdp)

        custom_vbox.addWidget(card_range)
        vbox.addStretch()
        return page


    def _build_controls_tab(self) -> QWidget:
        page = QWidget()
        vbox = QVBoxLayout(page)
        vbox.setContentsMargins(2, 4, 6, 8)
        vbox.setSpacing(10)

        self.btn_ip_nav = QPushButton(f"🎮  {tr('lbl_ip_title', self.ui_language)}   ›")
        self.btn_ip_nav.setProperty("class", "ActionBtn")
        self.btn_ip_nav.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 rgba(37, 99, 235, 0.25), stop:1 rgba(14, 165, 233, 0.18));
                border: 1px solid rgba(56, 189, 248, 0.4);
                border-radius: 8px;
                padding: 10px 14px;
                font-weight: 700;
                font-size: 13px;
                color: #38bdf8;
                text-align: left;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 rgba(37, 99, 235, 0.4), stop:1 rgba(14, 165, 233, 0.3));
                border-color: #38bdf8;
            }
        """)
        self.btn_ip_nav.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_ip_nav.clicked.connect(self._open_inputplumber_submenu)
        vbox.addWidget(self.btn_ip_nav)

        card_rgb, l_rgb, self.card_rgb_title = self._make_card(tr("card_rgb", self.ui_language))

        self.chk_power_led = QCheckBox(tr("chk_power_led", self.ui_language))
        self.chk_power_led.toggled.connect(self._on_power_led_toggled)
        l_rgb.addWidget(self.chk_power_led)

        self.chk_rgb_control = QCheckBox(tr("chk_rgb_control", self.ui_language))
        self.chk_rgb_control.toggled.connect(self._on_rgb_control_toggled)
        l_rgb.addWidget(self.chk_rgb_control)

        self.rgb_details_container = QWidget()
        rgb_vbox = QVBoxLayout(self.rgb_details_container)
        rgb_vbox.setContentsMargins(0, 4, 0, 0)
        rgb_vbox.setSpacing(8)

        self.chk_controller_led = QCheckBox(tr("chk_controller_led", self.ui_language))
        self.chk_controller_led.toggled.connect(self._on_controller_led_toggled)
        rgb_vbox.addWidget(self.chk_controller_led)

        self.stick_preview = DualStickRgbWidget(self)
        rgb_vbox.addWidget(self.stick_preview)

        mode_row = QHBoxLayout()
        self.lbl_mode = QLabel(tr("lbl_rgb_mode", self.ui_language))
        self.lbl_mode.setProperty("class", "RowLabel")
        self.cmb_rgb_mode = QComboBox()
        for m in RGB_MODES:
            self.cmb_rgb_mode.addItem(m.capitalize(), m)
        self.cmb_rgb_mode.currentIndexChanged.connect(self._on_rgb_param_changed)
        mode_row.addWidget(self.lbl_mode)
        mode_row.addStretch()
        mode_row.addWidget(self.cmb_rgb_mode)
        rgb_vbox.addLayout(mode_row)

        b_top = QHBoxLayout()
        self.lbl_rgb_b_title = QLabel(tr("lbl_rgb_brightness", self.ui_language))
        b_top.addWidget(self.lbl_rgb_b_title)
        self.lbl_rgb_brightness = QLabel("50%")
        self.lbl_rgb_brightness.setProperty("class", "ValueBadge")
        b_top.addStretch()
        b_top.addWidget(self.lbl_rgb_brightness)
        rgb_vbox.addLayout(b_top)

        self.slider_rgb_brightness = QSlider(Qt.Orientation.Horizontal)
        self.slider_rgb_brightness.setRange(1, 100)
        self.slider_rgb_brightness.setValue(50)
        self.slider_rgb_brightness.valueChanged.connect(self._on_rgb_slider_preview)
        self.slider_rgb_brightness.sliderReleased.connect(self._on_rgb_param_changed)
        rgb_vbox.addWidget(self.slider_rgb_brightness)

        self.speed_widget = QWidget()
        sp_vbox = QVBoxLayout(self.speed_widget)
        sp_vbox.setContentsMargins(0, 0, 0, 0)
        sp_vbox.setSpacing(4)
        sp_top = QHBoxLayout()
        self.lbl_rgb_s_title = QLabel(tr("lbl_rgb_speed", self.ui_language))
        sp_top.addWidget(self.lbl_rgb_s_title)
        self.lbl_rgb_speed = QLabel("50%")
        self.lbl_rgb_speed.setProperty("class", "ValueBadge")
        sp_top.addStretch()
        sp_top.addWidget(self.lbl_rgb_speed)
        sp_vbox.addLayout(sp_top)

        self.slider_rgb_speed = QSlider(Qt.Orientation.Horizontal)
        self.slider_rgb_speed.setRange(1, 100)
        self.slider_rgb_speed.setValue(50)
        self.slider_rgb_speed.valueChanged.connect(self._on_rgb_slider_preview)
        self.slider_rgb_speed.sliderReleased.connect(self._on_rgb_param_changed)
        sp_vbox.addWidget(self.slider_rgb_speed)
        rgb_vbox.addWidget(self.speed_widget)

        self.hue_widget = QWidget()
        hue_vbox = QVBoxLayout(self.hue_widget)
        hue_vbox.setContentsMargins(0, 0, 0, 0)
        hue_vbox.setSpacing(4)
        h_top = QHBoxLayout()
        h_top.addWidget(QLabel("Hue (Color)"))
        self.lbl_rgb_hue = QLabel("0°")
        self.lbl_rgb_hue.setProperty("class", "ValueBadge")
        h_top.addStretch()
        h_top.addWidget(self.lbl_rgb_hue)
        hue_vbox.addLayout(h_top)

        self.slider_rgb_hue = QSlider(Qt.Orientation.Horizontal)
        self.slider_rgb_hue.setObjectName("HueSlider")
        self.slider_rgb_hue.setRange(0, 359)
        self.slider_rgb_hue.setValue(0)
        self.slider_rgb_hue.valueChanged.connect(self._on_rgb_slider_preview)
        self.slider_rgb_hue.sliderReleased.connect(self._on_rgb_param_changed)
        hue_vbox.addWidget(self.slider_rgb_hue)

        self.chk_sync_slider_color = QCheckBox(tr("chk_sync_slider_color", self.ui_language))
        self.chk_sync_slider_color.setStyleSheet("font-size: 11px; font-weight: 600; margin-top: 4px;")
        self.chk_sync_slider_color.toggled.connect(self._on_sync_slider_color_toggled)
        hue_vbox.addWidget(self.chk_sync_slider_color)

        rgb_vbox.addWidget(self.hue_widget)

        l_rgb.addWidget(self.rgb_details_container)
        vbox.addWidget(card_rgb)

        card_remap, l_remap, self.card_remap_title = self._make_card(tr("card_remap", self.ui_language))

        row_rumble = QHBoxLayout()
        self.lbl_rumble = QLabel(tr("lbl_rumble_intensity", self.ui_language))
        self.lbl_rumble.setProperty("class", "RowLabel")
        self.cmb_rumble = QComboBox()
        for r_key, r_code in [("rumble_off", "OFF"), ("rumble_low", "LOW"), ("rumble_medium", "MEDIUM"), ("rumble_high", "HIGH")]:
            self.cmb_rumble.addItem(tr(r_key, self.ui_language), r_code)
        self.cmb_rumble.currentIndexChanged.connect(self._on_rumble_changed)
        row_rumble.addWidget(self.lbl_rumble)
        row_rumble.addStretch()
        row_rumble.addWidget(self.cmb_rumble)
        l_remap.addLayout(row_rumble)

        self.chk_touchpad = QCheckBox(tr("chk_touchpad", self.ui_language))
        self.chk_touchpad.toggled.connect(self._on_touchpad_toggled)
        l_remap.addWidget(self.chk_touchpad)

        self.chk_guide_shortcut = QCheckBox(tr("chk_guide_shortcut", self.ui_language))
        self.chk_guide_shortcut.setChecked(True)
        self.chk_guide_shortcut.toggled.connect(self._on_guide_shortcut_toggled)
        l_remap.addWidget(self.chk_guide_shortcut)

        self.chk_remap_enabled = QCheckBox(tr("chk_remap_enabled", self.ui_language))
        self.chk_remap_enabled.toggled.connect(self._on_remap_changed)
        l_remap.addWidget(self.chk_remap_enabled)

        self.remap_combos = {}
        self.remap_labels = {}
        button_keys = [
            ("Y1", "btn_y1"),
            ("Y2", "btn_y2"),
            ("Y3", "btn_y3"),
            ("M2", "btn_m2"),
            ("M3", "btn_m3"),
        ]
        for btn_code, key_name in button_keys:
            row = QHBoxLayout()
            lbl = QLabel(tr(key_name, self.ui_language))
            lbl.setProperty("class", "RowLabel")
            self.remap_labels[btn_code] = (lbl, key_name)
            cmb = QComboBox()
            for opt_key, act_code in REMAP_OPTIONS:
                display_txt = tr(opt_key, self.ui_language) if opt_key.startswith("remap_") else opt_key
                cmb.addItem(display_txt, act_code)
            cmb.currentIndexChanged.connect(
                lambda idx, b=btn_code: self._on_single_button_remap(b)
            )
            self.remap_combos[btn_code] = cmb
            row.addWidget(lbl)
            row.addStretch()
            row.addWidget(cmb)
            l_remap.addLayout(row)

        vbox.addWidget(card_remap)
        vbox.addStretch()
        return page


    def _build_inputplumber_page(self) -> QWidget:
        page = QWidget()
        vbox = QVBoxLayout(page)
        vbox.setContentsMargins(2, 4, 6, 8)
        vbox.setSpacing(8)

        self.btn_ip_back = QPushButton(f"‹  {tr('btn_ip_back', self.ui_language)}")
        self.btn_ip_back.setProperty("class", "ActionBtn")
        self.btn_ip_back.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 6px;
                padding: 6px 10px;
                font-weight: 700;
                font-size: 11px;
                color: #60a5fa;
                text-align: left;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.15);
            }
        """)
        self.btn_ip_back.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_ip_back.clicked.connect(lambda: self._switch_tab(1))
        vbox.addWidget(self.btn_ip_back)

        card_ip, l_ip, self.card_ip_title = self._make_card(tr("lbl_ip_title", self.ui_language))

        st_row = QHBoxLayout()
        self.lbl_ip_st_title = QLabel("Status:")
        self.lbl_ip_st_title.setProperty("class", "RowLabel")
        self.lbl_ip_st_title.setStyleSheet("font-size: 11px;")
        self.lbl_ip_status = QLabel(tr("lbl_ip_status_standby", self.ui_language))
        self.lbl_ip_status.setStyleSheet("color: #f59e0b; font-weight: 700; font-size: 11px;")
        st_row.addWidget(self.lbl_ip_st_title)
        st_row.addStretch()
        st_row.addWidget(self.lbl_ip_status)
        l_ip.addLayout(st_row)

        m_row = QVBoxLayout()
        m_row.setSpacing(4)
        self.lbl_ip_mode_title = QLabel(tr("lbl_ip_mode", self.ui_language))
        self.lbl_ip_mode_title.setProperty("class", "RowLabel")
        self.lbl_ip_mode_title.setStyleSheet("font-size: 11px; font-weight: 600;")
        self.cmb_ip_mode = QComboBox()
        self.cmb_ip_mode.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cmb_ip_mode.setStyleSheet("font-size: 11px; padding: 4px 6px;")

        self._ip_modes_data = [
            ("default", "Por Defecto (Nativo Legion Go)", "Default (Native Legion Go)"),
            ("xbox-elite", "Xbox Elite", "Xbox Elite"),
            ("xbox-series", "Xbox Series X|S", "Xbox Series X|S"),
            ("ds5", "PlayStation DualSense (PS5)", "PlayStation DualSense (PS5)"),
            ("ds5-edge", "PlayStation DualSense Edge", "PlayStation DualSense Edge"),
            ("deck-uhid", "Steam Deck (Virtual)", "Steam Deck (Virtual)"),
            ("hori-steam", "Hori Steam Controller", "Hori Steam Controller"),
            ("8bitdo-u2", "8BitDo Ultimate 2", "8BitDo Ultimate 2"),
        ]
        is_es = (self.ui_language == "es")
        for m_code, l_es, l_en in self._ip_modes_data:
            self.cmb_ip_mode.addItem(l_es if is_es else l_en, m_code)

        self.cmb_ip_mode.currentIndexChanged.connect(self._on_ip_mode_changed)
        m_row.addWidget(self.lbl_ip_mode_title)
        m_row.addWidget(self.cmb_ip_mode)
        l_ip.addLayout(m_row)

        self.lbl_ip_prof_title = QLabel(tr("lbl_ip_profiles", self.ui_language))
        self.lbl_ip_prof_title.setProperty("class", "SectionTitle")
        self.lbl_ip_prof_title.setStyleSheet("font-size: 10px; margin-top: 4px;")
        l_ip.addWidget(self.lbl_ip_prof_title)

        self.chk_ip_swap_menu = QCheckBox(tr("chk_ip_swap_menu", self.ui_language))
        self.chk_ip_swap_menu.setStyleSheet("font-size: 11px; font-weight: 500; line-height: 1.2;")
        self.chk_ip_swap_vol = QCheckBox(tr("chk_ip_swap_vol", self.ui_language))
        self.chk_ip_swap_vol.setStyleSheet("font-size: 11px; font-weight: 500; line-height: 1.2;")
        self.chk_ip_swap_menu.toggled.connect(self._on_ip_profiles_changed)
        self.chk_ip_swap_vol.toggled.connect(self._on_ip_profiles_changed)
        l_ip.addWidget(self.chk_ip_swap_menu)
        l_ip.addWidget(self.chk_ip_swap_vol)

        l_ip.addSpacing(6)
        self.btn_reset_ctrl = QPushButton("🔄  " + tr("btn_reset_controllers", self.ui_language))
        self.btn_reset_ctrl.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_reset_ctrl.setStyleSheet("""
            QPushButton {
                background: rgba(239, 68, 68, 0.15);
                border: 1px solid rgba(239, 68, 68, 0.35);
                border-radius: 6px;
                padding: 6px 10px;
                font-weight: 700;
                font-size: 11px;
                color: #f87171;
            }
            QPushButton:hover {
                background: rgba(239, 68, 68, 0.28);
                border-color: #f87171;
                color: #ffffff;
            }
        """)
        self.btn_reset_ctrl.clicked.connect(self._on_reset_controllers_clicked)
        l_ip.addWidget(self.btn_reset_ctrl)

        self.lbl_reset_ctrl_desc = QLabel(tr("lbl_reset_controllers_desc", self.ui_language))
        self.lbl_reset_ctrl_desc.setWordWrap(True)
        self.lbl_reset_ctrl_desc.setStyleSheet("color: #64748b; font-size: 10px; margin-top: 1px;")
        l_ip.addWidget(self.lbl_reset_ctrl_desc)

        vbox.addWidget(card_ip)
        vbox.addStretch()
        return page

    def _on_reset_controllers_clicked(self):
        self.btn_reset_ctrl.setEnabled(False)
        self.btn_reset_ctrl.setText("⏳  " + tr("lbl_ip_status_active", self.ui_language))
        QApplication.processEvents()
        try:
            self.backend.call("reset_controllers")
        except Exception:
            pass
        try:
            import controllers
            controllers.reset_controllers()
        except Exception:
            pass

        self._refresh_inputplumber_status()
        if hasattr(self, "stick_preview"):
            self.stick_preview.set_rgb_state(True, "SOLID", 202, 50, 50)
        if hasattr(self, "slider_rgb_brightness"):
            self.slider_rgb_brightness.setValue(50)
        if hasattr(self, "slider_rgb_hue"):
            self.slider_rgb_hue.setValue(202)
        if hasattr(self, "chk_ip_swap_menu"):
            self.chk_ip_swap_menu.setChecked(False)
        if hasattr(self, "chk_ip_swap_vol"):
            self.chk_ip_swap_vol.setChecked(False)

        self.btn_reset_ctrl.setText("✓  " + tr("msg_reset_controllers_success", self.ui_language))
        self.btn_reset_ctrl.setStyleSheet("""
            QPushButton {
                background: rgba(16, 185, 129, 0.2);
                border: 1px solid rgba(16, 185, 129, 0.4);
                border-radius: 8px;
                padding: 10px 14px;
                font-weight: 700;
                font-size: 12px;
                color: #34d399;
            }
        """)
        QTimer.singleShot(3000, self._restore_reset_button_state)

    def _restore_reset_button_state(self):
        if hasattr(self, "btn_reset_ctrl"):
            self.btn_reset_ctrl.setEnabled(True)
            self.btn_reset_ctrl.setText("🔄  " + tr("btn_reset_controllers", self.ui_language))
            self.btn_reset_ctrl.setStyleSheet("""
                QPushButton {
                    background: rgba(239, 68, 68, 0.15);
                    border: 1px solid rgba(239, 68, 68, 0.35);
                    border-radius: 8px;
                    padding: 10px 14px;
                    font-weight: 700;
                    font-size: 12px;
                    color: #f87171;
                }
                QPushButton:hover {
                    background: rgba(239, 68, 68, 0.28);
                    border-color: #f87171;
                    color: #ffffff;
                }
            """)

    def _open_inputplumber_submenu(self):
        self.stack.setCurrentIndex(3)
        self._refresh_inputplumber_status()

    def _refresh_inputplumber_status(self):
        try:
            info = self.backend.call("get_inputplumber_info")
            if not isinstance(info, dict):
                import inputplumber_utils
                info = inputplumber_utils.get_inputplumber_info()

            active = info.get("serviceActive") or info.get("dbusReady")
            if active:
                self.lbl_ip_status.setText(tr("lbl_ip_status_active", self.ui_language))
                self.lbl_ip_status.setStyleSheet("color: #10b981; font-weight: 700; font-size: 12px;")
            else:
                self.lbl_ip_status.setText(tr("lbl_ip_status_standby", self.ui_language))
                self.lbl_ip_status.setStyleSheet("color: #f59e0b; font-weight: 700; font-size: 12px;")
            
            cur_mode = info.get("currentMode", "default")
            idx = self.cmb_ip_mode.findData(cur_mode)
            if idx >= 0:
                self.cmb_ip_mode.blockSignals(True)
                self.cmb_ip_mode.setCurrentIndex(idx)
                self.cmb_ip_mode.blockSignals(False)

            active_p = info.get("activeProfiles", [])
            self.chk_ip_swap_menu.blockSignals(True)
            self.chk_ip_swap_vol.blockSignals(True)
            self.chk_ip_swap_menu.setChecked("swap_menu_buttons" in active_p)
            self.chk_ip_swap_vol.setChecked("swap_volume" in active_p)
            self.chk_ip_swap_menu.blockSignals(False)
            self.chk_ip_swap_vol.blockSignals(False)
        except Exception as e:
            print(f"[LeGO Suite Desktop] _refresh_inputplumber_status error: {e}")

    def _on_ip_profiles_changed(self):
        active = []
        if self.chk_ip_swap_menu.isChecked():
            active.append("swap_menu_buttons")
        if self.chk_ip_swap_vol.isChecked():
            active.append("swap_volume")
        try:
            self.backend.call("set_inputplumber_profiles", active)
        except Exception:
            pass
        try:
            import inputplumber_utils
            inputplumber_utils.set_active_profiles(active)
        except Exception:
            pass
        self.settings_cache["inputPlumberActiveProfiles"] = active
        self._mark_saved()

    def _on_ip_mode_changed(self, idx: int):
        mode = self.cmb_ip_mode.currentData()
        if not mode:
            return
        try:
            self.backend.call("set_inputplumber_mode", mode)
        except Exception:
            pass
        try:
            import inputplumber_utils
            inputplumber_utils.set_controller_mode(mode)
        except Exception:
            pass
        self.settings_cache["inputPlumberMode"] = mode
        self._mark_saved()


    def _build_screen_tab(self) -> QWidget:
        page = QWidget()
        vbox = QVBoxLayout(page)
        vbox.setContentsMargins(2, 4, 6, 8)
        vbox.setSpacing(10)

        es = (self.ui_language == "es")

        card_rot, l_rot, self.card_sensor_title = self._make_card(tr("card_sensor", self.ui_language))

        status_row = QHBoxLayout()
        self.lbl_s_info = QLabel(tr("lbl_hwdb_status_title", self.ui_language))
        self.lbl_s_info.setProperty("class", "RowLabel")
        self.lbl_hwdb_status = QLabel("Comprobando..." if es else "Checking...")
        status_row.addWidget(self.lbl_s_info)
        status_row.addStretch()
        status_row.addWidget(self.lbl_hwdb_status)
        l_rot.addLayout(status_row)

        self.desc_hwdb_lbl = QLabel(tr("lbl_hwdb_desc", self.ui_language))
        self.desc_hwdb_lbl.setStyleSheet("color: #9ca3af; font-size: 11px;")
        self.desc_hwdb_lbl.setWordWrap(True)
        l_rot.addWidget(self.desc_hwdb_lbl)

        btn_row = QHBoxLayout()
        self.btn_inject_hwdb = QPushButton("Inyectar Sensor (Sudo en Konsole)" if es else "Inject Sensor (Sudo in Konsole)")
        self.btn_inject_hwdb.setProperty("class", "ActionBtn")
        self.btn_inject_hwdb.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_inject_hwdb.clicked.connect(self._inject_hwdb_sensor)
        btn_row.addWidget(self.btn_inject_hwdb)
        l_rot.addLayout(btn_row)

        self.lbl_auto_rotate_hint = QLabel(tr("lbl_auto_rotate_hint", self.ui_language))
        self.lbl_auto_rotate_hint.setStyleSheet("color: #60a5fa; font-weight: 600; font-size: 11px; padding: 4px 0px;")
        self.lbl_auto_rotate_hint.setWordWrap(True)
        l_rot.addWidget(self.lbl_auto_rotate_hint)

        vbox.addWidget(card_rot)
        vbox.addStretch()

        self._check_hwdb_status()
        return page

    def _open_theme_dialog(self):
        dlg = ThemeSettingsDialog(
            self,
            self.ui_bg_color,
            self.ui_content_color,
            self.ui_accent_color,
            self.ui_language,
            self._apply_and_save_theme,
            getattr(self, "dock_mode_enabled", True),
            getattr(self, "ui_content_color_2", DEFAULT_CONTENT_COLOR_2),
        )
        dlg.setStyleSheet(build_dynamic_stylesheet(self.ui_bg_color, self.ui_content_color, self.ui_accent_color, getattr(self, "ui_content_color_2", DEFAULT_CONTENT_COLOR_2)))
        dlg.exec()

    def _apply_and_save_theme(
        self,
        bg_color: str,
        content_color: str,
        accent_color: str = DEFAULT_ACCENT_COLOR,
        lang: str = "es",
        dock_mode: bool = True,
        content_color_2: str = "",
    ):
        self.ui_bg_color = bg_color
        self.ui_content_color = content_color
        self.ui_content_color_2 = content_color_2 or _lighten_hex(content_color, 1.15)
        self.ui_accent_color = accent_color
        self.ui_language = lang
        self.dock_mode_enabled = bool(dock_mode)
        if hasattr(self, "btn_dock"):
            self.btn_dock.setVisible(self.dock_mode_enabled)
        self.setStyleSheet(build_dynamic_stylesheet(bg_color, content_color, accent_color, self.ui_content_color_2))
        self.backend.call(
            "save_settings",
            {
                "language": lang,
                "desktopTheme": {
                    "bgColor": bg_color,
                    "contentColor": content_color,
                    "contentColor2": self.ui_content_color_2,
                    "accentColor": accent_color,
                    "language": lang,
                    "dockModeEnabled": self.dock_mode_enabled,
                    "topRightTouchGesture": self.dock_mode_enabled,
                }
            },
        )
        self._update_ui_texts()
        self._mark_saved()


    def _set_skip_taskbar(self, skip: bool):
        """
        Dynamically hides or shows the window icon in KDE Plasma's Task Manager
        (gestor de tareas) via X11 EWMH _NET_WM_STATE_SKIP_TASKBAR.
        """
        try:
            win_id = str(int(self.winId()))
            if win_id and win_id != "0":
                if skip:
                    subprocess.run(
                        ["xprop", "-id", win_id, "-f", "_NET_WM_STATE", "32a", "-set", "_NET_WM_STATE", "_NET_WM_STATE_SKIP_TASKBAR"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        check=False,
                    )
                else:
                    subprocess.run(
                        ["xprop", "-id", win_id, "-remove", "_NET_WM_STATE"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        check=False,
                    )
        except Exception:
            pass

    def collapse_to_dock(self):
        if getattr(self, "is_collapsed", False):
            return
        self.is_collapsed = True

        screen = QApplication.primaryScreen() or self.screen()
        geo = screen.availableGeometry() if screen else QRect(0, 0, 1138, 711)
        sw = geo.width()
        sh = geo.height()
        panel_w = 490
        panel_h = min(720, max(520, sh - 20))

        handle_w = 54
        handle_h = 150
        cur_geom = self.geometry()
        dock_x = max(0, geo.x() + sw - handle_w)
        dock_y = geo.y() + max(10, (sh - handle_h) // 2)

        if hasattr(self, "_anim_dock") and self._anim_dock:
            self._anim_dock.stop()

        self.setMinimumSize(0, 0)
        self.setMaximumSize(16777215, 16777215)

        self._anim_dock = QPropertyAnimation(self, b"geometry")
        self._anim_dock.setDuration(240)
        self._anim_dock.setStartValue(cur_geom)
        self._anim_dock.setEndValue(QRect(dock_x, dock_y, handle_w, handle_h))
        self._anim_dock.setEasingCurve(QEasingCurve.Type.InOutCubic)

        def _on_collapse_done():
            try:
                self._anim_dock.finished.disconnect(_on_collapse_done)
            except Exception:
                pass
            if hasattr(self, "window_frame"):
                self.window_frame.hide()
            if hasattr(self, "dock_handle"):
                self.dock_handle.setGeometry(0, 0, handle_w, handle_h)
                self.dock_handle.show()
            self.setGeometry(dock_x, dock_y, handle_w, handle_h)
            self._set_skip_taskbar(True)

        self._anim_dock.finished.connect(_on_collapse_done)
        self._anim_dock.start()

    def expand_from_dock(self):
        if not getattr(self, "is_collapsed", False):
            return
        self.is_collapsed = False

        screen = QApplication.primaryScreen() or self.screen()
        geo = screen.availableGeometry() if screen else QRect(0, 0, 1138, 711)
        sw = geo.width()
        sh = geo.height()
        panel_w = 490
        panel_h = min(720, max(520, sh - 20))
        expanded_x = max(0, geo.x() + sw - panel_w - 4)
        target_y = geo.y() + 10

        handle_w = 36
        handle_h = 130
        cur_geom = self.geometry()

        if hasattr(self, "_anim_dock") and self._anim_dock:
            self._anim_dock.stop()

        self._set_skip_taskbar(False)

        if hasattr(self, "dock_handle"):
            self.dock_handle.hide()
        if hasattr(self, "window_frame"):
            self.window_frame.setGeometry(0, 0, panel_w, panel_h)
            self.window_frame.show()

        self.setMinimumSize(0, 0)
        self.setMaximumSize(16777215, 16777215)

        self._anim_dock = QPropertyAnimation(self, b"geometry")
        self._anim_dock.setDuration(240)
        self._anim_dock.setStartValue(cur_geom)
        self._anim_dock.setEndValue(QRect(expanded_x, target_y, panel_w, panel_h))
        self._anim_dock.setEasingCurve(QEasingCurve.Type.OutCubic)

        def _on_expand_done():
            try:
                self._anim_dock.finished.disconnect(_on_expand_done)
            except Exception:
                pass
            self.setGeometry(expanded_x, target_y, panel_w, panel_h)
            if hasattr(self, "window_frame"):
                self.window_frame.setGeometry(0, 0, panel_w, panel_h)
            self.raise_()
            self.activateWindow()

        self._anim_dock.finished.connect(_on_expand_done)
        self._anim_dock.start()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        w = self.width()
        h = self.height()
        if getattr(self, "is_collapsed", False):
            if hasattr(self, "dock_handle"):
                self.dock_handle.setGeometry(0, 0, w, h)
        else:
            if hasattr(self, "window_frame"):
                is_animating = (
                    hasattr(self, "_anim_dock")
                    and self._anim_dock
                    and self._anim_dock.state() == QPropertyAnimation.State.Running
                )
                if not is_animating:
                    self.window_frame.setGeometry(0, 0, w, h)

    def showEvent(self, event):
        super().showEvent(event)
        if not getattr(self, "_initial_pos_set", False):
            self._initial_pos_set = True
            self._position_top_right()


    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if event.position().y() <= 85:
                self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and hasattr(self, "_drag_pos") and self._drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        super().mouseReleaseEvent(event)

    def _position_top_right(self):
        screen = QApplication.primaryScreen() or self.screen()
        if not screen:
            return
        geo = screen.availableGeometry()
        panel_w = 490
        panel_h = min(720, max(520, geo.height() - 20))
        target_x = max(0, geo.x() + geo.width() - panel_w - 4)
        target_y = geo.y() + 10
        self.setGeometry(target_x, target_y, panel_w, panel_h)
        if hasattr(self, "window_frame"):
            self.window_frame.setGeometry(0, 0, panel_w, panel_h)

    def toggle_slide_panel(self):
        """
        Reveals the window in the top-right corner with smooth animation,
        or slides it away to hide if already open and visible.
        """
        if self.isVisible() and not self.isMinimized() and self.windowOpacity() > 0.7:
            if getattr(self, "is_collapsed", False):
                self.expand_from_dock()
            else:
                self._slide_out()
        else:
            if getattr(self, "is_collapsed", False):
                self.expand_from_dock()
            else:
                self._slide_in()

    def _slide_in(self):
        if hasattr(self, "_anim_fade") and self._anim_fade:
            self._anim_fade.stop()

        self.is_collapsed = False
        if hasattr(self, "dock_handle"):
            self.dock_handle.hide()
        if hasattr(self, "window_frame"):
            self.window_frame.show()

        self._position_top_right()
        self.refresh_from_backend(force=False)
        self.setWindowOpacity(0.0)
        self.show()
        self.raise_()
        self.activateWindow()

        self._anim_fade = QPropertyAnimation(self, b"windowOpacity")
        self._anim_fade.setDuration(220)
        self._anim_fade.setStartValue(0.0)
        self._anim_fade.setEndValue(1.0)
        self._anim_fade.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim_fade.start()

    def _slide_out(self):
        if hasattr(self, "_anim_fade") and self._anim_fade:
            self._anim_fade.stop()

        self._anim_fade = QPropertyAnimation(self, b"windowOpacity")
        self._anim_fade.setDuration(180)
        self._anim_fade.setStartValue(self.windowOpacity())
        self._anim_fade.setEndValue(0.0)
        self._anim_fade.setEasingCurve(QEasingCurve.Type.InCubic)
        self._anim_fade.finished.connect(self._on_slide_out_finished)
        self._anim_fade.start()

    def _on_slide_out_finished(self):
        try:
            self._anim_fade.finished.disconnect(self._on_slide_out_finished)
        except Exception:
            pass
        self.hide()
        self.setWindowOpacity(1.0)


    def _build_tray(self):
        self.tray = QSystemTrayIcon(self)
        if LOGO_ICON_PATH.exists():
            self.tray.setIcon(QIcon(str(LOGO_ICON_PATH)))
        else:
            pix = QPixmap(64, 64)
            pix.fill(QColor("#000000"))
            self.tray.setIcon(QIcon(pix))

        self.tray.setToolTip("LeGO Suite v0.198")

        menu = QMenu()
        menu.setStyleSheet(
            """
            QMenu {
                background-color: #181b24;
                color: #f3f4f6;
                border: 1px solid #2e3446;
                padding: 6px;
            }
            QMenu::item {
                padding: 6px 18px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #3b82f6;
                color: #ffffff;
            }
            """
        )

        act_toggle = QAction("Abrir / Ocultar LeGO Suite", self)
        act_toggle.triggered.connect(self.toggle_window)
        menu.addAction(act_toggle)
        menu.addSeparator()

        tdp_menu = menu.addMenu("TDP Rápido")
        for w_val in (8, 12, 15, 20, 25, 30):
            act = QAction(f"{w_val} W", self)
            act.triggered.connect(lambda checked=False, v=w_val: self._set_quick_tdp(v))
            tdp_menu.addAction(act)

        bat_menu = menu.addMenu("Límite de Carga de Batería")
        act_bat_off = QAction("Desactivado (100%)", self)
        act_bat_off.triggered.connect(lambda: self._set_quick_charge_limit(False, 80))
        bat_menu.addAction(act_bat_off)
        act_bat_80 = QAction("Limitar al 80%", self)
        act_bat_80.triggered.connect(lambda: self._set_quick_charge_limit(True, 80))
        bat_menu.addAction(act_bat_80)

        menu.addSeparator()

        self.act_autostart = QAction("Iniciar con el Escritorio", self)
        self.act_autostart.setCheckable(True)
        self.act_autostart.setChecked(self._is_autostart_enabled())
        self.act_autostart.triggered.connect(self._toggle_autostart)
        menu.addAction(self.act_autostart)

        menu.addSeparator()
        act_quit = QAction("Salir de LeGO Suite", self)
        act_quit.triggered.connect(self._quit_app)
        menu.addAction(act_quit)

        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

    def _on_tray_activated(self, reason):
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self.toggle_slide_panel()

    def toggle_window(self):
        self.toggle_slide_panel()

    def closeEvent(self, event):
        event.ignore()
        self._slide_out()
        if not self._first_close_notified and self.tray.isVisible():
            self._first_close_notified = True
            self.tray.showMessage(
                "LeGO Suite sigue activo",
                "La aplicación permanece en reposo en el panel de miniaplicaciones de la barra.",
                QSystemTrayIcon.MessageIcon.Information,
                3000,
            )

    def _quit_app(self):
        self.tray.hide()
        QApplication.quit()

    def _autostart_path(self) -> Path:
        return Path.home() / ".config" / "autostart" / "lego-suite-desktop.desktop"

    def _is_autostart_enabled(self) -> bool:
        return self._autostart_path().exists()

    def _toggle_autostart(self, enabled: bool):
        p = self._autostart_path()
        if enabled:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(
                f"[Desktop Entry]\n"
                f"Type=Application\n"
                f"Name=LeGO Suite Desktop\n"
                f"Comment=LeGO Suite Tray Companion\n"
                f"Exec=env QT_QPA_PLATFORM=xcb /usr/bin/python3 \"{ Path(__file__).resolve() }\" --tray\n"
                f"Icon={LOGO_ICON_PATH}\n"
                f"Terminal=false\n"
                f"Categories=Utility;HardwareSettings;\n",
                encoding="utf-8",
            )
        else:
            if p.exists():
                p.unlink()


    def _switch_tab(self, index: int):
        self.stack.setCurrentIndex(index)
        for idx, btn in enumerate((self.btn_tab_tdp, self.btn_tab_controls, self.btn_tab_screen)):
            btn.setProperty("active", "true" if idx == index else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _check_external_sync(self):
        try:
            mtime = 0.0
            if SETTINGS_FILE.exists():
                mtime = max(mtime, SETTINGS_FILE.stat().st_mtime)
            if TDP_FILE.exists():
                mtime = max(mtime, TDP_FILE.stat().st_mtime)
            if mtime > self._last_mtime:
                self.refresh_from_backend(force=False)
        except Exception:
            pass

    def _enforce_charge_limit_tick(self):
        try:
            if self.chk_charge_limit.isChecked():
                self.backend.call("set_charge_limit", True, 80)
        except Exception:
            pass

    def refresh_from_backend(self, force: bool = False):
        if not force and (
            self.slider_tdp.isSliderDown()
            or self.slider_rgb_brightness.isSliderDown()
            or self.slider_rgb_speed.isSliderDown()
            or self.slider_rgb_hue.isSliderDown()
        ):
            return

        settings = self.backend.call("get_settings")
        if not isinstance(settings, dict):
            try:
                if SETTINGS_FILE.exists():
                    settings = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
                else:
                    settings = {}
            except Exception:
                settings = {}

        if not settings.get("tdpProfiles") and TDP_FILE.exists():
            try:
                settings["tdpProfiles"] = json.loads(TDP_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass

        if not self.power_info:
            pinfo = self.backend.call("get_power_control_info")
            if isinstance(pinfo, dict):
                self.power_info = pinfo

        try:
            mtime = 0.0
            if SETTINGS_FILE.exists():
                mtime = max(mtime, SETTINGS_FILE.stat().st_mtime)
            if TDP_FILE.exists():
                mtime = max(mtime, TDP_FILE.stat().st_mtime)
            if mtime > 0.0:
                self._last_mtime = mtime
        except Exception:
            pass

        self.settings_cache = settings
        self._apply_settings_to_ui(settings)

    def _apply_settings_to_ui(self, s: dict):
        self._updating_ui = True
        try:
            theme = s.get("desktopTheme") or {}
            new_bg = theme.get("bgColor") or DEFAULT_BG_COLOR
            new_ct = theme.get("contentColor") or DEFAULT_CONTENT_COLOR
            new_ct2 = theme.get("contentColor2") or _lighten_hex(new_ct, 1.15)
            new_ac = theme.get("accentColor") or DEFAULT_ACCENT_COLOR
            new_lang = s.get("language") or theme.get("language") or "es"
            new_dock = theme.get("dockModeEnabled", theme.get("topRightTouchGesture", True))
            self.dock_mode_enabled = bool(new_dock)
            if hasattr(self, "btn_dock"):
                self.btn_dock.setVisible(self.dock_mode_enabled)

            if (new_bg != self.ui_bg_color or new_ct != self.ui_content_color 
                or new_ct2 != getattr(self, "ui_content_color_2", "")
                or new_ac != self.ui_accent_color or new_lang != self.ui_language):
                self.ui_bg_color = new_bg
                self.ui_content_color = new_ct
                self.ui_content_color_2 = new_ct2
                self.ui_accent_color = new_ac
                self.ui_language = new_lang
                self.setStyleSheet(build_dynamic_stylesheet(new_bg, new_ct, new_ac, new_ct2))
                self._update_ui_texts()

            mode_txt = tr("status_decky_rpc" if self.backend.rpc_available else "status_local_sync", self.ui_language)
            self.version_label.setText(f"Version 0.198 • {mode_txt}")

            current_mode = str(s.get("tdpMode", "custom")).lower()
            if hasattr(self, "tdp_mode_buttons"):
                for m_key, btn in self.tdp_mode_buttons.items():
                    is_active = (m_key == current_mode)
                    col = getattr(self, "tdp_mode_colors", {}).get(m_key, "#3b82f6")
                    if is_active:
                        btn.setStyleSheet(f"background-color: {col}; color: #000000; font-size: 11px; font-weight: 800; padding: 7px 4px; border-radius: 6px; border: none;")
                    else:
                        btn.setStyleSheet("background-color: rgba(255, 255, 255, 0.08); color: #9ca3af; font-size: 11px; font-weight: 600; padding: 7px 4px; border-radius: 6px; border: 1px solid rgba(255,255,255,0.08);")

            if hasattr(self, "custom_tdp_container"):
                is_custom = (current_mode == "custom")
                self.custom_tdp_container.setEnabled(is_custom)
                if is_custom:
                    self.custom_tdp_container.setStyleSheet("")
                else:
                    self.custom_tdp_container.setStyleSheet("QWidget { color: #6b7280; } QSlider::groove:horizontal { background: #1f2937; } QSlider::handle:horizontal { background: #4b5563; } QPushButton { background-color: rgba(255,255,255,0.03); color: #6b7280; border-color: rgba(255,255,255,0.03); }")

            min_tdp = int(s.get("minTdp", 4))
            max_tdp = int(s.get("maxTdp", 40))
            self.slider_min_tdp.setValue(min_tdp)
            self.slider_max_tdp.setValue(max_tdp)
            self.lbl_min_tdp.setText(f"{min_tdp} W")
            self.lbl_max_tdp.setText(f"{max_tdp} W")

            self.slider_tdp.setRange(min_tdp, max_tdp)
            tdp_prof = (s.get("tdpProfiles") or {}).get("default")
            if not tdp_prof and TDP_FILE.exists():
                try:
                    tdp_prof = (json.loads(TDP_FILE.read_text(encoding="utf-8")) or {}).get("default")
                except Exception:
                    pass
            tdp_prof = tdp_prof or {}
            
            if "tdp" in tdp_prof:
                tdp_val = int(tdp_prof["tdp"])
            else:
                tdp_val = self.slider_tdp.value()
            self.slider_tdp.setValue(tdp_val)
            self.lbl_tdp_val.setText(f"{tdp_val} W")

            self.chk_cpu_boost.setChecked(bool(tdp_prof.get("cpuBoost", False)))
            self.chk_smt.setChecked(bool(tdp_prof.get("smt", True)))

            scaling_driver = self.power_info.get("scalingDriver") or "amd-pstate-epp"
            p_controls = (tdp_prof.get("powerControls") or {}).get(scaling_driver) or {}
            gov = p_controls.get("powerGovernor", "powersave")
            epp = p_controls.get("epp", "balance_power")
            if self.cmb_governor.findText(gov) >= 0:
                self.cmb_governor.setCurrentText(gov)
            if self.cmb_epp.findText(epp) >= 0:
                self.cmb_epp.setCurrentText(epp)

            c_enabled = bool(s.get("chargeLimitEnabled", False))
            c_val = 80
            self.chk_charge_limit.setChecked(c_enabled)
            self.chk_charge_limit.setText(tr("chk_charge_limit", self.ui_language))

            fan_enabled = bool(s.get("customFanCurvesEnabled", False))
            self.chk_fan_enabled.setChecked(fan_enabled)
            self.fan_controls_container.setVisible(fan_enabled)
            fan_prof = (s.get("fan") or {}).get("default") or {}
            self.chk_full_fan.setChecked(bool(fan_prof.get("fullFanSpeedEnabled", False)))
            for temp in FAN_TEMPS:
                spd = int(fan_prof.get(temp, 50))
                self.fan_sliders[temp].setValue(spd)
                self.fan_labels[temp].setText(f"{spd}%")
                self.fan_sliders[temp].setEnabled(not self.chk_full_fan.isChecked())

            self.chk_power_led.setChecked(bool(s.get("powerLedEnabled", True)))
            rgb_ctrl = bool(s.get("enableRgbControl", False))
            self.chk_rgb_control.setChecked(rgb_ctrl)
            self.rgb_details_container.setVisible(rgb_ctrl)

            rgb_right = ((s.get("rgb") or {}).get("default") or {}).get("RIGHT") or {}
            led_on = bool(rgb_right.get("enabled", False))
            mode = str(rgb_right.get("mode", "SOLID")).upper()
            brightness = int(rgb_right.get("brightness", 50))
            speed = int(rgb_right.get("speed", 50))
            hue = int(rgb_right.get("hue", 0))

            self.chk_controller_led.setChecked(led_on)
            m_idx = self.cmb_rgb_mode.findData(mode)
            if m_idx >= 0:
                self.cmb_rgb_mode.setCurrentIndex(m_idx)
            self.slider_rgb_brightness.setValue(brightness)
            self.lbl_rgb_brightness.setText(f"{brightness}%")
            self.slider_rgb_speed.setValue(speed)
            self.lbl_rgb_speed.setText(f"{speed}%")
            self.slider_rgb_hue.setValue(hue)
            self.lbl_rgb_hue.setText(f"{hue}°")

            if hasattr(self, "chk_sync_slider_color"):
                self.chk_sync_slider_color.blockSignals(True)
                self.chk_sync_slider_color.setChecked(False)
                self.chk_sync_slider_color.blockSignals(False)

            self.speed_widget.setVisible(led_on and mode != "SOLID")
            self.hue_widget.setVisible(led_on and mode not in ("DYNAMIC", "SPIRAL"))
            self.stick_preview.setVisible(led_on)
            self.stick_preview.set_rgb_state(led_on, mode, hue, brightness, speed)

            remap_on = bool(s.get("controllerRemappingEnabled", False))
            self.chk_remap_enabled.setChecked(remap_on)
            ctrl_prof = (s.get("controller") or {}).get("default") or {}
            self.chk_touchpad.setChecked(bool(ctrl_prof.get("TOUCHPAD", True)))
            guide_shortcut_on = bool(ctrl_prof.get("GUIDE_SHORTCUT", True))
            self.chk_guide_shortcut.setChecked(guide_shortcut_on)
            if hasattr(self, "_controller_thread"):
                self._controller_thread.enabled = guide_shortcut_on
            rumble_val = str(ctrl_prof.get("RUMBLE", "MEDIUM")).upper()
            idx_rumble = self.cmb_rumble.findData(rumble_val)
            if idx_rumble >= 0:
                self.cmb_rumble.setCurrentIndex(idx_rumble)
            for btn_code, cmb in self.remap_combos.items():
                act_val = ctrl_prof.get(btn_code, "DISABLED")
                idx = cmb.findData(act_val)
                if idx >= 0:
                    cmb.setCurrentIndex(idx)
                cmb.setEnabled(remap_on)

            ip_mode = s.get("inputPlumberMode")
            if not ip_mode:
                try:
                    import inputplumber_utils
                    ip_mode = inputplumber_utils.get_current_mode()
                except Exception:
                    ip_mode = "default"
            if ip_mode and hasattr(self, "cmb_ip_mode"):
                idx_m = self.cmb_ip_mode.findData(ip_mode)
                if idx_m >= 0:
                    self.cmb_ip_mode.blockSignals(True)
                    self.cmb_ip_mode.setCurrentIndex(idx_m)
                    self.cmb_ip_mode.blockSignals(False)

            active_p = s.get("inputPlumberActiveProfiles")
            if active_p is None:
                try:
                    import inputplumber_utils
                    active_p = inputplumber_utils.get_active_profiles()
                except Exception:
                    active_p = []
            if hasattr(self, "chk_ip_swap_menu"):
                self.chk_ip_swap_menu.blockSignals(True)
                self.chk_ip_swap_menu.setChecked("swap_menu_buttons" in active_p)
                self.chk_ip_swap_menu.blockSignals(False)
            if hasattr(self, "chk_ip_swap_vol"):
                self.chk_ip_swap_vol.blockSignals(True)
                self.chk_ip_swap_vol.setChecked("swap_volume" in active_p)
                self.chk_ip_swap_vol.blockSignals(False)

            charge_disp = c_val if c_enabled else 100
            self.tray.setToolTip(
                tr("tray_tooltip", self.ui_language).format(tdp=tdp_val, charge=charge_disp)
            )
        finally:
            self._updating_ui = False

    def _update_live_temps_and_fan(self):
        try:
            is_full_fan = hasattr(self, "chk_full_fan") and self.chk_full_fan.isChecked()
            temps = self.backend.call("get_temperatures")
            if isinstance(temps, dict):
                cpu_t = temps.get("cpu")
                gpu_t = temps.get("gpu")
                rpm_v = temps.get("rpm")

                if is_full_fan and (rpm_v is None or int(rpm_v) < 6000):
                    rpm_v = 6500

                if cpu_t is not None and hasattr(self, "lbl_cpu_temp_val"):
                    t_val = float(cpu_t)
                    color = "#38bdf8" if t_val < 60 else ("#facc15" if t_val < 75 else "#ef4444")
                    bg_color = "rgba(56, 189, 248, 0.12)" if t_val < 60 else ("rgba(250, 204, 21, 0.12)" if t_val < 75 else "rgba(239, 68, 68, 0.15)")
                    self.lbl_cpu_temp_val.setStyleSheet(f"color: {color}; font-weight: 800; font-size: 12px; background: {bg_color}; padding: 2px 6px; border-radius: 5px;")
                    self.lbl_cpu_temp_val.setText(f"{t_val:.1f} °C")

                if gpu_t is not None and hasattr(self, "lbl_gpu_temp_val"):
                    t_val = float(gpu_t)
                    color = "#38bdf8" if t_val < 60 else ("#facc15" if t_val < 75 else "#ef4444")
                    bg_color = "rgba(56, 189, 248, 0.12)" if t_val < 60 else ("rgba(250, 204, 21, 0.12)" if t_val < 75 else "rgba(239, 68, 68, 0.15)")
                    self.lbl_gpu_temp_val.setStyleSheet(f"color: {color}; font-weight: 800; font-size: 12px; background: {bg_color}; padding: 2px 6px; border-radius: 5px;")
                    self.lbl_gpu_temp_val.setText(f"{t_val:.1f} °C")

                if rpm_v is not None:
                    val_rpm = int(rpm_v)
                    if hasattr(self, "fan_anim_widget"):
                        self.fan_anim_widget.set_rpm(val_rpm)
                    if hasattr(self, "lbl_fan_rpm_val"):
                        color = "#38bdf8" if val_rpm < 4000 else ("#facc15" if val_rpm < 5500 else "#ef4444")
                        bg_color = "rgba(56, 189, 248, 0.12)" if val_rpm < 4000 else ("rgba(250, 204, 21, 0.12)" if val_rpm < 5500 else "rgba(239, 68, 68, 0.15)")
                        self.lbl_fan_rpm_val.setStyleSheet(f"color: {color}; font-weight: 800; font-size: 12px; background: {bg_color}; padding: 2px 6px; border-radius: 5px;")
                        self.lbl_fan_rpm_val.setText(f"{val_rpm} RPM")
        except Exception:
            pass


    def _on_tdp_mode_selected(self, mode: str):
        if self._updating_ui:
            return
        self.backend.call("set_tdp_mode", mode)
        if hasattr(self, "tdp_mode_buttons"):
            for m_key, btn in self.tdp_mode_buttons.items():
                is_active = (m_key == mode)
                col = getattr(self, "tdp_mode_colors", {}).get(m_key, "#3b82f6")
                if is_active:
                    btn.setStyleSheet(f"background-color: {col}; color: #000000; font-size: 11px; font-weight: 800; padding: 7px 4px; border-radius: 6px; border: none;")
                else:
                    btn.setStyleSheet("background-color: rgba(255, 255, 255, 0.08); color: #9ca3af; font-size: 11px; font-weight: 600; padding: 7px 4px; border-radius: 6px; border: 1px solid rgba(255,255,255,0.08);")
        if hasattr(self, "custom_tdp_container"):
            is_custom = (mode == "custom")
            self.custom_tdp_container.setEnabled(is_custom)
            if is_custom:
                self.custom_tdp_container.setStyleSheet("")
            else:
                self.custom_tdp_container.setStyleSheet("QWidget { color: #6b7280; } QSlider::groove:horizontal { background: #1f2937; } QSlider::handle:horizontal { background: #4b5563; } QPushButton { background-color: rgba(255,255,255,0.03); color: #6b7280; border-color: rgba(255,255,255,0.03); }")
        self._mark_saved()

    def _write_tdp_file_direct(self, watts: int):
        """Escribe directamente en tdp.json bajo 'default' para persistencia inmediata."""
        try:
            tdp_data = {}
            if TDP_FILE.exists():
                try:
                    tdp_data = json.loads(TDP_FILE.read_text(encoding="utf-8")) or {}
                except Exception:
                    tdp_data = {}
            if not isinstance(tdp_data, dict):
                tdp_data = {}
            default_prof = tdp_data.setdefault("default", {})
            default_prof["tdp"] = watts
            TDP_FILE.write_text(json.dumps(tdp_data, indent=4), encoding="utf-8")
        except Exception as e:
            print(f"[LeGO Suite Desktop] Error writing tdp.json directly: {e}")

    def _on_tdp_slider_preview(self, val: int):
        self.lbl_tdp_val.setText(f"{val} W")

    def _on_tdp_slider_commit(self):
        if self._updating_ui:
            return
        val = self.slider_tdp.value()
        self.lbl_tdp_val.setText(f"{val} W")
        self._write_tdp_file_direct(val)
        self.backend.call("persist_tdp", val, "default")
        self._mark_saved()

    def _set_quick_tdp(self, watts: int):
        self.slider_tdp.setValue(watts)
        self.lbl_tdp_val.setText(f"{watts} W")
        self._write_tdp_file_direct(watts)
        self.backend.call("persist_tdp", watts, "default")
        self._mark_saved()

    def _on_cpu_boost_toggled(self, checked: bool):
        if self._updating_ui:
            return
        self.backend.call("persist_cpu_boost", checked, "default")
        self._mark_saved()

    def _on_smt_toggled(self, checked: bool):
        if self._updating_ui:
            return
        self.backend.call("persist_smt", checked, "default")
        self._mark_saved()

    def _on_governor_changed(self, gov: str):
        if self._updating_ui or not gov:
            return
        driver = self.power_info.get("scalingDriver") or "amd-pstate-epp"
        self.backend.call(
            "set_power_governor",
            {"scalingDriver": driver, "powerGovernor": gov},
            "default",
        )
        self._mark_saved()

    def _on_epp_changed(self, epp: str):
        if self._updating_ui or not epp:
            return
        driver = self.power_info.get("scalingDriver") or "amd-pstate-epp"
        self.backend.call(
            "set_epp",
            {"scalingDriver": driver, "epp": epp},
            "default",
        )
        self._mark_saved()

    def _on_tdp_range_commit(self):
        if self._updating_ui:
            return
        min_v = self.slider_min_tdp.value()
        max_v = self.slider_max_tdp.value()
        self.backend.call("set_setting", "minTdp", min_v)
        self.backend.call("set_setting", "maxTdp", max_v)
        self.slider_tdp.setRange(min_v, max_v)
        self._mark_saved()


    def _on_charge_limit_toggled(self, checked: bool):
        if self._updating_ui:
            return
        self.chk_charge_limit.setText(tr("chk_charge_limit", self.ui_language))
        self.backend.call("set_charge_limit", checked, 80)
        self._mark_saved()

    def _set_quick_charge_limit(self, enabled: bool, pct: int):
        self.backend.call("set_charge_limit", enabled, pct)
        self.refresh_from_backend(force=True)


    def _on_fan_enabled_toggled(self, checked: bool):
        if self._updating_ui:
            return
        self.fan_controls_container.setVisible(checked)
        if not checked:
            self.backend.call("disable_fan_profiles", True)
        else:
            self._on_fan_curve_commit()
        self._mark_saved()

    def _on_full_fan_toggled(self, checked: bool):
        for sl in self.fan_sliders.values():
            sl.setEnabled(not checked)
        if self._updating_ui:
            return
        self._on_fan_curve_commit()

    def _on_fan_point_preview(self, temp: str, val: int):
        self.fan_labels[temp].setText(f"{val}%")

    def _on_fan_curve_commit(self):
        if self._updating_ui:
            return
        default_fan = dict((self.settings_cache.get("fan") or {}).get("default") or {})
        default_fan.setdefault("10", 5)
        default_fan.setdefault("20", 5)
        default_fan.setdefault("30", 5)
        for temp, sl in self.fan_sliders.items():
            default_fan[temp] = sl.value()
        default_fan["fullFanSpeedEnabled"] = self.chk_full_fan.isChecked()

        fan_info = {
            "fanProfiles": {"default": default_fan},
            "fanPerGameProfilesEnabled": False,
            "customFanCurvesEnabled": self.chk_fan_enabled.isChecked(),
        }
        self.backend.call("save_fan_settings", fan_info, "default")
        self._mark_saved()


    def _on_power_led_toggled(self, checked: bool):
        if self._updating_ui:
            return
        self.backend.call("set_power_led", checked)
        self._mark_saved()

    def _on_rgb_control_toggled(self, checked: bool):
        if self._updating_ui:
            return
        self.rgb_details_container.setVisible(checked)
        self._on_rgb_param_changed()

    def _on_controller_led_toggled(self, checked: bool):
        if self._updating_ui:
            return
        self._on_rgb_param_changed()

    def _on_sync_slider_color_toggled(self, checked: bool):
        if self._updating_ui:
            return
        if checked:
            hue = self.slider_rgb_hue.value()
            r_f, g_f, b_f = colorsys.hls_to_rgb(hue / 360.0, 0.5, 1.0)
            hex_accent = f"#{int(round(r_f * 255)):02x}{int(round(g_f * 255)):02x}{int(round(b_f * 255)):02x}"
            self._apply_and_save_theme(
                self.ui_bg_color,
                self.ui_content_color,
                hex_accent,
                self.ui_language,
                self.dock_mode_enabled,
                getattr(self, "ui_content_color_2", DEFAULT_CONTENT_COLOR_2),
            )
        self._mark_saved()

    def _on_rgb_slider_preview(self):
        led_on = self.chk_controller_led.isChecked()
        mode = self.cmb_rgb_mode.currentData() or "SOLID"
        b = self.slider_rgb_brightness.value()
        sp = self.slider_rgb_speed.value()
        hue = self.slider_rgb_hue.value()

        self.lbl_rgb_brightness.setText(f"{b}%")
        self.lbl_rgb_speed.setText(f"{sp}%")
        self.lbl_rgb_hue.setText(f"{hue}°")
        self.stick_preview.set_rgb_state(led_on, mode, hue, b, sp)

        if hasattr(self, "chk_sync_slider_color") and self.chk_sync_slider_color.isChecked():
            r_f, g_f, b_f = colorsys.hls_to_rgb(hue / 360.0, 0.5, 1.0)
            hex_accent = f"#{int(round(r_f * 255)):02x}{int(round(g_f * 255)):02x}{int(round(b_f * 255)):02x}"
            self.ui_accent_color = hex_accent
            self.setStyleSheet(build_dynamic_stylesheet(self.ui_bg_color, self.ui_content_color, hex_accent, getattr(self, "ui_content_color_2", DEFAULT_CONTENT_COLOR_2)))

    def _on_rgb_param_changed(self):
        if self._updating_ui:
            return
        led_on = self.chk_controller_led.isChecked()
        mode = self.cmb_rgb_mode.currentData() or "SOLID"
        b = self.slider_rgb_brightness.value()
        sp = self.slider_rgb_speed.value()
        hue = self.slider_rgb_hue.value()

        self.speed_widget.setVisible(led_on and mode != "SOLID")
        self.hue_widget.setVisible(led_on and mode not in ("DYNAMIC", "SPIRAL"))
        self.stick_preview.setVisible(led_on)
        self.stick_preview.set_rgb_state(led_on, mode, hue, b, sp)

        r_f, g_f, b_f = colorsys.hls_to_rgb(hue / 360.0, 0.5, 1.0)
        r_i, g_i, b_i = int(round(r_f * 255)), int(round(g_f * 255)), int(round(b_f * 255))
        hex_accent = f"#{r_i:02x}{g_i:02x}{b_i:02x}"

        if hasattr(self, "chk_sync_slider_color") and self.chk_sync_slider_color.isChecked():
            self._apply_and_save_theme(
                self.ui_bg_color,
                self.ui_content_color,
                hex_accent,
                self.ui_language,
                self.dock_mode_enabled,
                getattr(self, "ui_content_color_2", DEFAULT_CONTENT_COLOR_2),
            )

        light_cfg = {
            "enabled": led_on,
            "mode": mode,
            "brightness": b,
            "speed": sp,
            "hue": hue,
            "red": r_i,
            "green": g_i,
            "blue": b_i,
        }
        rgb_profiles = {
            "default": {
                "LEFT": dict(light_cfg),
                "RIGHT": dict(light_cfg),
            }
        }
        payload = {
            "currentGameId": "default",
            "rgbProfiles": rgb_profiles,
            "enableRgbControl": self.chk_rgb_control.isChecked(),
        }
        self.backend.call("save_rgb_settings", payload)
        self._mark_saved()


    def _on_rumble_changed(self, index: int):
        if self._updating_ui:
            return
        intensity = self.cmb_rumble.currentData() or "MEDIUM"
        self.backend.call("set_rumble_intensity", intensity)
        self._on_remap_changed()

    def _on_touchpad_toggled(self, checked: bool):
        if self._updating_ui:
            return
        self.backend.call("set_touchpad", checked)
        self._on_remap_changed()

    def _on_guide_shortcut_toggled(self, checked: bool):
        if hasattr(self, "_controller_thread"):
            self._controller_thread.enabled = checked
        if not self._updating_ui:
            self._on_remap_changed()

    def _on_single_button_remap(self, btn_code: str):
        if self._updating_ui:
            return
        act_code = self.remap_combos[btn_code].currentData() or "DISABLED"
        self.backend.call("remap_button", btn_code, act_code)
        self._on_remap_changed()

    def _on_remap_changed(self):
        if self._updating_ui:
            return
        remap_on = self.chk_remap_enabled.isChecked()
        for cmb in self.remap_combos.values():
            cmb.setEnabled(remap_on)

        prof = {
            "TOUCHPAD": self.chk_touchpad.isChecked(),
            "GUIDE_SHORTCUT": self.chk_guide_shortcut.isChecked() if hasattr(self, "chk_guide_shortcut") else True,
            "RUMBLE": self.cmb_rumble.currentData() or "MEDIUM",
            "LEFT_GYRO": "DISABLED",
            "RIGHT_GYRO": "DISABLED",
        }
        for btn_code, cmb in self.remap_combos.items():
            prof[btn_code] = cmb.currentData() or "DISABLED"

        controller_payload = {
            "controllerProfiles": {"default": prof},
            "perGameProfilesEnabled": False,
            "controllerRemappingEnabled": remap_on,
        }
        self.backend.call("save_controller_settings", controller_payload, "default")
        self._mark_saved()

    def _mark_saved(self):
        try:
            mtime = 0.0
            if SETTINGS_FILE.exists():
                mtime = max(mtime, SETTINGS_FILE.stat().st_mtime)
            if TDP_FILE.exists():
                mtime = max(mtime, TDP_FILE.stat().st_mtime)
            if mtime > 0.0:
                self._last_mtime = mtime
        except Exception:
            pass



def ensure_single_instance(show_callback):
    try:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("127.0.0.1", SINGLE_INSTANCE_PORT))
        server.listen(2)
        server.setblocking(False)
    except OSError:
        try:
            with socket.create_connection(("127.0.0.1", SINGLE_INSTANCE_PORT), timeout=1.0) as c:
                c.sendall(b"SHOW\n")
        except Exception:
            pass
        sys.exit(0)

    timer = QTimer()
    timer.setInterval(300)

    def _poll():
        try:
            conn, _ = server.accept()
            conn.close()
            show_callback()
        except BlockingIOError:
            pass
        except Exception:
            pass

    timer.timeout.connect(_poll)
    timer.start()
    return server, timer


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("LeGO Suite")
    app.setApplicationVersion("0.198")
    app.setDesktopFileName("lego-suite-desktop")
    app.setQuitOnLastWindowClosed(False)

    backend = BackendClient()
    win = LeGOSuiteMainWindow(backend)

    _srv, _tmr = ensure_single_instance(win._slide_in)

    if "--tray" not in sys.argv:
        win._slide_in()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

# Si no existe Dios ¿Cómo explicas lo maravilloso que eres?
