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
          error: "Failed to load statistics",
        });
      }
    }

    fetchStats();
  }, []);

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
            {t("home.title", "HyphaGraph")}
          </Typography>
          <Typography variant="h6" sx={{ opacity: 0.9 }}>
            {t(
              "home.subtitle",
              "Hypergraph-based Evidence Knowledge System"
            )}
          </Typography>
          <Typography variant="body1" sx={{ opacity: 0.85, maxWidth: 700 }}>
            {t(
              "home.description",
              "Build and explore a knowledge graph with computed inferences. Track entities, sources, and relations with confidence scores and evidence aggregation."
            )}
          </Typography>
        </Stack>
      </Paper>

      {/* Error Alert */}
      {stats.error && (
        <Alert severity="warning" sx={{ mb: 3 }}>
          {stats.error}
        </Alert>
      )}

      {/* Statistics Cards */}
      {stats.isLoading ? (
        <Box sx={{ display: "flex", justifyContent: "center", my: 8 }}>
          <CircularProgress />
        </Box>
      ) : (
        <>
          <Typography variant="h5" fontWeight="bold" mb={3}>
            {t("home.overview", "Knowledge Graph Overview")}
          </Typography>

          <Grid container spacing={3} mb={4}>
            {/* Entities */}
            <Grid item xs={12} sm={6} md={3}>
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

            {/* Sources */}
            <Grid item xs={12} sm={6} md={3}>
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

            {/* Relations */}
            <Grid item xs={12} sm={6} md={3}>
              <Card variant="outlined" sx={{ height: "100%" }}>
                <CardContent>
                  <Stack direction="row" spacing={2} alignItems="center" mb={2}>
                    <Box
                      sx={{
                        bgcolor: "warning.light",
                        color: "warning.dark",
                        p: 1.5,
                        borderRadius: 2,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                      }}
                    >
                      <AccountTreeIcon fontSize="large" />
                    </Box>
                    <Box flex={1}>
                      <Typography variant="body2" color="text.secondary">
                        {t("home.relations", "Relations")}
                      </Typography>
                      <Typography variant="body1" color="text.secondary" mt={1}>
                        {t(
                          "home.relationsDesc",
                          "Organized by source"
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
                    {t("home.browseSources", "Browse Sources")}
                  </Button>
                </CardActions>
              </Card>
            </Grid>

            {/* Inferences */}
            <Grid item xs={12} sm={6} md={3}>
              <Card variant="outlined" sx={{ height: "100%" }}>
                <CardContent>
                  <Stack direction="row" spacing={2} alignItems="center" mb={2}>
                    <Box
                      sx={{
                        bgcolor: "secondary.light",
                        color: "secondary.dark",
                        p: 1.5,
                        borderRadius: 2,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                      }}
                    >
                      <PsychologyIcon fontSize="large" />
                    </Box>
                    <Box flex={1}>
                      <Typography variant="body2" color="text.secondary">
                        {t("home.inferences", "Inferences")}
                      </Typography>
                      <Typography variant="body1" color="text.secondary" mt={1}>
                        {t(
                          "home.inferencesDesc",
                          "Computed insights"
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
                    {t("home.exploreInferences", "Explore")}
                  </Button>
                </CardActions>
              </Card>
            </Grid>
          </Grid>

          {/* Quick Start Guide */}
          <Paper variant="outlined" sx={{ p: 3 }}>
            <Typography variant="h6" fontWeight="bold" mb={2}>
              {t("home.quickStart", "Quick Start Guide")}
            </Typography>
            <Stack spacing={2}>
              <Box>
                <Typography variant="subtitle2" fontWeight="bold" gutterBottom>
                  {t("home.step1Title", "1. Create Sources")}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {t(
                    "home.step1Desc",
                    "Add research papers, articles, or datasets as evidence sources."
                  )}
                </Typography>
              </Box>
              <Box>
                <Typography variant="subtitle2" fontWeight="bold" gutterBottom>
                  {t("home.step2Title", "2. Define Entities")}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {t(
                    "home.step2Desc",
                    "Create entities representing concepts, drugs, conditions, or any domain objects."
                  )}
                </Typography>
              </Box>
              <Box>
                <Typography variant="subtitle2" fontWeight="bold" gutterBottom>
                  {t("home.step3Title", "3. Add Relations")}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {t(
                    "home.step3Desc",
                    "Connect entities through relations from your sources, specifying roles and confidence."
                  )}
                </Typography>
              </Box>
              <Box>
                <Typography variant="subtitle2" fontWeight="bold" gutterBottom>
                  {t("home.step4Title", "4. Explore Inferences")}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {t(
                    "home.step4Desc",
                    "View computed role inferences with aggregated scores, confidence, and disagreement metrics."
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
