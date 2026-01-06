/**
 * Dedicated view for PubMed bulk search and import.
 *
 * Workflow:
 * 1. User enters search query or pastes PubMed search URL
 * 2. Search PubMed and display results
 * 3. User selects articles to import
 * 4. Batch create sources from selected articles
 */
import { useState } from "react";
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
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Checkbox,
  Chip,
  Link,
  Stack,
} from "@mui/material";
import SearchIcon from "@mui/icons-material/Search";
import DownloadIcon from "@mui/icons-material/Download";
import { bulkSearchPubMed, bulkImportPubMed } from "../api/pubmed";
import type { PubMedSearchResult } from "../types/pubmed";

export function PubMedImportView() {
  const navigate = useNavigate();

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

  const handleSearch = async () => {
    if (!searchInput.trim()) {
      setSearchError("Please enter a search query or paste a PubMed search URL");
      return;
    }

    setSearching(true);
    setSearchError(null);
    setResults([]);
    setSelectedPmids(new Set());

    try {
      // Determine if input is a URL or query
      const isUrl = searchInput.startsWith("http");

      const response = await bulkSearchPubMed({
        query: isUrl ? undefined : searchInput,
        search_url: isUrl ? searchInput : undefined,
        max_results: maxResults,
      });

      setResults(response.results);
      setQuery(response.query);
      setTotalResults(response.total_results);

      // Auto-select all results by default
      const allPmids = new Set(response.results.map((r) => r.pmid));
      setSelectedPmids(allPmids);
    } catch (error) {
      setSearchError(
        error instanceof Error ? error.message : "Failed to search PubMed"
      );
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

    setImporting(true);
    setImportError(null);

    try {
      const response = await bulkImportPubMed({
        pmids: Array.from(selectedPmids),
      });

      // Show success message
      const failedCount = response.failed_pmids.length;
      const successMessage =
        failedCount === 0
          ? `Successfully imported ${response.sources_created} articles!`
          : `Imported ${response.sources_created} articles. ${failedCount} failed: ${response.failed_pmids.join(", ")}`;

      alert(successMessage);

      // Navigate to sources list
      navigate("/sources");
    } catch (error) {
      setImportError(
        error instanceof Error ? error.message : "Failed to import articles"
      );
    } finally {
      setImporting(false);
    }
  };

  const selectedResults = results.filter((r) => selectedPmids.has(r.pmid));

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

        <Button
          variant="contained"
          startIcon={searching ? <CircularProgress size={16} /> : <SearchIcon />}
          onClick={handleSearch}
          disabled={searching}
        >
          {searching ? "Searching..." : "Search PubMed"}
        </Button>

        {searchError && (
          <Alert severity="error" sx={{ mt: 2 }} onClose={() => setSearchError(null)}>
            {searchError}
          </Alert>
        )}
      </Paper>

      {/* Search Results */}
      {results.length > 0 && (
        <Paper sx={{ p: 3 }}>
          <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
            <Box>
              <Typography variant="h6">
                Search Results
              </Typography>
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
                onClick={handleImport}
                disabled={importing || selectedPmids.size === 0}
              >
                {importing ? "Importing..." : `Import ${selectedPmids.size} Articles`}
              </Button>
            </Box>
          </Box>

          {importError && (
            <Alert severity="error" sx={{ mb: 2 }} onClose={() => setImportError(null)}>
              {importError}
            </Alert>
          )}

          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell padding="checkbox">
                    <Checkbox
                      checked={selectedPmids.size === results.length && results.length > 0}
                      indeterminate={selectedPmids.size > 0 && selectedPmids.size < results.length}
                      onChange={handleSelectAll}
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
                    onClick={() => handleToggleSelect(result.pmid)}
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
                      <Link href={result.url} target="_blank" rel="noopener noreferrer" onClick={(e) => e.stopPropagation()}>
                        {result.pmid}
                      </Link>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
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
    </Stack>
  );
}
