/**
 * Batch relation creation view.
 *
 * Allows creating multiple relations from a single source in one session.
 * Layout: shared source selector → list of relation cards → submit all.
 *
 * Each relation card has: kind, confidence, and N roles (entity + role_type).
 * After submit, a result summary replaces the form.
 */
import { useEffect, useId, useRef, useState } from "react";
import { Link as RouterLink } from "react-router-dom";
import { useTranslation } from "react-i18next";

import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Divider,
  IconButton,
  MenuItem,
  Paper,
  Stack,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import DeleteIcon from "@mui/icons-material/Delete";
import ErrorOutlineIcon from "@mui/icons-material/ErrorOutline";

import { listEntities } from "../api/entities";
import { listSources } from "../api/sources";
import { createRelation, type RoleWrite } from "../api/relations";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface RelationDraft {
  id: string;
  kind: string;
  confidence: number;
  roles: RoleWrite[];
}

interface RowResult {
  id: string;
  kind: string;
  ok: boolean;
  error?: string;
  relationId?: string;
}

interface EntityOption {
  id: string;
  label: string;
}

interface SourceOption {
  id: string;
  title?: string;
}

const MAX_ROWS = 20;
let draftCounter = 0;
function newDraftId() {
  return `draft-${++draftCounter}`;
}

