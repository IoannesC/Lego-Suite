import json
import os
import locale
import decky_plugin

STEAM_CONFIG_PATHS = [
    f'{decky_plugin.DECKY_USER_HOME}/.steam/registry.vdf',
]

PLUGIN_DIR = getattr(decky_plugin, 'DECKY_PLUGIN_DIR', f'{decky_plugin.DECKY_USER_HOME}/homebrew/plugins/LeGO Suite')
I18N_DIR = os.path.join(PLUGIN_DIR, 'i18n')
if not os.path.exists(I18N_DIR):
    I18N_DIR = os.path.join(PLUGIN_DIR, 'defaults', 'i18n')

LANGS = None
STEAM_LANGUAGE_MAP = None

def load_configs():
    global LANGS
    global STEAM_LANGUAGE_MAP

    if LANGS and STEAM_LANGUAGE_MAP:
        return

    if not os.path.exists(I18N_DIR):
        return

    try:
        with open(os.path.join(I18N_DIR, 'language_metadata.json'), 'r', encoding='utf-8') as f:
            LANGS = json.load(f)
    except Exception as e:
        print(f"Error loading language metadata: {e}")

    try:
        with open(os.path.join(I18N_DIR, 'steam_language_map.json'), 'r', encoding='utf-8') as f:
            STEAM_LANGUAGE_MAP = json.load(f)
    except Exception as e:
        print(f"Error loading steam language map: {e}")

load_configs()

def load_translations():
    """Load all translation files from the i18n directory"""
    translations = {}

    if not os.path.exists(I18N_DIR):
        return translations
    
    try:
        for filename in os.listdir(I18N_DIR):
            if filename.startswith('language_metadata'):
                continue

            if filename.startswith('steam_language_map'):
                continue

            if filename.endswith('.json'):
                lang = filename.replace('.json', '')
                try:
                    with open(os.path.join(I18N_DIR, filename), 'r', encoding='utf-8') as f:
                        translations[lang] = json.load(f)
                except Exception as e:
                    print(f"Error loading translation file {filename}: {e}")
    except Exception as e:
        print(f"Error reading i18n directory {I18N_DIR}: {e}")
    
    return translations

TRANSLATIONS = load_translations()

_cached_lang = None
_cached_steam_lang = None

def get_steam_lang():
    global _cached_steam_lang

    if _cached_steam_lang:
        return _cached_steam_lang

    get_current_language()

    return _cached_steam_lang

