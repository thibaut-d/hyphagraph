import { useState } from "react";
import type { ComponentType } from "react";
import { Link as RouterLink, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import i18n from "i18next";
import type { SvgIconProps } from "@mui/material";
import {
  Drawer,
  Box,
  Typography,
  IconButton,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  ListItemIcon,
  Collapse,
  Divider,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import ExpandLessIcon from "@mui/icons-material/ExpandLess";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import FiberManualRecordIcon from "@mui/icons-material/FiberManualRecord";
import type { UICategoryOption } from "../../api/entities";
import type { UserRead } from "../../types/auth";
import { LanguageSwitch } from "./LanguageSwitch";

export interface MenuItem {
  key: string;
  path: string;
  icon: ComponentType<SvgIconProps>;
  requiresAuth?: boolean;
}

interface MobileDrawerProps {
  open: boolean;
  onClose: () => void;
  menuItems: MenuItem[];
  categories: UICategoryOption[];
  user: UserRead | null;
}

/**
 * Mobile navigation drawer.
 *
 * Displays navigation menu in a drawer for mobile screens.
 * Includes expandable entity categories.
 */
export function MobileDrawer({
  open,
  onClose,
  menuItems,
  categories,
  user,
}: MobileDrawerProps) {
  const location = useLocation();
  const { t } = useTranslation();
  const [entitiesExpanded, setEntitiesExpanded] = useState(false);

  return (
    <Drawer
      anchor="left"
      open={open}
      onClose={onClose}
      sx={{
        display: { xs: "block", md: "none" },
        "& .MuiDrawer-paper": {
          width: 280,
        },
      }}
    >
      {/* Drawer Header */}
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          p: 2,
          borderBottom: 1,
          borderColor: "divider",
        }}
      >
        <Typography variant="h6" sx={{ fontWeight: 600 }}>
          {t("menu.navigation", "Navigation")}
        </Typography>
        <IconButton onClick={onClose} size="small">
          <CloseIcon />
        </IconButton>
      </Box>

      {/* Navigation Links */}
      <List>
        {menuItems
          .filter((item) => !item.requiresAuth || user)
          .map((item) => {
            const Icon = item.icon;
            const isActive =
              location.pathname === item.path ||
              (item.path !== "/" && location.pathname.startsWith(item.path));

            // Special case for Entities menu with expandable categories
            if (item.path === "/entities" && categories.length > 0) {
              return (
                <Box key={item.path}>
                  <ListItem disablePadding>
                    <ListItemButton
                      onClick={() => setEntitiesExpanded(!entitiesExpanded)}
                      selected={isActive}
                      sx={{
                        py: 1.5,
                        "&.Mui-selected": {
                          backgroundColor: "action.selected",
                          "&:hover": {
                            backgroundColor: "action.hover",
                          },
                        },
                      }}
                    >
                      <ListItemIcon>
                        <Icon color={isActive ? "primary" : "inherit"} />
                      </ListItemIcon>
                      <ListItemText
                        primary={t(item.key)}
                        primaryTypographyProps={{
                          fontWeight: isActive ? 600 : 400,
                        }}
                      />
                      {entitiesExpanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                    </ListItemButton>
                  </ListItem>
                  <Collapse in={entitiesExpanded} timeout="auto" unmountOnExit>
                    <List component="div" disablePadding>
                      <ListItemButton
                        component={RouterLink}
                        to="/entities"
                        onClick={onClose}
                        sx={{ pl: 4, py: 1 }}
                      >
                        <ListItemIcon>
                          <FiberManualRecordIcon fontSize="small" />
                        </ListItemIcon>
                        <ListItemText
                          primary={t("menu.all_entities", "All Entities")}
                          primaryTypographyProps={{ fontWeight: 600 }}
                        />
                      </ListItemButton>
                      {categories.map((category) => {
                        const label =
                          category.label[i18n.language as "en" | "fr"] || category.label.en;
                        return (
                          <ListItemButton
                            key={category.id}
                            component={RouterLink}
                            to={`/entities?ui_category_id=${category.id}`}
                            onClick={onClose}
                            sx={{ pl: 4, py: 1 }}
                          >
                            <ListItemIcon>
                              <FiberManualRecordIcon fontSize="small" />
                            </ListItemIcon>
                            <ListItemText primary={label} />
                          </ListItemButton>
                        );
                      })}
                    </List>
                  </Collapse>
                </Box>
              );
            }

            return (
              <ListItem key={item.path} disablePadding>
                <ListItemButton
                  component={RouterLink}
                  to={item.path}
                  onClick={onClose}
                  selected={isActive}
                  sx={{
                    py: 1.5,
                    "&.Mui-selected": {
                      backgroundColor: "action.selected",
                      "&:hover": {
                        backgroundColor: "action.hover",
                      },
                    },
                  }}
                >
                  <ListItemIcon>
                    <Icon color={isActive ? "primary" : "inherit"} />
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

      {/* Footer: Language switcher */}
      <Divider />
      <Box sx={{ p: 1, display: "flex", alignItems: "center", gap: 1 }}>
        <Typography variant="body2" sx={{ flexGrow: 1 }}>
          {t("menu.current_language")}
        </Typography>
        <LanguageSwitch />
      </Box>
    </Drawer>
  );
}
