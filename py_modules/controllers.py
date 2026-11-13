import controller_settings
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
import legion_configurator
from controller_enums import Controller, RemappableButtons, RemapActions, GyroRemapActions, Gyro, RumbleIntensity

def sync_controller_profile_settings(current_game_id):
    settings = controller_settings.get_settings()
    controller_profile = (settings.get('controller') or {}).get(current_game_id, {})

    try:
        for remappable_button_name, remap_action in controller_profile.items():
            controller_code = None
            if remappable_button_name in ['Y3', 'M2', 'M3']:
                controller_code = Controller['RIGHT'].value
            elif remappable_button_name in ['Y1', 'Y2']:
                controller_code = Controller['LEFT'].value
            if not controller_code:
                continue

            btn_code = RemappableButtons[remappable_button_name].value
            action_code = RemapActions[remap_action].value
            remap_command = legion_configurator.create_button_remap_command(controller_code, btn_code, action_code)

            legion_configurator.send_command(remap_command)
    except Exception as e:
        decky_plugin.logger.error(f"sync_controller_profile_settings: {e}")

def sync_touchpad(current_game_id):
    settings = controller_settings.get_settings()
    controller_profile = (settings.get('controller') or {}).get(current_game_id, {})

    try:
        new_touchpad_state = bool(controller_profile.get('TOUCHPAD'))
        t_toggle = legion_configurator.create_touchpad_command(new_touchpad_state)
        legion_configurator.send_command(t_toggle)
    except Exception as e:
        decky_plugin.logger.error(f"sync_touchpad: {e}")

def sync_gyros(current_game_id):
    settings = controller_settings.get_settings()
    controller_profile = (settings.get('controller') or {}).get(current_game_id, {})

    for gyro in [g.name for g in Gyro]:
        try:
            gyro_remap_action = controller_profile.get(gyro)
            gyro_remap_action_code = GyroRemapActions[gyro_remap_action].value
            gyro_code = Gyro[gyro].value

            if gyro_remap_action_code >= 0 and gyro_code > 0:
                # valid codes, set gyro
                gyro_command = legion_configurator.create_gyro_remap_command(gyro_code, gyro_remap_action_code)
                legion_configurator.send_command(gyro_command)
        except Exception as e:
            decky_plugin.logger.error(f"sync_gyros {e}")

def sync_rumble(current_game_id):
    settings = controller_settings.get_settings()
    controller_profile = (settings.get('controller') or {}).get(current_game_id, {})

    try:
        rumble_name = str(controller_profile.get('RUMBLE', 'MEDIUM')).upper()
        if hasattr(RumbleIntensity, rumble_name):
            intensity_code = RumbleIntensity[rumble_name].value
            cmd = legion_configurator.create_rumble_intensity_command(intensity_code, 0x00)
            legion_configurator.send_command(cmd)
    except Exception as e:
        decky_plugin.logger.error(f"sync_rumble: {e}")

def trigger_test_vibration(intensity_name: str = "MEDIUM"):
    """
    Triggers a short test buzz on both controllers according to selected intensity.
    """
    import time
    try:
        level_map = {
            "OFF": 0x00,
            "LOW": 0x01,
            "MEDIUM": 0x02,
            "HIGH": 0x03
        }
        level = level_map.get(str(intensity_name).upper(), 0x02)
        if level == 0x00:
            return

        cmd_left = legion_configurator.create_vibration_command(0x03, level)
        cmd_right = legion_configurator.create_vibration_command(0x04, level)
        legion_configurator.send_command(cmd_left)
        legion_configurator.send_command(cmd_right)

        time.sleep(0.18)

        cmd_stop_left = legion_configurator.create_vibration_command(0x03, 0x00)
        cmd_stop_right = legion_configurator.create_vibration_command(0x04, 0x00)
        legion_configurator.send_command(cmd_stop_left)
        legion_configurator.send_command(cmd_stop_right)
    except Exception as e:
        decky_plugin.logger.error(f"trigger_test_vibration error: {e}")


