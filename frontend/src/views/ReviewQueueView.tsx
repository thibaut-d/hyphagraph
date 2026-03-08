import { useEffect, useState, useCallback } from "react";
import {
  listPendingExtractions,
  getReviewStats,
  reviewExtraction,
  batchReview,
  type StagedExtractionRead,
  type ReviewStats,
  type StagedExtractionFilters,
} from "../api/extractionReview";
import { Link as RouterLink } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useNotification } from "../notifications/NotificationContext";

import {
  Typography,
  List,
  ListItem,
  ListItemText,
  Paper,
  Box,
  Button,
  Stack,
  Alert,
  CircularProgress,
  Chip,
  Card,
  CardContent,
  Grid,
  IconButton,
  Checkbox,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Divider,
} from "@mui/material";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import CancelIcon from "@mui/icons-material/Cancel";
import WarningIcon from "@mui/icons-material/Warning";
import VerifiedIcon from "@mui/icons-material/Verified";
import RefreshIcon from "@mui/icons-material/Refresh";
import SelectAllIcon from "@mui/icons-material/SelectAll";
import DeselectIcon from "@mui/icons-material/Deselect";

const PAGE_SIZE = 20;

export function ReviewQueueView() {
  const { t } = useTranslation();
  const { showError } = useNotification();
  const [extractions, setExtractions] = useState<StagedExtractionRead[]>([]);
  const [stats, setStats] = useState<ReviewStats | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [reviewDialogOpen, setReviewDialogOpen] = useState(false);
  const [reviewNotes, setReviewNotes] = useState("");
  const [reviewDecision, setReviewDecision] = useState<"approve" | "reject">("approve");

  // Filters
  const [minScore, setMinScore] = useState<number | undefined>(undefined);
  const [onlyFlagged, setOnlyFlagged] = useState(false);

  const loadExtractions = useCallback(async (reset: boolean = false) => {
    setIsLoading(true);

    try {
      const filters: StagedExtractionFilters = {
        page: reset ? 1 : page,
        page_size: PAGE_SIZE,
        min_validation_score: minScore,
        has_flags: onlyFlagged || undefined,
      };

      const response = await listPendingExtractions(filters);

      if (reset) {
        setExtractions(response.extractions);
        setPage(1);
      } else {
        setExtractions(prev => [...prev, ...response.extractions]);
      }

      setHasMore(response.has_more);
    } catch (err) {
      showError(err);
    } finally {
      setIsLoading(false);
    }
  }, [page, minScore, onlyFlagged, showError]);

  const loadStats = useCallback(async () => {
    try {
      const statsData = await getReviewStats();
      setStats(statsData);
    } catch (err) {
      console.error("Failed to load stats:", err);
    }
  }, []);

  useEffect(() => {
    loadExtractions(true);
    loadStats();
  }, [minScore, onlyFlagged]);

  const handleRefresh = () => {
    setSelectedIds(new Set());
    loadExtractions(true);
    loadStats();
  };

  const handleLoadMore = () => {
    setPage(prev => prev + 1);
    loadExtractions(false);
  };

  const handleToggleSelect = (id: string) => {
    setSelectedIds(prev => {
      const newSet = new Set(prev);
      if (newSet.has(id)) {
        newSet.delete(id);
      } else {
        newSet.add(id);
      }
      return newSet;
    });
  };

  const handleSelectAll = () => {
    setSelectedIds(new Set(extractions.map(e => e.id)));
  };

  const handleDeselectAll = () => {
    setSelectedIds(new Set());
  };

  const handleSingleReview = async (extractionId: string, decision: "approve" | "reject", notes?: string) => {
    try {
      await reviewExtraction(extractionId, { decision, notes });
      handleRefresh();
    } catch (err) {
      showError(err);
    }
  };

  const handleBatchReview = async () => {
    if (selectedIds.size === 0) return;

    try {
      const result = await batchReview({
        extraction_ids: Array.from(selectedIds),
        decision: reviewDecision,
        notes: reviewNotes || undefined,
      });

      setReviewDialogOpen(false);
      setReviewNotes("");
      handleRefresh();

      if (result.failed > 0) {
        showError(new Error(`Batch review completed: ${result.succeeded} succeeded, ${result.failed} failed`));
      }
    } catch (err) {
      showError(err);
    }
  };

  const openBatchReviewDialog = (decision: "approve" | "reject") => {
    setReviewDecision(decision);
    setReviewDialogOpen(true);
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "auto_verified": return "success";
      case "approved": return "success";
      case "pending": return "warning";
      case "rejected": return "error";
      default: return "default";
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "auto_verified": return <VerifiedIcon fontSize="small" />;
      case "approved": return <CheckCircleIcon fontSize="small" />;
      case "pending": return <WarningIcon fontSize="small" />;
      case "rejected": return <CancelIcon fontSize="small" />;
      default: return undefined;
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      <Stack spacing={3}>
        {/* Header */}
        <Stack direction="row" justifyContent="space-between" alignItems="center">
          <Typography variant="h4">Review Queue</Typography>
          <Button
            startIcon={<RefreshIcon />}
            onClick={handleRefresh}
            disabled={isLoading}
          >
            Refresh
          </Button>
        </Stack>

        {/* Statistics Cards */}
        {stats && (
          <Grid container spacing={2}>
            <Grid size={{ xs: 12, sm: 6, md: 3 }}>
              <Card>
                <CardContent>
                  <Typography color="text.secondary" gutterBottom>
                    Pending Review
                  </Typography>
                  <Typography variant="h4">{stats.total_pending}</Typography>
                  <Typography variant="body2" color="text.secondary">
                    {stats.pending_entities} entities, {stats.pending_relations} relations
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid size={{ xs: 12, sm: 6, md: 3 }}>
              <Card>
                <CardContent>
                  <Typography color="text.secondary" gutterBottom>
                    Auto-Verified
                  </Typography>
                  <Typography variant="h4">{stats.total_auto_verified}</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid size={{ xs: 12, sm: 6, md: 3 }}>
              <Card>
                <CardContent>
                  <Typography color="text.secondary" gutterBottom>
                    Average Score
                  </Typography>
                  <Typography variant="h4">
                    {(stats.avg_validation_score * 100).toFixed(0)}%
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid size={{ xs: 12, sm: 6, md: 3 }}>
              <Card>
                <CardContent>
                  <Typography color="text.secondary" gutterBottom>
                    Flagged
                  </Typography>
                  <Typography variant="h4">{stats.flagged_count}</Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        )}

        {/* Filters */}
        <Paper sx={{ p: 2 }}>
          <Stack direction="row" spacing={2} alignItems="center">
            <TextField
              label="Min Validation Score"
              type="number"
              size="small"
              value={minScore ?? ""}
              onChange={(e) => setMinScore(e.target.value ? parseFloat(e.target.value) : undefined)}
              inputProps={{ min: 0, max: 1, step: 0.1 }}
              sx={{ width: 200 }}
            />
            <Button
              variant={onlyFlagged ? "contained" : "outlined"}
              onClick={() => setOnlyFlagged(!onlyFlagged)}
              startIcon={<WarningIcon />}
            >
              Only Flagged
            </Button>
          </Stack>
        </Paper>

        {/* Batch Actions */}
        {selectedIds.size > 0 && (
          <Paper sx={{ p: 2, bgcolor: "action.selected" }}>
            <Stack direction="row" spacing={2} alignItems="center">
              <Typography>
                {selectedIds.size} selected
              </Typography>
              <Button
                variant="contained"
                color="success"
                startIcon={<CheckCircleIcon />}
                onClick={() => openBatchReviewDialog("approve")}
              >
                Approve Selected
              </Button>
              <Button
                variant="contained"
                color="error"
                startIcon={<CancelIcon />}
                onClick={() => openBatchReviewDialog("reject")}
              >
                Reject Selected
              </Button>
              <Button
                startIcon={<DeselectIcon />}
                onClick={handleDeselectAll}
              >
                Deselect All
              </Button>
            </Stack>
          </Paper>
        )}

        {/* Selection Controls */}
        {extractions.length > 0 && (
          <Stack direction="row" spacing={2}>
            <Button
              startIcon={<SelectAllIcon />}
              onClick={handleSelectAll}
              size="small"
            >
              Select All
            </Button>
          </Stack>
        )}

        {/* Extractions List */}
        {isLoading && extractions.length === 0 ? (
          <Box sx={{ display: "flex", justifyContent: "center", p: 4 }}>
            <CircularProgress />
          </Box>
        ) : extractions.length === 0 ? (
          <Paper sx={{ p: 4, textAlign: "center" }}>
            <Typography variant="h6" color="text.secondary">
              No pending extractions
            </Typography>
            <Typography variant="body2" color="text.secondary">
              All extractions have been reviewed!
            </Typography>
          </Paper>
        ) : (
          <List>
            {extractions.map((extraction) => (
              <Paper key={extraction.id} sx={{ mb: 2 }}>
                <ListItem>
                  <Checkbox
                    checked={selectedIds.has(extraction.id)}
                    onChange={() => handleToggleSelect(extraction.id)}
                  />
                  <ListItemText
                    primary={
                      <Stack direction="row" spacing={1} alignItems="center">
                        <Typography variant="h6">
                          {extraction.extraction_data.slug || "Unnamed"}
                        </Typography>
                        <Chip
                          label={extraction.extraction_type}
                          size="small"
                          color="primary"
                          variant="outlined"
                        />
                        <Chip
                          label={extraction.status}
                          size="small"
                          color={getStatusColor(extraction.status)}
                          icon={getStatusIcon(extraction.status)}
                        />
                        <Chip
                          label={`Score: ${(extraction.validation_score * 100).toFixed(0)}%`}
                          size="small"
                          color={extraction.validation_score >= 0.9 ? "success" : "warning"}
                        />
                        {extraction.validation_flags.length > 0 && (
                          <Chip
                            label={`${extraction.validation_flags.length} flags`}
                            size="small"
                            color="warning"
                            icon={<WarningIcon />}
                          />
                        )}
                      </Stack>
                    }
                    secondary={
                      <Stack spacing={1} sx={{ mt: 1 }}>
                        <Typography variant="body2">
                          {extraction.extraction_data.summary || "No summary"}
                        </Typography>
                        {extraction.validation_flags.length > 0 && (
                          <Box>
                            <Typography variant="caption" color="text.secondary">
                              Validation issues:
                            </Typography>
                            {extraction.validation_flags.map((flag, idx) => (
                              <Chip
                                key={idx}
                                label={flag}
                                size="small"
                                sx={{ ml: 0.5, mt: 0.5 }}
                              />
                            ))}
                          </Box>
                        )}
                        <Typography variant="caption" color="text.secondary">
                          Text span: "{extraction.extraction_data.text_span}"
                        </Typography>
                        <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
                          <Button
                            size="small"
                            variant="contained"
                            color="success"
                            startIcon={<CheckCircleIcon />}
                            onClick={() => handleSingleReview(extraction.id, "approve")}
                          >
                            Approve
                          </Button>
                          <Button
                            size="small"
                            variant="outlined"
                            color="error"
                            startIcon={<CancelIcon />}
                            onClick={() => handleSingleReview(extraction.id, "reject")}
                          >
                            Reject
                          </Button>
                          {extraction.materialized_entity_id && (
                            <Button
                              size="small"
                              component={RouterLink}
                              to={`/entities/${extraction.materialized_entity_id}`}
                            >
                              View Entity
                            </Button>
                          )}
                        </Stack>
                      </Stack>
                    }
                  />
                </ListItem>
              </Paper>
            ))}
          </List>
        )}

        {/* Load More */}
        {hasMore && !isLoading && extractions.length > 0 && (
          <Box sx={{ display: "flex", justifyContent: "center" }}>
            <Button onClick={handleLoadMore} variant="outlined">
              Load More
            </Button>
          </Box>
        )}
      </Stack>

      {/* Batch Review Dialog */}
      <Dialog open={reviewDialogOpen} onClose={() => setReviewDialogOpen(false)}>
        <DialogTitle>
          {reviewDecision === "approve" ? "Approve" : "Reject"} {selectedIds.size} Extractions
        </DialogTitle>
        <DialogContent>
          <TextField
            label="Review Notes (optional)"
            multiline
            rows={4}
            fullWidth
            value={reviewNotes}
            onChange={(e) => setReviewNotes(e.target.value)}
            sx={{ mt: 2 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setReviewDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={handleBatchReview}
            variant="contained"
            color={reviewDecision === "approve" ? "success" : "error"}
          >
            {reviewDecision === "approve" ? "Approve" : "Reject"} All
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
