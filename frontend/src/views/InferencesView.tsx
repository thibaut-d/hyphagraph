import { useEffect, useMemo, useState, useCallback } from "react";
import { Link as RouterLink } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  FormControl,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import HelpOutlineIcon from "@mui/icons-material/HelpOutline";
import TrendingDownIcon from "@mui/icons-material/TrendingDown";
import TrendingFlatIcon from "@mui/icons-material/TrendingFlat";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";

import { ScrollToTop } from "../components/ScrollToTop";
import { useInfiniteScroll } from "../hooks/useInfiniteScroll";
import { listEntities } from "../api/entities";
import { getInferenceForEntity } from "../api/inferences";
import type { EntityRead } from "../types/entity";
import type { RoleInference } from "../types/inference";

const PAGE_SIZE = 20;
const INFERENCE_LOAD_ERROR = "Failed to load inferences";

interface EntityWithInferences {
  entity: EntityRead;
  roleInferences: RoleInference[];
  isLoading: boolean;
  error: string | null;
}

interface InferenceIndexRow {
  entityId: string;
  entitySlug: string;
  roleType: string;
  score: number | null;
  confidence: number;
  disagreement: number;
  evidenceCount: number;
}

type ScoreDirectionFilter = "all" | "supports" | "mixed" | "contradicts" | "no_data";

function getScoreDirection(score: number | null): ScoreDirectionFilter {
  if (score === null) {
    return "no_data";
  }
  if (score > 0.3) {
    return "supports";
  }
  if (score < -0.3) {
    return "contradicts";
  }
  return "mixed";
}

function formatScoreDirectionLabel(direction: ScoreDirectionFilter) {
  switch (direction) {
    case "supports":
      return "Support-leaning";
    case "contradicts":
      return "Contradiction-leaning";
    case "mixed":
      return "Mixed / balanced";
    case "no_data":
      return "No score";
    default:
      return "All directions";
  }
}

function ScoreDirectionChip({ score }: { score: number | null }) {
  const direction = getScoreDirection(score);

  if (direction === "supports") {
    return <Chip icon={<TrendingUpIcon />} color="success" label="Support-leaning" size="small" />;
  }
  if (direction === "contradicts") {
    return <Chip icon={<TrendingDownIcon />} color="error" label="Contradiction-leaning" size="small" />;
  }
  if (direction === "mixed") {
    return <Chip icon={<TrendingFlatIcon />} color="warning" label="Mixed / balanced" size="small" />;
  }

  return <Chip icon={<TrendingFlatIcon />} label="No score" size="small" variant="outlined" />;
}

function ConfidenceChip({ confidence }: { confidence: number }) {
  const color = confidence > 0.7 ? "success" : confidence > 0.4 ? "warning" : "default";
  return (
    <Chip
      label={`${Math.round(confidence * 100)}%`}
      size="small"
      color={color}
      variant="outlined"
    />
  );
}

function DisagreementChip({ disagreement }: { disagreement: number }) {
  const color = disagreement > 0.3 ? "warning" : "default";
  return (
    <Chip
      label={`${Math.round(disagreement * 100)}%`}
      size="small"
      color={color}
      variant="outlined"
    />
  );
}

