import { Link as RouterLink } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  Box,
  Breadcrumbs,
  Button,
  Chip,
  Divider,
  IconButton,
  Link,
  Paper,
  Stack,
  Tooltip,
  Typography,
} from "@mui/material";
import DeleteIcon from "@mui/icons-material/Delete";
import EditIcon from "@mui/icons-material/Edit";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import FormatListBulletedIcon from "@mui/icons-material/FormatListBulleted";
import LinkIcon from "@mui/icons-material/Link";
import UploadFileIcon from "@mui/icons-material/UploadFile";

import type { SourceRead } from "../../types/source";
import { SourceVerificationSummary } from "./SourceVerificationSummary";

interface SourceMetadataSectionProps {
  source: SourceRead;
  relationsCount: number;
  statementsCount: number;
  onDelete: () => void;
}

export function SourceMetadataSection({
  source,
  relationsCount,
  statementsCount,
  onDelete,
}: SourceMetadataSectionProps) {
  const { t } = useTranslation();

  return (
    <Paper sx={{ p: { xs: 2, sm: 3 } }}>
      <Stack spacing={3}>
        <Breadcrumbs>
          <Link component={RouterLink} to="/sources" underline="hover" color="inherit">
            {t("menu.sources", "Sources")}
          </Link>
          <Typography color="text.primary">
            {source.title ?? t("sources.untitled", "Untitled source")}
          </Typography>
        </Breadcrumbs>

        <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1 }}>
          <Button
            component={RouterLink}
            to="/sources"
            variant="outlined"
            size="small"
            startIcon={<FormatListBulletedIcon />}
          >
            {t("source_metadata.back_to_sources", "Back to sources")}
          </Button>
          <Button
            component="a"
            href="#source-evidence"
            variant="text"
            size="small"
            startIcon={<LinkIcon />}
          >
            {t("source_metadata.jump_to_evidence", "Jump to evidence")}
          </Button>
          <Button
            component="a"
            href="#knowledge-extraction"
            variant="text"
            size="small"
            startIcon={<UploadFileIcon />}
          >
            {t("source_metadata.jump_to_extraction", "Jump to extraction")}
          </Button>
        </Box>

        <Box
          sx={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-start",
            flexDirection: { xs: "column", sm: "row" },
            gap: 2,
          }}
        >
          <Stack spacing={2} sx={{ flex: 1, minWidth: 0, width: "100%" }}>
            <Typography variant="h4" sx={{ overflowWrap: "anywhere" }}>
              {source.title ?? t("sources.untitled", "Untitled source")}
            </Typography>

            {/* Bibliographic identity */}
            <Stack spacing={0.5}>
              <Typography variant="overline" color="text.secondary" lineHeight={1.5}>
                {t("source_metadata.section_bibliographic", "Bibliographic")}
              </Typography>
              <Box sx={{ display: "flex", gap: 1, alignItems: "center", flexWrap: "wrap" }}>
                <Chip label={source.kind} size="small" />
                {source.year && <Chip label={source.year} size="small" variant="outlined" />}
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
            </Stack>

            <Divider />

            {/* Provenance */}
            {(source.url || source.source_metadata?.pmid || source.source_metadata?.doi) && (
              <>
                <Stack spacing={0.5}>
                  <Typography variant="overline" color="text.secondary" lineHeight={1.5}>
                    {t("source_metadata.section_provenance", "Provenance")}
                  </Typography>
                  <Box sx={{ display: "flex", gap: 1, alignItems: "center", flexWrap: "wrap" }}>
                    {source.url && (
                      <Tooltip title={source.url}>
                        <Link
                          href={source.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          sx={{ display: "flex", alignItems: "center", gap: 0.5, fontSize: "0.875rem" }}
                        >
                          {t("source_metadata.full_text_link", "Open source link")}
                          <OpenInNewIcon sx={{ fontSize: "0.875rem" }} />
                        </Link>
                      </Tooltip>
                    )}
                    {source.source_metadata?.pmid && (
                      <Chip
                        label={`PMID: ${source.source_metadata.pmid}`}
                        size="small"
                        component="a"
                        href={`https://pubmed.ncbi.nlm.nih.gov/${source.source_metadata.pmid}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        clickable
                      />
                    )}
                    {source.source_metadata?.doi && (
                      <Chip
                        label={`DOI: ${source.source_metadata.doi}`}
                        size="small"
                        variant="outlined"
                      />
                    )}
                  </Box>
                </Stack>
                <Divider />
              </>
            )}

            {/* Assessment */}
            {source.trust_level != null && (
              <Stack spacing={0.5}>
                <Typography variant="overline" color="text.secondary" lineHeight={1.5}>
                  {t("source_metadata.section_assessment", "Quality assessment")}
                </Typography>
                <Box sx={{ display: "flex", gap: 1, alignItems: "center", flexWrap: "wrap" }}>
                  <Chip
                    label={t("source_metadata.trust_label", "Evidence weight: {{pct}}%", { pct: Math.round(source.trust_level * 100) })}
                    size="small"
                    color={source.trust_level >= 0.9 ? "success" : source.trust_level >= 0.75 ? "info" : "default"}
                    sx={{ maxWidth: "100%" }}
                  />
                  <Typography variant="caption" color="text.secondary">
                    {t("source_metadata.trust_hint", "Algorithmic quality score — affects inference weighting")}
                  </Typography>
                </Box>
              </Stack>
            )}
          </Stack>

          <Box sx={{ display: "flex", gap: 1, alignSelf: { xs: "flex-end", sm: "flex-start" } }}>
            <IconButton
              component={RouterLink}
              to={`/sources/${source.id}/edit`}
              color="primary"
              title={t("common.edit", "Edit")}
              aria-label={t("common.edit", "Edit")}
            >
              <EditIcon />
            </IconButton>
            <IconButton onClick={onDelete} color="error" title={t("common.delete", "Delete")} aria-label={t("common.delete", "Delete")}>
              <DeleteIcon />
            </IconButton>
          </Box>
        </Box>

        <SourceVerificationSummary
          title={source.title ?? t("sources.untitled", "Untitled source")}
          trustLevel={source.trust_level}
          relationsCount={relationsCount}
          statementsCount={statementsCount}
          isConfirmed={source.status === "confirmed"}
        />
      </Stack>
    </Paper>
  );
}
