import type { ReactNode } from "react";

import { Alert, Box, Button, Stack, Typography } from "@mui/material";
import { Navigate } from "react-router-dom";
import { Link as RouterLink } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { ProtectedRoute } from "./ProtectedRoute";
import { useAuth } from "../auth/useAuth";

interface SuperuserRouteProps {
  children: ReactNode;
}

export function SuperuserRoute({ children }: SuperuserRouteProps) {
  const { user } = useAuth();
  const { t } = useTranslation();

  return (
    <ProtectedRoute>
      {user?.is_superuser ? children : (
        user ? (
          <Box sx={{ maxWidth: 720, mx: "auto", mt: 4 }}>
            <Alert severity="error">
              <Stack spacing={1}>
                <Typography variant="h6">{t("auth.forbidden_title", "403 Forbidden")}</Typography>
                <Typography variant="body2">
                  {t("auth.forbidden_message", "You do not have permission to access this page.")}
                </Typography>
                <Box>
                  <Button component={RouterLink} to="/" size="small" variant="outlined">
                    {t("auth.return_home", "Return Home")}
                  </Button>
                </Box>
              </Stack>
            </Alert>
          </Box>
        ) : <Navigate to="/" replace />
      )}
    </ProtectedRoute>
  );
}
