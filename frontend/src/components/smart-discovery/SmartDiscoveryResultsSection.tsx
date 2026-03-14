import {
  Alert,
  Box,
  Button,
  Checkbox,
  Chip,
  Divider,
  Link,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";
import DownloadIcon from "@mui/icons-material/Download";
import InfoIcon from "@mui/icons-material/Info";

import type { SmartDiscoveryResult } from "../../api/smart-discovery";

interface ImportSuccess {
  created: number;
  failed: number;
}

interface SmartDiscoveryResultsSectionProps {
  results: SmartDiscoveryResult[];
  queryUsed: string;
  totalFound: number;
  maxResults: number;
  selectedPmids: Set<string>;
  selectedCount: number;
  notImportedCount: number;
  alreadyImportedCount: number;
  importing: boolean;
  importError: string | null;
  importSuccess: ImportSuccess | null;
  onToggleSelect: (pmid: string) => void;
  onSelectAll: () => void;
  onImport: () => void;
  getQualityLabel: (trustLevel: number) => string;
  getQualityColor: (trustLevel: number) => "success" | "info" | "warning" | "error";
}

export function SmartDiscoveryResultsSection({
  results,
  queryUsed,
  totalFound,
  maxResults,
  selectedPmids,
  selectedCount,
  notImportedCount,
  alreadyImportedCount,
  importing,
  importError,
  importSuccess,
  onToggleSelect,
  onSelectAll,
  onImport,
  getQualityLabel,
  getQualityColor,
}: SmartDiscoveryResultsSectionProps) {
  if (results.length === 0) {
    return null;
  }

  return (
    <>
      <Paper sx={{ p: 3 }}>
        <Typography variant="h5" gutterBottom sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          <span>3️⃣</span> Review & Import
        </Typography>

        <Alert severity="success" icon={<InfoIcon />}>
          <strong>Found {totalFound} sources</strong> ({selectedCount} selected for import)
          <br />
          <Typography variant="caption">
            Query: <strong>{queryUsed}</strong> • Top {maxResults} highest-quality sources pre-selected
          </Typography>
        </Alert>

        {alreadyImportedCount > 0 && (
          <Alert severity="info" sx={{ mt: 2 }}>
            {alreadyImportedCount} sources are already in your database (marked with ✓)
          </Alert>
        )}

        {importSuccess && (
          <Alert severity="success" sx={{ mt: 2 }}>
            <strong>✓ Import complete!</strong>
            <br />
            {importSuccess.created} sources created
            {importSuccess.failed > 0 && `, ${importSuccess.failed} failed`}
            <br />
            <Typography variant="caption">Redirecting to sources list...</Typography>
          </Alert>
        )}

        {importError && <Alert severity="error" sx={{ mt: 2 }}>{importError}</Alert>}
      </Paper>

      <Paper sx={{ p: 3 }}>
        <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
          <Typography variant="h6">Discovered Sources ({results.length})</Typography>
          <Box sx={{ display: "flex", gap: 2, alignItems: "center" }}>
            <Button variant="outlined" size="small" onClick={onSelectAll} disabled={importing}>
              {selectedPmids.size === notImportedCount ? "Deselect All" : "Select All"}
            </Button>
            <Chip
              label={`${selectedCount} / ${notImportedCount} selected`}
              color={selectedCount > 0 ? "primary" : "default"}
            />
          </Box>
        </Box>

        <Divider sx={{ mb: 2 }} />

        <TableContainer sx={{ maxHeight: 600 }}>
          <Table stickyHeader size="small">
            <TableHead>
              <TableRow>
                <TableCell padding="checkbox" sx={{ width: 50 }}>
                  <Checkbox
                    checked={selectedPmids.size > 0 && selectedPmids.size === notImportedCount}
                    indeterminate={selectedPmids.size > 0 && selectedPmids.size < notImportedCount}
                    onChange={onSelectAll}
                    disabled={importing}
                  />
                </TableCell>
                <TableCell><strong>Quality</strong></TableCell>
                <TableCell><strong>Title</strong></TableCell>
                <TableCell><strong>Journal</strong></TableCell>
                <TableCell><strong>Year</strong></TableCell>
                <TableCell><strong>Relevance</strong></TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {results.map((result, index) => {
                const isSelected = result.pmid ? selectedPmids.has(result.pmid) : false;
                const isImported = result.already_imported;
                const isInBudget = index < maxResults && !isImported;

                return (
                  <TableRow
                    key={result.pmid || index}
                    hover={!isImported}
                    sx={{
                      bgcolor: isImported ? "action.disabledBackground" : isInBudget ? "success.50" : "inherit",
                      opacity: isImported ? 0.6 : 1,
                    }}
                  >
                    <TableCell padding="checkbox">
                      {!isImported && result.pmid && (
                        <Checkbox
                          checked={isSelected}
                          onChange={() => onToggleSelect(result.pmid!)}
                          disabled={importing}
                        />
                      )}
                      {isImported && <span>✓</span>}
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={`${(result.trust_level * 100).toFixed(0)}%`}
                        size="small"
                        color={getQualityColor(result.trust_level)}
                      />
                      <Typography variant="caption" display="block" color="text.secondary">
                        {getQualityLabel(result.trust_level)}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Link
                        href={result.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        sx={{ fontWeight: isInBudget ? 600 : 400 }}
                      >
                        {result.title}
                      </Link>
                      {result.authors.length > 0 && (
                        <Typography variant="caption" display="block" color="text.secondary">
                          {result.authors.slice(0, 3).join(", ")}
                          {result.authors.length > 3 && " et al."}
                        </Typography>
                      )}
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">{result.journal || "N/A"}</Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">{result.year || "N/A"}</Typography>
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={`${(result.relevance_score * 100).toFixed(0)}%`}
                        size="small"
                        variant="outlined"
                        color={result.relevance_score >= 0.8 ? "success" : "default"}
                      />
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </TableContainer>

        <Box sx={{ mt: 3, display: "flex", gap: 2, justifyContent: "space-between", alignItems: "center" }}>
          <Typography variant="body2" color="text.secondary">
            {selectedCount > maxResults
              ? `⚠️ ${selectedCount} selected (over budget of ${maxResults})`
              : selectedCount > 0
                ? `✓ Ready to import ${selectedCount} sources`
                : "Select sources to import"}
          </Typography>

          <Button
            variant="contained"
            size="large"
            startIcon={importing ? undefined : <DownloadIcon />}
            onClick={onImport}
            disabled={importing || selectedCount === 0}
            sx={{ minWidth: 200, fontWeight: 600 }}
          >
            {importing ? "Importing..." : `Import ${selectedCount} Sources`}
          </Button>
        </Box>
      </Paper>
    </>
  );
}
