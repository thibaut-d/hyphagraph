import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";

import {
  Alert,
  Box,
  Chip,
  Typography,
  Paper,
  Stack,
  TextField,
  Button,
  IconButton,
  MenuItem,
  Divider,
  CircularProgress,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import DeleteIcon from "@mui/icons-material/Delete";

import { listEntities } from "../api/entities";
import { listSources } from "../api/sources";
import { createRelation, RoleWrite } from "../api/relations";
import { useAsyncAction } from "../hooks/useAsyncAction";
import { useValidationMessage } from "../hooks/useValidationMessage";

type EntityOption = {
  id: string;
  label: string;
};

type SourceOption = {
  id: string;
  title?: string;
};

type ValidationField = "source" | "kind" | "roles";

const RELATION_KIND_PRESETS = [
  "treats",
  "causes",
  "associated_with",
  "improves",
  "inhibits",
];

const ROLE_TYPE_PRESETS = ["subject", "object", "drug", "condition", "population", "outcome"];
const DIRECTION_PRESETS = ["supports", "contradicts", "uncertain"];

export function CreateRelationView() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const [entities, setEntities] = useState<EntityOption[]>([]);
  const [sources, setSources] = useState<SourceOption[]>([]);

  const [sourceId, setSourceId] = useState("");
  const [kind, setKind] = useState("");
  const [direction, setDirection] = useState("");
  const [confidence, setConfidence] = useState(0.5);
  const [roles, setRoles] = useState<RoleWrite[]>([]);
  const {
    setValidationMessage,
    clearValidationMessage: clearError,
    getFieldError,
    hasFieldError,
  } = useValidationMessage<ValidationField>();
  const [submitError, setSubmitError] = useState<string | null>(null);

  const [loading, setLoading] = useState(true);
  const { isRunning: submitting, run } = useAsyncAction(setSubmitError);
  // Load entities & sources
  useEffect(() => {
    setLoading(true);

    Promise.all([listEntities(), listSources()])
      .then(([entitiesRes, sourcesRes]) => {
        const entityItems = Array.isArray(entitiesRes)
          ? entitiesRes
          : (entitiesRes.items ?? []);

        setEntities(
          entityItems.map((entity) => ({
            id: entity.id,
            label: entity.slug,
          }))
        );
        setSources(sourcesRes.items || []);
      })
      .finally(() => setLoading(false));
  }, []);

  // Pre-fill role from query param
  useEffect(() => {
    const entityId = searchParams.get("entity_id");
    if (entityId) {
      setRoles([{ entity_id: entityId, role_type: "" }]);
    }
  }, [searchParams]);

  const addRole = () => {
    setRoles([...roles, { entity_id: "", role_type: "" }]);
  };

  const updateRole = (index: number, patch: Partial<RoleWrite>) => {
    setRoles(
      roles.map((r, i) => (i === index ? { ...r, ...patch } : r)),
    );
  };

  const removeRole = (index: number) => {
    setRoles(roles.filter((_, i) => i !== index));
  };

  const submit = async () => {
    clearError();
    setSubmitError(null);

    if (!sourceId) {
      setValidationMessage(t("relation.validation.source_required", "Please select a source"), "source");
      return;
    }

    if (!kind.trim()) {
      setValidationMessage(t("relation.validation.kind_required", "Please enter a relation kind"), "kind");
      return;
    }

    if (roles.length < 2) {
      setValidationMessage(t("relation.validation.roles_required", "Please add at least two roles (a relation requires at least two participating entities)"), "roles");
      return;
    }

    if (roles.some((role) => !role.entity_id.trim() || !role.role_type.trim())) {
      setValidationMessage(
        t(
          "relation.validation.role_fields_required",
          "Each role must include both an entity and a role type"
        ),
        "roles"
      );
      return;
    }

    const result = await run(async () => {
      const createdRelation = await createRelation({
        source_id: sourceId,
        kind,
        direction,
        confidence,
        roles,
      });

      navigate(`/relations/${createdRelation.id}`);
    }, t("common.error", "Something went wrong"));

    if (!result.ok) {
      return;
    }
  };

  if (loading) {
    return (
      <Stack alignItems="center" mt={4}>
        <CircularProgress />
      </Stack>
    );
  }

  return (
    <Paper sx={{ p: 3 }}>
      <Stack spacing={3}>
        <Typography variant="h5">
          {t("relation.create", "Create relation")}
        </Typography>

        <Alert severity="info">
          {t(
            "relation.guidance",
            "Describe one source-backed statement. Pick the source, choose the relation pattern that best matches the evidence, then assign each participating entity a clear role."
          )}
        </Alert>

        {/* Source */}
        <TextField
          select
          label={t("relation.source", "Source")}
          value={sourceId}
          onChange={(e) => {
            setSourceId(e.target.value);
            clearError("source");
          }}
          fullWidth
          error={hasFieldError("source")}
          helperText={
            getFieldError("source") ??
            t(
              "relation.source_help",
              "Select the publication or document that directly states this relation."
            )
          }
        >
          {sources.map((s) => (
            <MenuItem key={s.id} value={s.id}>
              {s.title ?? s.id}
            </MenuItem>
          ))}
        </TextField>

        {/* Relation fields */}
        <TextField
          label={t("relation.kind", "Relation kind")}
          value={kind}
          onChange={(e) => {
            setKind(e.target.value);
            clearError("kind");
          }}
          fullWidth
          error={hasFieldError("kind")}
          helperText={
            getFieldError("kind") ??
            t(
              "relation.kind_help",
              "Use a short verb phrase that reflects the source wording. You can start from a preset and refine it."
            )
          }
        />
        <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1 }}>
          {RELATION_KIND_PRESETS.map((preset) => (
            <Chip
              key={preset}
              label={preset}
              variant={kind === preset ? "filled" : "outlined"}
              color={kind === preset ? "primary" : "default"}
              onClick={() => {
                setKind(preset);
                clearError("kind");
              }}
            />
          ))}
        </Box>

        <TextField
          label={t("relation.direction", "Direction")}
          value={direction}
          onChange={(e) => setDirection(e.target.value)}
          fullWidth
          helperText={t(
            "relation.direction_help",
            "Mark whether the source supports, contradicts, or leaves the relation uncertain."
          )}
        />
        <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1 }}>
          {DIRECTION_PRESETS.map((preset) => (
            <Chip
              key={preset}
              label={preset}
              variant={direction === preset ? "filled" : "outlined"}
              color={direction === preset ? "primary" : "default"}
              onClick={() => setDirection(preset)}
            />
          ))}
        </Box>

        <TextField
          label={t("relation.confidence", "Confidence")}
          type="number"
          inputProps={{ min: 0, max: 1, step: 0.05 }}
          value={confidence}
          onChange={(e) => setConfidence(Number(e.target.value))}
          fullWidth
          helperText={t(
            "relation.confidence_help",
            "Capture how strongly the source presents this statement, from 0 to 1."
          )}
        />

        <Divider />

        {/* Roles */}
        <Typography variant="h6">
          {t("relation.roles", "Roles")}
        </Typography>

        <Typography variant="body2" color="text.secondary">
          {t(
            "relation.roles_help",
            "Add at least two participants. Use role labels like subject/object or domain-specific roles such as drug and condition so the evidence remains readable."
          )}
        </Typography>

        {hasFieldError("roles") && (
          <Typography color="error" variant="body2">
            {getFieldError("roles")}
          </Typography>
        )}

        {roles.map((role, index) => (
          <Stack
            key={index}
            direction={{ xs: "column", sm: "row" }}
            spacing={2}
            alignItems={{ xs: "stretch", sm: "flex-start" }}
          >
            <TextField
              select
              label={t("relation.entity", "Entity")}
              value={role.entity_id}
              onChange={(e) => {
                updateRole(index, { entity_id: e.target.value });
                clearError("roles");
              }}
              sx={{ flex: 2 }}
              helperText={t("relation.role_entity_help", "Choose the entity mentioned in the source")}
            >
              {entities.map((e) => (
                <MenuItem key={e.id} value={e.id}>
                  {e.label}
                </MenuItem>
              ))}
            </TextField>

            <TextField
              label={t("relation.role_type", "Role")}
              value={role.role_type}
              onChange={(e) => {
                updateRole(index, { role_type: e.target.value });
                clearError("roles");
              }}
              sx={{ flex: 2 }}
              helperText={t("relation.role_type_help", "Describe what this entity does in the statement")}
            />

            <Box sx={{ display: "flex", justifyContent: { xs: "flex-end", sm: "center" }, alignItems: "flex-start", pt: { sm: 1 } }}>
              <IconButton onClick={() => removeRole(index)} aria-label="Remove participant">
                <DeleteIcon />
              </IconButton>
            </Box>
          </Stack>
        ))}

        {roles.length > 0 && (
          <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1 }}>
            {ROLE_TYPE_PRESETS.map((preset) => (
              <Chip
                key={preset}
                label={preset}
                variant="outlined"
                onClick={() => {
                  const nextIndex = roles.findIndex((role) => !role.role_type.trim());
                  if (nextIndex >= 0) {
                    updateRole(nextIndex, { role_type: preset });
                  }
                }}
              />
            ))}
          </Box>
        )}

        <Button
          startIcon={<AddIcon />}
          variant="outlined"
          onClick={addRole}
        >
          {t("relation.add_role", "Add role")}
        </Button>

        {submitError && (
          <Typography color="error">{submitError}</Typography>
        )}

        <Button
          variant="contained"
          onClick={submit}
          disabled={submitting}
        >
          {t("relation.submit", "Create")}
        </Button>
      </Stack>
    </Paper>
  );
}
