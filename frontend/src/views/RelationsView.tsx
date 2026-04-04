import { Alert, Stack } from "@mui/material";
import { useTranslation } from "react-i18next";
import { Navigate } from "react-router-dom";

export default function RelationsView() {
  const { t } = useTranslation();

  return (
    <Stack spacing={2}>
      <Alert severity="info">
        {t(
          "relations.redirect_notice",
          "Relations are browsed from source evidence sections. Redirecting to Sources."
        )}
      </Alert>
      <Navigate to="/sources" replace />
    </Stack>
  );
}
