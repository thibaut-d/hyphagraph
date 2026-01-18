import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  Menu,
  MenuItem,
  ListItemIcon,
  ListItemText,
  Divider,
  Box,
  Typography,
} from "@mui/material";
import {
  Person as PersonIcon,
  Settings as SettingsIcon,
  Logout as LogoutIcon,
  VpnKey as VpnKeyIcon,
  AdminPanelSettings as AdminIcon,
} from "@mui/icons-material";

import { UserAvatar } from "./UserAvatar";
import { useAuthContext } from "../auth/AuthContext";

interface ProfileMenuProps {
  /**
   * Optional size for the avatar (default: 40)
   */
  size?: number;
}

/**
 * Profile menu component with user avatar and dropdown menu.
 * Displays user info and provides navigation to profile-related pages.
 */
export function ProfileMenu({ size = 40 }: ProfileMenuProps) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { user, logout } = useAuthContext();
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);

  const handleClick = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const handleProfile = () => {
    handleClose();
    navigate("/profile");
  };

  const handleChangePassword = () => {
    handleClose();
    navigate("/change-password");
  };

  const handleSettings = () => {
    handleClose();
    navigate("/settings");
  };

  const handleAdmin = () => {
    handleClose();
    navigate("/admin");
  };

  const handleLogout = () => {
    handleClose();
    logout();
    navigate("/account");
  };

  if (!user) {
    return null;
  }

  return (
    <>
      <Box onClick={handleClick} sx={{ cursor: "pointer" }}>
        <UserAvatar email={user.email} size={size} />
      </Box>

      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleClose}
        onClick={handleClose}
        transformOrigin={{ horizontal: "right", vertical: "top" }}
        anchorOrigin={{ horizontal: "right", vertical: "bottom" }}
        slotProps={{
          paper: {
            sx: {
              mt: 1.5,
              minWidth: 220,
            },
          },
        }}
      >
        {/* User info header */}
        <Box sx={{ px: 2, py: 1.5, borderBottom: 1, borderColor: "divider" }}>
          <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
            {user.email}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {t("profile.signed_in", "Signed in")}
          </Typography>
        </Box>

        {/* Menu items */}
        <MenuItem onClick={handleProfile}>
          <ListItemIcon>
            <PersonIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>{t("profile.my_profile", "My Profile")}</ListItemText>
        </MenuItem>

        <MenuItem onClick={handleChangePassword}>
          <ListItemIcon>
            <VpnKeyIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>
            {t("profile.change_password", "Change Password")}
          </ListItemText>
        </MenuItem>

        <MenuItem onClick={handleSettings}>
          <ListItemIcon>
            <SettingsIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>{t("profile.settings", "Settings")}</ListItemText>
        </MenuItem>

        {/* Admin panel link (superusers only) */}
        {user.is_superuser && (
          <MenuItem onClick={handleAdmin}>
            <ListItemIcon>
              <AdminIcon fontSize="small" />
            </ListItemIcon>
            <ListItemText>{t("admin.panel", "Administration")}</ListItemText>
          </MenuItem>
        )}

        <Divider />

        <MenuItem onClick={handleLogout}>
          <ListItemIcon>
            <LogoutIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>{t("profile.logout", "Logout")}</ListItemText>
        </MenuItem>
      </Menu>
    </>
  );
}
