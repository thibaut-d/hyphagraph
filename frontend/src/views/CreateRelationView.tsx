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

type EntityOption = {
  id: string;
  label: string;
};

type SourceOption = {
  id: string;
  title?: string;
};

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

  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load entities & sources
  useEffect(() => {
    setLoading(true);

    Promise.all([listEntities(), listSources()])
      .then(([entitiesRes, sourcesRes]) => {
        setEntities(entitiesRes.items || []);
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
    setSubmitting(true);
    setError(null);

    try {
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
    } catch (e: any) {
      setError(e.message ?? "Error");
    } finally {
      setSubmitting(false);
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
          onChange={(e) => setSourceId(e.target.value)}
          fullWidth
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
          onChange={(e) => setKind(e.target.value)}
          fullWidth
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

        {roles.map((role, index) => (
          <Stack direction="row" spacing={2} key={index}>
            <TextField
              select
              label={t("relation.entity", "Entity")}
              value={role.entity_id}
              onChange={(e) =>
                updateRole(index, { entity_id: e.target.value })
              }
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
              onChange={(e) =>
                updateRole(index, { role_type: e.target.value })
              }
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

        {error && (
          <Typography color="error">{error}</Typography>
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