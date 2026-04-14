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


function getDraftTitle(item: DraftRevisionRead): string {
  return item.slug ?? item.title ?? item.kind ?? item.id;
}


function getDraftSummary(item: DraftRevisionRead, t: (key: string, options?: Record<string, unknown>) => string): string {
  switch (item.revision_kind) {
    case "entity":
      return t("llm_drafts.summary_entity", {
        slug: item.slug ?? item.id,
      });
    case "relation":
      return t("llm_drafts.summary_relation", {
        kind: item.kind ?? t("llm_drafts.kind_unknown"),
      });
    case "source":
      return t("llm_drafts.summary_source", {
        title: item.title ?? item.id,
      });
    default:
      return item.id;
  }
}


function getDraftDateLabel(item: DraftRevisionRead): string {
  return new Date(item.created_at).toLocaleDateString();
}


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
        <Stack divider={<Divider flexItem />}>
          {items.map((item) => (
            <Box
              key={item.id}
              sx={{
                px: { xs: 2, sm: 3 },
                py: 2,
              }}
            >
              <Stack spacing={1.5}>
                <Stack
                  direction={{ xs: "column", sm: "row" }}
                  spacing={1.5}
                  justifyContent="space-between"
                  alignItems={{ xs: "flex-start", sm: "flex-start" }}
                >
                  <Stack spacing={0.75} sx={{ minWidth: 0, flex: 1 }}>
                    <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap">
                      <Chip
                        label={t(`llm_drafts.kind_${item.revision_kind}`)}
                        size="small"
                        color={KIND_COLORS[item.revision_kind] ?? "default"}
                      />
                      <Chip
                        label={item.llm_review_status ?? t("review_queue.pending_review")}
                        size="small"
                        variant="outlined"
                        color="warning"
                      />
                    </Stack>
                    <Typography variant="subtitle1" sx={{ wordBreak: "break-word" }}>
                      {getDraftTitle(item)}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {getDraftSummary(item, t)}
                    </Typography>
                  </Stack>

                  <Stack
                    direction={{ xs: "column", sm: "row" }}
                    spacing={1}
                    sx={{ width: { xs: "100%", sm: "auto" } }}
                  >
                    <Button
                      size="small"
                      variant="contained"
                      color="success"
                      startIcon={<CheckCircleIcon />}
                      fullWidth
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
                      fullWidth
                      disabled={actionInFlight === item.id}
                      onClick={() => void handleDiscard(item)}
                    >
                      {t("llm_drafts.discard")}
                    </Button>
                  </Stack>
                </Stack>

                <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap">
                  <Chip
                    label={t("llm_drafts.meta_model", {
                      model: item.created_with_llm ?? "LLM",
                    })}
                    size="small"
                    variant="outlined"
                  />
                  <Chip
                    label={t("llm_drafts.meta_date", {
                      date: getDraftDateLabel(item),
                    })}
                    size="small"
                    variant="outlined"
                  />
                  <Chip
                    label={t("llm_drafts.meta_id", {
                      id: item.id,
                    })}
                    size="small"
                    variant="outlined"
                    sx={{ maxWidth: "100%" }}
                  />
                </Stack>
              </Stack>
            </Box>
          ))}
        </Stack>
      </Paper>
    </Stack>
  );
}
