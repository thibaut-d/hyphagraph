import { useCallback } from "react";
import { Link as RouterLink, useNavigate, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  Alert,
  Box,
  Breadcrumbs,
  Button,
  Chip,
  CircularProgress,
  Divider,
  Link,
  Paper,
  Stack,
  Typography,
} from "@mui/material";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import EditIcon from "@mui/icons-material/Edit";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";

import { getRelation } from "../api/relations";
import { getSource } from "../api/sources";
import type { RelationRead } from "../types/relation";
import type { SourceRead } from "../types/source";
import { useAsyncResource } from "../hooks/useAsyncResource";
import { usePageErrorHandler } from "../hooks/usePageErrorHandler";

interface RelationDetailData {
  relation: RelationRead;
  source: SourceRead | null;
}

function formatDirectionColor(direction: string | null | undefined) {
  switch (direction) {
    case "supports":
      return "success";
    case "contradicts":
      return "error";
    default:
      return "default";
  }
}

function formatDirectionLabel(direction: string | null | undefined, fallback: string) {
  if (!direction) {
    return fallback;
  }

  return direction.replace(/[_-]+/g, " ");
}

function formatNotes(notes: string | Record<string, string> | null | undefined) {
  if (!notes) {
    return null;
  }

  if (typeof notes === "string") {
    return notes;
  }

  return Object.entries(notes)
    .map(([language, value]) => `${language}: ${value}`)
    .join("\n");
}

