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
import { useAsyncAction } from "../hooks/useAsyncAction";
import { useValidationMessage } from "../hooks/useValidationMessage";

type ValidationField = "email";

export function ForgotPasswordView() {
  const { t } = useTranslation();
  const [email, setEmail] = useState("");
  const [success, setSuccess] = useState(false);
  const {
    setValidationMessage,
    clearValidationMessage: clearError,
    getFieldError,
    hasFieldError,
  } = useValidationMessage<ValidationField>();
  const [submitError, setSubmitError] = useState<string | null>(null);
  const { isRunning: loading, run } = useAsyncAction((message) => setSubmitError(message ?? ""));

  const handleSubmit = async () => {
    clearError();
    setSuccess(false);
    setSubmitError(null);
    if (!email.trim()) {
      setValidationMessage(t("forgot_password.email_required", "Email is required"), "email");
      return;
    }
    const result = await run(async () => {
      await requestPasswordReset(email.trim());
      setSuccess(true);
      setEmail("");
    }, t("forgot_password.error", "Failed to send reset link"));

    if (!result.ok) {
      return;
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

        {submitError && <Alert severity="error">{submitError}</Alert>}

        <TextField
          label={t("forgot_password.email", "Email")}
          type="email"
          value={email}
          onChange={(e) => {
            setEmail(e.target.value);
            clearError("email");
          }}
          disabled={loading || success}
          fullWidth
          error={hasFieldError("email")}
          helperText={getFieldError("email") ?? " "}
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
