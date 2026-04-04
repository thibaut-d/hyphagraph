import { Alert } from "@mui/material";
import { Navigate, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";

/**
 * Legacy route shim.
 *
 * `/explain/:entityId/:roleType` now redirects to the canonical
 * entity property-detail page under `/entities/:id/properties/:roleType`.
 */
export function ExplanationView() {
  const { entityId, roleType } = useParams<{ entityId: string; roleType: string }>();
  const { t } = useTranslation();

  if (!entityId || !roleType) {
    return (
      <Alert severity="error">
        {t("common.error", "An error occurred")}
      </Alert>
    );
  }

  return <Navigate to={`/entities/${entityId}/properties/${roleType}`} replace />;
}
