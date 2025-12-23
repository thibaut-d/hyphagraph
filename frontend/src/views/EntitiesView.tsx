import { useEffect, useState } from "react";
import { listEntities } from "../api/entities";
import { EntityRead } from "../types/entity";
import { Link as RouterLink } from "react-router-dom";

import {
  Typography,
  List,
  ListItem,
  ListItemText,
  Link,
  Paper,
} from "@mui/material";

export function EntitiesView() {
  const [entities, setEntities] = useState<EntityRead[]>([]);

  useEffect(() => {
    listEntities().then(setEntities);
  }, []);

  return (
    <Paper sx={{ p: 2 }}>
      <Typography variant="h5" gutterBottom>
        Entities
      </Typography>

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
  );
}