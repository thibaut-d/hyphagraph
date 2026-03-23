/**
 * Panel for reviewing LLM-generated draft revisions.
 *
 * Shows entity/relation/source revisions with status='draft' and lets humans
 * confirm (make authoritative) or discard (delete) each one.
 */
import { useState, useEffect, useCallback } from "react";
import { useTranslation } from "react-i18next";
import {
  Box,
  Typography,
  Stack,
  Paper,
  Chip,
  Button,
  CircularProgress,
  List,
  ListItem,
  ListItemText,
  Divider,
} from "@mui/material";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import DeleteIcon from "@mui/icons-material/Delete";
import {
  listDraftRevisions,
  getDraftRevisionCounts,
  confirmRevision,
  discardRevision,
  type DraftRevisionRead,
  type DraftRevisionCounts,
} from "../../api/revisionReview";
import { useNotification } from "../../notifications/NotificationContext";


const PAGE_SIZE = 50;

const KIND_COLORS: Record<string, "primary" | "secondary" | "warning"> = {
  entity: "primary",
  relation: "secondary",
  source: "warning",
};


export function LlmDraftsPanel() {
  const { t } = useTranslation();
  const { showSuccess, showError } = useNotification();

  const [items, setItems] = useState<DraftRevisionRead[]>([]);
  const [counts, setCounts] = useState<DraftRevisionCounts | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [actionInFlight, setActionInFlight] = useState<string | null>(null);

  const load = useCallback(async () => {
    setIsLoading(true);
    try {
      const [listResp, countsResp] = await Promise.all([
        listDraftRevisions({ page_size: PAGE_SIZE }),
        getDraftRevisionCounts(),
      ]);
      setItems(listResp.items);
      setCounts(countsResp);
    } catch (err) {
      showError(err);
    } finally {
      setIsLoading(false);
    }
  }, [showError]);

  // Background refresh after an action: no loading spinner, failure shown separately
  const silentRefresh = useCallback(async () => {
    try {
      const [listResp, countsResp] = await Promise.all([
        listDraftRevisions({ page_size: PAGE_SIZE }),
        getDraftRevisionCounts(),
      ]);
      setItems(listResp.items);
      setCounts(countsResp);
    } catch {
      showError(t("llm_drafts.refresh_failed", "List refresh failed — reload to see latest drafts"));
    }
  }, [showError, t]);

  useEffect(() => {
    void load();
  }, [load]);

  const handleConfirm = async (item: DraftRevisionRead) => {
    setActionInFlight(item.id);
    try {
      await confirmRevision(item.revision_kind, item.id);
      setItems((prev) => prev.filter((i) => i.id !== item.id));
      showSuccess(t("llm_drafts.confirmed_success"));
      void silentRefresh();
    } catch (err) {
      showError(err);
    } finally {
      setActionInFlight(null);
    }
  };

  const handleDiscard = async (item: DraftRevisionRead) => {
    setActionInFlight(item.id);
    try {
      await discardRevision(item.revision_kind, item.id);
      setItems((prev) => prev.filter((i) => i.id !== item.id));
      showSuccess(t("llm_drafts.discarded_success"));
      void silentRefresh();
    } catch (err) {
      showError(err);
    } finally {
      setActionInFlight(null);
    }
  };

  if (isLoading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", p: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (items.length === 0) {
    return (
      <Paper sx={{ p: 4, textAlign: "center" }}>
        <Typography variant="h6" color="text.secondary">
          {t("llm_drafts.no_drafts_title")}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          {t("llm_drafts.no_drafts_desc")}
        </Typography>
      </Paper>
    );
  }

  return (
    <Stack spacing={2}>
      {counts && (
        <Typography variant="body2" color="text.secondary">
          {t("llm_drafts.counts_label", {
            total: counts.total,
            entity: counts.entity,
            relation: counts.relation,
            source: counts.source,
          })}
        </Typography>
      )}

      <Paper>
        <List disablePadding>
          {items.map((item, idx) => (
            <Box key={item.id}>
              {idx > 0 && <Divider />}
              <ListItem
                secondaryAction={
                  <Stack direction="row" spacing={1}>
                    <Button
                      size="small"
                      variant="contained"
                      color="success"
                      startIcon={<CheckCircleIcon />}
                      disabled={actionInFlight === item.id}
                      onClick={() => void handleConfirm(item)}
                    >
                      {t("llm_drafts.confirm")}
                    </Button>
                    <Button
                      size="small"
                      variant="outlined"
                      color="error"
                      startIcon={<DeleteIcon />}
                      disabled={actionInFlight === item.id}
                      onClick={() => void handleDiscard(item)}
                    >
                      {t("llm_drafts.discard")}
                    </Button>
                  </Stack>
                }
              >
                <ListItemText
                  primary={
                    <Stack direction="row" spacing={1} alignItems="center">
                      <Chip
                        label={t(`llm_drafts.kind_${item.revision_kind}`)}
                        size="small"
                        color={KIND_COLORS[item.revision_kind] ?? "default"}
                      />
                      <Typography variant="body1">
                        {item.slug ?? item.title ?? item.kind ?? item.id}
                      </Typography>
                    </Stack>
                  }
                  secondary={
                    <Typography variant="caption" color="text.secondary">
                      {item.created_with_llm ?? "LLM"} &middot;{" "}
                      {new Date(item.created_at).toLocaleDateString()}
                    </Typography>
                  }
                />
              </ListItem>
            </Box>
          ))}
        </List>
      </Paper>
    </Stack>
  );
}
