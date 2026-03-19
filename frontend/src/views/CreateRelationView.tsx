import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";

import {
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

export function CreateRelationView() {
  const { t } = useTranslation();
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

    if (roles.length === 0) {
      setValidationMessage(t("relation.validation.role_required", "Please add at least one role"), "roles");
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
      await createRelation({
        source_id: sourceId,
        kind,
        direction,
        confidence,
        roles,
      });

      // reset form
      setSourceId("");
      setKind("");
      setDirection("");
      setConfidence(0.5);
      setRoles([]);
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
          helperText={getFieldError("source") ?? " "}
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
          helperText={getFieldError("kind") ?? " "}
        />

        <TextField
          label={t("relation.direction", "Direction")}
          value={direction}
          onChange={(e) => setDirection(e.target.value)}
          fullWidth
        />

        <TextField
          label={t("relation.confidence", "Confidence")}
          type="number"
          inputProps={{ min: 0, max: 1, step: 0.05 }}
          value={confidence}
          onChange={(e) => setConfidence(Number(e.target.value))}
          fullWidth
        />

        <Divider />

        {/* Roles */}
        <Typography variant="h6">
          {t("relation.roles", "Roles")}
        </Typography>

        {hasFieldError("roles") && (
          <Typography color="error" variant="body2">
            {getFieldError("roles")}
          </Typography>
        )}

        {roles.map((role, index) => (
          <Stack direction="row" spacing={2} key={index}>
            <TextField
              select
              label={t("relation.entity", "Entity")}
              value={role.entity_id}
              onChange={(e) => {
                updateRole(index, { entity_id: e.target.value });
                clearError("roles");
              }}
              sx={{ flex: 2 }}
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
            />

            <IconButton onClick={() => removeRole(index)}>
              <DeleteIcon />
            </IconButton>
          </Stack>
        ))}

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
