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

export function AccountView() {
  const { t } = useTranslation();
  const { user, login, logout } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [registrationSuccess, setRegistrationSuccess] = useState(false);

  const handleLogin = async () => {
    setError(null);
    setRegistrationSuccess(false);
    try {
      const res = await apiLogin({
        username: email,
        password,
      });
      login(res.access_token, res.refresh_token);
    } catch (e: any) {
      setError(e.message);
    }
  };

  const handleRegister = async () => {
    setError(null);
    setRegistrationSuccess(false);
    try {
      await apiRegister({ email, password });
      // Show success message instead of auto-login
      // (in case email verification is required)
      setRegistrationSuccess(true);
      setPassword(""); // Clear password for security
    } catch (e: any) {
      setError(e.message);
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
      <Stack spacing={2}>
        <Typography variant="h5">
          {t("account.login", "Login")}
        </Typography>

        <TextField
          label={t("account.email", "Email")}
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />

        <TextField
          label={t("account.password", "Password")}
          type="password"
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

        <Button variant="contained" onClick={handleLogin}>
          {t("account.login", "Login")}
        </Button>

        <Button variant="outlined" onClick={handleRegister}>
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