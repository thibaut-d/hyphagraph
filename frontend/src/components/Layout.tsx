import { useState } from "react";
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
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  ListItemIcon,
  Divider,
  useMediaQuery,
  useTheme,
} from "@mui/material";
import MenuIcon from "@mui/icons-material/Menu";
import CloseIcon from "@mui/icons-material/Close";
import LanguageIcon from "@mui/icons-material/Language";
import HomeIcon from "@mui/icons-material/Home";
import CategoryIcon from "@mui/icons-material/Category";
import LibraryBooksIcon from "@mui/icons-material/LibraryBooks";
import SearchIcon from "@mui/icons-material/Search";

import { ProfileMenu } from "./ProfileMenu";
import { GlobalSearch } from "./GlobalSearch";
import { useAuthContext } from "../auth/AuthContext";

const menuItems = [
  { key: "menu.home", path: "/", icon: HomeIcon },
  { key: "menu.entities", path: "/entities", icon: CategoryIcon },
  { key: "menu.sources", path: "/sources", icon: LibraryBooksIcon },
  { key: "menu.search", path: "/search", icon: SearchIcon },
];

export function Layout() {
  const location = useLocation();
  const { t } = useTranslation();
  const { user } = useAuthContext();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));

  // Mobile menu state
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const toggleLanguage = () => {
    i18n.changeLanguage(i18n.language === "en" ? "fr" : "en");
  };

  const handleMobileMenuOpen = () => {
    setMobileMenuOpen(true);
  };

  const handleMobileMenuClose = () => {
    setMobileMenuOpen(false);
  };

  return (
    <>
      <AppBar position="static">
        <Toolbar sx={{ gap: { xs: 1, sm: 2 } }}>
          {/* Mobile: Hamburger menu (xs/sm only) */}
          <IconButton
            color="inherit"
            aria-label="open menu"
            onClick={handleMobileMenuOpen}
            sx={{ display: { xs: 'flex', md: 'none' } }}
          >
            <MenuIcon />
          </IconButton>

          {/* Logo/Title */}
          <Typography
            variant="h6"
            component={RouterLink}
            to="/"
            sx={{
              color: "inherit",
              textDecoration: "none",
              fontSize: { xs: '1.1rem', sm: '1.25rem' },
              mr: { xs: 0, md: 4 },
            }}
          >
            HyphaGraph
          </Typography>

          {/* Desktop: Main menu (md+ only) */}
          <Box sx={{
            display: { xs: 'none', md: 'flex' },
            alignItems: "center",
            gap: 2,
            flexGrow: 1
          }}>
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

            {/* Desktop: Global Search */}
            <Box sx={{ ml: "auto" }}>
              <GlobalSearch />
            </Box>
          </Box>

          {/* Spacer for mobile (pushes icons to right) */}
          <Box sx={{ flexGrow: 1, display: { xs: 'block', md: 'none' } }} />

          {/* Language switch */}
          <Tooltip title={t("common.change_language", "Change language")}>
            <IconButton
              color="inherit"
              onClick={toggleLanguage}
              size={isMobile ? 'small' : 'medium'}
            >
              <LanguageIcon />
            </IconButton>
          </Tooltip>

          {/* Profile menu or login button */}
          {user ? (
            <ProfileMenu size={isMobile ? 32 : 40} />
          ) : (
            <Button
              component={RouterLink}
              to="/account"
              color="inherit"
              variant="outlined"
              size={isMobile ? 'small' : 'medium'}
              sx={{ ml: { xs: 1, md: 2 } }}
            >
              {t("auth.login", "Login")}
            </Button>
          )}
        </Toolbar>
      </AppBar>

      {/* Mobile: Navigation Drawer */}
      <Drawer
        anchor="left"
        open={mobileMenuOpen}
        onClose={handleMobileMenuClose}
        sx={{
          display: { xs: 'block', md: 'none' },
          '& .MuiDrawer-paper': {
            width: 280,
          },
        }}
      >
        {/* Drawer Header */}
        <Box sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          p: 2,
          borderBottom: 1,
          borderColor: 'divider',
        }}>
          <Typography variant="h6" sx={{ fontWeight: 600 }}>
            {t("menu.navigation", "Navigation")}
          </Typography>
          <IconButton onClick={handleMobileMenuClose} size="small">
            <CloseIcon />
          </IconButton>
        </Box>

        {/* Navigation Links */}
        <List>
          {menuItems.map((item) => {
            const Icon = item.icon;
            const isActive =
              location.pathname === item.path ||
              (item.path !== "/" && location.pathname.startsWith(item.path));

            return (
              <ListItem key={item.path} disablePadding>
                <ListItemButton
                  component={RouterLink}
                  to={item.path}
                  onClick={handleMobileMenuClose}
                  selected={isActive}
                  sx={{
                    py: 1.5,
                    '&.Mui-selected': {
                      backgroundColor: 'action.selected',
                      '&:hover': {
                        backgroundColor: 'action.hover',
                      },
                    },
                  }}
                >
                  <ListItemIcon>
                    <Icon color={isActive ? 'primary' : 'inherit'} />
                  </ListItemIcon>
                  <ListItemText
                    primary={t(item.key)}
                    primaryTypographyProps={{
                      fontWeight: isActive ? 600 : 400,
                    }}
                  />
                </ListItemButton>
              </ListItem>
            );
          })}
        </List>

        <Divider />

        {/* Mobile: Additional Options */}
        <List>
          <ListItem disablePadding>
            <ListItemButton onClick={() => {
              toggleLanguage();
              handleMobileMenuClose();
            }}>
              <ListItemIcon>
                <LanguageIcon />
              </ListItemIcon>
              <ListItemText
                primary={t("common.change_language", "Change language")}
                secondary={i18n.language === 'en' ? 'Français' : 'English'}
              />
            </ListItemButton>
          </ListItem>
        </List>

        {/* User info in drawer (if logged in) */}
        {user && (
          <>
            <Divider />
            <Box sx={{ p: 2, mt: 'auto' }}>
              <Typography variant="caption" color="text.secondary">
                {t("profile.signed_in_as", "Signed in as")}
              </Typography>
              <Typography variant="body2" sx={{ fontWeight: 600 }}>
                {user.email}
              </Typography>
            </Box>
          </>
        )}
      </Drawer>

      {/* Content */}
      <Container
        maxWidth="lg"
        sx={{
          mt: 4,
          px: { xs: 2, sm: 3 },
          mb: 4,
        }}
      >
        <Outlet />
      </Container>
    </>
  );
}