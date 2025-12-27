import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  Paper,
  Typography,
  Stack,
  Box,
  Button,
  TextField,
  Alert,
  Divider,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
} from "@mui/material";
import {
  ArrowBack as ArrowBackIcon,
  Delete as DeleteIcon,
  PauseCircleOutline as DeactivateIcon,
} from "@mui/icons-material";

import { updateProfile, deactivateAccount, deleteAccount } from "../api/auth";
import { useAuthContext } from "../auth/AuthContext";

export function SettingsView() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { user, logout } = useAuthContext();

  const [email, setEmail] = useState(user?.email || "");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [deactivateDialogOpen, setDeactivateDialogOpen] = useState(false);
  const [deactivateLoading, setDeactivateLoading] = useState(false);

  // Redirect to login if not authenticated
  if (!user) {
    navigate("/account");
    return null;
  }

  const handleUpdateEmail = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    // Check if email changed
    if (email === user.email) {
      setError(t("settings.email_unchanged", "Email address unchanged"));
      return;
    }

    // Basic email validation
    if (!email.includes("@")) {
      setError(t("settings.invalid_email", "Please enter a valid email address"));
      return;
    }

    setLoading(true);

    try {
      await updateProfile({ email });
      setSuccess(t("settings.email_updated", "Email address updated successfully"));

      // Note: User might need to re-verify their email
      setTimeout(() => {
        setSuccess(null);
      }, 5000);
    } catch (e: any) {
      setError(e.message || t("settings.update_failed", "Failed to update email"));
    } finally {
      setLoading(false);
    }
  };

  const handleDeactivateAccount = async () => {
    setDeactivateLoading(true);

    try {
      await deactivateAccount();

      // Logout and redirect
      logout();
      navigate("/account");
    } catch (e: any) {
      setError(e.message || t("settings.deactivate_failed", "Failed to deactivate account"));
      setDeactivateDialogOpen(false);
      setDeactivateLoading(false);
    }
  };

  const handleDeleteAccount = async () => {
    setDeleteLoading(true);

    try {
      await deleteAccount();

      // Logout and redirect
      logout();
      navigate("/account");
    } catch (e: any) {
      setError(e.message || t("settings.delete_failed", "Failed to delete account"));
      setDeleteDialogOpen(false);
      setDeleteLoading(false);
    }
  };

  return (
    <Paper sx={{ p: 4, maxWidth: 800, mx: "auto" }}>
      <Stack spacing={4}>
        {/* Header with back button */}
        <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
          <IconButton onClick={() => navigate("/profile")} size="small">
            <ArrowBackIcon />
          </IconButton>
          <Typography variant="h5" sx={{ fontWeight: 600 }}>
            {t("settings.title", "Settings")}
          </Typography>
        </Box>

        {/* Success message */}
        {success && <Alert severity="success">{success}</Alert>}

        {/* Error message */}
        {error && <Alert severity="error">{error}</Alert>}

        {/* Email settings */}
        <Box>
          <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
            {t("settings.email_settings", "Email Settings")}
          </Typography>

          <form onSubmit={handleUpdateEmail}>
            <Stack spacing={2}>
              <TextField
                label={t("settings.email_address", "Email Address")}
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                disabled={loading}
                fullWidth
                helperText={t(
                  "settings.email_help",
                  "You may need to verify your new email address"
                )}
              />

              <Box sx={{ display: "flex", gap: 2 }}>
                <Button
                  variant="outlined"
                  onClick={() => setEmail(user.email)}
                  disabled={loading || email === user.email}
                >
                  {t("common.cancel", "Cancel")}
                </Button>
                <Button
                  type="submit"
                  variant="contained"
                  disabled={loading || email === user.email}
                >
                  {loading
                    ? t("settings.updating", "Updating...")
                    : t("settings.update_email", "Update Email")}
                </Button>
              </Box>
            </Stack>
          </form>
        </Box>

        <Divider />

        {/* Danger zone */}
        <Box>
          <Typography variant="h6" sx={{ mb: 2, fontWeight: 600, color: "error.main" }}>
            {t("settings.danger_zone", "Danger Zone")}
          </Typography>

          <Stack spacing={2}>
            {/* Deactivate Account */}
            <Paper
              variant="outlined"
              sx={{
                p: 3,
                borderColor: "warning.main",
                backgroundColor: (theme) =>
                  theme.palette.mode === "light" ? "#fff3e0" : "#3d2e1e",
              }}
            >
              <Stack spacing={2}>
                <Box>
                  <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 0.5 }}>
                    {t("settings.deactivate_account", "Deactivate Account")}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {t(
                      "settings.deactivate_warning",
                      "Temporarily disable your account without deleting your data. You can reactivate it later by logging in again."
                    )}
                  </Typography>
                </Box>

                <Button
                  variant="outlined"
                  color="warning"
                  startIcon={<DeactivateIcon />}
                  onClick={() => setDeactivateDialogOpen(true)}
                  sx={{ alignSelf: "flex-start" }}
                >
                  {t("settings.deactivate_account_button", "Deactivate My Account")}
                </Button>
              </Stack>
            </Paper>

            {/* Delete Account */}
            <Paper
              variant="outlined"
              sx={{
                p: 3,
                borderColor: "error.main",
                backgroundColor: (theme) =>
                  theme.palette.mode === "light" ? "#ffebee" : "#3d1e1e",
              }}
            >
              <Stack spacing={2}>
                <Box>
                  <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 0.5 }}>
                    {t("settings.delete_account", "Delete Account")}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {t(
                      "settings.delete_warning",
                      "Once you delete your account, there is no going back. This action is permanent and will remove all your data."
                    )}
                  </Typography>
                </Box>

                <Button
                  variant="outlined"
                  color="error"
                  startIcon={<DeleteIcon />}
                  onClick={() => setDeleteDialogOpen(true)}
                  sx={{ alignSelf: "flex-start" }}
                >
                  {t("settings.delete_account_button", "Delete My Account")}
                </Button>
              </Stack>
            </Paper>
          </Stack>
        </Box>
      </Stack>

      {/* Deactivate confirmation dialog */}
      <Dialog
        open={deactivateDialogOpen}
        onClose={() => !deactivateLoading && setDeactivateDialogOpen(false)}
      >
        <DialogTitle>{t("settings.confirm_deactivate", "Confirm Account Deactivation")}</DialogTitle>
        <DialogContent>
          <DialogContentText>
            {t(
              "settings.deactivate_confirmation",
              "Are you sure you want to deactivate your account? Your account will be temporarily disabled, but you can reactivate it by logging in again. Your data will be preserved."
            )}
          </DialogContentText>
          <DialogContentText sx={{ mt: 2, fontWeight: 600 }}>
            {t("settings.email_to_deactivate", "Account:")} {user.email}
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => setDeactivateDialogOpen(false)}
            disabled={deactivateLoading}
          >
            {t("common.cancel", "Cancel")}
          </Button>
          <Button
            onClick={handleDeactivateAccount}
            color="warning"
            variant="contained"
            disabled={deactivateLoading}
            autoFocus
          >
            {deactivateLoading
              ? t("settings.deactivating", "Deactivating...")
              : t("settings.deactivate_confirm_button", "Deactivate Account")}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Delete confirmation dialog */}
      <Dialog
        open={deleteDialogOpen}
        onClose={() => !deleteLoading && setDeleteDialogOpen(false)}
      >
        <DialogTitle>{t("settings.confirm_delete", "Confirm Account Deletion")}</DialogTitle>
        <DialogContent>
          <DialogContentText>
            {t(
              "settings.delete_confirmation",
              "Are you absolutely sure you want to delete your account? This action cannot be undone and all your data will be permanently removed."
            )}
          </DialogContentText>
          <DialogContentText sx={{ mt: 2, fontWeight: 600 }}>
            {t("settings.email_to_delete", "Account:")} {user.email}
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => setDeleteDialogOpen(false)}
            disabled={deleteLoading}
          >
            {t("common.cancel", "Cancel")}
          </Button>
          <Button
            onClick={handleDeleteAccount}
            color="error"
            variant="contained"
            disabled={deleteLoading}
            autoFocus
          >
            {deleteLoading
              ? t("settings.deleting", "Deleting...")
              : t("settings.delete_permanently", "Delete Permanently")}
          </Button>
        </DialogActions>
      </Dialog>
    </Paper>
  );
}
