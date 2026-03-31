import { useState, useEffect, useCallback } from "react";
import { Link as RouterLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";

import {
  AppBar,
  Toolbar,
  Typography,
  Box,
  Button,
  Container,
  IconButton,
  Tooltip,
  useMediaQuery,
  useTheme,
} from "@mui/material";
import MenuIcon from "@mui/icons-material/Menu";
import SearchIcon from "@mui/icons-material/Search";
import HomeIcon from "@mui/icons-material/Home";
import CategoryIcon from "@mui/icons-material/Category";
import LibraryBooksIcon from "@mui/icons-material/LibraryBooks";
import RateReviewIcon from "@mui/icons-material/RateReview";
import BugReportIcon from "@mui/icons-material/BugReport";

import { ProfileMenu } from "./ProfileMenu";
import { LanguageSwitch } from "./layout/LanguageSwitch";
import { DesktopNavigation } from "./layout/DesktopNavigation";
import { MobileDrawer } from "./layout/MobileDrawer";
import { MobileSearchDialog } from "./layout/MobileSearchDialog";
import { BugReportDialog } from "./BugReportDialog";
import { useAuthContext } from "../auth/AuthContext";
import { usePageErrorHandler } from "../hooks/usePageErrorHandler";
import { getEntityFilterOptions } from "../api/entities";
import type { UICategoryOption } from "../api/entities";
const menuItems = [
  { key: "menu.home", path: "/", icon: HomeIcon },
  { key: "menu.entities", path: "/entities", icon: CategoryIcon },
  { key: "menu.sources", path: "/sources", icon: LibraryBooksIcon },
  { key: "menu.search", path: "/search", icon: SearchIcon },
  {
    key: "menu.review_queue",
    path: "/review-queue",
    icon: RateReviewIcon,
    requiresAuth: true,
    requiresSuperuser: true,
  },
];

export function Layout() {
  const location = useLocation();
  const navigate = useNavigate();
  const { t } = useTranslation();
  const { user } = useAuthContext();
  const handlePageError = usePageErrorHandler();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));

  // Mobile menu state
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [mobileSearchOpen, setMobileSearchOpen] = useState(false);
  const [bugReportOpen, setBugReportOpen] = useState(false);
  const openBugReport = useCallback(() => setBugReportOpen(true), []);
  const closeBugReport = useCallback(() => setBugReportOpen(false), []);

  // Entities dropdown state
  const [categories, setCategories] = useState<UICategoryOption[]>([]);

  // Fetch UI categories for Entities dropdown
  useEffect(() => {
    getEntityFilterOptions()
      .then((options) => {
        if (options.ui_categories) {
          setCategories(options.ui_categories);
        }
      })
      .catch((error) => {
        handlePageError(error, "Failed to fetch UI categories");
      });
  }, []);

  // Close mobile search dialog on navigation
  useEffect(() => {
    setMobileSearchOpen(false);
  }, [location.pathname]);


  return (
    <>
      <AppBar position="static">
        <Toolbar sx={{ gap: { xs: 1, sm: 2 } }}>
          {/* Mobile: Hamburger menu (xs/sm only) */}
          <IconButton
            color="inherit"
            aria-label="open menu"
            onClick={() => setMobileMenuOpen(true)}
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
          <DesktopNavigation
            menuItems={menuItems}
            categories={categories}
            user={user}
            onNavigate={navigate}
          />

          {/* Spacer for mobile (pushes icons to right) */}
          <Box sx={{ flexGrow: 1, display: { xs: 'block', md: 'none' } }} />

          {/* Mobile: Search button (xs/sm only) */}
          <Tooltip title={t("common.search", "Search")}>
            <IconButton
              color="inherit"
              onClick={() => setMobileSearchOpen(true)}
              size="small"
              sx={{ display: { xs: 'flex', md: 'none' } }}
            >
              <SearchIcon />
            </IconButton>
          </Tooltip>

          {/* Bug report */}
          <Tooltip title={t("bug_report.tooltip", "Report a bug")}>
            <IconButton color="inherit" onClick={openBugReport} size="small" aria-label={t("bug_report.tooltip", "Report a bug")}>
              <BugReportIcon fontSize="small" />
            </IconButton>
          </Tooltip>

          {/* Language switch */}
          <LanguageSwitch />

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
      <MobileDrawer
        open={mobileMenuOpen}
        onClose={() => setMobileMenuOpen(false)}
        menuItems={menuItems}
        categories={categories}
        user={user}
      />

      {/* Bug Report Dialog */}
      <BugReportDialog open={bugReportOpen} onClose={closeBugReport} />

      {/* Mobile: Search Dialog */}
      <MobileSearchDialog
        open={mobileSearchOpen}
        onClose={() => setMobileSearchOpen(false)}
      />

      {/* Content */}
      <Container
        component="main"
        maxWidth="lg"
        sx={{
          mt: { xs: 2, sm: 3, md: 4 },
          px: { xs: 2, sm: 3, md: 4 },
          mb: { xs: 3, sm: 4 },
        }}
      >
        <Outlet />
      </Container>
    </>
  );
}
