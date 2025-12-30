import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import {
  Paper,
  Typography,
  Stack,
  TextField,
  Button,
  Alert,
} from "@mui/material";

import { requestPasswordReset } from "../api/auth";

export function ForgotPasswordView() {
  const { t } = useTranslation();
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    setError(null);
    setSuccess(false);
    setLoading(true);

    try {
      await requestPasswordReset(email);
      setSuccess(true);
      setEmail("");
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Paper sx={{ p: 3, maxWidth: 500, mx: "auto", mt: 4 }}>
      <Stack spacing={2}>
        <Typography variant="h5">
          {t("forgot_password.title", "Forgot Password")}
        </Typography>

        <Typography variant="body2" color="text.secondary">
          {t(
            "forgot_password.description",
            "Enter your email address and we'll send you a link to reset your password."
          )}
        </Typography>

        {success && (
          <Alert severity="success">
            {t(
              "forgot_password.success",
              "If an account exists with that email, we've sent a password reset link. Please check your email."
            )}
          </Alert>
        )}

        {error && <Alert severity="error">{error}</Alert>}

        <TextField
          label={t("forgot_password.email", "Email")}
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          disabled={loading || success}
          fullWidth
        />

        <Button
          variant="contained"
          onClick={handleSubmit}
          disabled={loading || success || !email}
          fullWidth
        >
          {t("forgot_password.submit", "Send Reset Link")}
        </Button>

        <Link to="/account" style={{ textAlign: "center", display: "block" }}>
          {t("forgot_password.back_to_login", "Back to Login")}
        </Link>
      </Stack>
    </Paper>
  );
}
