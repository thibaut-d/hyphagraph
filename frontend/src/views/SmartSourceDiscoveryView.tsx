/**
 * SmartSourceDiscoveryView
 *
 * Intelligent multi-source discovery based on entities.
 *
 * Features:
 * - Entity-based search (1-10 entities)
 * - Multi-database support (PubMed, arXiv, etc.)
 * - Automatic quality scoring
 * - Budget-based pre-selection
 * - Deduplication against existing sources
 * - Bulk import workflow
 */

import { useState, useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  Paper,
  Typography,
  Stack,
  Button,
  Box,
  Alert,
  CircularProgress,
  TextField,
  Slider,
  Chip,
  Autocomplete,
  FormControlLabel,
  Checkbox as MuiCheckbox,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Checkbox,
  Link,
  IconButton,
  Divider,
} from "@mui/material";
import SearchIcon from "@mui/icons-material/Search";
import DownloadIcon from "@mui/icons-material/Download";
import AutoFixHighIcon from "@mui/icons-material/AutoFixHigh";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import InfoIcon from "@mui/icons-material/Info";

import { smartDiscovery, bulkImportFromDiscovery, SmartDiscoveryResult } from "../api/smart-discovery";
import { listEntities } from "../api/entities";
import { EntityRead } from "../types/entity";

