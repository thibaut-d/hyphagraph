import { Link as RouterLink } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  Alert,
  Box,
  Chip,
  IconButton,
  Link,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TableSortLabel,
  Tooltip,
  Typography,
} from "@mui/material";
import CancelIcon from "@mui/icons-material/Cancel";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import HelpIcon from "@mui/icons-material/Help";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";

import type { EnrichedRelation } from "../../hooks/useEvidenceRelations";

export type SortField = "kind" | "direction" | "confidence" | "source";
export type SortOrder = "asc" | "desc";

interface EvidenceTableSectionProps {
  entityId: string;
  entityLabel: string;
  language: string;
  roleType?: string;
  relations: EnrichedRelation[];
  sortField: SortField;
  sortOrder: SortOrder;
  onSort: (field: SortField) => void;
  resolveNotes: (
    notes: string | Record<string, string> | null | undefined,
    language: string,
  ) => string | null;
}

function getDirectionChip(direction: string, t: (key: string, fallback: string) => string) {
  switch (direction) {
    case "supports":
      return (
        <Chip
          icon={<CheckCircleIcon />}
          label={t("evidence.supports", "Supports")}
          color="success"
          size="small"
        />
      );
    case "contradicts":
      return (
        <Chip
          icon={<CancelIcon />}
          label={t("evidence.contradicts", "Contradicts")}
          color="error"
          size="small"
        />
      );
    default:
      return (
        <Chip
          icon={<HelpIcon />}
          label={t("evidence.neutral", "Neutral")}
          color="default"
          size="small"
          variant="outlined"
        />
      );
  }
}

function formatRoleTypeLabel(
  roleType: string,
  t: (key: string, fallbackOrOptions?: string | { defaultValue?: string }) => string,
): string {
  const defaultLabel = roleType
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
  return t(`evidence.roles.${roleType}`, { defaultValue: defaultLabel });
}

export function EvidenceTableSection({
  entityId,
  entityLabel,
  language,
  roleType,
  relations,
  sortField,
  sortOrder,
  onSort,
  resolveNotes,
}: EvidenceTableSectionProps) {
  const { t } = useTranslation();

  if (relations.length === 0) {
    return (
      <Alert severity="info">
        <Typography variant="body1" gutterBottom>
          {t("evidence.no_data.title", "No evidence found")}
        </Typography>
        <Typography variant="body2">
          {roleType
            ? t("evidence.no_data.filtered", "No evidence items found for this specific property type.")
            : t(
                "evidence.no_data.all",
                "This entity has no associated relations yet. Add sources and relations to build the evidence base."
              )}
        </Typography>
      </Alert>
    );
  }

  return (
    <TableContainer component={Paper}>
      <Table>
        <TableHead>
          <TableRow>
            <TableCell>
              <TableSortLabel active={sortField === "kind"} direction={sortField === "kind" ? sortOrder : "asc"} onClick={() => onSort("kind")}>
                <strong>{t("evidence.table.claim", "Claim / Relation Kind")}</strong>
              </TableSortLabel>
            </TableCell>
            <TableCell>
              <TableSortLabel active={sortField === "direction"} direction={sortField === "direction" ? sortOrder : "asc"} onClick={() => onSort("direction")}>
                <strong>{t("evidence.table.direction", "Direction")}</strong>
              </TableSortLabel>
            </TableCell>
            <TableCell>
              <TableSortLabel active={sortField === "confidence"} direction={sortField === "confidence" ? sortOrder : "asc"} onClick={() => onSort("confidence")}>
                <strong>{t("evidence.table.confidence", "Confidence")}</strong>
              </TableSortLabel>
            </TableCell>
            <TableCell>
              <strong>{t("evidence.table.roles", "Roles")}</strong>
            </TableCell>
            <TableCell>
              <TableSortLabel active={sortField === "source"} direction={sortField === "source" ? sortOrder : "asc"} onClick={() => onSort("source")}>
                <strong>{t("evidence.table.source", "Source")}</strong>
              </TableSortLabel>
            </TableCell>
            <TableCell>
              <strong>{t("evidence.table.notes", "Notes")}</strong>
            </TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {relations.map((relation) => {
            const resolvedNotes = resolveNotes(relation.notes, language);
            const confidence = relation.confidence ?? 0;

            return (
              <TableRow key={relation.id} hover>
                <TableCell>
                  <Typography variant="body2" fontWeight={500}>
                    {relation.kind || "-"}
                  </Typography>
                </TableCell>

                <TableCell>{getDirectionChip(relation.direction || "", t)}</TableCell>

                <TableCell>
                  <Chip
                    label={`${Math.round(confidence * 100)}%`}
                    size="small"
                    color={confidence > 0.7 ? "success" : confidence > 0.4 ? "warning" : "error"}
                  />
                </TableCell>

                <TableCell>
                  <Stack spacing={0.5}>
                    {relation.roles.map((role, index) => (
                      <Box key={index} sx={{ display: "flex", gap: 0.5, alignItems: "center" }}>
                        <Typography variant="caption" color="text.secondary">
                          {formatRoleTypeLabel(role.role_type, t)}:
                        </Typography>
                        <Link component={RouterLink} to={`/entities/${role.entity_id}`} variant="caption" underline="hover">
                          {role.entity_id === entityId
                            ? entityLabel
                            : role.entity_slug || role.entity_id}
                        </Link>
                      </Box>
                    ))}
                  </Stack>
                </TableCell>

                <TableCell>
                  {relation.source ? (
                    <Box>
                      <Link
                        component={RouterLink}
                        to={`/sources/${relation.source_id}`}
                        variant="body2"
                        sx={{ display: "flex", alignItems: "center", gap: 0.5 }}
                      >
                        {relation.source.title}
                        <OpenInNewIcon fontSize="small" />
                      </Link>
                      {relation.source.authors && relation.source.authors.length > 0 && (
                        <Typography variant="caption" color="text.secondary">
                          {relation.source.authors.slice(0, 2).join(", ")}
                          {relation.source.authors.length > 2 && " et al."}
                          {relation.source.year && ` (${relation.source.year})`}
                        </Typography>
                      )}
                    </Box>
                  ) : (
                    <Link component={RouterLink} to={`/sources/${relation.source_id}`} variant="body2">
                      {t("evidence.table.view_source", "View Source")}
                    </Link>
                  )}
                </TableCell>

                <TableCell>
                  {resolvedNotes ? (
                    <Tooltip title={resolvedNotes} arrow>
                      <IconButton size="small">
                        <HelpIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  ) : (
                    <Typography variant="caption" color="text.secondary">
                      -
                    </Typography>
                  )}
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </TableContainer>
  );
}