function emptyDraft(): RelationDraft {
  return {
    id: newDraftId(),
    kind: "",
    confidence: 0.7,
    roles: [
      { entity_id: "", role_type: "" },
      { entity_id: "", role_type: "" },
    ],
  };
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function BatchCreateRelationsView() {
  const { t } = useTranslation();
  const headingId = useId();

  const [entities, setEntities] = useState<EntityOption[]>([]);
  const [sources, setSources] = useState<SourceOption[]>([]);
  const [loadingMeta, setLoadingMeta] = useState(true);
  const [metaError, setMetaError] = useState<string | null>(null);

  // Shared source
  const [sourceId, setSourceId] = useState("");
  const [sourceError, setSourceError] = useState<string | null>(null);

  // List of relation drafts
  const [drafts, setDrafts] = useState<RelationDraft[]>([emptyDraft()]);

  // Submission state
  const [submitting, setSubmitting] = useState(false);
  const [results, setResults] = useState<RowResult[] | null>(null);

  // Scroll to first error
  const firstErrorRef = useRef<HTMLDivElement>(null);

  // -------------------------------------------------------------------------
  // Load entities + sources
  // -------------------------------------------------------------------------
  useEffect(() => {
    Promise.all([listEntities(), listSources()])
      .then(([entitiesRes, sourcesRes]) => {
        const items = Array.isArray(entitiesRes)
          ? entitiesRes
          : (entitiesRes.items ?? []);
        setEntities(items.map((e) => ({ id: e.id, label: e.slug })));
        setSources(sourcesRes.items ?? []);
      })
      .catch((err: unknown) => {
        setMetaError(err instanceof Error ? err.message : String(err));
      })
      .finally(() => setLoadingMeta(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // -------------------------------------------------------------------------
  // Draft mutations
  // -------------------------------------------------------------------------
  const addDraft = () => {
    if (drafts.length >= MAX_ROWS) return;
    setDrafts((prev) => [...prev, emptyDraft()]);
  };

  const removeDraft = (id: string) => {
    setDrafts((prev) => prev.filter((d) => d.id !== id));
  };

  const updateDraft = (id: string, patch: Partial<Omit<RelationDraft, "id" | "roles">>) => {
    setDrafts((prev) =>
      prev.map((d) => (d.id === id ? { ...d, ...patch } : d))
    );
  };

  const addRole = (draftId: string) => {
    setDrafts((prev) =>
      prev.map((d) =>
        d.id === draftId
          ? { ...d, roles: [...d.roles, { entity_id: "", role_type: "" }] }
          : d
      )
    );
  };

  const updateRole = (draftId: string, roleIndex: number, patch: Partial<RoleWrite>) => {
    setDrafts((prev) =>
      prev.map((d) =>
        d.id === draftId
          ? {
              ...d,
              roles: d.roles.map((r, i) =>
                i === roleIndex ? { ...r, ...patch } : r
              ),
            }
          : d
      )
    );
  };

  const removeRole = (draftId: string, roleIndex: number) => {
    setDrafts((prev) =>
      prev.map((d) =>
        d.id === draftId
          ? { ...d, roles: d.roles.filter((_, i) => i !== roleIndex) }
          : d
      )
    );
  };

  // -------------------------------------------------------------------------
  // Validation (client-side)
  // -------------------------------------------------------------------------
  function validateDraft(d: RelationDraft): string | null {
    if (!d.kind.trim()) return t("batch_relations.error_kind_required");
    if (d.roles.length < 2) return t("batch_relations.error_roles_required");
    if (d.roles.some((r) => !r.entity_id || !r.role_type.trim()))
      return t("batch_relations.error_role_fields_required");
    return null;
  }

  // -------------------------------------------------------------------------
  // Submit
  // -------------------------------------------------------------------------
  const handleSubmit = async () => {
    if (!sourceId) {
      setSourceError(t("batch_relations.error_source_required"));
      return;
    }
    setSourceError(null);
    setSubmitting(true);
    const rowResults: RowResult[] = [];

    for (const draft of drafts) {
      const validationError = validateDraft(draft);
      if (validationError) {
        rowResults.push({ id: draft.id, kind: draft.kind, ok: false, error: validationError });
        continue;
      }
      try {
        const relation = await createRelation({
          source_id: sourceId,
          kind: draft.kind.trim(),
          confidence: draft.confidence,
          roles: draft.roles,
        });
        rowResults.push({ id: draft.id, kind: draft.kind, ok: true, relationId: relation.id });
      } catch (err: unknown) {
        rowResults.push({
          id: draft.id,
          kind: draft.kind,
          ok: false,
          error: err instanceof Error ? err.message : t("common.error"),
        });
      }
    }

    setResults(rowResults);
    setSubmitting(false);
  };

  const handleReset = () => {
    setResults(null);
    setDrafts([emptyDraft()]);
    setSourceId("");
  };

  // -------------------------------------------------------------------------
  // Render: loading
  // -------------------------------------------------------------------------
  if (loadingMeta) {
    return (
      <Stack alignItems="center" mt={6}>
        <CircularProgress role="progressbar" />
      </Stack>
    );
  }

  // -------------------------------------------------------------------------
  // Render: results summary
  // -------------------------------------------------------------------------
  if (results) {
    const succeeded = results.filter((r) => r.ok).length;
    const failed = results.filter((r) => !r.ok).length;
    return (
      <Box sx={{ p: 2 }}>
        <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
          <Button component={RouterLink} to="/relations" size="small" startIcon={<ArrowBackIcon />}>
            {t("relations.title")}
          </Button>
        </Stack>

        <Typography variant="h5" sx={{ mb: 3 }}>
          {t("batch_relations.page_title")}
        </Typography>

        <Paper sx={{ p: 3, maxWidth: 600 }}>
          <Stack spacing={2}>
            <Stack direction="row" spacing={1} alignItems="center">
              {failed === 0 ? (
                <CheckCircleOutlineIcon color="success" />
              ) : (
                <ErrorOutlineIcon color="warning" />
              )}
              <Typography variant="h6">{t("batch_relations.done_title")}</Typography>
            </Stack>

            <Stack direction="row" spacing={1}>
              <Chip
                label={t("batch_relations.stat_created", { count: succeeded })}
                color="success"
                size="small"
              />
              {failed > 0 && (
                <Chip
                  label={t("batch_relations.stat_failed", { count: failed })}
                  color="error"
                  size="small"
                />
              )}
            </Stack>

            {/* Per-row result list */}
            <Stack spacing={1}>
              {results.map((r) => (
                <Stack key={r.id} direction="row" spacing={1} alignItems="center">
                  {r.ok ? (
                    <CheckCircleOutlineIcon color="success" fontSize="small" />
                  ) : (
                    <ErrorOutlineIcon color="error" fontSize="small" />
                  )}
                  <Typography variant="body2" sx={{ fontWeight: 500, flex: 1 }}>
                    {r.kind || "—"}
                  </Typography>
                  {!r.ok && r.error && (
                    <Typography variant="caption" color="error">
                      {r.error}
                    </Typography>
                  )}
                </Stack>
              ))}
            </Stack>

            <Stack direction="row" spacing={2}>
              <Button variant="outlined" onClick={handleReset}>
                {t("batch_relations.create_more")}
              </Button>
              <Button
                variant="contained"
                component={RouterLink}
                to="/relations"
                startIcon={<ArrowBackIcon />}
              >
                {t("batch_relations.back_to_relations")}
              </Button>
            </Stack>
          </Stack>
        </Paper>
      </Box>
    );
  }

  // -------------------------------------------------------------------------
  // Render: batch form
  // -------------------------------------------------------------------------
  const canSubmit = drafts.length > 0 && !submitting;

  return (
    <Box sx={{ p: 2 }}>
      {/* Header */}
      <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
        <Button component={RouterLink} to="/relations" size="small" startIcon={<ArrowBackIcon />}>
          {t("relations.title")}
        </Button>
      </Stack>

      <Typography variant="h5" id={headingId} sx={{ mb: 3 }}>
        {t("batch_relations.page_title")}
      </Typography>

      {metaError && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {metaError}
        </Alert>
      )}

      {/* Shared source selector */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Typography variant="subtitle2" sx={{ mb: 1 }}>
          {t("batch_relations.source_label")}
        </Typography>
        <TextField
          select
          label={t("batch_relations.source_label")}
          value={sourceId}
          onChange={(e) => {
            setSourceId(e.target.value);
            setSourceError(null);
          }}
          fullWidth
          size="small"
          error={!!sourceError}
          helperText={sourceError ?? " "}
          data-testid="source-select"
        >
          {sources.map((s) => (
            <MenuItem key={s.id} value={s.id}>
              {s.title ?? s.id}
            </MenuItem>
          ))}
        </TextField>
      </Paper>

      {/* Relation cards */}
      <Stack spacing={2} sx={{ mb: 2 }}>
        {drafts.map((draft, draftIndex) => (
          <Card key={draft.id} variant="outlined" ref={draftIndex === 0 ? firstErrorRef : null}>
            <CardContent>
              <Stack spacing={2}>
                {/* Card header */}
                <Stack direction="row" alignItems="center" spacing={1}>
                  <Typography variant="subtitle2" sx={{ flex: 1 }}>
                    {t("batch_relations.relation_n", { n: draftIndex + 1 })}
                  </Typography>
                  <Tooltip title={t("common.delete")}>
                    <span>
                      <IconButton
                        size="small"
                        onClick={() => removeDraft(draft.id)}
                        disabled={drafts.length === 1}
                        aria-label={t("common.delete")}
                      >
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    </span>
                  </Tooltip>
                </Stack>

                {/* Kind + Confidence */}
                <Stack direction={{ xs: "column", sm: "row" }} spacing={2}>
                  <TextField
                    label={t("batch_relations.kind_label")}
                    value={draft.kind}
                    onChange={(e) => updateDraft(draft.id, { kind: e.target.value })}
                    size="small"
                    sx={{ flex: 2 }}
                    placeholder={t("batch_relations.kind_placeholder")}
                  />
                  <TextField
                    label={t("batch_relations.confidence_label")}
                    type="number"
                    inputProps={{ min: 0, max: 1, step: 0.05 }}
                    value={draft.confidence}
                    onChange={(e) =>
                      updateDraft(draft.id, { confidence: Number(e.target.value) })
                    }
                    size="small"
                    sx={{ flex: 1 }}
                  />
                </Stack>

                <Divider />

                {/* Roles */}
                <Typography variant="caption" color="text.secondary">
                  {t("batch_relations.roles_label")}
                </Typography>

                {draft.roles.map((role, roleIndex) => (
                  <Stack direction="row" spacing={1} key={roleIndex} alignItems="center">
                    <TextField
                      select
                      label={t("batch_relations.entity_label")}
                      value={role.entity_id}
                      onChange={(e) =>
                        updateRole(draft.id, roleIndex, { entity_id: e.target.value })
                      }
                      size="small"
                      sx={{ flex: 2 }}
                    >
                      {entities.map((e) => (
                        <MenuItem key={e.id} value={e.id}>
                          {e.label}
                        </MenuItem>
                      ))}
                    </TextField>
                    <TextField
                      label={t("batch_relations.role_type_label")}
                      value={role.role_type}
                      onChange={(e) =>
                        updateRole(draft.id, roleIndex, { role_type: e.target.value })
                      }
                      size="small"
                      sx={{ flex: 2 }}
                      placeholder={t("batch_relations.role_type_placeholder")}
                    />
                    <IconButton
                      size="small"
                      onClick={() => removeRole(draft.id, roleIndex)}
                      disabled={draft.roles.length <= 1}
                      aria-label={t("batch_relations.remove_role")}
                    >
                      <DeleteIcon fontSize="small" />
                    </IconButton>
                  </Stack>
                ))}

                <Button
                  size="small"
                  startIcon={<AddIcon />}
                  variant="text"
                  onClick={() => addRole(draft.id)}
                >
                  {t("batch_relations.add_role")}
                </Button>
              </Stack>
            </CardContent>
          </Card>
        ))}
      </Stack>

      {/* Add relation + submit */}
      <Stack direction={{ xs: "column", sm: "row" }} spacing={2} alignItems="flex-start">
        <Button
          variant="outlined"
          startIcon={<AddIcon />}
          onClick={addDraft}
          disabled={drafts.length >= MAX_ROWS}
        >
          {t("batch_relations.add_relation")}
        </Button>

        <Button
          variant="contained"
          onClick={handleSubmit}
          disabled={!canSubmit}
          startIcon={submitting ? <CircularProgress size={16} /> : undefined}
        >
          {submitting
            ? t("batch_relations.submitting")
            : t("batch_relations.submit", { count: drafts.length })}
        </Button>
      </Stack>

      {drafts.length >= MAX_ROWS && (
        <Alert severity="warning" sx={{ mt: 2 }}>
          {t("batch_relations.max_rows_warning", { max: MAX_ROWS })}
        </Alert>
      )}
    </Box>
  );
}