export function SmartSourceDiscoveryView() {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const [searchParams] = useSearchParams();

  // Entity selection state
  const [availableEntities, setAvailableEntities] = useState<EntityRead[]>([]);
  const [selectedEntities, setSelectedEntities] = useState<EntityRead[]>([]);
  const [loadingEntities, setLoadingEntities] = useState(false);

  // Search configuration
  const [maxResults, setMaxResults] = useState(20);
  const [minQuality, setMinQuality] = useState(0.75); // Default: RCT+ only
  const [selectedDatabases, setSelectedDatabases] = useState<string[]>(["pubmed"]);

  // Search state
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);

  // Results state
  const [results, setResults] = useState<SmartDiscoveryResult[]>([]);
  const [queryUsed, setQueryUsed] = useState("");
  const [totalFound, setTotalFound] = useState(0);
  const [selectedPmids, setSelectedPmids] = useState<Set<string>>(new Set());

  // Import state
  const [importing, setImporting] = useState(false);
  const [importError, setImportError] = useState<string | null>(null);
  const [importSuccess, setImportSuccess] = useState<{ created: number; failed: number } | null>(null);

  // Load entities on mount
  useEffect(() => {
    setLoadingEntities(true);
    listEntities({ limit: 100, offset: 0 })
      .then((response) => {
        setAvailableEntities(response.items);

        // Pre-select entities from URL params (if navigated from EntityDetailView)
        const entitySlugParam = searchParams.get("entity");
        if (entitySlugParam) {
          const entity = response.items.find((e) => e.slug === entitySlugParam);
          if (entity) {
            setSelectedEntities([entity]);
          }
        }
      })
      .catch((error) => {
        console.error("Failed to load entities:", error);
      })
      .finally(() => {
        setLoadingEntities(false);
      });
  }, [searchParams]);

  const handleSearch = async () => {
    if (selectedEntities.length === 0) {
      setSearchError("Please select at least one entity");
      return;
    }

    setSearching(true);
    setSearchError(null);
    setResults([]);
    setSelectedPmids(new Set());
    setImportSuccess(null);

    try {
      const entitySlugs = selectedEntities.map((e) => e.slug);

      const response = await smartDiscovery({
        entity_slugs: entitySlugs,
        max_results: maxResults,
        min_quality: minQuality,
        databases: selectedDatabases,
      });

      setResults(response.results);
      setQueryUsed(response.query_used);
      setTotalFound(response.total_found);

      // Auto-select top N results (budget), excluding already imported
      const toSelect = response.results
        .filter((r) => !r.already_imported)
        .slice(0, maxResults)
        .map((r) => r.pmid)
        .filter((pmid): pmid is string => pmid !== null && pmid !== undefined);

      setSelectedPmids(new Set(toSelect));
    } catch (error) {
      setSearchError(error instanceof Error ? error.message : "Failed to search databases");
    } finally {
      setSearching(false);
    }
  };

  const handleToggleSelect = (pmid: string) => {
    const newSelected = new Set(selectedPmids);
    if (newSelected.has(pmid)) {
      newSelected.delete(pmid);
    } else {
      newSelected.add(pmid);
    }
    setSelectedPmids(newSelected);
  };

  const handleSelectAll = () => {
    if (selectedPmids.size === results.filter((r) => r.pmid && !r.already_imported).length) {
      setSelectedPmids(new Set());
    } else {
      const allPmids = results
        .filter((r) => r.pmid && !r.already_imported)
        .map((r) => r.pmid)
        .filter((pmid): pmid is string => pmid !== null && pmid !== undefined);
      setSelectedPmids(new Set(allPmids));
    }
  };

  const handleImport = async () => {
    if (selectedPmids.size === 0) {
      setImportError("Please select at least one article to import");
      return;
    }

    setImporting(true);
    setImportError(null);

    try {
      const response = await bulkImportFromDiscovery(Array.from(selectedPmids));

      setImportSuccess({
        created: response.sources_created,
        failed: response.failed_pmids.length,
      });

      // Navigate to sources list after success
      setTimeout(() => {
        navigate("/sources");
      }, 2000);
    } catch (error) {
      setImportError(error instanceof Error ? error.message : "Failed to import articles");
    } finally {
      setImporting(false);
    }
  };

  const selectedCount = selectedPmids.size;
  const notImportedCount = results.filter((r) => !r.already_imported).length;
  const alreadyImportedCount = results.filter((r) => r.already_imported).length;

  const getQualityLabel = (trustLevel: number): string => {
    if (trustLevel >= 0.9) return "Systematic Review / Meta-analysis";
    if (trustLevel >= 0.75) return "RCT / High Quality";
    if (trustLevel >= 0.65) return "Case-Control";
    if (trustLevel >= 0.5) return "Observational";
    return "Low Quality";
  };

  const getQualityColor = (trustLevel: number): "success" | "info" | "warning" | "error" => {
    if (trustLevel >= 0.9) return "success";
    if (trustLevel >= 0.75) return "info";
    if (trustLevel >= 0.5) return "warning";
    return "error";
  };

  return (
    <Stack spacing={3}>
      {/* Header */}
      <Paper sx={{ p: 3 }}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 2, mb: 2 }}>
          <IconButton onClick={() => navigate(-1)} size="small">
            <ArrowBackIcon />
          </IconButton>
          <Typography variant="h4">
            {t("smart_discovery.title", "🔍 Smart Source Discovery")}
          </Typography>
        </Box>

        <Alert severity="info" icon={<AutoFixHighIcon />}>
          {t(
            "smart_discovery.description",
            "Automatically discover high-quality scientific sources related to your entities. The system will search PubMed, arXiv, and other databases, score each source using OCEBM/GRADE standards, and pre-select the best ones for you."
          )}
        </Alert>
      </Paper>

      {/* Step 1: Entity Selection */}
      <Paper sx={{ p: 3 }}>
        <Typography variant="h5" gutterBottom sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          <span>1️⃣</span> {t("smart_discovery.step1", "Select Entities")}
        </Typography>

        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          {t(
            "smart_discovery.step1_help",
            "Choose 1-10 entities to search for. The system will find sources that mention all selected entities."
          )}
        </Typography>

        <Autocomplete
          multiple
          options={availableEntities}
          getOptionLabel={(entity) => entity.slug}
          value={selectedEntities}
          onChange={(_, newValue) => setSelectedEntities(newValue)}
          loading={loadingEntities}
          renderInput={(params) => (
            <TextField
              {...params}
              label={t("smart_discovery.select_entities", "Select entities (1-10)")}
              placeholder={t("smart_discovery.entity_placeholder", "Start typing to search...")}
            />
          )}
          renderTags={(value, getTagProps) =>
            value.map((entity, index) => (
              <Chip
                label={entity.slug}
                {...getTagProps({ index })}
                color="primary"
              />
            ))
          }
        />

        {selectedEntities.length > 0 && (
          <Alert severity="success" sx={{ mt: 2 }}>
            {t("smart_discovery.query_preview", "Query will search for:")} <strong>{selectedEntities.map((e) => e.slug.replace("-", " ").toUpperCase()).join(" AND ")}</strong>
          </Alert>
        )}
      </Paper>

      {/* Step 2: Search Configuration */}
      <Paper sx={{ p: 3 }}>
        <Typography variant="h5" gutterBottom sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          <span>2️⃣</span> {t("smart_discovery.step2", "Configure Search")}
        </Typography>

        <Stack spacing={3}>
          {/* Databases */}
          <Box>
            <Typography variant="subtitle2" gutterBottom>
              {t("smart_discovery.databases", "Databases to Search")}
            </Typography>
            <Stack direction="row" spacing={2}>
              <FormControlLabel
                control={
                  <MuiCheckbox
                    checked={selectedDatabases.includes("pubmed")}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setSelectedDatabases([...selectedDatabases, "pubmed"]);
                      } else {
                        setSelectedDatabases(selectedDatabases.filter((d) => d !== "pubmed"));
                      }
                    }}
                  />
                }
                label="PubMed (Medical Literature)"
              />
              <FormControlLabel
                control={<MuiCheckbox disabled />}
                label="arXiv (Coming Soon)"
              />
              <FormControlLabel
                control={<MuiCheckbox disabled />}
                label="Wikipedia (Coming Soon)"
              />
            </Stack>
          </Box>

          {/* Budget */}
          <Box>
            <Typography variant="subtitle2" gutterBottom>
              {t("smart_discovery.budget", "Results Budget")}: {maxResults} sources
            </Typography>
            <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 1 }}>
              {t("smart_discovery.budget_help", "Number of top-quality sources to pre-select (you can adjust selection later)")}
            </Typography>
            <Slider
              value={maxResults}
              onChange={(_, value) => setMaxResults(value as number)}
              min={5}
              max={50}
              step={5}
              marks={[
                { value: 5, label: "5" },
                { value: 20, label: "20" },
                { value: 50, label: "50" },
              ]}
              valueLabelDisplay="auto"
            />
          </Box>

          {/* Min Quality */}
          <Box>
            <Typography variant="subtitle2" gutterBottom>
              {t("smart_discovery.min_quality", "Minimum Quality")}: {(minQuality * 100).toFixed(0)}% ({getQualityLabel(minQuality)})
            </Typography>
            <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 1 }}>
              {t("smart_discovery.quality_help", "Only include sources with quality score above this threshold")}
            </Typography>
            <Slider
              value={minQuality}
              onChange={(_, value) => setMinQuality(value as number)}
              min={0.3}
              max={1.0}
              step={0.05}
              marks={[
                { value: 0.3, label: "Low" },
                { value: 0.5, label: "Neutral" },
                { value: 0.75, label: "RCT+" },
                { value: 0.9, label: "SR" },
              ]}
              valueLabelDisplay="auto"
              valueLabelFormat={(value) => `${(value * 100).toFixed(0)}%`}
            />
          </Box>

          {/* Search Button */}
          <Button
            variant="contained"
            size="large"
            fullWidth
            startIcon={searching ? <CircularProgress size={20} /> : <SearchIcon />}
            onClick={handleSearch}
            disabled={searching || selectedEntities.length === 0}
            sx={{ py: 2, fontSize: "1.1rem", fontWeight: 600 }}
          >
            {searching
              ? t("smart_discovery.searching", "Searching databases...")
              : t("smart_discovery.search", "🔍 Discover Sources")}
          </Button>
        </Stack>
      </Paper>

      {/* Search Error */}
      {searchError && (
        <Alert severity="error" onClose={() => setSearchError(null)}>
          {searchError}
        </Alert>
      )}

      {/* Results */}
      {results.length > 0 && (
        <>
          {/* Results Header */}
          <Paper sx={{ p: 3 }}>
            <Typography variant="h5" gutterBottom sx={{ display: "flex", alignItems: "center", gap: 1 }}>
              <span>3️⃣</span> {t("smart_discovery.step3", "Review & Import")}
            </Typography>

            <Alert severity="success" icon={<InfoIcon />}>
              <strong>
                {t("smart_discovery.results_found", "Found {{total}} sources", { total: totalFound })}
              </strong>
              {" "}
              ({selectedCount} selected for import)
              <br />
              <Typography variant="caption">
                Query: <strong>{queryUsed}</strong> • Top {maxResults} highest-quality sources pre-selected
              </Typography>
            </Alert>

            {alreadyImportedCount > 0 && (
              <Alert severity="info" sx={{ mt: 2 }}>
                {t("smart_discovery.already_imported", "{{count}} sources are already in your database (marked with ✓)", {
                  count: alreadyImportedCount,
                })}
              </Alert>
            )}

            {/* Import Success */}
            {importSuccess && (
              <Alert severity="success" sx={{ mt: 2 }}>
                <strong>{t("smart_discovery.import_success", "✓ Import complete!")}</strong>
                <br />
                {importSuccess.created} sources created
                {importSuccess.failed > 0 && `, ${importSuccess.failed} failed`}
                <br />
                <Typography variant="caption">Redirecting to sources list...</Typography>
              </Alert>
            )}

            {/* Import Error */}
            {importError && (
              <Alert severity="error" sx={{ mt: 2 }} onClose={() => setImportError(null)}>
                {importError}
              </Alert>
            )}
          </Paper>

          {/* Results Table */}
          <Paper sx={{ p: 3 }}>
            <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
              <Typography variant="h6">
                {t("smart_discovery.results", "Discovered Sources")} ({results.length})
              </Typography>

              <Box sx={{ display: "flex", gap: 2, alignItems: "center" }}>
                <Button
                  variant="outlined"
                  size="small"
                  onClick={handleSelectAll}
                  disabled={importing}
                >
                  {selectedPmids.size === notImportedCount
                    ? t("smart_discovery.deselect_all", "Deselect All")
                    : t("smart_discovery.select_all", "Select All")}
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
                        onChange={handleSelectAll}
                        disabled={importing}
                      />
                    </TableCell>
                    <TableCell>
                      <strong>Quality</strong>
                    </TableCell>
                    <TableCell>
                      <strong>Title</strong>
                    </TableCell>
                    <TableCell>
                      <strong>Journal</strong>
                    </TableCell>
                    <TableCell>
                      <strong>Year</strong>
                    </TableCell>
                    <TableCell>
                      <strong>Relevance</strong>
                    </TableCell>
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
                          bgcolor: isImported
                            ? "action.disabledBackground"
                            : isInBudget
                            ? "success.50"
                            : "inherit",
                          opacity: isImported ? 0.6 : 1,
                        }}
                      >
                        <TableCell padding="checkbox">
                          {!isImported && result.pmid && (
                            <Checkbox
                              checked={isSelected}
                              onChange={() => handleToggleSelect(result.pmid!)}
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
                          {result.authors && result.authors.length > 0 && (
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

            {/* Import Actions */}
            <Box sx={{ mt: 3, display: "flex", gap: 2, justifyContent: "space-between", alignItems: "center" }}>
              <Typography variant="body2" color="text.secondary">
                {selectedCount > maxResults
                  ? t("smart_discovery.over_budget", "⚠️ {{count}} selected (over budget of {{budget}})", {
                      count: selectedCount,
                      budget: maxResults,
                    })
                  : selectedCount > 0
                  ? t("smart_discovery.ready_to_import", "✓ Ready to import {{count}} sources", {
                      count: selectedCount,
                    })
                  : t("smart_discovery.no_selection", "Select sources to import")}
              </Typography>

              <Button
                variant="contained"
                size="large"
                startIcon={importing ? <CircularProgress size={20} /> : <DownloadIcon />}
                onClick={handleImport}
                disabled={importing || selectedCount === 0}
                sx={{ minWidth: 200, fontWeight: 600 }}
              >
                {importing
                  ? t("smart_discovery.importing", "Importing...")
                  : t("smart_discovery.import", "Import {{count}} Sources", { count: selectedCount })}
              </Button>
            </Box>
          </Paper>
        </>
      )}
    </Stack>
  );
}
