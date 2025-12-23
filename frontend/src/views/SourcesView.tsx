import { useEffect, useState } from "react";
import { Link as RouterLink } from "react-router-dom";
import { useTranslation } from "react-i18next";

import {
  Paper,
  Typography,
  List,
  ListItem,
  ListItemText,
  Link,
  Stack,
} from "@mui/material";

import { listSources } from "../api/sources";
import { SourceRead } from "../types/source";

export function SourcesView() {
  const { t } = useTranslation();
  const [sources, setSources] = useState<SourceRead[]>([]);

  useEffect(() => {
    listSources().then(setSources);
  }, []);

  return (
    <Paper sx={{ p: 3 }}>
      <Stack spacing={2}>
        <Typography variant="h5">
          {t("sources.title", "Sources")}
        </Typography>

        <List>
          {sources.map((s) => (
            <ListItem key={s.id}>
              <ListItemText
                primary={
                  <Link component={RouterLink} to={`/sources/${s.id}`}>
                    {s.title ?? s.id}
                  </Link>
                }
                secondary={[
                  s.kind,
                  s.year && `(${s.year})`,
                ]
                  .filter(Boolean)
                  .join(" ")}
              />
            </ListItem>
          ))}
        </List>

        {sources.length === 0 && (
          <Typography color="text.secondary">
            {t("sources.no_data", "No sources")}
          </Typography>
        )}
      </Stack>
    </Paper>
  );
}