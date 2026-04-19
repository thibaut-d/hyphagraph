import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Grid,
  List,
  Paper,
  Stack,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from "@mui/material";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import CancelIcon from "@mui/icons-material/Cancel";
import DeselectIcon from "@mui/icons-material/Deselect";
import RefreshIcon from "@mui/icons-material/Refresh";
import SelectAllIcon from "@mui/icons-material/SelectAll";
import WarningIcon from "@mui/icons-material/Warning";

import type { ExtractionType } from "../api/extractionReview";
import { ExtractionCard } from "../components/extraction/ExtractionCard";
import { useReviewDialog } from "../hooks/useReviewDialog";
import { useReviewQueue } from "../hooks/useReviewQueue";
import { useSelection } from "../hooks/useSelection";

const PAGE_SIZE = 20;

function QueueIdentitySection({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <Paper sx={{ p: 3 }}>
      <Stack spacing={1.5}>
        <Typography variant="h5">{title}</Typography>
        <Typography variant="body2" color="text.secondary">
          {description}
        </Typography>
      </Stack>
    </Paper>
  );
}

export function ReviewQueueView() {
  const { t } = useTranslation();
  const [minScore, setMinScore] = useState<number | undefined>(undefined);
  const [onlyFlagged, setOnlyFlagged] = useState(false);
  const [extractionType, setExtractionType] = useState<ExtractionType | undefined>(undefined);

  const { extractions, stats, isLoading, hasMore, loadMore, refresh } = useReviewQueue({
    pageSize: PAGE_SIZE,
    minScore,
    onlyFlagged,
    extractionType,
  });

  const { selectedIds, toggleSelection, selectAll, clearSelection, selectedCount } = useSelection();
  const visibleExtractionIds = extractions.map((extraction) => extraction.id).join("|");

  // Clear selection whenever the visible extraction set changes due to a filter or tab switch (UX31-M1)
  useEffect(() => {
    clearSelection();
  }, [minScore, onlyFlagged, extractionType, visibleExtractionIds, clearSelection]);

  const {
    isOpen: reviewDialogOpen,
    notes: reviewNotes,
    decision: reviewDecision,
    setNotes: setReviewNotes,
    setDecision: setReviewDecision,
    openDialog: openReviewDialog,
    closeDialog: closeReviewDialog,
    submitReview,
    submitBatchReview,
  } = useReviewDialog();

  const handleRefresh = () => {
    clearSelection();
    refresh();
  };

  const handleSelectAll = () => {
    selectAll(extractions.map((extraction) => extraction.id));
  };

  const handleSingleReview = async (extractionId: string, decision: "approve" | "reject") => {
    await submitReview(extractionId, handleRefresh, decision);
  };

  const handleBatchReview = async () => {
    await submitBatchReview(selectedIds, () => {
      clearSelection();
      refresh();
    });
  };

  const openBatchReviewDialog = (decision: "approve" | "reject") => {
    setReviewDecision(decision);
    openReviewDialog(decision);
  };

  const stagedIdentityTitle = t("review_queue.queue_staged_title", "Staged extraction review");
  const stagedIdentityDescription = t(
    "review_queue.queue_staged_description",
    "This queue holds staged entity and relation extractions that need human review before they are materialized into the graph."
  );
  return (
    <Box>
      <Stack spacing={3}>
        <Stack
          direction={{ xs: "column", sm: "row" }}
          justifyContent="space-between"
          alignItems={{ xs: "stretch", sm: "center" }}
          spacing={2}
        >
          <Typography variant="h4">{t("menu.review_queue", "Review queue")}</Typography>
          <Button startIcon={<RefreshIcon />} onClick={handleRefresh} disabled={isLoading}>
            {t("review_queue.refresh", "Refresh queue")}
          </Button>
        </Stack>

        <QueueIdentitySection
          title={stagedIdentityTitle}
          description={stagedIdentityDescription}
        />

        <Paper sx={{ p: 2 }}>
          <Stack spacing={2}>
            <Typography variant="h6">
              {t("review_queue.summary_title", "Summary metrics")}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {t(
                "review_queue.summary_description",
                "Use these signals to decide where to start: pending volume shows queue pressure, average score shows automated confidence, and flags highlight likely review risk."
              )}
            </Typography>
            {stats && (
              <Grid container spacing={2}>
                <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                  <Card>
                    <CardContent>
                      <Typography color="text.secondary" gutterBottom>
                        {t("review_queue.pending_review")}
                      </Typography>
                      <Typography variant="h4">{stats.total_pending}</Typography>
                      <Typography variant="body2" color="text.secondary">
                        {t("review_queue.pending_breakdown", {
                          entities: stats.pending_entities,
                          relations: stats.pending_relations,
                        })}
                      </Typography>
                      <Typography variant="caption" color="text.disabled">
                        {t("review_queue.pending_review_hint")}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                  <Card>
                    <CardContent>
                      <Typography color="text.secondary" gutterBottom>
                        {t("review_queue.auto_verified")}
                      </Typography>
                      <Typography variant="h4">{stats.total_auto_verified}</Typography>
                      <Typography variant="caption" color="text.disabled">
                        {t("review_queue.auto_verified_hint")}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                  <Card>
                    <CardContent>
                      <Typography color="text.secondary" gutterBottom>
                        {t("review_queue.average_score")}
                      </Typography>
                      <Typography variant="h4">
                        {(stats.avg_validation_score * 100).toFixed(0)}%
                      </Typography>
                      <Typography variant="caption" color="text.disabled">
                        {t("review_queue.average_score_hint")}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                  <Card>
                    <CardContent>
                      <Typography color="text.secondary" gutterBottom>
                        {t("review_queue.flagged")}
                      </Typography>
                      <Typography variant="h4">{stats.flagged_count}</Typography>
                      <Typography variant="caption" color="text.disabled">
                        {t("review_queue.flagged_hint")}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
              </Grid>
            )}
          </Stack>
        </Paper>

        <Paper sx={{ p: 2 }}>
          <Stack spacing={2}>
            <Typography variant="h6">
              {t("review_queue.filters_title", "Filters")}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {t(
                "review_queue.filters_description",
                "Narrow the staged extraction queue by review priority, flagged risk, or extraction type."
              )}
            </Typography>
            <Stack direction={{ xs: "column", sm: "row" }} spacing={2} alignItems={{ xs: "stretch", sm: "center" }} flexWrap="wrap">
              <TextField
                label={t("review_queue.min_score_label", "Minimum validation score")}
                type="number"
                size="small"
                value={minScore ?? ""}
                onChange={(event) =>
                  setMinScore(event.target.value ? parseFloat(event.target.value) : undefined)
                }
                inputProps={{ min: 0, max: 1, step: 0.1 }}
                sx={{ width: { xs: "100%", sm: 200 } }}
              />
              <Button
                variant={onlyFlagged ? "contained" : "outlined"}
                onClick={() => setOnlyFlagged(!onlyFlagged)}
                startIcon={<WarningIcon />}
              >
                {t("review_queue.only_flagged", "Only flagged items")}
              </Button>
            </Stack>
            <ToggleButtonGroup
              value={extractionType ?? "all"}
              exclusive
              onChange={(_event, value) =>
                setExtractionType(value === "all" ? undefined : (value as ExtractionType))
              }
              size="small"
              aria-label={t("review_queue.type_filter_label", "Filter by extraction type")}
              sx={{ flexWrap: "wrap" }}
            >
              <ToggleButton value="all">{t("review_queue.type_all", "All staged items")}</ToggleButton>
              <ToggleButton value="entity">{t("review_queue.type_entity")}</ToggleButton>
              <ToggleButton value="relation">{t("review_queue.type_relation")}</ToggleButton>
            </ToggleButtonGroup>
          </Stack>
        </Paper>

        <Paper sx={{ p: 2, bgcolor: selectedCount > 0 ? "action.selected" : "background.paper" }}>
          <Stack spacing={2}>
            <Typography variant="h6">
              {t("review_queue.batch_tools_title", "Batch tools")}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {selectedCount > 0
                ? t("review_queue.selected_count", { count: selectedCount })
                : t(
                    "review_queue.batch_tools_description",
                    "Select staged extractions to approve or reject them in one batch."
                  )}
            </Typography>
            <Stack direction={{ xs: "column", sm: "row" }} spacing={2} flexWrap="wrap">
              <Button
                startIcon={<SelectAllIcon />}
                onClick={handleSelectAll}
                size="small"
                disabled={extractions.length === 0}
              >
                {t("review_queue.select_all")}
              </Button>
              <Button
                startIcon={<DeselectIcon />}
                onClick={clearSelection}
                size="small"
                disabled={selectedCount === 0}
              >
                {t("review_queue.deselect_all")}
              </Button>
              <Button
                variant="contained"
                color="success"
                startIcon={<CheckCircleIcon />}
                onClick={() => openBatchReviewDialog("approve")}
                disabled={selectedCount === 0}
              >
                {t("review_queue.approve_selected")}
              </Button>
              <Button
                variant="contained"
                color="error"
                startIcon={<CancelIcon />}
                onClick={() => openBatchReviewDialog("reject")}
                disabled={selectedCount === 0}
              >
                {t("review_queue.reject_selected")}
              </Button>
            </Stack>
          </Stack>
        </Paper>

        <Paper sx={{ p: 2 }}>
          <Stack spacing={2}>
            <Typography variant="h6">
              {t("review_queue.items_title", "Queue items")}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {t(
                "review_queue.items_description",
                "Review staged extractions item by item, or use the batch tools above after selecting a set."
              )}
            </Typography>

            {isLoading && extractions.length === 0 ? (
              <Box sx={{ display: "flex", justifyContent: "center", p: 4 }}>
                <CircularProgress />
              </Box>
            ) : extractions.length === 0 ? (
              <Alert severity="info">
                <Typography variant="h6" color="text.secondary">
                  {t("review_queue.no_pending_title")}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {t("review_queue.no_pending_desc")}
                </Typography>
              </Alert>
            ) : (
              <List>
                {extractions.map((extraction) => (
                  <ExtractionCard
                    key={extraction.id}
                    extraction={extraction}
                    isSelected={selectedIds.has(extraction.id)}
                    onToggleSelect={() => toggleSelection(extraction.id)}
                    onApprove={() => handleSingleReview(extraction.id, "approve")}
                    onReject={() => handleSingleReview(extraction.id, "reject")}
                  />
                ))}
              </List>
            )}

            {hasMore && !isLoading && extractions.length > 0 && (
              <Box sx={{ display: "flex", justifyContent: "center" }}>
                <Button onClick={loadMore} variant="outlined">
                  {t("common.load_more")}
                </Button>
              </Box>
            )}
          </Stack>
        </Paper>
      </Stack>

      <Dialog open={reviewDialogOpen} onClose={closeReviewDialog}>
        <DialogTitle>
          {t("review_queue.dialog_title", {
            action:
              reviewDecision === "approve"
                ? t("review_queue.dialog_action_approve")
                : t("review_queue.dialog_action_reject"),
            count: selectedCount,
          })}
        </DialogTitle>
        <DialogContent>
          <TextField
            label={t("review_queue.review_notes")}
            multiline
            rows={4}
            fullWidth
            value={reviewNotes}
            onChange={(event) => setReviewNotes(event.target.value)}
            sx={{ mt: 2 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={closeReviewDialog}>{t("common.cancel")}</Button>
          <Button
            onClick={handleBatchReview}
            variant="contained"
            color={reviewDecision === "approve" ? "success" : "error"}
          >
            {t("review_queue.action_all", {
              action:
                reviewDecision === "approve"
                  ? t("review_queue.dialog_action_approve")
                  : t("review_queue.dialog_action_reject"),
            })}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
