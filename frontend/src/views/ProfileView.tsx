import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  Paper,
  Typography,
  Stack,
  Box,
  Button,
  Divider,
} from "@mui/material";
import {
  Person as PersonIcon,
  VpnKey as VpnKeyIcon,
  Settings as SettingsIcon,
} from "@mui/icons-material";

import { useAuthContext } from "../auth/AuthContext";
import { UserAvatar } from "../components/UserAvatar";

export function ProfileView() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { user, logout } = useAuthContext();

  // Redirect to login if not authenticated
  if (!user) {
    navigate("/account");
    return null;
  }

  return (
    <Paper sx={{ p: 4, maxWidth: 800, mx: "auto" }}>
      <Stack spacing={3}>
        {/* Header with avatar */}
        <Box sx={{ display: "flex", alignItems: "center", gap: 3 }}>
          <UserAvatar email={user.email} size={80} />
          <Box>
            <Typography variant="h4" sx={{ fontWeight: 600 }}>
              {t("profile.my_profile", "My Profile")}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {t("profile.signed_in", "Signed in")}
            </Typography>
          </Box>
        </Box>

        <Divider />

        {/* User information */}
        <Box>
          <Typography
            variant="subtitle2"
            color="text.secondary"
            sx={{ mb: 0.5 }}
          >
            {t("profile.email_label", "Email address")}
          </Typography>
          <Typography variant="body1" sx={{ fontWeight: 500 }}>
            {user.email}
          </Typography>
        </Box>

        <Box>
          <Typography
            variant="subtitle2"
            color="text.secondary"
            sx={{ mb: 0.5 }}
          >
            {t("profile.user_id", "User ID")}
          </Typography>
          <Typography variant="body2" sx={{ fontFamily: "monospace" }}>
            {user.id}
          </Typography>
        </Box>

        <Divider />

        {/* Action buttons */}
        <Stack spacing={2}>
          <Typography variant="h6" sx={{ fontWeight: 600 }}>
            {t("profile.account_actions", "Account Actions")}
          </Typography>

          <Button
            variant="outlined"
            startIcon={<VpnKeyIcon />}
            onClick={() => navigate("/change-password")}
            sx={{ justifyContent: "flex-start" }}
          >
            {t("profile.change_password", "Change Password")}
          </Button>

          <Button
            variant="outlined"
            startIcon={<SettingsIcon />}
            onClick={() => navigate("/settings")}
            sx={{ justifyContent: "flex-start" }}
          >
            {t("profile.settings", "Settings")}
          </Button>
        </Stack>

        <Divider />

        {/* Logout button */}
        <Box sx={{ pt: 2 }}>
          <Button
            variant="outlined"
            color="error"
            onClick={() => {
              logout();
              navigate("/account");
            }}
            fullWidth
          >
            {t("profile.logout", "Logout")}
          </Button>
        </Box>
      </Stack>
    </Paper>
  );
}
