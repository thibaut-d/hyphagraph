import { useState } from "react";
import { Link as RouterLink, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  Box,
  Button,
  Menu,
  MenuItem,
} from "@mui/material";
import ArrowDropDownIcon from "@mui/icons-material/ArrowDropDown";
import FiberManualRecordIcon from "@mui/icons-material/FiberManualRecord";
import { GlobalSearch } from "../GlobalSearch";
import type { UICategoryOption } from "../../api/entities";

export interface MenuItem {
  key: string;
  path: string;
  icon: any;
  requiresAuth?: boolean;
}

interface DesktopNavigationProps {
  menuItems: MenuItem[];
  categories: UICategoryOption[];
  user: any;
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
  const { t } = useTranslation();
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
          .filter((item) => !item.requiresAuth || user)
          .map((item) => {
            const isActive =
              location.pathname === item.path ||
              (item.path !== "/" && location.pathname.startsWith(item.path));

            // Special case for Entities menu with dropdown
            if (item.path === "/entities" && categories.length > 0) {
              return (
                <Button
                  key={item.path}
                  color="inherit"
                  endIcon={<ArrowDropDownIcon />}
                  onClick={(e) => setEntitiesMenuAnchor(e.currentTarget)}
                  sx={{
                    fontWeight: isActive ? "bold" : "normal",
                    textDecoration: isActive ? "underline" : "none",
                  }}
                >
                  {t(item.key)}
                </Button>
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
        {categories.map((category) => (
          <MenuItem
            key={category.value}
            onClick={() => handleCategoryClick(category.value)}
          >
            <FiberManualRecordIcon sx={{ fontSize: 8, mr: 1, opacity: 0.6 }} />
            {category.label}
          </MenuItem>
        ))}
      </Menu>
    </>
  );
}