def get_current_language():
    """
    Get the current language (Steam Deck / Settings compatible)
    Priority:
        0. User preference in settings.json ('language')
        1. Steam language config file
        ...
    """
    global _cached_lang
    global _cached_steam_lang
    
    try:
        from plugin_settings import get_saved_settings
        saved_s = get_saved_settings()
        if isinstance(saved_s, dict):
            pref_lang = saved_s.get("language")
            if not pref_lang:
                d_theme = saved_s.get("desktopTheme")
                if isinstance(d_theme, dict):
                    pref_lang = d_theme.get("language")
            if pref_lang and pref_lang in LANGS:
                _cached_lang = pref_lang
                return pref_lang
    except Exception:
        pass

    if _cached_lang:
        return _cached_lang

    lang = None
    
    try:
        
        for config_path in STEAM_CONFIG_PATHS:
            if os.path.exists(config_path):
                try:
                    with open(config_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        
                        import re
                        
                        hkcu_section = re.search(r'"HKCU"\s*\{(.*?)\}\s*\}', content, re.DOTALL)
                        if hkcu_section:
                            hkcu_content = hkcu_section.group(1)
                            
                            hkcu_content = re.sub(r'"steamglobal"\s*\{[^}]*\}', '', hkcu_content, flags=re.DOTALL)
                            
                            match = re.search(r'"language"\s+"(\w+)"', hkcu_content, re.IGNORECASE)
                            if match:
                                steam_lang = match.group(1).lower()
                                _cached_steam_lang = steam_lang

                                lang_code = STEAM_LANGUAGE_MAP.get(steam_lang, steam_lang[:2])
                                if lang_code in LANGS:
                                    lang = lang_code
                                    break
                except PermissionError:
                    continue
                except Exception:
                    continue
    except Exception:
        pass
    
    if not lang:
        steam_lang = os.environ.get('STEAM_COMPAT_CLIENT_INSTALL_PATH', '')
        if 'korean' in steam_lang.lower():
            lang = 'ko'
    
    if not lang:
        lang_env = os.environ.get('LANGUAGE', '').split(':')[0].split('_')[0].lower()
        if lang_env in LANGS:
            lang = lang_env
    
    if not lang:
        lang_env = os.environ.get('LANG', '').split('.')[0].split('_')[0].lower()
        if lang_env in LANGS:
            lang = lang_env
    
    if not lang:
        try:
            system_locale = locale.getdefaultlocale()[0]
            if system_locale:
                lang_code = system_locale.split('_')[0].lower()
                if lang_code in LANGS:
                    lang = lang_code
        except:
            pass
    
    if not lang:
        lang = 'en'
    
    _cached_lang = lang
    return lang

def get_language_name(lang=None):
    """
    Get the display name of a language
    
    Args:
        lang (str, optional): Language code. If None, uses current language
    
    Returns:
        str: Language display name (e.g., '한국어', 'English')
    
    Example:
        get_language_name('ko')  # Returns: '한국어'
        get_language_name()      # Returns: current language name
    """
    if lang is None:
        lang = get_current_language()
    
    return LANGS.get(lang, {}).get('name', lang)

def t(key, default_text, lang=None):
    """
    Translate a key to the target language
    
    Args:
        key (str): Translation key
        default_text (str): Default text (fallback, usually English)
        lang (str, optional): Language code. If None, uses current system language
    
    Returns:
        str: Translated string or default text if translation not found
    
    Example:
        # With explicit language
        t('ADVANCED_ENABLE_TDP_CONTROLS', 'Enable TDP Controls', 'ko')
        # Returns: 'TDP 제어 활성화'
        
        # With auto-detected language
        t('ADVANCED_ENABLE_TDP_CONTROLS', 'Enable TDP Controls')
        # Returns: translation based on system language
    """
    if lang is None:
        lang = get_current_language()
    
    return TRANSLATIONS.get(lang, {}).get(key, default_text)

def set_language(lang):
    """
    Manually set the current language (overrides auto-detection)
    
    Args:
        lang (str): Language code to set
    
    Example:
        set_language('ko')  # Force Korean
        set_language('en')  # Force English
    """
    global _cached_lang
    if lang in LANGS:
        _cached_lang = lang
    else:
        print(f"Warning: Language '{lang}' not supported. Available: {list(LANGS.keys())}")

def reset_language():
    """
    Reset language cache to force re-detection
    
    Example:
        reset_language()  # Next call to get_current_language() will re-detect
    """
    global _cached_lang
    _cached_lang = None

def get_language_debug_info():
    """
    Get debug information about language detection (useful for Decky Plugin debugging)
    
    Returns:
        dict: Debug information including paths, environment variables, and detection result
    
    Example:
        debug_info = get_language_debug_info()
        print(json.dumps(debug_info, indent=2))
    """
    import re
    
    debug_info = {
        'detected_language': get_current_language(),
        'cached': _cached_lang is not None,
        'current_file': os.path.abspath(__file__),
        'working_directory': os.getcwd(),
        'steam_config_files': {},
        'environment_variables': {},
        'decky_environment': {},
        'translations_loaded': list(TRANSLATIONS.keys()),
        'supported_languages': list(LANGS.keys()),
        'i18n_paths_checked': [],
    }
    
    decky_vars = [
        'DECKY_PLUGIN_DIR',
        'DECKY_PLUGIN_NAME',
        'DECKY_USER_HOME',
        'DECKY_HOME',
        'DECKY_VERSION',
    ]
    for var in decky_vars:
        value = os.environ.get(var)
        if value:
            debug_info['decky_environment'][var] = value
    
    if os.environ.get('DECKY_PLUGIN_DIR'):
        plugin_dir = os.environ.get('DECKY_PLUGIN_DIR')
        decky_i18n_path = os.path.join(plugin_dir, 'i18n')
        debug_info['decky_environment']['expected_i18n_path'] = decky_i18n_path
        debug_info['decky_environment']['expected_i18n_exists'] = os.path.exists(decky_i18n_path)
    
    current_file = os.path.abspath(__file__)
    possible_i18n_paths = [
        ('Environment variable I18N_DIR', os.environ.get('I18N_DIR')),
        ('Decky Plugin (DECKY_PLUGIN_DIR/i18n)', 
         os.path.join(os.environ.get('DECKY_PLUGIN_DIR', ''), 'i18n') if os.environ.get('DECKY_PLUGIN_DIR') else None),
        ('Same directory (i18n/)', os.path.dirname(current_file)),
    ]
    
    for desc, path in possible_i18n_paths:
        if not path:
            continue
            
        abs_path = os.path.abspath(path)
        path_info = {
            'description': desc,
            'path': abs_path,
            'exists': os.path.exists(abs_path),
            'is_dir': os.path.isdir(abs_path) if os.path.exists(abs_path) else False,
            'files': []
        }
        
        if path_info['exists'] and path_info['is_dir']:
            try:
                path_info['files'] = [f for f in os.listdir(abs_path) if f.endswith('.json')]
            except Exception as e:
                path_info['error'] = str(e)
        
        debug_info['i18n_paths_checked'].append(path_info)
    
    for path in STEAM_CONFIG_PATHS:
        exists = os.path.exists(path)
        language_found = None
        
        if exists:
            try:
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    match = re.search(r'"language"\s+"(\w+)"', content, re.IGNORECASE)
                    if match:
                        language_found = match.group(1)
            except Exception as e:
                language_found = f'ERROR: {str(e)}'
        
        debug_info['steam_config_files'][path] = {
            'exists': exists,
            'language': language_found
        }
    
    env_vars = ['I18N_DIR', 'LANGUAGE', 'LANG', 'LC_ALL', 'STEAM_COMPAT_CLIENT_INSTALL_PATH', 'HOME', 'USER']
    for var in env_vars:
        debug_info['environment_variables'][var] = os.environ.get(var, None)
    
    debug_info['i18n_directory_used'] = None
    for path_info in debug_info['i18n_paths_checked']:
        if path_info['exists'] and path_info['is_dir'] and path_info['files']:
            debug_info['i18n_directory_used'] = path_info['path']
            break
    
    return debug_info

def reload_translations():
    """Reload translation files (useful for development)"""
    global TRANSLATIONS
    TRANSLATIONS = load_translations()