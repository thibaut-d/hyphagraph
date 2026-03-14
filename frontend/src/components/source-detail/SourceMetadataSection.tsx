import { Link as RouterLink } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  Box,
  Chip,
  IconButton,
  Link,
  Paper,
  Stack,
  Typography,
} from "@mui/material";
import DeleteIcon from "@mui/icons-material/Delete";
import EditIcon from "@mui/icons-material/Edit";
import LinkIcon from "@mui/icons-material/Link";

import type { SourceRead } from "../../types/source";

interface SourceMetadataSectionProps {
  source: SourceRead;
  onDelete: () => void;
}

export function SourceMetadataSection({
  source,
  onDelete,
}: SourceMetadataSectionProps) {
  const { t } = useTranslation();

  return (
    <Paper sx={{ p: 3 }}>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <Stack spacing={1} sx={{ flex: 1 }}>
          <Typography variant="h4">
            {source.title ?? t("sources.untitled", "Untitled source")}
          </Typography>

          <Box sx={{ display: "flex", gap: 1, alignItems: "center", flexWrap: "wrap" }}>
            <Chip label={source.kind} size="small" />
            {source.year && <Chip label={source.year} size="small" variant="outlined" />}
            {source.trust_level != null && (
              <Chip
                label={`Quality: ${Math.round(source.trust_level * 100)}%`}
                size="small"
                color={source.trust_level >= 0.9 ? "success" : source.trust_level >= 0.75 ? "info" : "default"}
              />
            )}
          </Box>

          {source.authors && source.authors.length > 0 && (
            <Typography variant="body2" color="text.secondary">
              {source.authors.join(", ")}
            </Typography>
          )}

          {source.origin && (
            <Typography variant="body2" color="text.secondary">
              {source.origin}
            </Typography>
          )}

          {source.url && (
            <Link href={source.url} target="_blank" rel="noopener noreferrer" sx={{ fontSize: "0.875rem" }}>
              {source.url}
            </Link>
          )}

          {source.source_metadata?.pmid && (
            <Box sx={{ display: "flex", gap: 1, mt: 1 }}>
              <Chip label={`PMID: ${source.source_metadata.pmid}`} size="small" icon={<LinkIcon />} />
              {source.source_metadata?.doi && (
                <Chip label={`DOI: ${source.source_metadata.doi}`} size="small" icon={<LinkIcon />} />
              )}
            </Box>
          )}
        </Stack>

        <Box sx={{ display: "flex", gap: 1 }}>
          <IconButton
            component={RouterLink}
            to={`/sources/${source.id}/edit`}
            color="primary"
            title={t("common.edit", "Edit")}
          >
            <EditIcon />
          </IconButton>
          <IconButton onClick={onDelete} color="error" title={t("common.delete", "Delete")}>
            <DeleteIcon />
          </IconButton>
        </Box>
      </Box>
    </Paper>
  );
}
