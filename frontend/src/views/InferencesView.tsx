import { useEffect, useState, useCallback } from "react";
import { listEntities } from "../api/entities";
import { getInferenceForEntity } from "../api/inferences";
import { EntityRead } from "../types/entity";
import { RoleInference } from "../types/inference";
import { Link as RouterLink } from "react-router-dom";
import { useTranslation } from "react-i18next";

import {
  Typography,
  List,
  ListItem,
  Paper,
  Box,
  Stack,
  Chip,
  Button,
  CircularProgress,
  Alert,
  LinearProgress,
  Divider,
} from "@mui/material";
import HelpOutlineIcon from "@mui/icons-material/HelpOutline";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import TrendingDownIcon from "@mui/icons-material/TrendingDown";
import TrendingFlatIcon from "@mui/icons-material/TrendingFlat";

import { ScrollToTop } from "../components/ScrollToTop";
import { useInfiniteScroll } from "../hooks/useInfiniteScroll";

const PAGE_SIZE = 20;

interface EntityWithInferences {
  entity: EntityRead;
  roleInferences: RoleInference[];
  isLoading: boolean;
  error: string | null;
}

function ScoreIndicator({ score }: { score: number | null }) {
  if (score === null) {
    return (
      <Chip
        icon={<TrendingFlatIcon />}
        label="No data"
        size="small"
        variant="outlined"
      />
    );
  }

  const color = score > 0.3 ? "success" : score < -0.3 ? "error" : "warning";
  const Icon = score > 0.3 ? TrendingUpIcon : score < -0.3 ? TrendingDownIcon : TrendingFlatIcon;

  return (
    <Chip
      icon={<Icon />}
      label={score.toFixed(2)}
      size="small"
      color={color}
      sx={{ fontWeight: 'bold', minWidth: 80 }}
    />
  );
}

function EntityInferenceCard({ item }: { item: EntityWithInferences }) {
  const { entity, roleInferences, isLoading, error } = item;

  return (
    <ListItem
      sx={{
        display: 'block',
        py: 2,
        px: 0,
        '&:hover': {
          bgcolor: 'action.hover',
          borderRadius: 1,
        },
      }}
    >
      <Paper variant="outlined" sx={{ p: 2 }}>
        <Stack spacing={2}>
          {/* Entity Header */}
          <Stack direction="row" justifyContent="space-between" alignItems="center">
            <Box>
              <Typography
                component={RouterLink}
                to={`/entities/${entity.id}`}
                variant="h6"
                sx={{
                  textDecoration: 'none',
                  color: 'primary.main',
                  '&:hover': { textDecoration: 'underline' },
                }}
              >
                {entity.label || entity.slug}
              </Typography>
              {entity.kind && (
                <Chip label={entity.kind} size="small" sx={{ mt: 0.5 }} />
              )}
            </Box>
          </Stack>

          <Divider />

          {/* Inference Results */}
          {isLoading && (
            <Box display="flex" justifyContent="center" py={2}>
              <CircularProgress size={24} />
            </Box>
          )}

          {error && (
            <Alert severity="warning" size="small">
              {error}
            </Alert>
          )}

          {!isLoading && !error && roleInferences.length === 0 && (
            <Typography variant="body2" color="text.secondary" align="center">
              No inferences computed yet
            </Typography>
          )}

          {!isLoading && !error && roleInferences.length > 0 && (
            <Stack spacing={1.5}>
              {roleInferences.map((roleInf) => (
                <Stack
                  key={roleInf.role_type}
                  direction="row"
                  justifyContent="space-between"
                  alignItems="center"
                  spacing={2}
                >
                  <Stack direction="row" spacing={2} alignItems="center" flex={1}>
                    <Typography variant="body1" sx={{ minWidth: 120, fontWeight: 500 }}>
                      {roleInf.role_type}
                    </Typography>
                    <ScoreIndicator score={roleInf.score} />
                    <Stack direction="row" spacing={1}>
                      <Chip
                        label={`Confidence: ${(roleInf.confidence * 100).toFixed(0)}%`}
                        size="small"
                        variant="outlined"
                      />
                      {roleInf.disagreement > 0.3 && (
                        <Chip
                          label={`Disagreement: ${(roleInf.disagreement * 100).toFixed(0)}%`}
                          size="small"
                          color="warning"
                          variant="outlined"
                        />
                      )}
                    </Stack>
                  </Stack>
                  <Button
                    component={RouterLink}
                    to={`/explain/${entity.id}/${roleInf.role_type}`}
                    size="small"
                    startIcon={<HelpOutlineIcon />}
                    variant="outlined"
                  >
                    Explain
                  </Button>
                </Stack>
              ))}
            </Stack>
          )}
        </Stack>
      </Paper>
    </ListItem>
  );
}

