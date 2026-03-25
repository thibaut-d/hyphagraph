import { useTranslation } from "react-i18next";
import i18n from "i18next";
import { Button, Tooltip } from "@mui/material";
import LanguageIcon from "@mui/icons-material/Language";

/**
 * Language switcher component.
 *
 * Toggles between English and French languages.
 * The button label shows the language you will switch TO (e.g. "FR" when current is English).
 */
export function LanguageSwitch() {
  const { t } = useTranslation();
  const nextLang = i18n.language === "en" ? "fr" : "en";
  const nextLangLabel = i18n.language === "en" ? "FR" : "EN";

  const toggleLanguage = () => {
    i18n.changeLanguage(nextLang);
    localStorage.setItem("hyphagraph_lang", nextLang);
  };

  return (
    <Tooltip title={t("common.change_language", "Change Language")}>
      <Button
        color="inherit"
        onClick={toggleLanguage}
        size="small"
        startIcon={<LanguageIcon />}
        aria-label={nextLangLabel}
      >
        {nextLangLabel}
      </Button>
    </Tooltip>
  );
}
