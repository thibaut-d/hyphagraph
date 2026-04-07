import { useEffect, useState, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { Link as RouterLink, useSearchParams } from "react-router-dom";

import {
  Paper,
  TextField,
  Typography,
  List,
  ListItem,
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

import {
  search,
  SearchResult,
  SearchResultType,
  type RelationSearchResult,
} from "../api/search";
import { usePageErrorHandler } from "../hooks/usePageErrorHandler";
import { entityPath } from "../utils/entityPath";

const RESULTS_PER_PAGE = 20;

export function SearchView() {
  const { t } = useTranslation();
  const handlePageError = usePageErrorHandler();
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
        setError(null);
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
        const parsedError = handlePageError(err, "Failed to perform search. Please try again.");
        setError(parsedError.userMessage);
        setResults([]);
        setTotal(0);
        setEntityCount(0);
        setSourceCount(0);
        setRelationCount(0);
      } finally {
        setLoading(false);
      }
    },
    [handlePageError]
  );

  // Search when query changes (debounced 300ms to avoid excess requests)
  useEffect(() => {
    const timer = setTimeout(() => {
      performSearch(query, page, typeFilter);
    }, 300);
    return () => clearTimeout(timer);
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

  const getRelationSourceLink = (result: RelationSearchResult): string =>
    `/sources/${result.source_id}?relation=${result.id}#relation-${result.id}`;

  const getResultLink = (result: SearchResult): string => {
    if (result.type === "entity") {
      return entityPath(result);
    } else if (result.type === "source") {
      return `/sources/${result.id}`;
    } else if (result.type === "relation") {
      return getRelationSourceLink(result);
    }
    return "#";
  };

  const getResultMetadata = (result: SearchResult): string => {
    if (result.type === "source") {
      const parts = [result.kind];
      if (result.year) parts.push(result.year.toString());
      if (result.authors && result.authors.length > 0) {
        parts.push(result.authors[0]);
      }
      return parts.join(" • ");
    } else if (result.type === "entity") {
      return result.slug;
    }
    return "";
  };

  const totalPages = Math.ceil(total / RESULTS_PER_PAGE);

  return (
    <Paper sx={{ p: { xs: 2, sm: 3 } }}>
      <Stack spacing={3}>
        <Typography variant="h5" sx={{ fontSize: { xs: '1.25rem', sm: '1.5rem' } }}>
          {t("search.title", "Search")}
        </Typography>

        {/* Search Input */}
        <TextField
          label={t("search.placeholder", "Search entities, sources, relations...")}
          value={query}
          onChange={handleQueryChange}
          fullWidth
          autoFocus
          helperText={t(
            "search.helper_text",
            "Search across entities, publications, and evidence claims. Match strength reflects text similarity, not confidence or study quality."
          )}
        />

        {/* Type Filter */}
        {query && (
          <Box>
            <Typography variant="subtitle2" gutterBottom>
              {t("search.filter_label", "Show results for:")}
            </Typography>
            <ToggleButtonGroup
              value={typeFilter}
              onChange={handleTypeFilterChange}
              aria-label={t("search.filter_aria", "Filter search results by kind")}
              size="small"
              sx={{
                flexWrap: 'wrap',
                '& .MuiToggleButton-root': {
                  fontSize: { xs: '0.75rem', sm: '0.875rem' },
                  py: { xs: 0.5, sm: 1 },
                }
              }}
            >
              <ToggleButton value="entity" aria-label={t("search.filter_entities", "Entities")}>
                {t("search.filter_entities", "Entities")} ({entityCount})
              </ToggleButton>
              <ToggleButton value="source" aria-label={t("search.filter_sources", "Publications & documents")}>
                {t("search.filter_sources", "Publications & documents")} ({sourceCount})
              </ToggleButton>
              <ToggleButton value="relation" aria-label={t("search.filter_relations", "Evidence claims")}>
                {t("search.filter_relations", "Evidence claims")} ({relationCount})
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
        {error && !loading && (
          <Alert severity="error">{error}</Alert>
        )}

        {/* Results */}
        {!loading && query && (
          <>
            {/* Results Summary */}
            {total > 0 && (
              <Typography variant="body2" color="text.secondary">
                {t("search.results_found", "{{count}} result(s) found", { count: total })}
                {typeFilter.length > 0 && (
                  <>
                    {" — "}
                    {t("search.results_filtered_by", "showing {{kinds}}", {
                      kinds: typeFilter.map(f =>
                        f === "entity" ? t("search.filter_entities", "Entities")
                        : f === "source" ? t("search.filter_sources", "Publications & documents")
                        : t("search.filter_relations", "Evidence claims")
                      ).join(", ")
                    })}
                  </>
                )}
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
                    <Stack spacing={1} sx={{ width: "100%" }}>
                      <Box sx={{ display: "flex", alignItems: "center", gap: 1, flexWrap: "wrap" }}>
                        <Chip
                          label={
                            result.type === "entity"
                              ? t("search.kind_entity", "Entity")
                              : result.type === "source"
                              ? t("search.kind_source", "Publication")
                              : t("search.kind_relation", "Evidence claim")
                          }
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
                        {result.type === "relation" && (
                          <Link
                            component={RouterLink}
                            to={`/relations/${result.id}`}
                            variant="body2"
                            color="text.secondary"
                            underline="hover"
                          >
                            {t("search.open_relation_detail", "Relation details")}
                          </Link>
                        )}
                        {result.relevance_score !== undefined && (
                          <Chip
                            label={t("search.match_score", "Match strength: {{pct}}%", { pct: Math.round(result.relevance_score * 100) })}
                            size="small"
                            variant="outlined"
                            title={t("search.match_score_title", "Text match strength — not a confidence or quality indicator")}
                          />
                        )}
                      </Box>
                      {getResultMetadata(result) && (
                        <Typography variant="body2" color="text.secondary">
                          {t("search.result_metadata", "Result details")}: {getResultMetadata(result)}
                        </Typography>
                      )}
                      {result.snippet && (
                        <Typography variant="body2" color="text.secondary">
                          {t("search.match_reason", "Why it matched")}: {result.snippet}
                        </Typography>
                      )}
                    </Stack>
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
            {t("search.empty_state", "Enter a search term to find entities, publications, and evidence claims.")}
          </Typography>
        )}
      </Stack>
    </Paper>
  );
}
