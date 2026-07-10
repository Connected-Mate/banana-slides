import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';

import zh from './locales/zh.json';
import en from './locales/en.json';

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      zh: { translation: zh },
      en: { translation: en },
    },
    fallbackLng: 'en',
    debug: false,
    interpolation: {
      escapeValue: false,
    },
    detection: {
      // English by default for new users, even on a zh/ja/etc browser locale.
      // Only an explicit choice (persisted below) switches the language;
      // browser-locale auto-detection is intentionally not used.
      order: ['localStorage'],
      caches: ['localStorage'],
      lookupLocalStorage: 'banana-slides-language',
    },
  });

export default i18n;
