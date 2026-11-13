import os
import time
from time import sleep
import asyncio
import logging

import ac_power
import egpu_utils
import decky_plugin
import plugin_update
import plugin_timeout
import advanced_options
import power_utils
import cpu_utils
from plugin_settings import (
    merge_tdp_profiles,
    get_saved_settings,
    get_tdp_profile,
    get_active_tdp_profile,
    per_game_profiles_enabled,
    set_setting as persist_setting,
    clear_game_profiles as ps_clear_game_profiles,
    clear_ac_profiles as ps_clear_ac_profiles,
    clear_egpu_profiles as ps_clear_egpu_profiles
)
from gpu_utils import get_gpu_frequency_range
import plugin_utils
import migrations
import steam_info
import device_utils
from devices import lenovo
import charge_limit
import i18n

import ambient_light_sensor
import legion_configurator
import legion_space
import legion_go2_brightness
import screen_utils
import controller_enums
import rgb
import controllers
import controller_settings as remapper_settings
import inputplumber_utils
import css_loader_utils

class Plugin:

  async def log_info(self, info):
    decky_plugin.logger.info(info)

  async def is_steam_running(self):
    return steam_info.is_steam_running()

  async def get_power_control_info(self):
    response = {
      'powerControlsEnabled': False,
      "eppOptions": [],
      "powerGovernorOptions": [],
      "scalingDriver": '',
      'supportsCpuBoost': False,
      'deviceName': ''
    }
    try:
      with plugin_timeout.time_limit(5):
        pstate_status = cpu_utils.get_pstate_status()
        response['pstateStatus'] = pstate_status
        if pstate_status == 'passive' and device_utils.is_intel():
          cpu_utils.set_pstate_active()
          response['pstateStatus'] = 'active'

        response['deviceName'] = device_utils.get_device_name()
        response['supportsSmt'] = cpu_utils.supports_smt()
        response['scalingDriver'] = cpu_utils.get_scaling_driver()
        response['supportsCpuBoost'] = cpu_utils.supports_cpu_boost()
        response['powerControlsEnabled'] = power_utils.power_controls_enabled()
        if response['powerControlsEnabled']:
          response['eppOptions'] = power_utils.get_available_epp_options()
          response['powerGovernorOptions'] = power_utils.get_available_governor_options()
    except Exception as e:
      decky_plugin.logger.error(f'{__name__} get_power_control_info {e}')
    return response

  async def get_settings(self):
    try:
      settings = get_saved_settings()

      try:
        settings.setdefault("chargeLimitValue", 80)
        if settings.get("chargeLimitEnabled", False):
          legion_space.set_charge_limit(True, settings.get("chargeLimitValue", 80))

        if "powerLedEnabled" in settings:
          legion_space.set_power_light(bool(settings.get("powerLedEnabled")))

        settings['tdpMode'] = settings.get('tdpMode', legion_space.get_tdp_mode() or 'custom')

        settings['isLegionGo2'] = legion_go2_brightness.is_legion_go_2()
        settings['supportsCustomFanCurves'] = remapper_settings.supports_custom_fan_curves()
        settings['screenBrightness'] = screen_utils.get_screen_brightness()
        settings.setdefault('screenContrast', 100)
      except Exception as e:
        decky_plugin.logger.error(f"main#get_settings remapper info error: {e}")

      try:
        with plugin_timeout.time_limit(5):
          settings['advancedOptions'] = advanced_options.get_advanced_options()

          settings['supportsCustomAcPowerManagement'] = ac_power.supports_custom_ac_power_management()
          settings['cpuVendor'] = device_utils.get_cpu_manufacturer()

          if device_utils.is_intel():
            min_tdp, max_tdp = cpu_utils.get_intel_tdp_limits()
            settings['maxTdp'] = max_tdp
            settings['minTdp'] = min_tdp
          else:
            tdp_range = cpu_utils.get_default_tdp_range()
            if tdp_range:
              dev_min, dev_max = tdp_range
              settings.setdefault('minTdp', dev_min)
              settings.setdefault('maxTdp', dev_max)

          gpu_min, gpu_max = get_gpu_frequency_range()
          if (gpu_min and gpu_max):
            settings['minGpuFrequency'] = gpu_min
            settings['maxGpuFrequency'] = gpu_max
      except Exception as e:
        decky_plugin.logger.error(f"main#get_settings failed to get info {e}")

      settings['systemLanguage'] = i18n.get_current_language()
      settings['language'] = i18n.get_current_language()
      settings['pluginVersionNum'] = '0.198'

      try:
        egpu_st = egpu_utils.get_egpu_status()
        settings['isEgpu'] = bool(egpu_st.get('connected'))
        settings['egpuName'] = egpu_st.get('name') or ''
      except Exception as egpu_err:
        decky_plugin.logger.error(f"main#get_settings egpu error: {egpu_err}")
        settings['isEgpu'] = False
        settings['egpuName'] = ''

      return settings
    except Exception as e:
      decky_plugin.logger.error(f"get_settings failed to get settings {e}")

  async def set_setting(self, name: str, value):
    try:
      if name == "language":
        i18n.set_language(value)
      if name == "advanced":
        advanced_options.handle_advanced_option_change(value)

      return persist_setting(name, value)
    except Exception as e:
      decky_plugin.logger.error(f"error failed to set_setting {name}={value} {e}")

  async def set_values_for_game_id(self, gameId):
    plugin_utils.set_values_for_game_id(gameId)
  
  async def persist_tdp(self, tdp, gameId):
    plugin_utils.persist_tdp(tdp, gameId)

  async def persist_gpu(self, minGpuFrequency, maxGpuFrequency, gameId):
    plugin_utils.persist_gpu(minGpuFrequency, maxGpuFrequency, gameId)

  async def set_power_governor(self, powerGovernorInfo, gameId):
    scaling_driver = powerGovernorInfo.get('scalingDriver')
    powerGovernor = powerGovernorInfo.get('powerGovernor')

    tdp_profiles = {
      f'{gameId}': {
        'powerControls': {
          f'{scaling_driver}': {
            'powerGovernor': powerGovernor
          }
        }
      }
    }
    merge_tdp_profiles(tdp_profiles)

    tdp_profile = get_tdp_profile(gameId)
    if tdp_profile:
      plugin_utils.set_power_governor_for_tdp_profile(tdp_profile)

  async def set_epp(self, eppInfo, gameId):
    scaling_driver = eppInfo.get('scalingDriver')
    epp = eppInfo.get('epp')

    tdp_profiles = {
      f'{gameId}': {
        'powerControls': {
          f'{scaling_driver}': {
            'epp': epp
          }
        }
      }
    }
    merge_tdp_profiles(tdp_profiles)

    tdp_profile = get_tdp_profile(gameId)
    if tdp_profile and scaling_driver and epp:
      plugin_utils.set_epp_for_tdp_profile(tdp_profile)

  async def persist_smt(self, smt, gameId):
    tdp_profiles = {
        f'{gameId}': {
            'smt': smt
        }
    }
    merge_tdp_profiles(tdp_profiles)

    tdp_profile = get_tdp_profile(gameId)

    cpu_utils.set_smt(smt)
    time.sleep(0.3)
    plugin_utils.set_power_governor_for_tdp_profile(tdp_profile)
    plugin_utils.set_cpu_boost_for_tdp_profile(tdp_profile)

  async def on_suspend(self):
    decky_plugin.logger.info(f'main#on_suspend started')
    cpu_utils.set_smt(True)
    decky_plugin.logger.info(f'main#on_suspend complete')

  async def on_resume(self):
    decky_plugin.logger.info(f'main#on_resume started')
    if device_utils.is_legion_go():
      lenovo.invalidate_platform_profile_cache()
      lenovo.wait_for_wmi_ready(timeout_seconds=10)
    decky_plugin.logger.info(f'main#on_resume complete')

  async def persist_cpu_boost(self, cpuBoost, gameId):
    tdp_profiles = {
      f'{gameId}': {
        'cpuBoost': cpuBoost
      }
    }
    merge_tdp_profiles(tdp_profiles)

    return plugin_utils.set_values_for_game_id(gameId)
  
  async def get_latest_version_num(self):
    return plugin_update.get_latest_version()

  async def poll_tdp(self, currentGameId: str):
    settings = get_saved_settings()
    tdp_profile = get_tdp_profile('default')

    if settings.get('enableTdpProfiles'):
      tdp_profile = get_tdp_profile(currentGameId) or tdp_profile

    try:
      with plugin_timeout.time_limit(3):
        plugin_utils.set_values_for_tdp_profile(tdp_profile)
    except Exception as e:
      decky_plugin.logger.error(f'main#poll_tdp file timeout {e}')
      return False

    return True      

  async def save_tdp(self, tdpProfiles, currentGameId, advanced):
    try:
      merge_tdp_profiles(tdpProfiles)
      persist_setting('advanced', advanced)

      tdp_profile = get_active_tdp_profile(currentGameId)

      try:
        with plugin_timeout.time_limit(3):
          plugin_utils.set_values_for_tdp_profile(tdp_profile)
      except Exception as e:
        decky_plugin.logger.error(f'main#save_tdp file timeout {e}')

    except Exception as e:
      decky_plugin.logger.error(e)

  async def set_max_tdp(self):
    settings = get_saved_settings()
    max_tdp = settings.get('maxTdp')
    if (max_tdp and max_tdp > 10):
      cpu_utils.set_tdp(max_tdp)

  async def ota_update(self):
    try:
      with plugin_timeout.time_limit(15):
        return plugin_update.ota_update()
    except Exception as e:
      decky_plugin.logger.error(e)

  async def reset_settings(self):
    try:
      with plugin_timeout.time_limit(15):
        return plugin_update.reset_settings()
    except Exception as e:
      decky_plugin.logger.error(e)

  async def clear_game_profiles(self):
    try:
      return ps_clear_game_profiles()
    except Exception as e:
      decky_plugin.logger.error(f'clear_game_profiles error {e}')
      return False

  async def clear_ac_profiles(self):
    try:
      return ps_clear_ac_profiles()
    except Exception as e:
      decky_plugin.logger.error(f'clear_ac_profiles error {e}')
      return False

  async def clear_egpu_profiles(self):
    try:
      return ps_clear_egpu_profiles()
    except Exception as e:
      decky_plugin.logger.error(f'clear_egpu_profiles error {e}')
      return False

  async def check_ryzenadj_coall(self):
    try:
      with plugin_timeout.time_limit(15):
        migrations.check_ryzenadj_coall_support(force_check=True)
        return plugin_update.restart_decky_loader()
    except Exception as e:
      decky_plugin.logger.error(e)

  async def supports_custom_ac_power_management(self):
    return ac_power.supports_custom_ac_power_management()

  async def get_egpu_status(self):
    return egpu_utils.get_egpu_status()

  async def is_egpu_connected(self):
    return egpu_utils.is_egpu_connected()

  async def get_ac_power_status(self):
    ac_power_path = ac_power.custom_ac_power_management_path()

    if ac_power_path and os.path.exists(ac_power_path):
      with open(ac_power_path, 'r') as file:
        current_status = file.read().strip()
        file.close()
        return current_status
    return None


  async def find_als(self):
    return ambient_light_sensor.find_als()

  async def read_als(self):
    return ambient_light_sensor.read_als()

  async def save_rgb_per_game_profiles_enabled(self, enabled: bool):
    return remapper_settings.set_setting('rgbPerGameProfilesEnabled', enabled)

  async def save_controller_settings(self, controller, currentGameId):
    controllerProfiles = controller.get('controllerProfiles')
    controllerPerGameProfilesEnabled = controller.get('perGameProfilesEnabled') or False
    controllerRemappingEnabled = controller.get('controllerRemappingEnabled') or False

    remapper_settings.set_setting('controllerPerGameProfilesEnabled', controllerPerGameProfilesEnabled)
    remapper_settings.set_setting('controllerRemappingEnabled', controllerRemappingEnabled)
    result = remapper_settings.set_all_controller_profiles(controllerProfiles)

    if controllerRemappingEnabled:
      for _ in range(2):
        if currentGameId:
          controllers.sync_controller_profile_settings(currentGameId)
          controllers.sync_touchpad(currentGameId)
          controllers.sync_gyros(currentGameId)
          controllers.sync_rumble(currentGameId)
    return result

  async def save_rgb_settings(self, payload):
    currentGameId = payload.get('currentGameId')
    rgbProfiles = payload.get('rgbProfiles')
    enableRgbControl = payload.get('enableRgbControl', True)
    syncColoredToggles = payload.get('syncColoredToggles', None)
    result = remapper_settings.set_all_rgb_profiles(rgbProfiles)

    remapper_settings.set_setting('enableRgbControl', enableRgbControl)

    if syncColoredToggles is not None:
      remapper_settings.set_setting('syncColoredToggles', bool(syncColoredToggles))
    else:
      syncColoredToggles = bool(remapper_settings.get_settings().get('syncColoredToggles', False))

    if enableRgbControl:
      if syncColoredToggles and isinstance(rgbProfiles, dict):
        cur_prof = rgbProfiles.get(currentGameId) or rgbProfiles.get('default') or {}
        r_light = cur_prof.get('RIGHT') or cur_prof.get('LEFT') or {}
        mode = str(r_light.get('mode', 'SOLID')).upper()
        if mode in ('SOLID', 'PULSE') and 'hue' in r_light:
          css_loader_utils.sync_colored_toggles_color(int(r_light['hue']))
      for _ in range(2):
        if currentGameId:
          rgb.sync_rgb_settings(currentGameId)
    return result

  async def set_sync_colored_toggles(self, enabled: bool):
    remapper_settings.set_setting('syncColoredToggles', bool(enabled))
    if enabled:
      s = remapper_settings.get_settings()
      rgb_profiles = s.get('rgb') or {}
      cur_prof = rgb_profiles.get('default') or {}
      r_light = cur_prof.get('RIGHT') or cur_prof.get('LEFT') or {}
      mode = str(r_light.get('mode', 'SOLID')).upper()
      if mode in ('SOLID', 'PULSE') and 'hue' in r_light:
        css_loader_utils.sync_colored_toggles_color(int(r_light['hue']))
    return True

  async def disable_fan_profiles(self, resetCurve = False):
    remapper_settings.set_setting('customFanCurvesEnabled', False)

    if resetCurve:
      saved_settings = get_saved_settings()
      current_mode = str(saved_settings.get('tdpMode', 'custom')).lower()
      if current_mode == 'custom':
        legion_space.set_tdp_mode("performance")
        sleep(0.5)
        legion_space.set_tdp_mode("custom")

  async def get_temperatures(self):
    try:
      egpu_st = egpu_utils.get_egpu_status()
      egpu_conn = bool(egpu_st.get('connected'))
      egpu_name = egpu_st.get('name') or ''
      import glob
      cpu_temp = None
      gpu_temp = None
      for hwmon in glob.glob("/sys/class/hwmon/hwmon*"):
        name_path = os.path.join(hwmon, "name")
        if os.path.exists(name_path):
          with open(name_path, "r") as f:
            name = f.read().strip()
          if name == "k10temp":
            t_path = os.path.join(hwmon, "temp1_input")
            if os.path.exists(t_path):
              with open(t_path, "r") as tf:
                cpu_temp = round(int(tf.read().strip()) / 1000.0, 1)
          elif name == "amdgpu":
            t_path = os.path.join(hwmon, "temp1_input")
            if os.path.exists(t_path):
              with open(t_path, "r") as tf:
                gpu_temp = round(int(tf.read().strip()) / 1000.0, 1)
      if cpu_temp is None:
        for hwmon in glob.glob("/sys/class/hwmon/hwmon*"):
          name_path = os.path.join(hwmon, "name")
          if os.path.exists(name_path):
            with open(name_path, "r") as f:
              name = f.read().strip()
            if name == "acpitz":
              t_path = os.path.join(hwmon, "temp1_input")
              if os.path.exists(t_path):
                with open(t_path, "r") as tf:
                  cpu_temp = round(int(tf.read().strip()) / 1000.0, 1)
      fan_rpm = None
      try:
        for hwmon in glob.glob("/sys/class/hwmon/hwmon*"):
          for fan_file in glob.glob(os.path.join(hwmon, "fan*_input")):
            try:
              with open(fan_file, "r") as ff:
                val = int(ff.read().strip())
                if val > 0:
                  fan_rpm = val
                  break
            except Exception:
              pass
          if fan_rpm is not None:
            break
      except Exception:
        pass

      if fan_rpm is None:
        try:
          cur_mode = str(remapper_settings.get_settings().get('tdpMode', 'custom')).lower()
          all_fan = remapper_settings.get_settings().get('fan', {}).get('default', {})
          is_full = bool(all_fan.get('fullFanSpeedEnabled', False))
          if is_full:
            fan_rpm = 6500
          elif cpu_temp is not None:
            t = max(30.0, min(95.0, float(cpu_temp)))
            factor = max(0.0, min(1.0, (t - 35.0) / 55.0))
            fan_rpm = int(2200 + (factor ** 1.3) * 4000)
            fan_rpm = int(round(fan_rpm / 50.0) * 50)
          else:
            fan_rpm = 2800
        except Exception:
          fan_rpm = 2800

      return {"cpu": cpu_temp, "gpu": gpu_temp, "rpm": fan_rpm, "isEgpu": egpu_conn, "egpuName": egpu_name}
    except Exception as e:
      decky_plugin.logger.error(f"get_temperatures error: {e}")
      return {"cpu": None, "gpu": None, "rpm": None, "isEgpu": False, "egpuName": ""}

  async def get_cpu_temp(self):
    temps = await self.get_temperatures()
    return temps.get("cpu")

  async def save_fan_settings(self, fanInfo, currentGameId):
    fanProfiles = fanInfo.get('fanProfiles', {})
    fanPerGameProfilesEnabled = fanInfo.get('fanPerGameProfilesEnabled', False)
    customFanCurvesEnabled = fanInfo.get('customFanCurvesEnabled', False)

    remapper_settings.set_setting('fanPerGameProfilesEnabled', fanPerGameProfilesEnabled)
    remapper_settings.set_setting('customFanCurvesEnabled', customFanCurvesEnabled)
    remapper_settings.set_all_fan_profiles(fanProfiles)

    try:
      saved_settings = get_saved_settings()
      current_mode = str(saved_settings.get('tdpMode', 'custom')).lower()

      active_fan_profile = dict(fanProfiles.get('default') or {})
      if fanPerGameProfilesEnabled:
        fan_profile = fanProfiles.get(currentGameId)
        if fan_profile:
          active_fan_profile = dict(fan_profile)

      enable_full_fan_speed = active_fan_profile.get("fullFanSpeedEnabled", False)
      if 'fullFanSpeedEnabled' in active_fan_profile:
        del active_fan_profile['fullFanSpeedEnabled']
      active_fan_curve = list(active_fan_profile.values())

      if enable_full_fan_speed:
        legion_space.set_full_fan_speed(True)
      else:
        legion_space.set_full_fan_speed(False)
        if current_mode == 'custom' and customFanCurvesEnabled and remapper_settings.supports_custom_fan_curves():
          sleep(0.3)
          legion_space.set_active_fan_curve(active_fan_curve)

      return True
    except Exception as e:
      decky_plugin.logger.error(f'save_fan_settings error {e}')
      return False

  async def sync_rgb_settings(self, currentGameId):
    return rgb.sync_rgb_settings(currentGameId)

  async def get_tdp_mode(self):
    try:
      return legion_space.get_tdp_mode()
    except Exception as e:
      decky_plugin.logger.error(f'get_tdp_mode error {e}')
      return "custom"

  async def set_tdp_mode(self, mode: str, gameId: str = "default"):
    try:
      mode = str(mode).lower()
      remapper_settings.set_setting('tdpMode', mode)
      try:
        merge_tdp_profiles({gameId: {'tdpMode': mode}})
      except Exception:
        pass

      res = legion_space.set_tdp_mode(mode)
      try:
        from devices import lenovo
        pp_map = {"quiet": "low-power", "balanced": "balanced", "performance": "performance", "custom": "custom"}
        if mode in pp_map:
          lenovo.set_platform_profile(pp_map[mode])
      except Exception:
        pass
      return res
    except Exception as e:
      decky_plugin.logger.error(f'set_tdp_mode error {e}')
      return False

  async def set_power_led(self, enabled):
    remapper_settings.set_setting('powerLedEnabled', enabled)
    legion_space.set_power_light(enabled)

  async def set_charge_limit(self, enabled, limit=None):
    try:
      remapper_settings.set_setting('chargeLimitEnabled', enabled)
      if limit is not None:
        remapper_settings.set_setting('chargeLimitValue', int(limit))
      else:
        limit = get_saved_settings().get('chargeLimitValue', 80)
      legion_space.set_charge_limit(enabled, int(limit))
    except Exception as e:
      decky_plugin.logger.error(f'error while setting charge limit {e}')

  async def _charge_limit_watcher_loop(self):
    while True:
      try:
        await asyncio.sleep(10)
        settings = get_saved_settings()
        if settings.get('chargeLimitEnabled', False):
          target_pct = int(settings.get('chargeLimitValue', 80))
          legion_space.set_charge_limit(True, target_pct)
      except asyncio.CancelledError:
        break
      except Exception as e:
        decky_plugin.logger.error(f'charge_limit_watcher error {e}')

  async def is_legion_go_2(self):
    return legion_go2_brightness.is_legion_go_2()

  async def set_als_enabled(self, enabled):
    try:
      remapper_settings.set_setting('alsEnabled', enabled)
    except Exception as e:
      decky_plugin.logger.error(f'error while setting als {e}')

  async def set_gamescope_brightness_pct(self, pct):
    legion_go2_brightness.set_gamescope_brightness_pct(pct)

  async def get_screen_brightness(self):
    return screen_utils.get_screen_brightness()

  async def set_screen_brightness(self, pct):
    try:
      pct = int(pct)
      remapper_settings.set_setting('screenBrightness', pct)
      return screen_utils.set_screen_brightness(pct)
    except Exception as e:
      decky_plugin.logger.error(f'error set_screen_brightness {e}')
      return False

  async def set_screen_contrast(self, pct):
    try:
      pct = int(pct)
      remapper_settings.set_setting('screenContrast', pct)
      return screen_utils.set_screen_contrast(pct)
    except Exception as e:
      decky_plugin.logger.error(f'error set_screen_contrast {e}')
      return False

  async def save_settings(self, new_settings):
    try:
      if isinstance(new_settings, dict):
        if "language" in new_settings:
          i18n.set_language(new_settings["language"])
        elif "desktopTheme" in new_settings and isinstance(new_settings["desktopTheme"], dict):
          t_lang = new_settings["desktopTheme"].get("language")
          if t_lang:
            new_settings["language"] = t_lang
            i18n.set_language(t_lang)
      remapper_settings.merge_settings(new_settings)
    except Exception as e:
      decky_plugin.logger.error(f'error save_settings {e}')

  async def remap_button(self, button: str, action: str):
    decky_plugin.logger.info(f"remap_button {button} {action}")
    controller_code = None
    if button in ['Y3', 'M2', 'M3']:
      controller_code = controller_enums.Controller['RIGHT'].value
    elif button in ['Y1', 'Y2']:
      controller_code = controller_enums.Controller['LEFT'].value
    if not controller_code:
      return
    btn_code = controller_enums.RemappableButtons[button].value
    action_code = controller_enums.RemapActions[action].value
    remap_command = legion_configurator.create_button_remap_command(controller_code, btn_code, action_code)

    legion_configurator.send_command(remap_command)

  async def set_touchpad(self, enable: bool):
    t_toggle = legion_configurator.create_touchpad_command(enable)
    decky_plugin.logger.info(t_toggle)

    legion_configurator.send_command(t_toggle)

  async def set_rumble_intensity(self, intensity: str, test_haptic: bool = True):
    try:
      r_name = str(intensity).upper()
      if hasattr(controller_enums.RumbleIntensity, r_name):
        code = controller_enums.RumbleIntensity[r_name].value
        cmd = legion_configurator.create_rumble_intensity_command(code, 0x00)
        legion_configurator.send_command(cmd)

        if test_haptic and r_name != "OFF":
          controllers.trigger_test_vibration(r_name)
    except Exception as e:
      decky_plugin.logger.error(f"set_rumble_intensity error: {e}")


  async def get_inputplumber_info(self):
    return inputplumber_utils.get_inputplumber_info()

  async def set_inputplumber_mode(self, mode: str):
    return inputplumber_utils.set_controller_mode(mode)

  async def set_inputplumber_profiles(self, profiles: list):
    return inputplumber_utils.set_active_profiles(profiles)

  async def reset_controllers(self):
    return controllers.reset_controllers()


  async def _handle_desktop_rpc(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    try:
      data = await asyncio.wait_for(reader.readline(), timeout=5.0)
      if not data:
        writer.close()
        return
      import json
      req = json.loads(data.decode('utf-8'))
      method_name = req.get('method')
      args = req.get('args', [])
      kwargs = req.get('kwargs', {})

      if not method_name or method_name.startswith('_') or not hasattr(self, method_name):
        resp = {'ok': False, 'error': f'Unknown method: {method_name}'}
      else:
        fn = getattr(self, method_name)
        res = await fn(*args, **kwargs)
        resp = {'ok': True, 'result': res}
    except Exception as e:
      decky_plugin.logger.error(f"Desktop RPC error: {e}")
      resp = {'ok': False, 'error': str(e)}

    try:
      import json
      writer.write((json.dumps(resp) + '\n').encode('utf-8'))
      await writer.drain()
    except Exception:
      pass
    finally:
      try:
        writer.close()
      except Exception:
        pass


  async def _main(self):
    decky_plugin.logger.info("LeGO Suite Starting")
    migrations.check_ryzenadj_coall_support()

    try:
      settings = get_saved_settings()
      saved_mode = settings.get('tdpMode')
      if saved_mode:
        legion_space.set_tdp_mode(saved_mode)
    except Exception as e:
      decky_plugin.logger.error(f"Error restoring tdpMode on start: {e}")

    if charge_limit.supports_charge_limit():
      charge_limit.initialize_charge_limit()

    if legion_go2_brightness.is_legion_go_2():
      decky_plugin.logger.info("Legion Go 2 detected, starting backlight watcher")
      self._backlight_task = asyncio.create_task(
        legion_go2_brightness.backlight_watcher_loop()
      )
    self._charge_limit_task = asyncio.create_task(
      self._charge_limit_watcher_loop()
    )
    try:
      self._rpc_server = await asyncio.start_server(
        self._handle_desktop_rpc, '127.0.0.1', 47392
      )
      decky_plugin.logger.info("LeGO Suite Desktop RPC server listening on 127.0.0.1:47392")
    except Exception as e:
      decky_plugin.logger.error(f"Could not start Desktop RPC server: {e}")

  async def _unload(self):
    decky_plugin.logger.info("LeGO Suite Unloading")
    legion_go2_brightness.stop_backlight_watcher()
    if hasattr(self, '_rpc_server') and self._rpc_server:
      self._rpc_server.close()
      await self._rpc_server.wait_closed()
    if hasattr(self, '_backlight_task'):
      self._backlight_task.cancel()
    if hasattr(self, '_charge_limit_task'):
      self._charge_limit_task.cancel()

  async def _uninstall(self):
    decky_plugin.logger.info("LeGO Suite Uninstalling")
    pass

  async def _migration(self):
    decky_plugin.logger.info("Migrating")

# Samantha: Te portaste mal conmigo. Yo te quería