export default function InferencesView() {
  const { t } = useTranslation();
  const [items, setItems] = useState<EntityWithInferences[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoadingPage, setIsLoadingPage] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [offset, setOffset] = useState(0);

  // Load entities and their inferences
  const loadPage = useCallback(async (currentOffset: number) => {
    setIsLoadingPage(true);

    try {
      // Fetch paginated entities
      const response = await listEntities({
        limit: PAGE_SIZE,
        offset: currentOffset,
      });

      setTotal(response.total);
      setHasMore(currentOffset + response.items.length < response.total);

      // Create placeholder items with loading state
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

      // Load inferences for each entity asynchronously
      response.items.forEach(async (entity, index) => {
        try {
          const inference = await getInferenceForEntity(entity.id);
          const itemIndex = currentOffset === 0 ? index : items.length + index;

          setItems((prev) => {
            const updated = [...prev];
            updated[itemIndex] = {
              entity,
              roleInferences: inference.role_inferences,
              isLoading: false,
              error: null,
            };
            return updated;
          });
        } catch (error) {
          const itemIndex = currentOffset === 0 ? index : items.length + index;
          setItems((prev) => {
            const updated = [...prev];
            updated[itemIndex] = {
              entity,
              roleInferences: [],
              isLoading: false,
              error: "Failed to load inferences",
            };
            return updated;
          });
        }
      });
    } finally {
      setIsLoadingPage(false);
    }
  }, [items.length]);

  // Initial load
  useEffect(() => {
    loadPage(0);
  }, []);

  // Handle "Load More" button click
  const handleLoadMore = () => {
    const newOffset = offset + PAGE_SIZE;
    setOffset(newOffset);
    loadPage(newOffset);
  };

  // Infinite scroll support
  const { loadMoreRef } = useInfiniteScroll({
    hasMore: hasMore && !isLoadingPage,
    onLoadMore: handleLoadMore,
  });

  return (
    <Box sx={{ maxWidth: 1200, mx: 'auto', p: 3 }}>
      <ScrollToTop />

      {/* Header */}
      <Stack direction="row" justifyContent="space-between" alignItems="center" mb={3}>
        <Box>
          <Typography variant="h4" component="h1" gutterBottom>
            {t('inferences.title', 'Computed Inferences')}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {total > 0
              ? t('inferences.showing', { count: items.length, total }, `Showing ${items.length} of ${total} entities with inferences`)
              : t('inferences.loading', 'Loading entities...')}
          </Typography>
        </Box>
      </Stack>

      {/* Entity List with Inferences */}
      {items.length === 0 && !isLoadingPage && (
        <Alert severity="info">
          {t('inferences.noEntities', 'No entities found. Create entities and relations to see computed inferences.')}
        </Alert>
      )}

      {items.length > 0 && (
        <List sx={{ p: 0 }}>
          {items.map((item, index) => (
            <EntityInferenceCard key={item.entity.id || index} item={item} />
          ))}
        </List>
      )}

      {/* Load More */}
      {hasMore && (
        <Box ref={loadMoreRef} sx={{ display: 'flex', justifyContent: 'center', mt: 3 }}>
          {isLoadingPage ? (
            <CircularProgress />
          ) : (
            <Button variant="outlined" onClick={handleLoadMore}>
              {t('common.loadMore', 'Load More')}
            </Button>
          )}
        </Box>
      )}

      {/* Initial Loading */}
      {isLoadingPage && offset === 0 && (
        <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
          <CircularProgress />
        </Box>
      )}
    </Box>
  );
}
