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
  Box,
  Button,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";

import { listSources } from "../api/sources";
import { SourceRead } from "../types/source";

export function SourcesView() {
  const { t } = useTranslation();
  const [sources, setSources] = useState<SourceRead[]>([]);

  useEffect(() => {
    listSources().then(setSources);
  }, []);

  return (
    <Stack spacing={2}>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <Typography variant="h4">
          {t("sources.title", "Sources")}
        </Typography>
        <Button
          component={RouterLink}
          to="/sources/new"
          variant="contained"
          startIcon={<AddIcon />}
        >
          {t("sources.create", "Create Source")}
        </Button>
      </Box>

      <Paper sx={{ p: 3 }}>
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
      </Paper>
    </Stack>
  );
}