export default function InferencesView() {
  const { t } = useTranslation();
  const [items, setItems] = useState<EntityWithInferences[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const [isLoadingPage, setIsLoadingPage] = useState(false);
  const [roleFilter, setRoleFilter] = useState("all");
  const [scoreDirectionFilter, setScoreDirectionFilter] = useState<ScoreDirectionFilter>("all");
  const [searchTerm, setSearchTerm] = useState("");

  const loadEntityInference = useCallback(async (entity: EntityRead) => {
    setItems((prev) =>
      prev.map((item) =>
        item.entity.id === entity.id ? { ...item, isLoading: true, error: null } : item,
      ),
    );

    try {
      const inference = await getInferenceForEntity(entity.id);
      setItems((prev) =>
        prev.map((item) =>
          item.entity.id === entity.id
            ? {
                entity,
                roleInferences: inference.role_inferences || [],
                isLoading: false,
                error: null,
              }
            : item,
        ),
      );
    } catch {
      setItems((prev) =>
        prev.map((item) =>
          item.entity.id === entity.id
            ? {
                entity,
                roleInferences: [],
                isLoading: false,
                error: INFERENCE_LOAD_ERROR,
              }
            : item,
        ),
      );
    }
  }, []);

  const loadPage = useCallback(
    async (currentOffset: number) => {
      setIsLoadingPage(true);

      try {
        const response = await listEntities({
          limit: PAGE_SIZE,
          offset: currentOffset,
        });

        setTotal(response.total);
        setHasMore(currentOffset + response.items.length < response.total);

        const newItems: EntityWithInferences[] = response.items.map((entity) => ({
          entity,
          roleInferences: [],
          isLoading: true,
          error: null,
        }));

        if (currentOffset === 0) {
          setItems(newItems);
        } else {
          setItems((prev) => [...prev, ...newItems]);
        }

        response.items.forEach((entity) => {
          void loadEntityInference(entity);
        });
      } finally {
        setIsLoadingPage(false);
      }
    },
    [loadEntityInference],
  );

  useEffect(() => {
    void loadPage(0);
  }, [loadPage]);

  const handleLoadMore = () => {
    const newOffset = offset + PAGE_SIZE;
    setOffset(newOffset);
    void loadPage(newOffset);
  };

  const loadMoreRef = useInfiniteScroll({
    hasMore: hasMore && !isLoadingPage,
    isLoading: isLoadingPage,
    onLoadMore: handleLoadMore,
  });

  const rows = useMemo<InferenceIndexRow[]>(() => {
    return items.flatMap((item) =>
      item.roleInferences.map((roleInference) => ({
        entityId: item.entity.id,
        entitySlug: item.entity.slug,
        roleType: roleInference.role_type,
        score: roleInference.score,
        confidence: roleInference.confidence,
        disagreement: roleInference.disagreement,
        evidenceCount: roleInference.coverage,
      })),
    );
  }, [items]);

  const availableRoles = useMemo(
    () => ["all", ...Array.from(new Set(rows.map((row) => row.roleType))).sort()],
    [rows],
  );

  const filteredRows = useMemo(() => {
    const normalizedSearch = searchTerm.trim().toLowerCase();

    return rows.filter((row) => {
      const matchesRole = roleFilter === "all" || row.roleType === roleFilter;
      const matchesDirection =
        scoreDirectionFilter === "all" || getScoreDirection(row.score) === scoreDirectionFilter;
      const matchesSearch =
        normalizedSearch.length === 0 ||
        row.entitySlug.toLowerCase().includes(normalizedSearch) ||
        row.roleType.toLowerCase().includes(normalizedSearch);

      return matchesRole && matchesDirection && matchesSearch;
    });
  }, [roleFilter, rows, scoreDirectionFilter, searchTerm]);

  const errorItems = items.filter((item) => item.error);
  const loadingEntities = items.filter((item) => item.isLoading).length;
  const supportLeaningCount = rows.filter((row) => getScoreDirection(row.score) === "supports").length;
  const contradictionLeaningCount = rows.filter((row) => getScoreDirection(row.score) === "contradicts").length;
  const mixedCount = rows.filter((row) => getScoreDirection(row.score) === "mixed").length;
  const highDisagreementCount = rows.filter((row) => row.disagreement > 0.3).length;

  return (
    <Box sx={{ maxWidth: 1400, mx: "auto", p: 3 }}>
      <ScrollToTop />

      <Stack spacing={3}>
        <Paper sx={{ p: 3 }}>
          <Stack spacing={2}>
            <Typography variant="h4" component="h1">
              {t("inferences.title", "Inference Index")}
            </Typography>
            <Typography variant="body1" color="text.secondary">
              {t(
                "inferences.description",
                "Scan computed role-level readings across entities in one index. Each row shows the role, score direction, confidence, disagreement, and evidence count behind that reading."
              )}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {total > 0
                ? t("inferences.showing", {
                    defaultValue: "{{rows}} rows built from {{entities}} loaded entities out of {{total}} total entities.",
                    rows: filteredRows.length,
                    entities: items.length,
                    total,
                  })
                : t("inferences.loading", "Loading entity index...")}
            </Typography>
          </Stack>
        </Paper>

        <Paper sx={{ p: 3 }}>
          <Stack spacing={2}>
            <Typography variant="h6">{t("inferences.summary", "Index summary")}</Typography>
            <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
              <Chip label={`Rows: ${rows.length}`} color="primary" />
              <Chip label={`Support-leaning: ${supportLeaningCount}`} color="success" variant="outlined" />
              <Chip label={`Contradiction-leaning: ${contradictionLeaningCount}`} color="error" variant="outlined" />
              <Chip label={`Mixed: ${mixedCount}`} color="warning" variant="outlined" />
              <Chip label={`High disagreement: ${highDisagreementCount}`} variant="outlined" />
              <Chip label={`Entity load errors: ${errorItems.length}`} variant="outlined" />
              <Chip label={`Loading entities: ${loadingEntities}`} variant="outlined" />
            </Box>
          </Stack>
        </Paper>

        <Paper sx={{ p: 3 }}>
          <Stack spacing={2}>
            <Typography variant="h6">{t("inferences.filters", "Filters")}</Typography>
            <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
              <TextField
                label={t("inferences.search", "Search entity or role")}
                value={searchTerm}
                onChange={(event) => setSearchTerm(event.target.value)}
                fullWidth
              />
              <FormControl sx={{ minWidth: 220 }}>
                <InputLabel id="role-filter-label">
                  {t("inferences.role_filter", "Role")}
                </InputLabel>
                <Select
                  labelId="role-filter-label"
                  value={roleFilter}
                  label={t("inferences.role_filter", "Role")}
                  onChange={(event) => setRoleFilter(event.target.value)}
                >
                  {availableRoles.map((role) => (
                    <MenuItem key={role} value={role}>
                      {role === "all" ? t("common.all", "All") : role}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
              <FormControl sx={{ minWidth: 220 }}>
                <InputLabel id="direction-filter-label">
                  {t("inferences.direction_filter", "Score direction")}
                </InputLabel>
                <Select
                  labelId="direction-filter-label"
                  value={scoreDirectionFilter}
                  label={t("inferences.direction_filter", "Score direction")}
                  onChange={(event) =>
                    setScoreDirectionFilter(event.target.value as ScoreDirectionFilter)
                  }
                >
                  {(["all", "supports", "mixed", "contradicts", "no_data"] as ScoreDirectionFilter[]).map(
                    (direction) => (
                      <MenuItem key={direction} value={direction}>
                        {formatScoreDirectionLabel(direction)}
                      </MenuItem>
                    ),
                  )}
                </Select>
              </FormControl>
            </Stack>
          </Stack>
        </Paper>

        {errorItems.length > 0 && (
          <Alert severity="warning">
            {t(
              "inferences.partial_errors",
              "Some entities could not load inferences. Retry those entities from the list below."
            )}
            <Stack spacing={1} sx={{ mt: 2 }}>
              {errorItems.map((item) => (
                <Box
                  key={item.entity.id}
                  sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 2 }}
                >
                  <Typography variant="body2">{item.entity.slug}: {item.error}</Typography>
                  <Button size="small" onClick={() => void loadEntityInference(item.entity)}>
                    Retry
                  </Button>
                </Box>
              ))}
            </Stack>
          </Alert>
        )}

        {items.length === 0 && !isLoadingPage ? (
          <Alert severity="info">
            {t(
              "inferences.noEntities",
              "No entities found. Create entities and relations to see computed inferences."
            )}
          </Alert>
        ) : (
          <TableContainer component={Paper} variant="outlined">
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>{t("inferences.table.entity", "Entity")}</TableCell>
                  <TableCell>{t("inferences.table.role", "Role")}</TableCell>
                  <TableCell>{t("inferences.table.direction", "Score direction")}</TableCell>
                  <TableCell>{t("inferences.table.score", "Score")}</TableCell>
                  <TableCell>{t("inferences.table.confidence", "Confidence")}</TableCell>
                  <TableCell>{t("inferences.table.disagreement", "Disagreement")}</TableCell>
                  <TableCell>{t("inferences.table.evidence_count", "Evidence count")}</TableCell>
                  <TableCell align="right">{t("inferences.table.detail", "Detail")}</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {filteredRows.map((row) => (
                  <TableRow key={`${row.entityId}-${row.roleType}`} hover>
                    <TableCell>
                      <Button component={RouterLink} to={`/entities/${row.entityId}`} size="small">
                        {row.entitySlug}
                      </Button>
                    </TableCell>
                    <TableCell>{row.roleType}</TableCell>
                    <TableCell>
                      <ScoreDirectionChip score={row.score} />
                    </TableCell>
                    <TableCell>
                      {row.score === null ? t("common.not_available", "N/A") : row.score.toFixed(2)}
                    </TableCell>
                    <TableCell>
                      <ConfidenceChip confidence={row.confidence} />
                    </TableCell>
                    <TableCell>
                      <DisagreementChip disagreement={row.disagreement} />
                    </TableCell>
                    <TableCell>{row.evidenceCount}</TableCell>
                    <TableCell align="right">
                      <Button
                        component={RouterLink}
                        to={`/entities/${row.entityId}/properties/${row.roleType}`}
                        size="small"
                        startIcon={<HelpOutlineIcon />}
                        variant="outlined"
                      >
                        {t("inference.explain", "View detail")}
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}

                {filteredRows.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={8}>
                      <Alert severity="info">
                        {t(
                          "inferences.no_filtered_rows",
                          "No inference rows match the current filters."
                        )}
                      </Alert>
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        )}

        {hasMore && (
          <Box ref={loadMoreRef} sx={{ display: "flex", justifyContent: "center" }}>
            {isLoadingPage ? (
              <CircularProgress />
            ) : (
              <Button variant="outlined" onClick={handleLoadMore}>
                {t("common.loadMore", "Load More")}
              </Button>
            )}
          </Box>
        )}

        {isLoadingPage && offset === 0 && (
          <Box sx={{ display: "flex", justifyContent: "center" }}>
            <CircularProgress />
          </Box>
        )}
      </Stack>
    </Box>
  );
}
