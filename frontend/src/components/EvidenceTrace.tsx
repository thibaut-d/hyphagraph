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
        No source evidence available.
      </Typography>
    );
  }

  return (
    <TableContainer component={Paper} variant="outlined">
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>
              <strong>Source</strong>
            </TableCell>
            <TableCell>
              <strong>Kind</strong>
            </TableCell>
            <TableCell>
              <strong>Direction</strong>
            </TableCell>
            <TableCell>
              <TableSortLabel
                active={sortField === "confidence"}
                direction={sortField === "confidence" ? sortOrder : "asc"}
                onClick={() => handleSort("confidence")}
              >
                <strong>Confidence</strong>
              </TableSortLabel>
            </TableCell>
            <TableCell>
              <TableSortLabel
                active={sortField === "contribution"}
                direction={sortField === "contribution" ? sortOrder : "asc"}
                onClick={() => handleSort("contribution")}
              >
                <strong>Contribution</strong>
              </TableSortLabel>
            </TableCell>
            <TableCell>
              <TableSortLabel
                active={sortField === "trust"}
                direction={sortField === "trust" ? sortOrder : "asc"}
                onClick={() => handleSort("trust")}
              >
                <strong>Trust</strong>
              </TableSortLabel>
            </TableCell>
            <TableCell>
              <TableSortLabel
                active={sortField === "year"}
                direction={sortField === "year" ? sortOrder : "asc"}
                onClick={() => handleSort("year")}
              >
                <strong>Year</strong>
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
                  to={`/sources/${source.source_id}`}
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
                        Supports
                      </Typography>
                    </>
                  ) : (
                    <>
                      <CancelIcon fontSize="small" color="error" />
                      <Typography variant="body2" color="error.main">
                        Contradicts
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
                    : "N/A"}
                </Typography>
              </TableCell>

              <TableCell>
                <Typography variant="body2">
                  {source.source_year || "N/A"}
                </Typography>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
}
