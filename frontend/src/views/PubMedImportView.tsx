/**
 * Dedicated view for PubMed bulk search and import.
 *
 * Workflow:
 * 1. User enters search query or pastes PubMed search URL
 * 2. Search PubMed and display results
 * 3. User selects articles to import
 * 4. Batch create sources from selected articles
 */
import { useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import {
  Paper,
  Typography,
  TextField,
  Button,
  Box,
  Alert,
  CircularProgress,
  Slider,
  Stack,
  Snackbar,
} from "@mui/material";
import SearchIcon from "@mui/icons-material/Search";
import { bulkSearchPubMed, bulkImportPubMed } from "../api/pubmed";
import { startBulkSourceExtractionJob } from "../api/extraction";
import { getLongRunningJob } from "../api/longRunningJobs";
import type { PubMedSearchResult } from "../types/pubmed";
import type { BulkSourceExtractionResponse } from "../types/extraction";
import { usePageErrorHandler } from "../hooks/usePageErrorHandler";
import { PubMedResultsTable } from "../components/source/PubMedResultsTable";

export function PubMedImportView() {
  const navigate = useNavigate();
  const handlePageError = usePageErrorHandler();

  // Search state
  const [searchInput, setSearchInput] = useState("");
  const [maxResults, setMaxResults] = useState(10);
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);

  // Results state
  const [results, setResults] = useState<PubMedSearchResult[]>([]);
  const [query, setQuery] = useState("");
  const [totalResults, setTotalResults] = useState(0);
  const [selectedPmids, setSelectedPmids] = useState<Set<string>>(new Set());

  // Import state
  const [importing, setImporting] = useState(false);
  const [importError, setImportError] = useState<string | null>(null);
  const [importSuccess, setImportSuccess] = useState<string | null>(null);

  const [bulkSearchTerm, setBulkSearchTerm] = useState("");
  const [bulkBudget, setBulkBudget] = useState(10);
  const [bulkExtracting, setBulkExtracting] = useState(false);
  const [bulkError, setBulkError] = useState<string | null>(null);
  const [bulkResult, setBulkResult] = useState<BulkSourceExtractionResponse | null>(null);

  // Abort controllers for cancellable long-running requests
  const searchControllerRef = useRef<AbortController | null>(null);
  const importControllerRef = useRef<AbortController | null>(null);

  const handleSearch = async () => {
    if (!searchInput.trim()) {
      setSearchError("Please enter a search query or paste a PubMed search URL");
      return;
    }

    // Cancel any in-flight search
    searchControllerRef.current?.abort();
    const controller = new AbortController();
    searchControllerRef.current = controller;

    setSearching(true);
    setSearchError(null);
    setResults([]);
    setSelectedPmids(new Set());

    try {
      // Determine if input is a URL or query
      const isUrl = searchInput.startsWith("http");

      const response = await bulkSearchPubMed(
        {
          query: isUrl ? undefined : searchInput,
          search_url: isUrl ? searchInput : undefined,
          max_results: maxResults,
        },
        controller.signal,
      );

      setResults(response.results);
      setQuery(response.query);
      setTotalResults(response.total_results);

      // Auto-select all results by default
      const allPmids = new Set(response.results.map((r) => r.pmid));
      setSelectedPmids(allPmids);
    } catch (error) {
      if (error instanceof Error && error.name === "AbortError") return;
      const parsedError = handlePageError(error, "Failed to search PubMed");
      setSearchError(parsedError.userMessage);
    } finally {
      setSearching(false);
    }
  };

  const handleCancelSearch = () => {
    searchControllerRef.current?.abort();
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
    if (selectedPmids.size === results.length) {
      setSelectedPmids(new Set());
    } else {
      const allPmids = new Set(results.map((r) => r.pmid));
      setSelectedPmids(allPmids);
    }
  };

  const handleImport = async () => {
    if (selectedPmids.size === 0) {
      setImportError("Please select at least one article to import");
      return;
    }

    const controller = new AbortController();
    importControllerRef.current = controller;

    setImporting(true);
    setImportError(null);

    try {
      const response = await bulkImportPubMed(
        { pmids: Array.from(selectedPmids) },
        controller.signal,
      );

      // Show success message
      const failedCount = response.failed_pmids.length;
      const successMessage =
        failedCount === 0
          ? `Successfully imported ${response.sources_created} articles!`
          : `Imported ${response.sources_created} articles. ${failedCount} failed: ${response.failed_pmids.join(", ")}`;

      setImportSuccess(successMessage);

      // Navigate to sources list after short delay to allow user to see message
      setTimeout(() => {
        navigate("/sources");
      }, 2000);
    } catch (error) {
      if (error instanceof Error && error.name === "AbortError") return;
      const parsedError = handlePageError(error, "Failed to import articles");
      setImportError(parsedError.userMessage);
    } finally {
      setImporting(false);
    }
  };

  const handleCancelImport = () => {
    importControllerRef.current?.abort();
  };

  const waitForBulkExtractionJob = async (jobId: string): Promise<BulkSourceExtractionResponse> => {
    for (let attempt = 0; attempt < 180; attempt += 1) {
      const job = await getLongRunningJob<BulkSourceExtractionResponse>(jobId);
      if (job.status === "succeeded" && job.result_payload) {
        return job.result_payload;
      }
      if (job.status === "failed") {
        throw new Error(job.error_message || "Bulk extraction failed");
      }
      await new Promise((resolve) => setTimeout(resolve, 2000));
    }
    throw new Error("Bulk extraction is still running. Check the review queue later.");
  };

  const handleBulkExtract = async () => {
    if (!bulkSearchTerm.trim()) {
      setBulkError("Enter words to search imported studies");
      return;
    }

    setBulkExtracting(true);
    setBulkError(null);
    setBulkResult(null);

    try {
      const job = await startBulkSourceExtractionJob({
        search: bulkSearchTerm,
        study_budget: bulkBudget,
      });
      const result = await waitForBulkExtractionJob(job.job_id);
      setBulkResult(result);
    } catch (error) {
      const parsedError = handlePageError(error, "Failed to bulk extract studies");
      setBulkError(parsedError.userMessage);
    } finally {
      setBulkExtracting(false);
    }
  };

  return (
    <Stack spacing={3}>
      {/* Header */}
      <Paper sx={{ p: 3 }}>
        <Typography variant="h4" gutterBottom>
          Import from PubMed
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Search PubMed and bulk import articles as sources for knowledge
          extraction.
        </Typography>
      </Paper>

      {/* Search Form */}
      <Paper sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom>
          Search PubMed
        </Typography>

        <Box sx={{ mb: 3 }}>
          <TextField
            fullWidth
            label="Search Query or PubMed URL"
            placeholder='e.g., "CRISPR AND 2024[pdat]" or paste PubMed search URL'
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            disabled={searching}
            multiline
            rows={2}
            onKeyPress={(e) => {
              if (e.key === "Enter" && !e.shiftKey && !searching) {
                e.preventDefault();
                handleSearch();
              }
            }}
          />
          <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: "block" }}>
            Enter a PubMed search query (supports all PubMed syntax) or paste a search URL from
            pubmed.ncbi.nlm.nih.gov
          </Typography>
        </Box>

        <Box sx={{ mb: 3 }}>
          <Typography gutterBottom>
            Maximum Results: {maxResults}
          </Typography>
          <Slider
            value={maxResults}
            onChange={(_, value) => setMaxResults(value as number)}
            min={1}
            max={100}
            step={1}
            marks={[
              { value: 1, label: "1" },
              { value: 25, label: "25" },
              { value: 50, label: "50" },
              { value: 75, label: "75" },
              { value: 100, label: "100" },
            ]}
            disabled={searching}
            sx={{ maxWidth: 600 }}
          />
          <Typography variant="caption" color="text.secondary">
            Note: Larger batches take longer due to NCBI rate limiting (3 requests/second)
          </Typography>
        </Box>

        <Stack direction="row" spacing={1}>
          <Button
            variant="contained"
            startIcon={searching ? <CircularProgress size={16} /> : <SearchIcon />}
            onClick={handleSearch}
            disabled={searching}
          >
            {searching ? "Searching..." : "Search PubMed"}
          </Button>
          {searching && (
            <Button variant="outlined" color="error" onClick={handleCancelSearch}>
              Cancel
            </Button>
          )}
        </Stack>

        {searchError && (
          <Alert severity="error" sx={{ mt: 2 }} onClose={() => setSearchError(null)}>
            {searchError}
          </Alert>
        )}
      </Paper>

      <Paper sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom>
          Bulk Extract Imported Studies
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Search already imported studies and run automatic entity and relation extraction on
          matching studies that have not been extracted yet.
        </Typography>
        <Stack spacing={2}>
          <TextField
            fullWidth
            label="Search imported studies"
            placeholder="e.g., ketamine depression"
            value={bulkSearchTerm}
            onChange={(event) => setBulkSearchTerm(event.target.value)}
            disabled={bulkExtracting}
          />
          <Box>
            <Typography gutterBottom>Study budget: {bulkBudget}</Typography>
            <Slider
              value={bulkBudget}
              onChange={(_, value) => setBulkBudget(value as number)}
              min={1}
              max={50}
              step={1}
              marks={[
                { value: 1, label: "1" },
                { value: 10, label: "10" },
                { value: 25, label: "25" },
                { value: 50, label: "50" },
              ]}
              disabled={bulkExtracting}
              sx={{ maxWidth: 600 }}
            />
          </Box>
          <Box>
            <Button
              variant="contained"
              startIcon={bulkExtracting ? <CircularProgress size={16} /> : <SearchIcon />}
              onClick={handleBulkExtract}
              disabled={bulkExtracting}
            >
              {bulkExtracting ? "Extracting..." : "Bulk Extract"}
            </Button>
          </Box>
        </Stack>
        {bulkError && (
          <Alert severity="error" sx={{ mt: 2 }} onClose={() => setBulkError(null)}>
            {bulkError}
          </Alert>
        )}
        {bulkResult && (
          <Alert severity={bulkResult.failed_count > 0 ? "warning" : "success"} sx={{ mt: 2 }}>
            Matched {bulkResult.matched_count} unextracted studies. Extracted{" "}
            {bulkResult.extracted_count} of {bulkResult.selected_count} selected studies;{" "}
            {bulkResult.failed_count} failed. Review staged entities and relations in the review
            queue.
          </Alert>
        )}
      </Paper>

      {/* Search Results */}
      {results.length > 0 && (
        <Paper sx={{ p: 3 }}>
          <PubMedResultsTable
            results={results}
            query={query}
            totalResults={totalResults}
            selectedPmids={selectedPmids}
            importing={importing}
            importError={importError}
            onToggleSelect={handleToggleSelect}
            onSelectAll={handleSelectAll}
            onImport={handleImport}
            onCancelImport={handleCancelImport}
            onClearImportError={() => setImportError(null)}
          />
        </Paper>
      )}

      {/* Help Text */}
      {results.length === 0 && !searching && (
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>
            How to Use
          </Typography>
          <Typography variant="body2" component="div">
            <ol>
              <li>
                <strong>Search by Query:</strong> Enter a PubMed search query using standard PubMed
                syntax
                <br />
                Examples: "CRISPR AND 2024[pdat]", "cancer immunotherapy", "vitamin d AND covid-19"
              </li>
              <li>
                <strong>Search by URL:</strong> Copy and paste a search URL from PubMed website
                <br />
                Example: https://pubmed.ncbi.nlm.nih.gov/?term=aspirin&filter=years.2020-2024
              </li>
              <li>
                <strong>Select Articles:</strong> Choose which articles to import (all selected by
                default)
              </li>
              <li>
                <strong>Import:</strong> Create sources from selected articles for knowledge
                extraction
              </li>
            </ol>
          </Typography>
        </Paper>
      )}

      {/* Success Snackbar */}
      <Snackbar
        open={Boolean(importSuccess)}
        autoHideDuration={6000}
        onClose={() => setImportSuccess(null)}
        anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
      >
        <Alert
          onClose={() => setImportSuccess(null)}
          severity="success"
          variant="filled"
          sx={{ width: "100%" }}
        >
          {importSuccess}
        </Alert>
      </Snackbar>
    </Stack>
  );
}