def reset_controllers() -> dict:
    """
    Reset Lenovo Legion Go controllers (HHD compliant):
    1. Visual LED Flash: Rapid 3x blink in bright white, then restore factory Legion Cyan (#00a0ff).
    2. Hardware MCU & Handle Reset: Write '1' to sysfs reset_mcu, left_handle/reset, right_handle/reset.
    3. Gyro Zero/Calibration: Trigger left/right calibrate_gyro sysfs nodes.
    4. Clear HID remappings: Y1-Y3, M2, M3 set to DISABLED, Touchpad ON.
    5. InputPlumber restore: Revert to default system profile.
    6. Persist factory controller and RGB settings.
    """
    import os
    import glob
    import time
    try:
        import fcntl
        USBDEVFS_RESET = ord('U') << 8 | 20
    except Exception:
        fcntl = None
        USBDEVFS_RESET = None

    decky_plugin.logger.info("Initiating HHD-style full controller reset & calibration...")
    results = {"led_flash": False, "sysfs_reset": 0, "hid": False, "inputplumber": False}

    # 1. LED Flash Sequence (Joysticks blink 3 times, then return to factory Legion Cyan)
    led_dir = "/sys/class/leds/go:rgb:joystick_rings"
    def _write_led_file(prop, val):
        p = os.path.join(led_dir, prop)
        if os.path.exists(p):
            try:
                with open(p, "w") as f:
                    f.write(str(val))
                return True
            except Exception:
                pass
        return False

    try:
        if os.path.isdir(led_dir):
            for _ in range(3):
                _write_led_file("enabled", "true")
                _write_led_file("mode", "custom")
                _write_led_file("effect", "monocolor")
                _write_led_file("brightness", "100")
                _write_led_file("multi_intensity", "100 100 100")
                time.sleep(0.12)
                _write_led_file("enabled", "false")
                time.sleep(0.08)

            # Return to native Lenovo Legion Go factory color (Cyan Blue)
            _write_led_file("enabled", "true")
            _write_led_file("mode", "custom")
            _write_led_file("effect", "monocolor")
            _write_led_file("brightness", "50")
            _write_led_file("multi_intensity", "0 4 255")
            _write_led_file("profile", "1")
            results["led_flash"] = True
    except Exception as e:
        decky_plugin.logger.warning(f"Error during LED flash sequence: {e}")

    # 2. Hardware MCU, Handle Resets and Gyro Calibration via hid-lenovo-go driver
    sysfs_targets = [
        "left_handle/reset",
        "right_handle/reset",
        "reset_mcu",
        "left_handle/calibrate_gyro",
        "right_handle/calibrate_gyro"
    ]
    for dev_path in glob.glob("/sys/bus/hid/drivers/hid-lenovo-go/0003:17EF:*"):
        for target in sysfs_targets:
            p = os.path.join(dev_path, target)
            if os.path.exists(p):
                try:
                    with open(p, "w") as f:
                        f.write("1")
                    results["sysfs_reset"] += 1
                except Exception:
                    pass

    # 3. Clear HID remappings (Y1-Y3, M2, M3 -> DISABLED, Touchpad -> ON)
    try:
        for btn in [RemappableButtons.Y1.value, RemappableButtons.Y2.value]:
            cmd = legion_configurator.create_button_remap_command(Controller.LEFT.value, btn, RemapActions.DISABLED.value)
            legion_configurator.send_command(cmd)

        for btn in [RemappableButtons.Y3.value, RemappableButtons.M2.value, RemappableButtons.M3.value]:
            cmd = legion_configurator.create_button_remap_command(Controller.RIGHT.value, btn, RemapActions.DISABLED.value)
            legion_configurator.send_command(cmd)

        t_cmd = legion_configurator.create_touchpad_command(True)
        legion_configurator.send_command(t_cmd)
        results["hid"] = True
    except Exception as e:
        decky_plugin.logger.debug(f"HID remapping clear note: {e}")

    # 4. Reset InputPlumber profiles back to default system profile and re-sync targets
    try:
        import inputplumber_utils
        time.sleep(0.3)
        inputplumber_utils.set_active_profiles([])
        inputplumber_utils.set_controller_mode("default")
        results["inputplumber"] = True
    except Exception as e:
        decky_plugin.logger.error(f"Error resetting InputPlumber during controller reset: {e}")

    # 5. Update settings.json with clean factory state
    try:
        import json
        cands = [
            os.environ.get("DECKY_PLUGIN_SETTINGS_DIR") and os.path.join(os.environ.get("DECKY_PLUGIN_SETTINGS_DIR"), "settings.json"),
            os.path.expanduser("~/homebrew/settings/LeGO Suite/settings.json"),
            os.path.expanduser("~/homebrew/settings/LeGO-Suite/settings.json"),
            os.path.expanduser("~/.config/lego-suite/settings.json"),
            "/tmp/lego-suite-settings/settings.json"
        ]
        for sp in cands:
            if sp and os.path.isfile(sp):
                try:
                    with open(sp, "r", encoding="utf-8") as f:
                        sdata = json.load(f)
                    sdata["controllerRemappingEnabled"] = False
                    sdata["inputPlumberActiveProfiles"] = []
                    if "rgb" in sdata and isinstance(sdata["rgb"], dict):
                        if "default" in sdata["rgb"] and isinstance(sdata["rgb"]["default"], dict):
                            sdata["rgb"]["default"]["RIGHT"] = {
                                "enabled": True,
                                "mode": "SOLID",
                                "red": 0,
                                "green": 160,
                                "blue": 255,
                                "brightness": 50,
                                "speed": 50,
                                "hue": 202
                            }
                    with open(sp, "w", encoding="utf-8") as f:
                        json.dump(sdata, f, indent=4)
                except Exception:
                    pass
    except Exception:
        pass

    decky_plugin.logger.info(f"HHD controller reset finished: {results}")
    return results