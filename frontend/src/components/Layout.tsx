import { Link as RouterLink, Outlet, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import i18n from "i18next";

import {
  AppBar,
  Toolbar,
  Typography,
  Box,
  Button,
  Container,
  IconButton,
  Tooltip,
} from "@mui/material";
import LanguageIcon from "@mui/icons-material/Language";

const menuItems = [
  { key: "menu.home", path: "/" },
  { key: "menu.entities", path: "/entities" },
  { key: "menu.sources", path: "/sources" },
  { key: "menu.search", path: "/search" },
  { key: "menu.account", path: "/account" },
];

export function Layout() {
  const location = useLocation();
  const { t } = useTranslation();

  const toggleLanguage = () => {
    i18n.changeLanguage(i18n.language === "en" ? "fr" : "en");
  };

  return (
    <>
      <AppBar position="static">
        <Toolbar>
          {/* Title */}
          <Typography
            variant="h6"
            component={RouterLink}
            to="/"
            sx={{ mr: 4, color: "inherit", textDecoration: "none" }}
          >
            HyphaGraph
          </Typography>

          {/* Main menu */}
          <Box sx={{ flexGrow: 1 }}>
            {menuItems.map((item) => {
              const isActive =
                location.pathname === item.path ||
                (item.path !== "/" && location.pathname.startsWith(item.path));

              return (
                <Button
                  key={item.path}
                  component={RouterLink}
                  to={item.path}
                  color="inherit"
                  sx={{
                    fontWeight: isActive ? "bold" : "normal",
                    textDecoration: isActive ? "underline" : "none",
                  }}
                >
                  {t(item.key)}
                </Button>
              );
            })}
          </Box>

          {/* Language switch */}
          <Tooltip title={t("common.change_language", "Change language")}>
            <IconButton color="inherit" onClick={toggleLanguage}>
              <LanguageIcon />
            </IconButton>
          </Tooltip>
        </Toolbar>
      </AppBar>

      {/* Content */}
      <Container maxWidth="lg" sx={{ mt: 4 }}>
        <Outlet />
      </Container>
    </>
  );
}