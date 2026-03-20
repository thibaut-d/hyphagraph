import { useTranslation } from "react-i18next";
import i18n from "i18next";
import { IconButton, Tooltip } from "@mui/material";
import LanguageIcon from "@mui/icons-material/Language";

/**
 * Language switcher component.
 *
 * Toggles between English and French languages.
 */
export function LanguageSwitch() {
  const { t } = useTranslation();

  const toggleLanguage = () => {
    const newLang = i18n.language === "en" ? "fr" : "en";
    i18n.changeLanguage(newLang);
    localStorage.setItem("hyphagraph_lang", newLang);
  };

  return (
    <Tooltip title={t("common.change_language", "Change Language")}>
      <IconButton color="inherit" onClick={toggleLanguage} size="large">
        <LanguageIcon />
      </IconButton>
    </Tooltip>
  );
}
