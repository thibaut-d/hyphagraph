import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link as RouterLink } from "react-router-dom";

import {
  Paper,
  TextField,
  Typography,
  List,
  ListItem,
  ListItemText,
  Link,
  Stack,
} from "@mui/material";

import { listEntities } from "../api/entities";
import { EntityRead } from "../types/entity";
import { resolveLabel } from "../utils/i18nLabel";

export function SearchView() {
  const { t, i18n } = useTranslation();

  const [entities, setEntities] = useState<EntityRead[]>([]);
  const [query, setQuery] = useState("");

  useEffect(() => {
    listEntities().then(setEntities);
  }, []);

  const results = useMemo(() => {
    const q = query.toLowerCase().trim();
    if (!q) return entities;

    return entities.filter((e) => {
      const label = resolveLabel(
        e.label,
        e.label_i18n,
        i18n.language,
      ).toLowerCase();

      return label.includes(q);
    });
  }, [entities, query, i18n.language]);

  return (
    <Paper sx={{ p: 3 }}>
      <Stack spacing={2}>
        <Typography variant="h5">
          {t("search.title", "Search")}
        </Typography>

        <TextField
          label={t("search.placeholder", "Search entities")}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          fullWidth
        />

        <List>
          {results.map((e) => {
            const label = resolveLabel(
              e.label,
              e.label_i18n,
              i18n.language,
            );

            return (
              <ListItem key={e.id}>
                <ListItemText
                  primary={
                    <Link component={RouterLink} to={`/entities/${e.id}`}>
                      {label}
                    </Link>
                  }
                  secondary={e.kind}
                />
              </ListItem>
            );
          })}
        </List>

        {results.length === 0 && (
          <Typography color="text.secondary">
            {t("search.no_results", "No results")}
          </Typography>
        )}
      </Stack>
    </Paper>
  );
}