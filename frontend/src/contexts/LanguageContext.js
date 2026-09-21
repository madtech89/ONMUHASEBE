import React, { createContext, useContext, useState } from 'react';
import tr from '../i18n/tr';
import en from '../i18n/en';

const translations = { tr, en };
const LanguageContext = createContext();

export function LanguageProvider({ children }) {
  const [language, setLanguage] = useState(() => localStorage.getItem('lang') || 'tr');

  const switchLanguage = (lang) => {
    setLanguage(lang);
    localStorage.setItem('lang', lang);
  };

  const t = (key) => {
    const keys = key.split('.');
    let value = translations[language];
    for (const k of keys) {
      value = value?.[k];
      if (value === undefined) return key;
    }
    return value || key;
  };

  return (
    <LanguageContext.Provider value={{ language, switchLanguage, t }}>
      {children}
    </LanguageContext.Provider>
  );
}

export const useLanguage = () => useContext(LanguageContext);
