import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { listEntities } from "../api/entities";
import { listSources } from "../api/sources";

import {
  Typography,
  Box,
  Stack,
  Paper,
  Button,
  Grid,
  Card,
  CardContent,
  CardActions,
  CircularProgress,
  Alert,
} from "@mui/material";
import StorageIcon from "@mui/icons-material/Storage";
import SourceIcon from "@mui/icons-material/Source";
import AccountTreeIcon from "@mui/icons-material/AccountTree";
import PsychologyIcon from "@mui/icons-material/Psychology";
import AddIcon from "@mui/icons-material/Add";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import RateReviewIcon from "@mui/icons-material/RateReview";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";
import { siteDisplayName } from "../config/site";

interface Stats {
  entities: number;
  sources: number;
  isLoading: boolean;
  error: string | null;
}

function StatCard({
  title,
  count,
  icon,
  color,
  actionLabel,
  onAction,
  viewLabel,
  onView,
}: {
  title: string;
  count: number | null;
  icon: React.ReactNode;
  color: string;
  actionLabel: string;
  onAction: () => void;
  viewLabel: string;
  onView: () => void;
}) {
  return (
    <Card variant="outlined" sx={{ height: "100%" }}>
      <CardContent>
        <Stack direction="row" spacing={2} alignItems="center" mb={2}>
          <Box
            sx={{
              bgcolor: `${color}.light`,
              color: `${color}.dark`,
              p: 1.5,
              borderRadius: 2,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            {icon}
          </Box>
          <Box flex={1}>
            <Typography variant="body2" color="text.secondary">
              {title}
            </Typography>
            <Typography variant="h4" fontWeight="bold">
              {count !== null ? count.toLocaleString() : "—"}
            </Typography>
          </Box>
        </Stack>
      </CardContent>
      <CardActions sx={{ justifyContent: "space-between", px: 2, pb: 2 }}>
        <Button
          size="small"
          startIcon={<AddIcon />}
          onClick={onAction}
          variant="contained"
          sx={{ bgcolor: color }}
        >
          {actionLabel}
        </Button>
        <Button size="small" endIcon={<ArrowForwardIcon />} onClick={onView}>
          {viewLabel}
        </Button>
      </CardActions>
    </Card>
  );
}

export function HomeView() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const emptyGraphMessage = t(
    "home.empty_graph",
    "No data yet. Create entities and relationships to start building the graph.",
  );
  const [stats, setStats] = useState<Stats>({
    entities: 0,
    sources: 0,
    isLoading: true,
    error: null,
  });

  useEffect(() => {
    async function fetchStats() {
      try {
        // Fetch counts from paginated endpoints (limit=1 to minimize data transfer)
        const [entitiesResponse, sourcesResponse] = await Promise.all([
          listEntities({ limit: 1, offset: 0 }),
          listSources({ limit: 1, offset: 0 }),
        ]);

        setStats({
          entities: entitiesResponse.total,
          sources: sourcesResponse.total,
          isLoading: false,
          error: null,
        });
      } catch (error) {
        setStats({
          entities: 0,
          sources: 0,
          isLoading: false,
          error: emptyGraphMessage,
        });
      }
    }

    fetchStats();
  }, [emptyGraphMessage]);

  const isEmptyGraph =
    !stats.isLoading &&
    !stats.error &&
    stats.entities === 0 &&
    stats.sources === 0;

  return (
    <Box sx={{ maxWidth: 1200, mx: "auto", p: 3 }}>
      {/* Hero Section */}
      <Paper
        sx={{
          background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
          color: "white",
          p: 4,
          mb: 4,
          borderRadius: 2,
        }}
      >
        <Stack spacing={2}>
          <Typography variant="h3" fontWeight="bold">
            {t("home.title", {
              brand: siteDisplayName,
              defaultValue: siteDisplayName,
            })}
          </Typography>
          <Typography variant="h6" sx={{ opacity: 0.9 }}>
            {t(
              "home.subtitle",
              "Review evidence, spot disagreement, and trace every conclusion back to its source"
            )}
          </Typography>
          <Typography variant="body1" sx={{ opacity: 0.85, maxWidth: 700 }}>
            {t(
              "home.description",
              {
                brand: siteDisplayName,
                defaultValue:
                  "Start from the evidence itself. Compare supporting and contradicting statements, inspect source quality, and keep provenance visible while you decide what the graph should say.",
              }
            )}
          </Typography>
          <Stack direction={{ xs: "column", sm: "row" }} spacing={1} pt={1}>
            <Button
              variant="contained"
              color="inherit"
              sx={{ color: "primary.main", bgcolor: "white" }}
              onClick={() => navigate("/review-queue")}
            >
              {t("home.cta_review_evidence", "Review new evidence")}
            </Button>
            <Button
              variant="outlined"
              color="inherit"
              sx={{ borderColor: "rgba(255,255,255,0.6)", color: "white" }}
              onClick={() => navigate("/inferences")}
            >
              {t("home.cta_explore_evidence", "Explore evidence")}
            </Button>
            <Button
              variant="outlined"
              color="inherit"
              sx={{ borderColor: "rgba(255,255,255,0.6)", color: "white" }}
              onClick={() => navigate("/search")}
            >
              {t("home.cta_search", "Search the knowledge base")}
            </Button>
          </Stack>
        </Stack>
      </Paper>

      {/* Error Alert */}
      {stats.error && (
        <Alert severity="warning" sx={{ mb: 3 }}>
          {stats.error}
        </Alert>
      )}

      {isEmptyGraph && (
        <Alert severity="info" sx={{ mb: 3 }}>
          {emptyGraphMessage}
        </Alert>
      )}

      {/* Statistics Cards */}
      {stats.isLoading ? (
        <Box sx={{ display: "flex", justifyContent: "center", my: 8 }}>
          <CircularProgress />
        </Box>
      ) : (
        <>
          {/* Data metrics */}
          <Typography variant="h6" color="text.secondary" mb={2}>
            {t("home.data_heading", "Data")}
          </Typography>
          <Grid container spacing={3} mb={4}>
            <Grid size={{ xs: 12, sm: 6 }}>
              <StatCard
                title={t("home.entities", "Entities")}
                count={stats.entities}
                icon={<StorageIcon fontSize="large" />}
                color="primary"
                actionLabel={t("home.createEntity", "Create")}
                onAction={() => navigate("/entities/new")}
                viewLabel={t("home.viewAll", "View All")}
                onView={() => navigate("/entities")}
              />
            </Grid>
            <Grid size={{ xs: 12, sm: 6 }}>
              <StatCard
                title={t("home.sources", "Sources")}
                count={stats.sources}
                icon={<SourceIcon fontSize="large" />}
                color="success"
                actionLabel={t("home.createSource", "Create")}
                onAction={() => navigate("/sources/new")}
                viewLabel={t("home.viewAll", "View All")}
                onView={() => navigate("/sources")}
              />
            </Grid>
          </Grid>

          {/* Analysis shortcuts */}
          <Typography variant="h6" color="text.secondary" mb={2}>
            {t("home.analysis_heading", "Analysis tasks")}
          </Typography>
          <Grid container spacing={3} mb={4}>
            <Grid size={{ xs: 12, sm: 6 }}>
              <Card variant="outlined" sx={{ height: "100%" }}>
                <CardContent>
                  <Stack direction="row" spacing={2} alignItems="flex-start">
                    <Box
                      sx={{
                        bgcolor: "secondary.light",
                        color: "secondary.dark",
                        p: 1.5,
                        borderRadius: 2,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        flexShrink: 0,
                      }}
                    >
                      <PsychologyIcon fontSize="large" />
                    </Box>
                    <Box>
                      <Typography variant="subtitle1" fontWeight="bold">
                        {t("home.inferences", "Inferences")}
                      </Typography>
                      <Typography variant="body2" color="text.secondary" mt={0.5}>
                        {t(
                          "home.inferencesDesc",
                          "Review aggregated evidence per entity. See confidence levels, contradictions, and source quality at a glance."
                        )}
                      </Typography>
                    </Box>
                  </Stack>
                </CardContent>
                <CardActions sx={{ justifyContent: "flex-end", px: 2, pb: 2 }}>
                  <Button
                    size="small"
                    endIcon={<ArrowForwardIcon />}
                    onClick={() => navigate("/inferences")}
                  >
                    {t("home.exploreInferences", "Explore inferences")}
                  </Button>
                </CardActions>
              </Card>
            </Grid>
            <Grid size={{ xs: 12, sm: 6 }}>
              <Card variant="outlined" sx={{ height: "100%" }}>
                <CardContent>
                  <Stack direction="row" spacing={2} alignItems="flex-start">
                    <Box
                      sx={{
                        bgcolor: "warning.light",
                        color: "warning.dark",
                        p: 1.5,
                        borderRadius: 2,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        flexShrink: 0,
                      }}
                    >
                      <AccountTreeIcon fontSize="large" />
                    </Box>
                    <Box>
                      <Typography variant="subtitle1" fontWeight="bold">
                        {t("home.relations", "Relations")}
                      </Typography>
                      <Typography variant="body2" color="text.secondary" mt={0.5}>
                        {t(
                          "home.relationsDesc",
                          "Inspect source-grounded claims linking entities. Follow evidence trails from relation to original document."
                        )}
                      </Typography>
                    </Box>
                  </Stack>
                </CardContent>
                <CardActions sx={{ justifyContent: "flex-end", px: 2, pb: 2 }}>
                  <Button
                    size="small"
                    endIcon={<ArrowForwardIcon />}
                    onClick={() => navigate("/sources")}
                  >
                    {t("home.browseSources", "Browse by source")}
                  </Button>
                </CardActions>
              </Card>
            </Grid>
          </Grid>

          <Typography variant="h6" color="text.secondary" mb={2}>
            {t("home.review_heading", "Next review steps")}
          </Typography>
          <Grid container spacing={3} mb={4}>
            <Grid size={{ xs: 12, sm: 6 }}>
              <Card variant="outlined" sx={{ height: "100%" }}>
                <CardContent>
                  <Stack direction="row" spacing={2} alignItems="flex-start">
                    <Box
                      sx={{
                        bgcolor: "info.light",
                        color: "info.dark",
                        p: 1.5,
                        borderRadius: 2,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        flexShrink: 0,
                      }}
                    >
                      <RateReviewIcon fontSize="large" />
                    </Box>
                    <Box>
                      <Typography variant="subtitle1" fontWeight="bold">
                        {t("home.review_queue", "Review queue")}
                      </Typography>
                      <Typography variant="body2" color="text.secondary" mt={0.5}>
                        {t(
                          "home.review_queue_desc",
                          "Triage newly extracted entities, relations, and claims before they change the visible graph."
                        )}
                      </Typography>
                    </Box>
                  </Stack>
                </CardContent>
                <CardActions sx={{ justifyContent: "flex-end", px: 2, pb: 2 }}>
                  <Button size="small" endIcon={<ArrowForwardIcon />} onClick={() => navigate("/review-queue")}>
                    {t("home.open_review_queue", "Open review queue")}
                  </Button>
                </CardActions>
              </Card>
            </Grid>
            <Grid size={{ xs: 12, sm: 6 }}>
              <Card variant="outlined" sx={{ height: "100%" }}>
                <CardContent>
                  <Stack direction="row" spacing={2} alignItems="flex-start">
                    <Box
                      sx={{
                        bgcolor: "error.light",
                        color: "error.dark",
                        p: 1.5,
                        borderRadius: 2,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        flexShrink: 0,
                      }}
                    >
                      <WarningAmberIcon fontSize="large" />
                    </Box>
                    <Box>
                      <Typography variant="subtitle1" fontWeight="bold">
                        {t("home.inspect_disagreements", "Inspect disagreements")}
                      </Typography>
                      <Typography variant="body2" color="text.secondary" mt={0.5}>
                        {t(
                          "home.inspect_disagreements_desc",
                          "Follow where sources diverge so contradiction stays visible instead of being averaged away."
                        )}
                      </Typography>
                    </Box>
                  </Stack>
                </CardContent>
                <CardActions sx={{ justifyContent: "flex-end", px: 2, pb: 2 }}>
                  <Button size="small" endIcon={<ArrowForwardIcon />} onClick={() => navigate("/inferences")}>
                    {t("home.open_disagreements", "Open disagreement views")}
                  </Button>
                </CardActions>
              </Card>
            </Grid>
          </Grid>

          {/* Evidence workflow guide */}
          <Paper variant="outlined" sx={{ p: 3 }}>
            <Typography variant="h6" fontWeight="bold" mb={2}>
              {t("home.workflowTitle", "Evidence analysis workflow")}
            </Typography>
            <Stack spacing={2}>
              <Box>
                <Typography variant="subtitle2" fontWeight="bold" gutterBottom>
                  {t("home.step1Title", "1. Review extracted evidence")}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {t(
                    "home.step1Desc",
                    "Check the review queue for newly extracted relations. Approve, reject, or flag each claim before it affects inferences."
                  )}
                </Typography>
              </Box>
              <Box>
                <Typography variant="subtitle2" fontWeight="bold" gutterBottom>
                  {t("home.step2Title", "2. Inspect disagreements")}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {t(
                    "home.step2Desc",
                    "Navigate to any entity's disagreement view to see where sources conflict. Contradictions are preserved — not resolved — so you can assess them directly."
                  )}
                </Typography>
              </Box>
              <Box>
                <Typography variant="subtitle2" fontWeight="bold" gutterBottom>
                  {t("home.step3Title", "3. Trace claims to their source")}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {t(
                    "home.step3Desc",
                    "Open any inference explanation to see which publications contributed, their confidence weights, and the exact passage or relation each came from."
                  )}
                </Typography>
              </Box>
              <Box>
                <Typography variant="subtitle2" fontWeight="bold" gutterBottom>
                  {t("home.step4Title", "4. Add or import new sources")}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {t(
                    "home.step4Desc",
                    "Extend coverage by adding publications via URL, PubMed ID, or bulk import. New sources trigger automatic relation extraction for review."
                  )}
                </Typography>
              </Box>
            </Stack>
          </Paper>
        </>
      )}
    </Box>
  );
}
