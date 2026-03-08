import { useState } from "react";
import { Link as RouterLink } from "react-router-dom";
import { useReviewQueue } from "../hooks/useReviewQueue";
import { useSelection } from "../hooks/useSelection";
import { useReviewDialog } from "../hooks/useReviewDialog";

import {
  Typography,
  List,
  ListItem,
  ListItemText,
  Paper,
  Box,
  Button,
  Stack,
  CircularProgress,
  Chip,
  Card,
  CardContent,
  Grid,
  Checkbox,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
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

  // Filters state (kept in component for TextField binding)
  const [minScore, setMinScore] = useState<number | undefined>(undefined);
  const [onlyFlagged, setOnlyFlagged] = useState(false);

  // Custom hooks
  const {
    extractions,
    stats,
    isLoading,
    hasMore,
    loadMore,
    refresh
  } = useReviewQueue({ pageSize: PAGE_SIZE, minScore, onlyFlagged });

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
    setReviewDecision(decision);
    await submitReview(extractionId, handleRefresh);
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
        {selectedCount > 0 && (
          <Paper sx={{ p: 2, bgcolor: "action.selected" }}>
            <Stack direction="row" spacing={2} alignItems="center">
              <Typography>
                {selectedCount} selected
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
                onClick={clearSelection}
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
                    onChange={() => toggleSelection(extraction.id)}
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
            <Button onClick={loadMore} variant="outlined">
              Load More
            </Button>
          </Box>
        )}
      </Stack>

      {/* Batch Review Dialog */}
      <Dialog open={reviewDialogOpen} onClose={closeReviewDialog}>
        <DialogTitle>
          {reviewDecision === "approve" ? "Approve" : "Reject"} {selectedCount} Extractions
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
          <Button onClick={closeReviewDialog}>Cancel</Button>
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
