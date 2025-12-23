import { useState } from "react";
import { useTranslation } from "react-i18next";

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

  const handleLogin = async () => {
    setError(null);
    try {
      const res: any = await apiLogin({
        username: email,
        password,
      });
      login(res.access_token);
    } catch (e: any) {
      setError(e.message);
    }
  };

  const handleRegister = async () => {
    setError(null);
    try {
      await apiRegister({ email, password });
      await handleLogin();
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

        <Button variant="contained" onClick={handleLogin}>
          {t("account.login", "Login")}
        </Button>

        <Button variant="outlined" onClick={handleRegister}>
          {t("account.register", "Register")}
        </Button>
      </Stack>
    </Paper>
  );
}