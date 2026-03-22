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
import CheckIcon from "@mui/icons-material/Check";
import DownloadIcon from "@mui/icons-material/Download";
import InfoIcon from "@mui/icons-material/Info";
import { useTranslation } from "react-i18next";

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
  const { t } = useTranslation();
  // The selectable budget is the smaller of the non-imported count and maxResults,
  // because handleSelectAll caps selection to maxResults items.
  const budgetedCount = Math.min(notImportedCount, maxResults);

  if (results.length === 0) {
    return null;
  }

  return (
    <>
      <Paper sx={{ p: 3 }}>
        <Typography variant="h5" gutterBottom sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          <span>3️⃣</span> {t("smart_discovery.step_review")}
        </Typography>

        <Alert severity="success" icon={<InfoIcon />}>
          <strong>{t("smart_discovery.found_sources", { total: totalFound })}</strong> ({t("smart_discovery.selected_for_import", { count: selectedCount })})
          <br />
          <Typography variant="caption">
            {t("smart_discovery.query_label")} <strong>{queryUsed}</strong> • {t("smart_discovery.top_preselected", { max: maxResults })}
          </Typography>
        </Alert>

        {alreadyImportedCount > 0 && (
          <Alert severity="info" sx={{ mt: 2 }}>
            {t("smart_discovery.already_imported_notice", { count: alreadyImportedCount })}
          </Alert>
        )}

        {importSuccess && (
          <Alert severity="success" sx={{ mt: 2 }}>
            <strong>{t("smart_discovery.import_complete")}</strong>
            <br />
            {t("smart_discovery.sources_created", { count: importSuccess.created })}
            {importSuccess.failed > 0 && `, ${t("smart_discovery.sources_failed", { count: importSuccess.failed })}`}
            <br />
            <Typography variant="caption">{t("smart_discovery.redirecting")}</Typography>
          </Alert>
        )}

        {importError && <Alert severity="error" sx={{ mt: 2 }}>{importError}</Alert>}
      </Paper>

      <Paper sx={{ p: 3 }}>
        <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
          <Typography variant="h6">{t("smart_discovery.discovered_sources_title", { count: results.length })}</Typography>
          <Box sx={{ display: "flex", gap: 2, alignItems: "center" }}>
            <Button variant="outlined" size="small" onClick={onSelectAll} disabled={importing}>
              {selectedPmids.size === budgetedCount && budgetedCount > 0 ? t("smart_discovery.deselect_all") : t("smart_discovery.select_all")}
            </Button>
            <Chip
              label={t("smart_discovery.selected_count", { selected: selectedCount, total: notImportedCount })}
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
                    checked={selectedPmids.size > 0 && selectedPmids.size === budgetedCount}
                    indeterminate={selectedPmids.size > 0 && selectedPmids.size < budgetedCount}
                    onChange={onSelectAll}
                    disabled={importing}
                  />
                </TableCell>
                <TableCell><strong>{t("smart_discovery.col_quality")}</strong></TableCell>
                <TableCell><strong>{t("smart_discovery.col_title")}</strong></TableCell>
                <TableCell><strong>{t("smart_discovery.col_journal")}</strong></TableCell>
                <TableCell><strong>{t("smart_discovery.col_year")}</strong></TableCell>
                <TableCell><strong>{t("smart_discovery.col_relevance")}</strong></TableCell>
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
                      {isImported && <CheckIcon fontSize="small" aria-label="already imported" />}
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
              ? t("smart_discovery.over_budget", { count: selectedCount, max: maxResults })
              : selectedCount > 0
                ? t("smart_discovery.ready_to_import", { count: selectedCount })
                : t("smart_discovery.select_sources_hint")}
          </Typography>

          <Button
            variant="contained"
            size="large"
            startIcon={importing ? undefined : <DownloadIcon />}
            onClick={onImport}
            disabled={importing || selectedCount === 0}
            sx={{ minWidth: 200, fontWeight: 600 }}
          >
            {importing ? t("smart_discovery.importing") : t("smart_discovery.import_button", { count: selectedCount })}
          </Button>
        </Box>
      </Paper>
    </>
  );
}
