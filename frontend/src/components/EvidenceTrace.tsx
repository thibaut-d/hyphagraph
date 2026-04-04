/**
 * Evidence Trace Component
 *
 * Visualizes the source chain for a computed inference,
 * showing which sources contributed and how.
 *
 * Provides clickable links to source detail views, enabling
 * the ≤2 click traceability requirement.
 */

import { useState } from "react";
import { Link as RouterLink } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Link,
  Chip,
  Box,
  TableSortLabel,
  Typography,
} from "@mui/material";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import CancelIcon from "@mui/icons-material/Cancel";

import { SourceContribution } from "../api/explanations";


type SortField = "contribution" | "confidence" | "year" | "trust";
type SortOrder = "asc" | "desc";


interface EvidenceTraceProps {
  sourceChain: SourceContribution[];
}


export function EvidenceTrace({ sourceChain }: EvidenceTraceProps) {
  const { t } = useTranslation();
  const [sortField, setSortField] = useState<SortField>("contribution");
  const [sortOrder, setSortOrder] = useState<SortOrder>("desc");

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      // Toggle order
      setSortOrder(sortOrder === "asc" ? "desc" : "asc");
    } else {
      // New field, default to descending
      setSortField(field);
      setSortOrder("desc");
    }
  };

  const sortedChain = [...sourceChain].sort((a, b) => {
    let aVal: number;
    let bVal: number;

    switch (sortField) {
      case "contribution":
        aVal = a.contribution_percentage;
        bVal = b.contribution_percentage;
        break;
      case "confidence":
        aVal = a.relation_confidence;
        bVal = b.relation_confidence;
        break;
      case "year":
        aVal = a.source_year || 0;
        bVal = b.source_year || 0;
        break;
      case "trust":
        aVal = a.source_trust || 0;
        bVal = b.source_trust || 0;
        break;
    }

    return sortOrder === "asc" ? aVal - bVal : bVal - aVal;
  });

  if (sourceChain.length === 0) {
    return (
      <Typography color="text.secondary">
        {t("evidence_trace.empty", "No source evidence available.")}
      </Typography>
    );
  }

  const buildEvidenceTarget = (sourceId: string, relationId: string) =>
    `/sources/${sourceId}?relation=${encodeURIComponent(relationId)}#relation-${relationId}`;

  return (
    <TableContainer component={Paper} variant="outlined">
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>
              <strong>{t("evidence_trace.columns.source", "Source")}</strong>
            </TableCell>
            <TableCell sx={{ maxWidth: 280 }}>
              <strong>{t("evidence_trace.columns.statement", "Supporting statement")}</strong>
            </TableCell>
            <TableCell>
              <strong>{t("evidence_trace.columns.kind", "Kind")}</strong>
            </TableCell>
            <TableCell>
              <strong>{t("evidence_trace.columns.direction", "Direction")}</strong>
            </TableCell>
            <TableCell>
              <TableSortLabel
                active={sortField === "confidence"}
                direction={sortField === "confidence" ? sortOrder : "asc"}
                onClick={() => handleSort("confidence")}
              >
                <strong>{t("evidence_trace.columns.confidence", "Confidence")}</strong>
              </TableSortLabel>
            </TableCell>
            <TableCell>
              <TableSortLabel
                active={sortField === "contribution"}
                direction={sortField === "contribution" ? sortOrder : "asc"}
                onClick={() => handleSort("contribution")}
              >
                <strong>{t("evidence_trace.columns.contribution", "Contribution")}</strong>
              </TableSortLabel>
            </TableCell>
            <TableCell>
              <TableSortLabel
                active={sortField === "trust"}
                direction={sortField === "trust" ? sortOrder : "asc"}
                onClick={() => handleSort("trust")}
              >
                <strong>{t("evidence_trace.columns.trust", "Trust")}</strong>
              </TableSortLabel>
            </TableCell>
            <TableCell>
              <TableSortLabel
                active={sortField === "year"}
                direction={sortField === "year" ? sortOrder : "asc"}
                onClick={() => handleSort("year")}
              >
                <strong>{t("evidence_trace.columns.year", "Year")}</strong>
              </TableSortLabel>
            </TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {sortedChain.map((source) => (
            <TableRow key={source.relation_id} hover>
              <TableCell>
                <Link
                  component={RouterLink}
                  to={buildEvidenceTarget(source.source_id, source.relation_id)}
                  underline="hover"
                  sx={{ fontWeight: 500 }}
                >
                  {source.source_title}
                </Link>
                {source.source_authors && source.source_authors.length > 0 && (
                  <Typography variant="caption" display="block" color="text.secondary">
                    {source.source_authors.slice(0, 3).join(", ")}
                    {source.source_authors.length > 3 && " et al."}
                  </Typography>
                )}
              </TableCell>

              <TableCell sx={{ maxWidth: 280 }}>
                {source.relation_notes && (source.relation_notes["en"] || Object.values(source.relation_notes)[0]) ? (
                  <Typography variant="body2" sx={{ fontStyle: "italic", color: "text.secondary" }}>
                    "{source.relation_notes["en"] || Object.values(source.relation_notes)[0]}"
                  </Typography>
                ) : (
                  <Typography variant="body2" color="text.disabled">
                    {t("evidence_trace.no_statement", "—")}
                  </Typography>
                )}
              </TableCell>

              <TableCell>
                <Chip
                  label={source.relation_kind}
                  size="small"
                  variant="outlined"
                />
              </TableCell>

              <TableCell>
                <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
                  {source.relation_direction === "supports" ? (
                    <>
                      <CheckCircleIcon fontSize="small" color="success" />
                      <Typography variant="body2" color="success.main">
                        {t("evidence_trace.direction.supports", "Supports")}
                      </Typography>
                    </>
                  ) : (
                    <>
                      <CancelIcon fontSize="small" color="error" />
                      <Typography variant="body2" color="error.main">
                        {t("evidence_trace.direction.contradicts", "Contradicts")}
                      </Typography>
                    </>
                  )}
                </Box>
              </TableCell>

              <TableCell>
                <Typography variant="body2">
                  {(source.relation_confidence * 100).toFixed(0)}%
                </Typography>
              </TableCell>

              <TableCell>
                <Typography variant="body2" fontWeight={600}>
                  {source.contribution_percentage.toFixed(1)}%
                </Typography>
              </TableCell>

              <TableCell>
                <Typography variant="body2">
                  {source.source_trust !== null && source.source_trust !== undefined
                    ? source.source_trust.toFixed(2)
                    : t("common.not_available", "N/A")}
                </Typography>
              </TableCell>

              <TableCell>
                <Typography variant="body2">
                  {source.source_year || t("common.not_available", "N/A")}
                </Typography>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
}
