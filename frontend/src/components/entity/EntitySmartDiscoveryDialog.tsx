import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
  LinearProgress,
  Slider,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import AutoAwesomeIcon from "@mui/icons-material/AutoAwesome";
import CloseIcon from "@mui/icons-material/Close";

import { useEntitySmartDiscovery } from "../../hooks/useEntitySmartDiscovery";

interface EntitySmartDiscoveryDialogProps {
  open: boolean;
  onClose: () => void;
  onCreated: () => void;
}

const COUNT_MARKS = [
  { value: 1, label: "1" },
  { value: 10, label: "10" },
  { value: 25, label: "25" },
  { value: 50, label: "50" },
];

export function EntitySmartDiscoveryDialog({
  open,
  onClose,
  onCreated,
}: EntitySmartDiscoveryDialogProps) {
  const { t } = useTranslation();

  const {
    phase,
    query,
    setQuery,
    count,
    setCount,
    suggesting,
    suggestError,
    terms,
    newTerm,
    setNewTerm,
    handleSuggest,
    handleAddTerm,
    handleRemoveTerm,
    handleBack,
    handleSmartCreate,
    doneCount,
    totalCount,
    createdCount,
    failedTerms,
    reset,
  } = useEntitySmartDiscovery();

  // Reset state when dialog opens
  useEffect(() => {
    if (open) reset();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const handleClose = () => {
    if (phase === "done" && createdCount > 0) {
      onCreated();
    }
    onClose();
  };

  const handleAddTermKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleAddTerm();
    }
  };

  const progress = totalCount > 0 ? Math.round((doneCount / totalCount) * 100) : 0;

  return (
    <Dialog open={open} onClose={handleClose} fullWidth maxWidth="sm">
      <DialogTitle
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 1,
          pr: 1,
        }}
      >
        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          <AutoAwesomeIcon fontSize="small" color="primary" />
          <span>
            {phase === "review"
              ? t(
                  "entity_smart_discover.review_title",
                  "Review suggested entities ({{count}})",
                  { count: terms.length }
                )
              : t("entity_smart_discover.dialog_title", "Smart Discover Entities")}
          </span>
        </Box>
        <IconButton size="small" onClick={handleClose} aria-label={t("common.close", "Close")}>
          <CloseIcon fontSize="small" />
        </IconButton>
      </DialogTitle>

      <DialogContent dividers>
        {/* ── Configure phase ── */}
        {phase === "configure" && (
          <Stack spacing={3}>
            <Typography variant="body2" color="text.secondary">
              {t(
                "entity_smart_discover.dialog_description",
                "Describe a topic and the AI will propose a list of relevant entity names for you to review before creating them."
              )}
            </Typography>

            <TextField
              label={t("entity_smart_discover.query_label", "Topic or area of interest")}
              placeholder={t(
                "entity_smart_discover.query_placeholder",
                "e.g. widespread chronic pain medication"
              )}
              helperText={t(
                "entity_smart_discover.query_help",
                "Describe the domain, condition, or substance area to explore."
              )}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSuggest();
                }
              }}
              multiline
              rows={2}
              fullWidth
              disabled={suggesting}
            />

            <Box>
              <Typography variant="body2" gutterBottom>
                {t("entity_smart_discover.count_label", "Number of entities: {{count}}", {
                  count,
                })}
              </Typography>
              <Slider
                value={count}
                onChange={(_, value) => setCount(value as number)}
                min={1}
                max={50}
                step={1}
                marks={COUNT_MARKS}
                valueLabelDisplay="auto"
                disabled={suggesting}
                sx={{ mt: 1 }}
              />
            </Box>

            {suggestError && <Alert severity="error">{suggestError}</Alert>}
          </Stack>
        )}

        {/* ── Review phase ── */}
        {phase === "review" && (
          <Stack spacing={3}>
            <Typography variant="body2" color="text.secondary">
              {t(
                "entity_smart_discover.review_description",
                "Add or remove entities from the list. Each will be created using AI prefill."
              )}
            </Typography>

            {terms.length === 0 ? (
              <Alert severity="warning">
                {t(
                  "entity_smart_discover.empty_list_warning",
                  "No entities in the list. Add some terms to continue."
                )}
              </Alert>
            ) : (
              <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1 }}>
                {terms.map((term) => (
                  <Chip
                    key={term}
                    label={term}
                    onDelete={() => handleRemoveTerm(term)}
                    color="primary"
                    variant="outlined"
                  />
                ))}
              </Box>
            )}

            <Stack direction="row" spacing={1}>
              <TextField
                label={t("entity_smart_discover.add_term_label", "Add entity name")}
                value={newTerm}
                onChange={(e) => setNewTerm(e.target.value)}
                onKeyDown={handleAddTermKeyDown}
                size="small"
                fullWidth
              />
              <Button
                variant="outlined"
                onClick={handleAddTerm}
                disabled={!newTerm.trim()}
                startIcon={<AddIcon />}
                sx={{ flexShrink: 0 }}
              >
                {t("entity_smart_discover.add_term_button", "Add")}
              </Button>
            </Stack>
          </Stack>
        )}

        {/* ── Creating phase ── */}
        {phase === "creating" && (
          <Stack spacing={2} alignItems="center" sx={{ py: 2 }}>
            <CircularProgress />
            <Typography variant="body1">
              {t("entity_smart_discover.creating", "Creating {{done}} / {{total}}...", {
                done: doneCount,
                total: totalCount,
              })}
            </Typography>
            <Box sx={{ width: "100%" }}>
              <LinearProgress variant="determinate" value={progress} />
            </Box>
          </Stack>
        )}

        {/* ── Done phase ── */}
        {phase === "done" && (
          <Stack spacing={2}>
            <Alert severity={createdCount > 0 ? "success" : "warning"}>
              {t("entity_smart_discover.done_created", "Created {{count}} entities", {
                count: createdCount,
              })}
            </Alert>
            {failedTerms.length > 0 && (
              <Alert severity="error">
                {t(
                  "entity_smart_discover.done_failed",
                  "{{count}} failed: {{terms}}",
                  {
                    count: failedTerms.length,
                    terms: failedTerms.join(", "),
                  }
                )}
              </Alert>
            )}
          </Stack>
        )}
      </DialogContent>

      <DialogActions sx={{ px: 3, py: 2 }}>
        {phase === "configure" && (
          <>
            <Button onClick={handleClose} disabled={suggesting}>
              {t("common.cancel", "Cancel")}
            </Button>
            <Button
              variant="contained"
              onClick={handleSuggest}
              disabled={suggesting || !query.trim()}
              startIcon={
                suggesting ? (
                  <CircularProgress size={16} color="inherit" />
                ) : (
                  <AutoAwesomeIcon fontSize="small" />
                )
              }
            >
              {suggesting
                ? t("entity_smart_discover.discovering", "Discovering...")
                : t("entity_smart_discover.discover_button", "Discover")}
            </Button>
          </>
        )}

        {phase === "review" && (
          <>
            <Button onClick={handleBack}>
              {t("entity_smart_discover.back_button", "Back")}
            </Button>
            <Button
              variant="contained"
              onClick={handleSmartCreate}
              disabled={terms.length === 0}
              startIcon={<AutoAwesomeIcon fontSize="small" />}
            >
              {t("entity_smart_discover.create_button", "Smart Create ({{count}})", {
                count: terms.length,
              })}
            </Button>
          </>
        )}

        {phase === "creating" && (
          <Button disabled>
            {t("entity_smart_discover.creating", "Creating {{done}} / {{total}}...", {
              done: doneCount,
              total: totalCount,
            })}
          </Button>
        )}

        {phase === "done" && (
          <Button variant="contained" onClick={handleClose}>
            {t("common.close", "Close")}
          </Button>
        )}
      </DialogActions>
    </Dialog>
  );
}
