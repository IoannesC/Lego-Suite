import decky_plugin
from plugin_settings import merge_tdp_profiles, get_saved_settings, set_setting
import device_utils
import ryzenadj

def check_ryzenadj_coall_support(force_check=False):
  if not device_utils.is_intel():
    try:
      settings = get_saved_settings()
      if force_check or settings.get('supportsRyzenadjCoall', None) == None:
        undervolt_supported = bool(ryzenadj._set_ryzenadj_undervolt(0))

        set_setting('supportsRyzenadjCoall', undervolt_supported)
    except Exception as e:
      decky_plugin.logger.error(f"{__name__} error while checking undervolt support {e}")










