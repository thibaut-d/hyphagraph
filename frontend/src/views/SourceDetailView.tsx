import { useEffect, useState } from "react";
import { useParams, Link as RouterLink } from "react-router-dom";
import { useTranslation } from "react-i18next";

import {
  Paper,
  Typography,
  Stack,
  Divider,
  List,
  ListItem,
  ListItemText,
  Link,
} from "@mui/material";

import { getSource } from "../api/sources";
import { listRelationsBySource } from "../api/relations";
import { SourceRead } from "../types/source";
import { RelationRead } from "../types/relation";

export function SourceDetailView() {
  const { id } = useParams<{ id: string }>();
  const { t } = useTranslation();

  const [source, setSource] = useState<SourceRead | null>(null);
  const [relations, setRelations] = useState<RelationRead[]>([]);

  useEffect(() => {
    if (!id) return;

    getSource(id).then(setSource);
    listRelationsBySource(id).then(setRelations);
  }, [id]);

  if (!source) {
    return (
      <Typography color="error">
        {t("common.not_found", "Not found")}
      </Typography>
    );
  }

  return (
    <Stack spacing={3}>
      <Paper sx={{ p: 3 }}>
        <Typography variant="h4">
          {source.title ?? t("sources.untitled", "Untitled source")}
        </Typography>

        <Typography variant="subtitle2" color="text.secondary">
          {source.kind}
          {source.year && ` • ${source.year}`}
        </Typography>

        {source.trust_level !== undefined && (
          <Typography variant="body2">
            {t("sources.trust", "Trust level")}:{" "}
            {Math.round(source.trust_level * 100)}%
          </Typography>
        )}
      </Paper>

      <Paper sx={{ p: 3 }}>
        <Typography variant="h5" gutterBottom>
          {t("sources.relations", "Relations")}
        </Typography>

        <Divider />

        <List>
          {relations.map((r) => (
            <ListItem key={r.id}>
              <ListItemText
                primary={`${r.kind} (${r.direction})`}
                secondary={
                  <Link
                    component={RouterLink}
                    to={`/entities/${r.roles[0]?.entity_id}`}
                  >
                    {t("sources.view_entity", "View entity")}
                  </Link>
                }
              />
            </ListItem>
          ))}
        </List>

        {relations.length === 0 && (
          <Typography color="text.secondary">
            {t("sources.no_relations", "No relations")}
          </Typography>
        )}
      </Paper>
    </Stack>
  );
}