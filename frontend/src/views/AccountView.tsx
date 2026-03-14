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
    setRegistrationSuccess(false);
    const result = await run(async () => {
      await apiRegister({ email, password });
      // Show success message instead of auto-login
      // (in case email verification is required)
      setRegistrationSuccess(true);
      setPassword(""); // Clear password for security
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

        <Button
          sx={{ mt: 2 }}
          variant="outlined"
          onClick={logout}
        >
          {t("account.logout", "Logout")}
        </Button>
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
