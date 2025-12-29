import { useEffect, useState, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { Link as RouterLink, useSearchParams } from "react-router-dom";

import {
  Paper,
  TextField,
  Typography,
  List,
  ListItem,
  ListItemText,
  Link,
  Stack,
  Box,
  Chip,
  CircularProgress,
  Pagination,
  ToggleButtonGroup,
  ToggleButton,
  Alert,
} from "@mui/material";

import { search, SearchResult, SearchResultType } from "../api/search";

const RESULTS_PER_PAGE = 20;

export function SearchView() {
  const { t } = useTranslation();
  const [searchParams, setSearchParams] = useSearchParams();

  const initialQuery = searchParams.get("q") || "";

  const [query, setQuery] = useState(initialQuery);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [total, setTotal] = useState(0);
  const [entityCount, setEntityCount] = useState(0);
  const [sourceCount, setSourceCount] = useState(0);
  const [relationCount, setRelationCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [typeFilter, setTypeFilter] = useState<SearchResultType[]>([]);

  // Perform search
  const performSearch = useCallback(
    async (searchQuery: string, currentPage: number, types: SearchResultType[]) => {
      if (!searchQuery.trim()) {
        setResults([]);
        setTotal(0);
        setEntityCount(0);
        setSourceCount(0);
        setRelationCount(0);
        return;
      }

      setLoading(true);
      setError(null);

      try {
        const response = await search({
          query: searchQuery.trim(),
          types: types.length > 0 ? types : undefined,
          limit: RESULTS_PER_PAGE,
          offset: (currentPage - 1) * RESULTS_PER_PAGE,
        });

        setResults(response.results);
        setTotal(response.total);
        setEntityCount(response.entity_count);
        setSourceCount(response.source_count);
        setRelationCount(response.relation_count);
      } catch (err) {
        console.error("Search failed:", err);
        setError("Failed to perform search. Please try again.");
        setResults([]);
        setTotal(0);
      } finally {
        setLoading(false);
      }
    },
    []
  );

  // Search when query changes
  useEffect(() => {
    performSearch(query, page, typeFilter);
  }, [query, page, typeFilter, performSearch]);

  // Update URL when query changes
  useEffect(() => {
    if (query) {
      setSearchParams({ q: query });
    } else {
      setSearchParams({});
    }
  }, [query, setSearchParams]);

  const handleQueryChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setQuery(e.target.value);
    setPage(1); // Reset to first page on new search
  };

  const handlePageChange = (_event: React.ChangeEvent<unknown>, value: number) => {
    setPage(value);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const handleTypeFilterChange = (
    _event: React.MouseEvent<HTMLElement>,
    newTypes: SearchResultType[]
  ) => {
    setTypeFilter(newTypes);
    setPage(1); // Reset to first page when filter changes
  };

  const getResultLink = (result: SearchResult): string => {
    if (result.type === "entity") {
      return `/entities/${result.id}`;
    } else if (result.type === "source") {
      return `/sources/${result.id}`;
    } else if (result.type === "relation") {
      return `/relations/${result.id}`;
    }
    return "#";
  };

  const getResultSecondaryText = (result: SearchResult): string => {
    if (result.type === "source") {
      const parts = [result.kind];
      if (result.year) parts.push(result.year.toString());
      if (result.authors && result.authors.length > 0) {
        parts.push(result.authors[0]);
      }
      return parts.join(" • ");
    } else if (result.type === "entity") {
      return result.snippet || result.slug;
    }
    return result.snippet || "";
  };

  const totalPages = Math.ceil(total / RESULTS_PER_PAGE);

  return (
    <Paper sx={{ p: 3 }}>
      <Stack spacing={3}>
        <Typography variant="h5">
          {t("search.title", "Search")}
        </Typography>

        {/* Search Input */}
        <TextField
          label={t("search.placeholder", "Search entities, sources, relations...")}
          value={query}
          onChange={handleQueryChange}
          fullWidth
          autoFocus
        />

        {/* Type Filter */}
        {query && (
          <Box>
            <Typography variant="subtitle2" gutterBottom>
              Filter by type:
            </Typography>
            <ToggleButtonGroup
              value={typeFilter}
              onChange={handleTypeFilterChange}
              aria-label="search result types"
              size="small"
            >
              <ToggleButton value="entity" aria-label="entities">
                Entities ({entityCount})
              </ToggleButton>
              <ToggleButton value="source" aria-label="sources">
                Sources ({sourceCount})
              </ToggleButton>
              <ToggleButton value="relation" aria-label="relations">
                Relations ({relationCount})
              </ToggleButton>
            </ToggleButtonGroup>
          </Box>
        )}

        {/* Loading State */}
        {loading && (
          <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
            <CircularProgress />
          </Box>
        )}

        {/* Error State */}
        {error && (
          <Alert severity="error">{error}</Alert>
        )}

        {/* Results */}
        {!loading && query && (
          <>
            {/* Results Summary */}
            {total > 0 && (
              <Typography variant="body2" color="text.secondary">
                {total} result{total !== 1 ? "s" : ""} found
                {typeFilter.length > 0 && ` (filtered by ${typeFilter.join(", ")})`}
              </Typography>
            )}

            {/* Results List */}
            <List>
              {results.map((result) => {
                return (
                  <ListItem
                    key={result.id}
                    sx={{
                      border: 1,
                      borderColor: "divider",
                      borderRadius: 1,
                      mb: 1,
                      "&:hover": {
                        backgroundColor: "action.hover",
                      },
                    }}
                  >
                    <ListItemText
                      primary={
                        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                          <Chip
                            label={result.type}
                            size="small"
                            color={
                              result.type === "entity"
                                ? "primary"
                                : result.type === "source"
                                ? "secondary"
                                : "default"
                            }
                          />
                          <Link
                            component={RouterLink}
                            to={getResultLink(result)}
                            sx={{ fontWeight: "medium" }}
                          >
                            {result.title}
                          </Link>
                          {result.relevance_score !== undefined && (
                            <Chip
                              label={`${Math.round(result.relevance_score * 100)}%`}
                              size="small"
                              variant="outlined"
                            />
                          )}
                        </Box>
                      }
                      secondary={getResultSecondaryText(result)}
                    />
                  </ListItem>
                );
              })}
            </List>

            {/* Pagination */}
            {totalPages > 1 && (
              <Box sx={{ display: "flex", justifyContent: "center", mt: 2 }}>
                <Pagination
                  count={totalPages}
                  page={page}
                  onChange={handlePageChange}
                  color="primary"
                  showFirstButton
                  showLastButton
                />
              </Box>
            )}
          </>
        )}

        {/* No Results */}
        {!loading && query && results.length === 0 && !error && (
          <Typography color="text.secondary">
            {t("search.no_results", "No results found")}
          </Typography>
        )}

        {/* Empty State */}
        {!query && (
          <Typography color="text.secondary">
            Enter a search query to find entities, sources, and relations.
          </Typography>
        )}
      </Stack>
    </Paper>
  );
}