export function RelationDetailView() {
  const { id } = useParams<{ id: string }>();
  const { t } = useTranslation();
  const navigate = useNavigate();
  const handlePageError = usePageErrorHandler();

  const loadRelationDetail = useCallback(async (): Promise<RelationDetailData> => {
    if (!id) {
      throw new Error("Missing relation ID");
    }

    const relation = await getRelation(id);
    const source = relation.source_id ? await getSource(relation.source_id) : null;
    return { relation, source };
  }, [id]);

  const {
    data,
    loading,
    error,
  } = useAsyncResource<RelationDetailData>({
    enabled: Boolean(id),
    deps: [id],
    load: loadRelationDetail,
    onError: (err) => handlePageError(err, "Failed to load relation").userMessage,
  });

  if (loading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", p: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error || !data) {
    return <Alert severity="error">{error || t("common.error", "An error occurred")}</Alert>;
  }

  const { relation, source } = data;
  const notesText = formatNotes(relation.notes);
  const participantSummary = relation.roles
    .map((role) => role.entity_slug || role.entity_id)
    .join(" • ");

  return (
    <Stack spacing={3}>
      <Breadcrumbs>
        <Link component={RouterLink} to="/relations" underline="hover">
          {t("relations.title", "Relations")}
        </Link>
        {source ? (
          <Link component={RouterLink} to={`/sources/${source.id}`} underline="hover">
            {source.title}
          </Link>
        ) : (
          <Typography color="text.primary">
            {relation.source_id}
          </Typography>
        )}
        <Typography color="text.primary">
          {relation.kind || t("relation.untitled", "Untitled relation")}
        </Typography>
      </Breadcrumbs>

      <Box>
        <Button
          startIcon={<ArrowBackIcon />}
          onClick={() => navigate(`/sources/${relation.source_id}`)}
          variant="outlined"
          size="small"
        >
          {t("common.back", "Back to source")}
        </Button>
      </Box>

      <Paper sx={{ p: 3 }}>
        <Stack spacing={2}>
          <Stack
            direction={{ xs: "column", sm: "row" }}
            justifyContent="space-between"
            spacing={2}
          >
            <Box>
              <Typography variant="h4" component="h1">
                {relation.kind || t("relation.untitled", "Untitled relation")}
              </Typography>
              <Typography variant="subtitle1" sx={{ mt: 1 }}>
                {participantSummary || t("relation.no_participants", "No linked participants")}
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                {t(
                  "relation.detail_description",
                  "Document-grounded relation with explicit roles, direction, and source traceability."
                )}
              </Typography>
            </Box>

            <Stack direction="row" spacing={1} flexWrap="wrap">
              <Chip
                label={formatDirectionLabel(
                  relation.direction,
                  t("relation.no_direction", "No direction"),
                )}
                color={formatDirectionColor(relation.direction)}
                variant="outlined"
              />
              <Chip
                label={`${t("relation.roles", "Roles")}: ${relation.roles.length}`}
                variant="outlined"
              />
              <Chip
                label={`${t("relation.confidence", "Confidence")}: ${Math.round((relation.confidence ?? 0) * 100)}%`}
                color={(relation.confidence ?? 0) >= 0.7 ? "success" : (relation.confidence ?? 0) >= 0.4 ? "warning" : "default"}
                variant="outlined"
              />
              <Chip
                label={`${t("relation.status", "Status")}: ${relation.status}`}
                variant="outlined"
              />
            </Stack>
          </Stack>

          <Stack direction="row" spacing={1}>
            <Button
              component={RouterLink}
              to={`/relations/${relation.id}/edit`}
              startIcon={<EditIcon />}
              variant="contained"
            >
              {t("common.edit", "Edit")}
            </Button>
            <Button
              component={RouterLink}
              to={`/sources/${relation.source_id}`}
              endIcon={<OpenInNewIcon />}
              variant="outlined"
            >
              {t("relation.view_source", "View source")}
            </Button>
          </Stack>
        </Stack>
      </Paper>

      <Paper sx={{ p: 3 }}>
        <Stack spacing={2}>
          <Typography variant="h5">
            {t("relation.roles", "Roles")}
          </Typography>
          <Divider />
          {relation.roles.length === 0 ? (
            <Alert severity="info">
              {t("relation.no_roles", "No roles were recorded for this relation.")}
            </Alert>
          ) : (
            <Stack spacing={1.5}>
              {relation.roles.map((role) => (
                <Paper key={role.id} variant="outlined" sx={{ p: 2 }}>
                  <Stack
                    direction={{ xs: "column", sm: "row" }}
                    justifyContent="space-between"
                    spacing={1}
                  >
                    <Box>
                      <Typography variant="subtitle2" color="text.secondary">
                        {role.role_type}
                      </Typography>
                      <Link component={RouterLink} to={`/entities/${role.entity_id}`} underline="hover">
                        {role.entity_slug || role.entity_id}
                      </Link>
                    </Box>
                    <Stack direction="row" spacing={1} flexWrap="wrap">
                      {role.weight != null && (
                        <Chip
                          label={`${t("relation.weight", "Weight")}: ${role.weight}`}
                          size="small"
                          variant="outlined"
                        />
                      )}
                      {role.coverage != null && (
                        <Chip
                          label={`${t("relation.coverage", "Coverage")}: ${role.coverage}`}
                          size="small"
                          variant="outlined"
                        />
                      )}
                      {role.disagreement != null && (
                        <Chip
                          label={`${t("relation.disagreement", "Disagreement")}: ${Math.round(role.disagreement * 100)}%`}
                          size="small"
                          variant="outlined"
                        />
                      )}
                    </Stack>
                  </Stack>
                </Paper>
              ))}
            </Stack>
          )}
        </Stack>
      </Paper>

      <Paper sx={{ p: 3 }}>
        <Stack spacing={2}>
          <Typography variant="h5">
            {t("relation.source_context", "Source context")}
          </Typography>
          <Divider />
          {source ? (
            <Stack spacing={1}>
              <Link component={RouterLink} to={`/sources/${source.id}`} variant="h6" underline="hover">
                {source.title}
              </Link>
              <Typography variant="body2" color="text.secondary">
                {[
                  source.kind,
                  source.year ? String(source.year) : null,
                  source.authors?.length ? source.authors.slice(0, 3).join(", ") : null,
                ]
                  .filter(Boolean)
                  .join(" • ")}
              </Typography>
              {source.summary?.en && (
                <Typography variant="body2">
                  {source.summary.en}
                </Typography>
              )}
            </Stack>
          ) : (
            <Alert severity="info">
              {t("relation.source_missing", "Source details are unavailable for this relation.")}
            </Alert>
          )}
        </Stack>
      </Paper>

      {(notesText || relation.scope || relation.created_at || relation.updated_at) && (
        <Paper sx={{ p: 3 }}>
          <Stack spacing={2}>
            <Typography variant="h5">
              {t("relation.audit_details", "Audit details")}
            </Typography>
            <Divider />
            {notesText && (
              <Box>
                <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                  {t("evidence.table.notes", "Notes")}
                </Typography>
                <Typography variant="body2" sx={{ whiteSpace: "pre-wrap" }}>
                  {notesText}
                </Typography>
              </Box>
            )}
            {relation.scope && (
              <Box>
                <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                  {t("relation.scope", "Scope")}
                </Typography>
                <Typography variant="body2" component="pre" sx={{ m: 0, whiteSpace: "pre-wrap" }}>
                  {JSON.stringify(relation.scope, null, 2)}
                </Typography>
              </Box>
            )}
            <Typography variant="body2" color="text.secondary">
              {t("common.created", "Created")}: {new Date(relation.created_at).toLocaleString()}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {t("common.updated", "Updated")}: {new Date(relation.updated_at).toLocaleString()}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {t("relation.id", "Relation ID")}: {relation.id}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {t("relation.source_id", "Source ID")}: {relation.source_id}
            </Typography>
          </Stack>
        </Paper>
      )}
    </Stack>
  );
}
