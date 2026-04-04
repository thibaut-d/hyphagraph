import { useState } from "react";
import type { ComponentType } from "react";
import { Link as RouterLink, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  Box,
  Button,
  Menu,
  MenuItem,
  IconButton,
  Tooltip,
} from "@mui/material";
import type { SvgIconProps } from "@mui/material";
import ArrowDropDownIcon from "@mui/icons-material/ArrowDropDown";
import FiberManualRecordIcon from "@mui/icons-material/FiberManualRecord";
import { GlobalSearch } from "../GlobalSearch";
import type { UICategoryOption } from "../../api/entities";
import type { UserRead } from "../../types/auth";

export interface MenuItem {
  key: string;
  path: string;
  icon: ComponentType<SvgIconProps>;
  requiresAuth?: boolean;
  requiresSuperuser?: boolean;
}

interface DesktopNavigationProps {
  menuItems: MenuItem[];
  categories: UICategoryOption[];
  user: UserRead | null;
  onNavigate: (path: string) => void;
}

/**
 * Desktop navigation menu.
 *
 * Displays navigation buttons with entity category dropdown.
 * Only shown on medium+ screens.
 */
export function DesktopNavigation({
  menuItems,
  categories,
  user,
  onNavigate,
}: DesktopNavigationProps) {
  const location = useLocation();
  const { t, i18n } = useTranslation();
  const [entitiesMenuAnchor, setEntitiesMenuAnchor] = useState<null | HTMLElement>(null);

  const handleCategoryClick = (categoryId: string) => {
    setEntitiesMenuAnchor(null);
    onNavigate(`/entities?ui_category_id=${categoryId}`);
  };

  return (
    <>
      <Box
        sx={{
          display: { xs: "none", md: "flex" },
          alignItems: "center",
          gap: 2,
          flexGrow: 1,
        }}
      >
        {menuItems
          .filter(
            (item) =>
              (!item.requiresAuth || user) &&
              (!item.requiresSuperuser || user?.is_superuser),
          )
          .map((item) => {
            const isActive =
              location.pathname === item.path ||
              (item.path !== "/" && location.pathname.startsWith(item.path));

            // Special case for Entities: direct link + adjacent chevron for category filter
            if (item.path === "/entities" && categories.length > 0) {
              return (
                <Box key={item.path} sx={{ display: "flex", alignItems: "center" }}>
                  <Button
                    component={RouterLink}
                    to={item.path}
                    color="inherit"
                    sx={{
                      fontWeight: isActive ? "bold" : "normal",
                      textDecoration: isActive ? "underline" : "none",
                      pr: 0.5,
                    }}
                  >
                    {t(item.key)}
                  </Button>
                  <Tooltip title={t("menu.entities_by_category", "Filter by category")}>
                    <IconButton
                      color="inherit"
                      size="small"
                      onClick={(e) => setEntitiesMenuAnchor(e.currentTarget)}
                      aria-label={t("menu.entities_by_category", "Filter by category")}
                      aria-haspopup="true"
                      aria-expanded={Boolean(entitiesMenuAnchor)}
                      sx={{ p: 0.25 }}
                    >
                      <ArrowDropDownIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                </Box>
              );
            }

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

      {/* Entities dropdown menu */}
      <Menu
        anchorEl={entitiesMenuAnchor}
        open={Boolean(entitiesMenuAnchor)}
        onClose={() => setEntitiesMenuAnchor(null)}
        anchorOrigin={{
          vertical: "bottom",
          horizontal: "left",
        }}
        transformOrigin={{
          vertical: "top",
          horizontal: "left",
        }}
      >
        <MenuItem
          component={RouterLink}
          to="/entities"
          onClick={() => setEntitiesMenuAnchor(null)}
        >
          <FiberManualRecordIcon sx={{ fontSize: 8, mr: 1, opacity: 0.6 }} />
          {t("menu.all_entities", "All Entities")}
        </MenuItem>
        {categories.map((category) => {
          const label = category.label[i18n.language as "en" | "fr"] || category.label.en || category.id;
          return (
            <MenuItem
              key={category.id}
              onClick={() => handleCategoryClick(category.id)}
            >
              <FiberManualRecordIcon sx={{ fontSize: 8, mr: 1, opacity: 0.6 }} />
              {label}
            </MenuItem>
          );
        })}
      </Menu>
    </>
  );
}
