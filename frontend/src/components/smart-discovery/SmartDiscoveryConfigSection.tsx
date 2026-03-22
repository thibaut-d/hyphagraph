import {
  Alert,
  Box,
  Button,
  CircularProgress,
  FormControlLabel,
  Paper,
  Slider,
  Stack,
  Typography,
} from "@mui/material";
import SearchIcon from "@mui/icons-material/Search";
import Checkbox from "@mui/material/Checkbox";
import { useTranslation } from "react-i18next";

interface SmartDiscoveryConfigSectionProps {
  maxResults: number;
  minQuality: number;
  selectedDatabases: string[];
  searching: boolean;
  searchError: string | null;
  onMaxResultsChange: (value: number) => void;
  onMinQualityChange: (value: number) => void;
  onDatabasesChange: (databases: string[]) => void;
  onSearch: () => void;
  searchDisabled: boolean;
  getQualityLabel: (trustLevel: number) => string;
}

export function SmartDiscoveryConfigSection({
  maxResults,
  minQuality,
  selectedDatabases,
  searching,
  searchError,
  onMaxResultsChange,
  onMinQualityChange,
  onDatabasesChange,
  onSearch,
  searchDisabled,
  getQualityLabel,
}: SmartDiscoveryConfigSectionProps) {
  const { t } = useTranslation();

  return (
    <Paper sx={{ p: 3 }}>
      <Typography variant="h5" gutterBottom sx={{ display: "flex", alignItems: "center", gap: 1 }}>
        <span>2️⃣</span> {t("smart_discovery.step_configure")}
      </Typography>

      <Stack spacing={3}>
        <Box>
          <Typography variant="subtitle2" gutterBottom>
            {t("smart_discovery.databases_label")}
          </Typography>
          <Stack direction="row" spacing={2}>
            <FormControlLabel
              control={
                <Checkbox
                  checked={selectedDatabases.includes("pubmed")}
                  onChange={(event) => {
                    if (event.target.checked) {
                      if (!selectedDatabases.includes("pubmed")) {
                        onDatabasesChange([...selectedDatabases, "pubmed"]);
                      }
                      return;
                    }

                    if (selectedDatabases.length > 1) {
                      onDatabasesChange(selectedDatabases.filter((database) => database !== "pubmed"));
                    }
                  }}
                />
              }
              label={t("smart_discovery.pubmed_label")}
            />
            <FormControlLabel control={<Checkbox disabled />} label={t("smart_discovery.arxiv_label")} />
            <FormControlLabel control={<Checkbox disabled />} label={t("smart_discovery.wikipedia_label")} />
          </Stack>
        </Box>

        <Box>
          <Typography variant="subtitle2" gutterBottom>
            {t("smart_discovery.results_budget_label", { count: maxResults })}
          </Typography>
          <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 1 }}>
            {t("smart_discovery.results_budget_hint")}
          </Typography>
          <Slider
            value={maxResults}
            onChange={(_, value) => onMaxResultsChange(value as number)}
            min={5}
            max={50}
            step={5}
            marks={[
              { value: 5, label: "5" },
              { value: 20, label: "20" },
              { value: 50, label: "50" },
            ]}
            valueLabelDisplay="auto"
          />
        </Box>

        <Box>
          <Typography variant="subtitle2" gutterBottom>
            {t("smart_discovery.min_quality_label", { percent: (minQuality * 100).toFixed(0), label: getQualityLabel(minQuality) })}
          </Typography>
          <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 1 }}>
            {t("smart_discovery.min_quality_hint")}
          </Typography>
          <Slider
            value={minQuality}
            onChange={(_, value) => onMinQualityChange(value as number)}
            min={0.3}
            max={1.0}
            step={0.05}
            marks={[
              { value: 0.3, label: t("smart_discovery.quality_mark_low") },
              { value: 0.5, label: t("smart_discovery.quality_mark_neutral") },
              { value: 0.75, label: t("smart_discovery.quality_mark_rct") },
              { value: 0.9, label: t("smart_discovery.quality_mark_sr") },
            ]}
            valueLabelDisplay="auto"
            valueLabelFormat={(value) => `${(value * 100).toFixed(0)}%`}
          />
        </Box>

        <Button
          variant="contained"
          size="large"
          fullWidth
          startIcon={searching ? <CircularProgress size={20} /> : <SearchIcon />}
          onClick={onSearch}
          disabled={searchDisabled}
          sx={{ py: 2, fontSize: "1.1rem", fontWeight: 600 }}
        >
          {searching ? t("smart_discovery.searching") : t("smart_discovery.discover_button")}
        </Button>

        {searchError && <Alert severity="error">{searchError}</Alert>}
      </Stack>
    </Paper>
  );
}
