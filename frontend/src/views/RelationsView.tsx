import { useCallback, useEffect, useState } from "react";
import { Link as RouterLink } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  List,
  ListItem,
  ListItemText,
  Link,
  Paper,
  Stack,
  Typography,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";

import { ExportMenu } from "../components/ExportMenu";
import { listRelations } from "../api/relations";
import type { RelationRead } from "../types/relation";

const PAGE_SIZE = 50;

export default function RelationsView() {
  const { t } = useTranslation();
  const [relations, setRelations] = useState<RelationRead[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadRelations = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await listRelations(PAGE_SIZE, 0);
      setRelations(response.items);
      setTotal(response.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("common.error", "An error occurred"));
    } finally {
      setIsLoading(false);
    }
  }, [t]);

  useEffect(() => {
    void loadRelations();
  }, [loadRelations]);

  return (
    <Stack spacing={2}>
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: { xs: "flex-start", sm: "center" },
          flexDirection: { xs: "column", sm: "row" },
          gap: 2,
        }}
      >
        <Box>
          <Typography variant="h4">{t("relations.title", "Relations")}</Typography>
          <Typography variant="body2" color="text.secondary">
            {t(
              "relations.description",
              "Browse current document-grounded relations across sources."
            )}
          </Typography>
        </Box>
        <Stack direction="row" spacing={1} flexWrap="wrap">
          <ExportMenu exportType="relations" buttonText={t("export.relations", "Export Relations")} size="small" />
          <Button
            component={RouterLink}
            to="/relations/batch"
            variant="contained"
            startIcon={<AddIcon />}
            size="small"
          >
            {t("relations.batch_create", "Batch Create")}
          </Button>
        </Stack>
      </Box>

      <Paper sx={{ p: { xs: 1, sm: 2 } }}>
        {error && <Alert severity="error">{error}</Alert>}

        {isLoading ? (
          <Box sx={{ display: "flex", justifyContent: "center", p: 3 }}>
            <CircularProgress />
          </Box>
        ) : relations.length === 0 ? (
          <Typography color="text.secondary">
            {t("relations.no_data", "No relations")}
          </Typography>
        ) : (
          <>
            <List>
              {relations.map((relation) => (
                <ListItem key={relation.id}>
                  <ListItemText
                    primary={
                      <Box sx={{ display: "flex", alignItems: "center", gap: 1, flexWrap: "wrap" }}>
                        <Link component={RouterLink} to={`/relations/${relation.id}`}>
                          {relation.kind || t("relation.untitled", "Untitled relation")}
                        </Link>
                        {relation.direction && (
                          <Chip label={relation.direction} size="small" variant="outlined" />
                        )}
                        {relation.confidence != null && (
                          <Chip
                            label={t("relation.confidence_chip", "Confidence {{value}}%", {
                              value: Math.round(relation.confidence * 100),
                            })}
                            size="small"
                            variant="outlined"
                          />
                        )}
                      </Box>
                    }
                    secondary={[
                      relation.source_title || relation.source_id,
                      relation.source_year ? `(${relation.source_year})` : null,
                    ]
                      .filter(Boolean)
                      .join(" ")}
                  />
                </ListItem>
              ))}
            </List>
            <Typography variant="caption" color="text.secondary">
              {t("relations.count", "Showing {{count}} of {{total}} relation(s)", {
                count: relations.length,
                total,
              })}
            </Typography>
          </>
        )}
      </Paper>
    </Stack>
  );
}
