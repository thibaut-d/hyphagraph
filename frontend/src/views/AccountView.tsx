import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import {
  Paper,
  Typography,
  Stack,
  TextField,
  Button,
} from "@mui/material";

import { login as apiLogin, register as apiRegister } from "../api/auth";
import { useAuth } from "../auth/useAuth";
import { useAsyncAction } from "../hooks/useAsyncAction";

export function AccountView() {
  const { t } = useTranslation();
  const { user, login, logout } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [passwordConfirm, setPasswordConfirm] = useState("");
  const [passwordConfirmError, setPasswordConfirmError] = useState("");
  const [registrationSuccess, setRegistrationSuccess] = useState(false);
  const [error, setError] = useState("");
  const { isRunning, run } = useAsyncAction((message) => setError(message ?? ""));

  const handleLogin = async () => {
    setError("");
    setRegistrationSuccess(false);
    const result = await run(async () => {
      const res = await apiLogin({
        username: email,
        password,
      });
      login(res.access_token, res.refresh_token);
    }, t("account.login_error", "Login failed"));

    if (!result.ok) {
      return;
    }
  };

  const handleRegister = async () => {
    setError("");
    setPasswordConfirmError("");
    setRegistrationSuccess(false);

    if (password.length < 8) {
      setError(t("account.password_too_short", "Password must be at least 8 characters"));
      return;
    }
    if (password !== passwordConfirm) {
      setPasswordConfirmError(t("account.password_mismatch", "Passwords do not match"));
      return;
    }

    const result = await run(async () => {
      await apiRegister({ email, password, password_confirmation: passwordConfirm });
      // Show success message instead of auto-login
      // (in case email verification is required)
      setRegistrationSuccess(true);
      setPassword(""); // Clear password for security
      setPasswordConfirm("");
    }, t("account.register_error", "Registration failed"));

    if (!result.ok) {
      return;
    }
  };

  if (user) {
    return (
      <Paper sx={{ p: 3 }}>
        <Typography variant="h5">
          {t("account.title", "My account")}
        </Typography>

        <Typography sx={{ mt: 2 }}>
          {t("account.logged_as", "Logged in as")} {user.email}
        </Typography>

        <Stack direction="row" spacing={2} sx={{ mt: 2 }}>
          <Button
            variant="outlined"
            component={Link}
            to="/account/change-password"
          >
            {t("account.change_password", "Change Password")}
          </Button>
          <Button
            variant="outlined"
            color="error"
            onClick={logout}
          >
            {t("account.logout", "Logout")}
          </Button>
        </Stack>
      </Paper>
    );
  }

  return (
    <Paper sx={{ p: 3 }}>
      <Stack
        component="form"
        spacing={2}
        onSubmit={(event) => {
          event.preventDefault();
          void handleLogin();
        }}
      >
        <Typography variant="h5">
          {t("account.login", "Login")}
        </Typography>

        <TextField
          label={t("account.email", "Email")}
          name="email"
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />

        <TextField
          label={t("account.password", "Password")}
          name="password"
          type="password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />

        <TextField
          label={t("account.password_confirm", "Confirm Password")}
          name="password_confirmation"
          type="password"
          value={passwordConfirm}
          onChange={(e) => {
            setPasswordConfirm(e.target.value);
            setPasswordConfirmError("");
          }}
          error={!!passwordConfirmError}
          helperText={passwordConfirmError || t("account.password_confirm_hint", "Only required for registration")}
        />

        {error && <Typography color="error">{error}</Typography>}

        {registrationSuccess && (
          <Paper
            sx={{
              p: 2,
              backgroundColor: "#f0fdf4",
              border: "1px solid #22c55e",
            }}
          >
            <Typography
              sx={{ fontWeight: "600", color: "#15803d", mb: 1 }}
            >
              {t("account.registration_success", "Registration Successful!")}
            </Typography>
            <Typography sx={{ fontSize: "14px", color: "#166534" }}>
              {t(
                "account.check_email",
                "Please check your email for a verification link. You may need to verify your email before logging in."
              )}
            </Typography>
            <Link
              to="/resend-verification"
              style={{
                display: "inline-block",
                marginTop: "8px",
                fontSize: "14px",
                color: "#0ea5e9",
                textDecoration: "none",
              }}
            >
              {t("account.resend_verification", "Resend verification email")}
            </Link>
          </Paper>
        )}

        <Button type="submit" variant="contained" disabled={isRunning}>
          {t("account.login", "Login")}
        </Button>

        <Button
          type="button"
          variant="outlined"
          disabled={isRunning}
          onClick={() => {
            void handleRegister();
          }}
        >
          {t("account.register", "Register")}
        </Button>

        <Link
          to="/forgot-password"
          style={{
            textAlign: "center",
            fontSize: "14px",
            color: "#1976d2",
            textDecoration: "none",
            marginTop: "8px",
          }}
        >
          {t("account.forgot_password", "Forgot password?")}
        </Link>
      </Stack>
    </Paper>
  );
}
