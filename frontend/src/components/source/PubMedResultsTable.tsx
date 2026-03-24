import {
  Box,
  Checkbox,
  Chip,
  Link,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";
import DownloadIcon from "@mui/icons-material/Download";
import { CircularProgress, Button } from "@mui/material";
import type { PubMedSearchResult } from "../../types/pubmed";

interface PubMedResultsTableProps {
  results: PubMedSearchResult[];
  query: string;
  totalResults: number;
  selectedPmids: Set<string>;
  importing: boolean;
  importError: string | null;
  onToggleSelect: (pmid: string) => void;
  onSelectAll: () => void;
  onImport: () => void;
  onCancelImport: () => void;
  onClearImportError: () => void;
}

export function PubMedResultsTable({
  results,
  query,
  totalResults,
  selectedPmids,
  importing,
  importError,
  onToggleSelect,
  onSelectAll,
  onImport,
  onCancelImport,
  onClearImportError,
}: PubMedResultsTableProps) {
  return (
    <Box>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
        <Box>
          <Typography variant="h6">Search Results</Typography>
          <Typography variant="body2" color="text.secondary">
            Query: "{query}" • Found {totalResults.toLocaleString()} total results, showing{" "}
            {results.length}
          </Typography>
        </Box>
        <Box sx={{ display: "flex", gap: 2, alignItems: "center" }}>
          <Chip
            label={`${selectedPmids.size} selected`}
            color={selectedPmids.size > 0 ? "primary" : "default"}
          />
          <Button
            variant="contained"
            startIcon={importing ? <CircularProgress size={16} /> : <DownloadIcon />}
            onClick={onImport}
            disabled={importing || selectedPmids.size === 0}
          >
            {importing ? "Importing..." : `Import ${selectedPmids.size} Articles`}
          </Button>
          {importing && (
            <Button variant="outlined" color="error" onClick={onCancelImport}>
              Cancel
            </Button>
          )}
        </Box>
      </Box>

      {importError && (
        <Box sx={{ mb: 2 }}>
          <Typography color="error" variant="body2">{importError}</Typography>
          <Button size="small" onClick={onClearImportError}>Dismiss</Button>
        </Box>
      )}

      <TableContainer>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell padding="checkbox">
                <Checkbox
                  checked={selectedPmids.size === results.length && results.length > 0}
                  indeterminate={selectedPmids.size > 0 && selectedPmids.size < results.length}
                  onChange={onSelectAll}
                />
              </TableCell>
              <TableCell>Article</TableCell>
              <TableCell>Authors</TableCell>
              <TableCell>Journal</TableCell>
              <TableCell>Year</TableCell>
              <TableCell>PMID</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {results.map((result) => (
              <TableRow
                key={result.pmid}
                hover
                onClick={() => onToggleSelect(result.pmid)}
                sx={{ cursor: "pointer" }}
              >
                <TableCell padding="checkbox">
                  <Checkbox checked={selectedPmids.has(result.pmid)} />
                </TableCell>
                <TableCell>
                  <Typography variant="body2" fontWeight="medium">
                    {result.title}
                  </Typography>
                  {result.doi && (
                    <Typography variant="caption" color="text.secondary">
                      DOI: {result.doi}
                    </Typography>
                  )}
                </TableCell>
                <TableCell>
                  <Typography variant="body2">
                    {result.authors.slice(0, 3).join(", ")}
                    {result.authors.length > 3 && " et al."}
                  </Typography>
                </TableCell>
                <TableCell>
                  <Typography variant="body2">{result.journal || "—"}</Typography>
                </TableCell>
                <TableCell>
                  <Typography variant="body2">{result.year || "—"}</Typography>
                </TableCell>
                <TableCell>
                  <Link
                    href={result.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={(e) => e.stopPropagation()}
                  >
                    {result.pmid}
                  </Link>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
}
