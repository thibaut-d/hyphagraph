import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
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
  Box,
  Alert,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import DeleteIcon from "@mui/icons-material/Delete";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";

import { listEntities } from "../api/entities";
import { getRelation, updateRelation, RoleWrite } from "../api/relations";
import { RelationRead } from "../types/relation";

type EntityOption = {
  id: string;
  label: string;
};

export function EditRelationView() {
  const { id } = useParams<{ id: string }>();
  const { t } = useTranslation();
  const navigate = useNavigate();

  const [relation, setRelation] = useState<RelationRead | null>(null);
  const [entities, setEntities] = useState<EntityOption[]>([]);

  const [kind, setKind] = useState("");
  const [direction, setDirection] = useState("");
  const [confidence, setConfidence] = useState(0.5);
  const [roles, setRoles] = useState<RoleWrite[]>([]);

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load relation and entities
  useEffect(() => {
    if (!id) return;

    setLoading(true);

    Promise.all([getRelation(id), listEntities()])
      .then(([relationRes, entitiesRes]) => {
        setRelation(relationRes);
        setEntities(entitiesRes);

        // Populate form with existing data
        setKind(relationRes.kind || "");
        setDirection(relationRes.direction || "");
        setConfidence(relationRes.confidence || 0.5);
        setRoles(
          relationRes.roles?.map((r) => ({
            entity_id: r.entity_id,
            role_type: r.role_type,
            weight: r.weight,
            coverage: r.coverage,
          })) || []
        );
      })
      .catch((err) => {
        setError(err.message || t("common.error", "An error occurred"));
      })
      .finally(() => setLoading(false));
  }, [id, t]);

  const addRole = () => {
    setRoles([...roles, { entity_id: "", role_type: "" }]);
  };

  const updateRole = (index: number, patch: Partial<RoleWrite>) => {
    setRoles(roles.map((r, i) => (i === index ? { ...r, ...patch } : r)));
  };

  const removeRole = (index: number) => {
    setRoles(roles.filter((_, i) => i !== index));
  };

  const handleSubmit = async () => {
    if (!id || !relation) return;

    setSaving(true);
    setError(null);

    try {
      await updateRelation(id, {
        source_id: relation.source_id, // source_id is immutable
        kind,
        direction,
        confidence,
        roles,
      });

      // Navigate back to source detail page (where relations are displayed)
      navigate(`/sources/${relation.source_id}`);
    } catch (e: any) {
      setError(
        e.message || t("edit_relation.error", "Failed to update relation")
      );
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <Stack alignItems="center" mt={4}>
        <CircularProgress />
      </Stack>
    );
  }

  if (!relation) {
    return (
      <Typography color="error">
        {t("common.not_found", "Not found")}
      </Typography>
    );
  }

  return (
    <Paper sx={{ p: 4, maxWidth: 900, mx: "auto" }}>
      <Stack spacing={3}>
        {/* Header with back button */}
        <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
          <IconButton
            onClick={() => navigate(`/sources/${relation.source_id}`)}
            size="small"
          >
            <ArrowBackIcon />
          </IconButton>
          <Typography variant="h5" sx={{ fontWeight: 600 }}>
            {t("edit_relation.title", "Edit Relation")}
          </Typography>
        </Box>

        <Typography variant="body2" color="text.secondary">
          {t(
            "edit_relation.description",
            "Update the relation details. Note that the source cannot be changed."
          )}
        </Typography>

        {/* Error message */}
        {error && <Alert severity="error">{error}</Alert>}

        {/* Source (read-only) */}
        <Alert severity="info">
          {t("edit_relation.source_immutable", "Source")}: {relation.source_id}
        </Alert>

        {/* Relation fields */}
        <TextField
          label={t("relation.kind", "Relation kind")}
          value={kind}
          onChange={(e) => setKind(e.target.value)}
          disabled={saving}
          fullWidth
        />

        <TextField
          label={t("relation.direction", "Direction")}
          value={direction}
          onChange={(e) => setDirection(e.target.value)}
          disabled={saving}
          fullWidth
        />

        <TextField
          label={t("relation.confidence", "Confidence")}
          type="number"
          inputProps={{ min: 0, max: 1, step: 0.05 }}
          value={confidence}
          onChange={(e) => setConfidence(Number(e.target.value))}
          disabled={saving}
          fullWidth
        />

        <Divider />

        {/* Roles */}
        <Typography variant="h6">{t("relation.roles", "Roles")}</Typography>

        {roles.map((role, index) => (
          <Stack direction="row" spacing={2} key={index}>
            <TextField
              select
              label={t("relation.entity", "Entity")}
              value={role.entity_id}
              onChange={(e) => updateRole(index, { entity_id: e.target.value })}
              disabled={saving}
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
              onChange={(e) => updateRole(index, { role_type: e.target.value })}
              disabled={saving}
              sx={{ flex: 2 }}
            />

            <IconButton onClick={() => removeRole(index)} disabled={saving}>
              <DeleteIcon />
            </IconButton>
          </Stack>
        ))}

        <Button
          startIcon={<AddIcon />}
          variant="outlined"
          onClick={addRole}
          disabled={saving}
        >
          {t("relation.add_role", "Add role")}
        </Button>

        <Box sx={{ display: "flex", gap: 2, pt: 2 }}>
          <Button
            variant="outlined"
            onClick={() => navigate(`/sources/${relation.source_id}`)}
            disabled={saving}
            fullWidth
          >
            {t("common.cancel", "Cancel")}
          </Button>
          <Button
            variant="contained"
            onClick={handleSubmit}
            disabled={saving}
            fullWidth
          >
            {saving
              ? t("edit_relation.saving", "Saving...")
              : t("edit_relation.save", "Save Changes")}
          </Button>
        </Box>
      </Stack>
    </Paper>
  );
}
