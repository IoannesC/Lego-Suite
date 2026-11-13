import legion_hid
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

vendor_id = 0x17EF

base_product_ids = [
    0x6180,
    0x61E0,
]

usage_page = 0xFFA0

global_config = None


def get_config():
    global global_config

    try:
        for dev in legion_hid.enumerate(vendor_id):
            for product_id in base_product_ids:
                product_id_match = lambda x: x & 0xFFF0 == product_id
                if product_id_match(dev["product_id"]) and dev["usage_page"] == usage_page:
                    global_config = dev
                    break
    except Exception as e:
        decky_plugin.logger.error("legion_configurator error: couldn't find device config {e}")

    if not global_config:
        decky_plugin.logger.error("Legion go configuration device not found.")

def send_command(command):
    global global_config
    get_config()
    assert len(command) == 64 and global_config
    try:
        with legion_hid.Device(path=global_config['path']) as device:
            device.write(command)
            print("Command sent successfully.")
    except IOError as e:
        print(f"Error opening HID device: {e}")


def create_touchpad_command(enable):
    """
    Create a command to enable or disable the touchpad.

    :param enable: bool - True to enable, False to disable the touchpad
    :return: bytes - The command byte array
    """
    enable_byte = 0x01 if enable else 0x00

    command = [
        0x05,
        0x06,
        0x6B,
        0x02,
        0x04,
        enable_byte,
        0x01
    ]

    byte_command = bytes(command)
    buffered_command = byte_command + bytes([0xCD] * (64 - len(byte_command)))
    return buffered_command

def create_rumble_intensity_command(intensity_code, controller=0x00):
    """
    Create a command to set the rumble / vibration intensity.

    :param intensity_code: byte - 0x01 (OFF), 0x02 (LOW), 0x03 (MEDIUM), 0x04 (HIGH)
    :param controller: byte - 0x00 for both, 0x03 for Left, 0x04 for Right
    :return: bytes - The command byte array (64 bytes)
    """
    command = [
        0x05,
        0x00,
        0x06,
        0x02,
        controller,
        intensity_code,
        0x01
    ]
    byte_command = bytes(command)
    buffered_command = byte_command + bytes([0xCD] * (64 - len(byte_command)))
    return buffered_command


def create_rgb_control_command(controller, mode, color, brightness, speed, profile=0x01, on=True):
    """
    Create a command to control the RGB LEDs, including setting the profile and turning them on or off.

    :param controller: byte - The controller byte (0x03 for left, 0x04 for right)
    :param mode: byte - The mode of the LED (e.g., 0x01 for solid, 0x02 for blinking)
    :param color: bytes - The RGB color value (e.g., b'\xFF\x00\x00' for red)
    :param brightness: byte - The brightness value (0x00 to 0x64)
    :param speed: byte - The speed setting for dynamic modes (0x00 to 0x64, higher is slower)
    :param profile: byte - The profile number
    :param on: bool - True to turn on, False to turn off the RGB LEDs
    :return: bytes - The command byte array
    """
    on_off_byte = 0x01 if on else 0x00
    command = [
        0x05, 0x0c if on else 0x06,
        0x72 if on else 0x70,
        0x01, controller
    ]

    if on:
        command += [mode] + list(color) + [brightness, speed, profile, 0x01]
    else:
        command += [on_off_byte, 0x01]

    return bytes(command) + bytes([0xCD] * (64 - len(command)))

def create_rgb_on_off_command(controller, on):
    """
    Create a command to turn the RGB LEDs on or off.

    :param controller: byte - The controller byte (e.g., 0x03 for left, 0x04 for right)
    :param on: bool - True to turn on, False to turn off
    :return: bytes - The command byte array
    """
    on_off_byte = 0x01 if on else 0x00
    command = [
        0x05, 0x06,
        0x70,
        0x02,
        controller,
        on_off_byte,
        0x01
    ]
    return bytes(command) + bytes([0xCD] * (64 - len(command)))

def create_gyro_remap_command(gyro, joystick):
    """
    Create a command for gyro remapping.

    :param gyro: byte - The gyro setting (e.g., 0x01, 0x02)
    :param joystick: byte - The joystick value (e.g., 0x00, 0x01, 0x02)
    :return: bytes - The command byte array
    """
    command = [
        0x05, 0x08,
        0x6a,
        0x06, 0x01, 0x01,
        gyro, joystick,
        0x01
    ]
    return bytes(command) + bytes([0xCD] * (64 - len(command)))

def create_button_remap_command(controller, button, action):
    """
    Create a command for button remapping.

    :param controller: byte - The controller byte (0x03 for left, 0x04 for right)
    :param button: byte - The button to remap. Button codes:
                    0x1c: Y1, 0x1d: Y2, 0x1e: Y3, 0x21: M2, 0x22: M3
    :param action: byte - The action to assign to the button. Action codes:
                   0x00: Disabled, 0x03: Left Stick Click, 0x04: Left Stick Up,
                   0x05: Left Stick Down, 0x06: Left Stick Left, 0x07: Left Stick Right,
                   0x08: Right Stick Click, 0x09: Right Stick Up, 0x0a: Right Stick Down,
                   0x0b: Right Stick Left, 0x0c: Right Stick Right, 0x0d: D-Pad Up,
                   0x0e: D-Pad Down, 0x0f: D-Pad Left, 0x10: D-Pad Right,
                   0x12: A, 0x13: B, 0x14: X, 0x15: Y, 0x16: Left Bumper,
                   0x17: Left Trigger, 0x18: Right Bumper, 0x19: Right Trigger,
                   0x23: View, 0x24: Menu
    :return: bytes - The command byte array
    """
    command = [
        0x05, 0x07,
        0x6c,
        0x02, controller, button, action,
        0x01
    ]
    return bytes(command) + bytes([0xCD] * (64 - len(command)))

def create_vibration_command(controller, vibration_level):
    """
    Create a command to control the vibration of the controller.

    :param controller: byte - The controller byte (0x03 for left, 0x04 for right)
    :param vibration_level: byte - Vibration level (0x00: Off, 0x01: Weak, 0x02: Medium, 0x03: Strong)
    :return: bytes - The command byte array
    """
    command = [
        0x05, 0x06,
        0x67,
        0x02,
        controller, vibration_level,
        0x01
    ]
    return bytes(command) + bytes([0xCD] * (64 - len(command)))

def create_fps_remap_command(controller, profile, button, action):
    """
    Create a command for FPS remapping.

    :param controller: byte - The controller byte (0x03 for left, 0x04 for right)
    :param profile: byte - The profile number (from 0x01 to 0x04)
    :param button: byte - The button to remap
    :param action: byte - The action to assign to the button
    :return: bytes - The command byte array
    """
    command = [
        0x05, 0x08,
        0x6c,
        0x04,
        controller, profile, button, action,
        0x01
    ]
    return bytes(command) + bytes([0xCD] * (64 - len(command)))

