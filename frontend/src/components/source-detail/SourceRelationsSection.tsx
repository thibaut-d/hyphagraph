import { Link as RouterLink } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  Alert,
  Box,
  Chip,
  Divider,
  IconButton,
  List,
  ListItem,
  ListItemText,
  Link,
  Paper,
  Typography,
} from "@mui/material";
import DeleteIcon from "@mui/icons-material/Delete";
import EditIcon from "@mui/icons-material/Edit";

import type { RelationRead } from "../../types/relation";

interface SourceRelationsSectionProps {
  relations: RelationRead[];
  relationsError: string | null;
  onDeleteRelation: (relation: RelationRead) => void;
}

export function SourceRelationsSection({
  relations,
  relationsError,
  onDeleteRelation,
}: SourceRelationsSectionProps) {
  const { t } = useTranslation();
  const hasRelations = relations.length > 0;

  return (
    <Paper sx={{ p: 3 }}>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
        <Typography variant="h5">{t("sources.relations", "Relations")}</Typography>
        {hasRelations && (
          <Chip label={`${relations.length} ${t("sources.relations_count", "relations")}`} color="primary" size="small" />
        )}
      </Box>

      <Divider sx={{ mb: 2 }} />

      {relationsError && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          {relationsError}
        </Alert>
      )}

      {relations.length === 0 && !relationsError ? (
        <Alert severity="info">
          {t("sources.no_relations", "No relations yet. Extract knowledge from this source to create relations.")}
        </Alert>
      ) : relations.length > 0 ? (
        <List>
          {relations.map((relation) => (
            <ListItem
              key={relation.id}
              sx={{
                borderLeft: 3,
                borderColor: relation.direction === "supports" ? "success.main" : relation.direction === "contradicts" ? "error.main" : "grey.400",
                mb: 1,
                bgcolor: "background.default",
              }}
              secondaryAction={
                <Box sx={{ display: "flex", gap: 0.5 }}>
                  <IconButton
                    component={RouterLink}
                    to={`/relations/${relation.id}/edit`}
                    edge="end"
                    size="small"
                    title={t("common.edit", "Edit")}
                  >
                    <EditIcon fontSize="small" />
                  </IconButton>
                  <IconButton
                    edge="end"
                    size="small"
                    color="error"
                    onClick={() => onDeleteRelation(relation)}
                    title={t("common.delete", "Delete")}
                  >
                    <DeleteIcon fontSize="small" />
                  </IconButton>
                </Box>
              }
            >
              <ListItemText
                primary={
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                    <Typography variant="body1" sx={{ fontWeight: 500 }}>
                      {relation.kind}
                    </Typography>
                    <Chip
                      label={relation.direction}
                      size="small"
                      color={relation.direction === "supports" ? "success" : relation.direction === "contradicts" ? "error" : "default"}
                      sx={{ fontSize: "0.7rem" }}
                    />
                  </Box>
                }
                secondary={
                  <>
                    {relation.roles.map((role, index) => (
                      <Link key={index} component={RouterLink} to={`/entities/${role.entity_id}`} sx={{ mr: 1 }}>
                        {role.role_type}
                      </Link>
                    ))}
                  </>
                }
              />
            </ListItem>
          ))}
        </List>
      ) : null}
    </Paper>
  );
}
