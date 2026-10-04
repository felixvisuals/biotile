import i18n from "i18next";
import LanguageDetector from "i18next-browser-languagedetector";
import { initReactI18next } from "react-i18next";
import de from "./de";
import en from "./en";

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: { en: { translation: en }, de: { translation: de } },
    fallbackLng: "en", // international jury first, German for schools
    supportedLngs: ["en", "de"],
    interpolation: { escapeValue: false },
    returnObjects: true,
    detection: { order: ["localStorage", "navigator"], caches: ["localStorage"] },
  });

i18n.on("languageChanged", (lng) => {
  document.documentElement.lang = lng;
});

export default i18n;
