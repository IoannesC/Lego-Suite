import os
from pathlib import Path

try:
    import decky_plugin
    _logger = decky_plugin.logger
except ImportError:
    import logging
    _logger = logging.getLogger("ambient_light_sensor")

def find_als():
    iio_base = Path('/sys/bus/iio/devices')
    if not iio_base.exists():
        return None
    try:
        for device_dir in iio_base.iterdir():
            if device_dir.name.startswith('iio:device'):
                name_file = device_dir / 'name'
                if name_file.exists():
                    try:
                        if name_file.read_text(encoding='utf-8').strip() == 'als':
                            return device_dir
                    except Exception:
                        pass
                if (device_dir / 'in_illuminance_raw').exists():
                    return device_dir
    except Exception as e:
        _logger.error(f"failed to find ALS {e}")
    return None

def read_als():
    """
    Reads the ambient light sensor raw illuminance or intensity.
    Returns integer reading, or None if unavailable.
    """
    als_dev = find_als()
    if not als_dev:
        return None

    candidates = [
        als_dev / 'in_illuminance_raw',
        als_dev / 'in_intensity_both_raw',
        als_dev / 'in_illuminance_input',
        als_dev / 'in_illuminance0_input'
    ]

    for sensor_file in candidates:
        if sensor_file.exists():
            try:
                val_str = sensor_file.read_text(encoding='utf-8').strip()
                return int(float(val_str))
            except Exception as e:
                _logger.error(f"Failed to read sensor data from {sensor_file}: {e}")

    return None
