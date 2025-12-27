import { useEffect, useState } from "react";
import { listEntities } from "../api/entities";
import { EntityRead } from "../types/entity";
import { Link as RouterLink } from "react-router-dom";
import { useTranslation } from "react-i18next";

import {
  Typography,
  List,
  ListItem,
  ListItemText,
  Link,
  Paper,
  Box,
  Button,
  Stack,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";

export function EntitiesView() {
  const { t } = useTranslation();
  const [entities, setEntities] = useState<EntityRead[]>([]);

  useEffect(() => {
    listEntities().then(setEntities);
  }, []);

  return (
    <Stack spacing={2}>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <Typography variant="h4">
          {t("entities.title", "Entities")}
        </Typography>
        <Button
          component={RouterLink}
          to="/entities/new"
          variant="contained"
          startIcon={<AddIcon />}
        >
          {t("entities.create", "Create Entity")}
        </Button>
      </Box>

      <Paper sx={{ p: 2 }}>
        <List>
          {entities.map((e) => (
            <ListItem key={e.id}>
              <ListItemText
                primary={
                  <Link component={RouterLink} to={`/entities/${e.id}`}>
                    {e.label}
                  </Link>
                }
                secondary={e.kind}
              />
            </ListItem>
          ))}
        </List>
      </Paper>
    </Stack>
  );
}