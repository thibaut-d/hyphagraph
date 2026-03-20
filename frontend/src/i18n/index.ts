import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import en from "./en.json";
import fr from "./fr.json";

const LANG_KEY = "hyphagraph_lang";

i18n
  .use(initReactI18next)
  .init({
    resources: {
      en: { translation: en },
      fr: { translation: fr },
    },
    lng: localStorage.getItem(LANG_KEY) ?? "en",  // restore persisted language
    fallbackLng: "en",
    interpolation: {
      escapeValue: false,
    },
  });

export default i18n;