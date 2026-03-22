import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useReviewQueue } from "../hooks/useReviewQueue";
import { useSelection } from "../hooks/useSelection";
import { useReviewDialog } from "../hooks/useReviewDialog";
import { ExtractionCard } from "../components/extraction/ExtractionCard";
import { LlmDraftsPanel } from "../components/review/LlmDraftsPanel";
import type { ExtractionType } from "../api/extractionReview";

import {
  Typography,
  List,
  Paper,
  Box,
  Button,
  Stack,
  CircularProgress,
  Card,
  CardContent,
  Grid,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  Tabs,
  Tab,
} from "@mui/material";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import CancelIcon from "@mui/icons-material/Cancel";
import WarningIcon from "@mui/icons-material/Warning";
import RefreshIcon from "@mui/icons-material/Refresh";
import SelectAllIcon from "@mui/icons-material/SelectAll";
import DeselectIcon from "@mui/icons-material/Deselect";

const PAGE_SIZE = 20;

export function ReviewQueueView() {
  const { t } = useTranslation();

  // Tab state: 0 = staged extractions, 1 = LLM drafts
  const [activeTab, setActiveTab] = useState(0);

  // Filters state (kept in component for TextField binding)
  const [minScore, setMinScore] = useState<number | undefined>(undefined);
  const [onlyFlagged, setOnlyFlagged] = useState(false);
  const [extractionType, setExtractionType] = useState<ExtractionType | undefined>(undefined);

  // Custom hooks
  const {
    extractions,
    stats,
    isLoading,
    hasMore,
    loadMore,
    refresh
  } = useReviewQueue({ pageSize: PAGE_SIZE, minScore, onlyFlagged, extractionType });

  const {
    selectedIds,
    toggleSelection,
    selectAll,
    clearSelection,
    selectedCount
  } = useSelection();

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

  // Handlers
  const handleRefresh = () => {
    clearSelection();
    refresh();
  };

  const handleSelectAll = () => {
    selectAll(extractions.map(e => e.id));
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

  return (
    <Box sx={{ p: 3 }}>
      <Stack spacing={3}>
        {/* Header */}
        <Stack direction="row" justifyContent="space-between" alignItems="center">
          <Typography variant="h4">{t("menu.review_queue")}</Typography>
          {activeTab === 0 && (
            <Button
              startIcon={<RefreshIcon />}
              onClick={handleRefresh}
              disabled={isLoading}
            >
              {t("review_queue.refresh")}
            </Button>
          )}
        </Stack>

        {/* Tabs */}
        <Tabs value={activeTab} onChange={(_e, v) => setActiveTab(v as number)}>
          <Tab label={t("review_queue.type_all")} />
          <Tab label={t("llm_drafts.tab_label")} />
        </Tabs>

        {/* LLM Drafts tab */}
        {activeTab === 1 && <LlmDraftsPanel />}

        {/* Staged Extractions tab content */}
        {activeTab === 0 && <>

        {/* Statistics Cards */}
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
                    {t("review_queue.pending_breakdown", { entities: stats.pending_entities, relations: stats.pending_relations })}
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
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        )}

        {/* Filters */}
        <Paper sx={{ p: 2 }}>
          <Stack spacing={2}>
            <Stack direction="row" spacing={2} alignItems="center">
              <TextField
                label={t("review_queue.min_score_label")}
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
                {t("review_queue.only_flagged")}
              </Button>
            </Stack>
            <ToggleButtonGroup
              value={extractionType ?? "all"}
              exclusive
              onChange={(_e, value) => setExtractionType(value === "all" ? undefined : value as ExtractionType)}
              size="small"
              aria-label={t("review_queue.type_filter_label")}
            >
              <ToggleButton value="all">{t("review_queue.type_all")}</ToggleButton>
              <ToggleButton value="entity">{t("review_queue.type_entity")}</ToggleButton>
              <ToggleButton value="relation">{t("review_queue.type_relation")}</ToggleButton>
              <ToggleButton value="claim">{t("review_queue.type_claim")}</ToggleButton>
            </ToggleButtonGroup>
          </Stack>
        </Paper>

        {/* Batch Actions */}
        {selectedCount > 0 && (
          <Paper sx={{ p: 2, bgcolor: "action.selected" }}>
            <Stack direction="row" spacing={2} alignItems="center">
              <Typography>
                {t("review_queue.selected_count", { count: selectedCount })}
              </Typography>
              <Button
                variant="contained"
                color="success"
                startIcon={<CheckCircleIcon />}
                onClick={() => openBatchReviewDialog("approve")}
              >
                {t("review_queue.approve_selected")}
              </Button>
              <Button
                variant="contained"
                color="error"
                startIcon={<CancelIcon />}
                onClick={() => openBatchReviewDialog("reject")}
              >
                {t("review_queue.reject_selected")}
              </Button>
              <Button
                startIcon={<DeselectIcon />}
                onClick={clearSelection}
              >
                {t("review_queue.deselect_all")}
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
              {t("review_queue.select_all")}
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
              {t("review_queue.no_pending_title")}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {t("review_queue.no_pending_desc")}
            </Typography>
          </Paper>
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

        {/* Load More */}
        {hasMore && !isLoading && extractions.length > 0 && (
          <Box sx={{ display: "flex", justifyContent: "center" }}>
            <Button onClick={loadMore} variant="outlined">
              {t("common.load_more")}
            </Button>
          </Box>
        )}

        </>}
      </Stack>

      {/* Batch Review Dialog */}
      <Dialog open={reviewDialogOpen} onClose={closeReviewDialog}>
        <DialogTitle>
          {t("review_queue.dialog_title", {
            action: reviewDecision === "approve" ? t("review_queue.dialog_action_approve") : t("review_queue.dialog_action_reject"),
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
            onChange={(e) => setReviewNotes(e.target.value)}
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
              action: reviewDecision === "approve" ? t("review_queue.dialog_action_approve") : t("review_queue.dialog_action_reject"),
            })}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
