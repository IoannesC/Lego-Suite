

import * as languages from "./languages.json";

function getLangs() {
  const langs = { ...languages.language_metadata };

  Object.keys(languages).map((lang) => {
    if (lang === "language_metadata" || lang == "steam_language_map") {
      return;
    }
    const strs = (languages as any)[lang];
    if (lang && strs && (langs as any)[lang]?.name) {
      (langs as any)[lang].strings = strs;
    }
  });

  return langs;
}

export const LANGS: {
  [key: string]: {
    name: string;
    strings: {
      [key: string]: string;
    };
  };
} = getLangs() as any;

let forcedLang: string | undefined = (() => {
  try {
    return window.localStorage.getItem("legoSuite.language") || undefined;
  } catch {
    return undefined;
  }
})();

export const setForcedLanguage = (lang: string) => {
  forcedLang = lang;
  try {
    window.localStorage.setItem("legoSuite.language", lang);
  } catch {}
};

export const getForcedLanguage = (): string | undefined => {
  return forcedLang;
};

export const getCurrentLanguage = (): string => {
  if (forcedLang) return forcedLang;

  const locales = (window as any).LocalizationManager?.m_rgLocalesToUse;
  if (locales && locales.length > 0) {
    let l = locales[0];
    if (l && l.includes("-")) l = l.split("-")[0];
    if (LANGS[l]) return l;
  }
  return "es";
};

export const getLanguageName = (lang?: string): string => {
  const targetLang = lang || getCurrentLanguage();
  return LANGS[targetLang]?.name || targetLang;
};


const t = (key: string, originalString: string): string => {
  let lang = getCurrentLanguage();
  if (lang && lang.includes("-")) {
    lang = lang.split("-")[0];
  }

  return LANGS[lang]?.strings?.[key] ?? originalString;
};

export default t;
