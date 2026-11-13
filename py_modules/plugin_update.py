import os
import stat
import decky_plugin
import subprocess

def restart_decky_loader():
  env = os.environ.copy()
  env["LD_LIBRARY_PATH"] = ""
  cmd = f'echo "sudo systemctl restart plugin_loader.service" | sh'

  return subprocess.run(cmd, shell=True, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)

def recursive_chmod(path, perms):
  for dirpath, dirnames, filenames in os.walk(path):
    current_perms = os.stat(dirpath).st_mode
    os.chmod(dirpath, current_perms | perms)
    for filename in filenames:
      os.chmod(os.path.join(dirpath, filename), current_perms | perms)

def sync_from_scratch():
  try:
    scratch_dir = os.environ.get("LEGO_SUITE_DEV_DIR", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    plugin_dir = os.environ.get("DECKY_PLUGIN_DIR", os.path.expanduser("~/homebrew/plugins/LeGO Suite"))
    if os.path.exists(scratch_dir) and os.path.exists(plugin_dir):
      cmd = f'rsync -av --no-perms --no-owner --no-group "{scratch_dir}/" "{plugin_dir}/" && chmod -R u+rwX,go+rX "{plugin_dir}"'
      res = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
      decky_plugin.logger.info(f"sync_from_scratch output: {res.stdout}")
      return True
  except Exception as e:
    decky_plugin.logger.error(f"sync_from_scratch error: {e}")
    return False

def ota_update():
  return False

def get_latest_version():
  return "0.198"

def reset_settings():
  try:
    settings_dir = os.environ.get("DECKY_PLUGIN_SETTINGS_DIR", f'{decky_plugin.DECKY_USER_HOME}/homebrew/settings/LeGO Suite')
    settings_file = os.path.join(settings_dir, 'settings.json')
    if os.path.exists(settings_file):
      os.remove(settings_file)

    decky_plugin.logger.info(f'removed settings file at {settings_file}')

    return restart_decky_loader()
  except Exception as e:
    decky_plugin.logger.error(f'error during plugin settings reset {e}')
    return False
