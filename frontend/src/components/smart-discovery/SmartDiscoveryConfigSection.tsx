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
  return (
    <Paper sx={{ p: 3 }}>
      <Typography variant="h5" gutterBottom sx={{ display: "flex", alignItems: "center", gap: 1 }}>
        <span>2️⃣</span> Configure Search
      </Typography>

      <Stack spacing={3}>
        <Box>
          <Typography variant="subtitle2" gutterBottom>
            Databases to Search
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
              label="PubMed (Medical Literature)"
            />
            <FormControlLabel control={<Checkbox disabled />} label="arXiv (Coming Soon)" />
            <FormControlLabel control={<Checkbox disabled />} label="Wikipedia (Coming Soon)" />
          </Stack>
        </Box>

        <Box>
          <Typography variant="subtitle2" gutterBottom>
            Results Budget: {maxResults} sources
          </Typography>
          <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 1 }}>
            Number of top-quality sources to pre-select (you can adjust selection later)
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
            Minimum Quality: {(minQuality * 100).toFixed(0)}% ({getQualityLabel(minQuality)})
          </Typography>
          <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 1 }}>
            Only include sources with quality score above this threshold
          </Typography>
          <Slider
            value={minQuality}
            onChange={(_, value) => onMinQualityChange(value as number)}
            min={0.3}
            max={1.0}
            step={0.05}
            marks={[
              { value: 0.3, label: "Low" },
              { value: 0.5, label: "Neutral" },
              { value: 0.75, label: "RCT+" },
              { value: 0.9, label: "SR" },
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
          {searching ? "Searching databases..." : "🔍 Discover Sources"}
        </Button>

        {searchError && <Alert severity="error">{searchError}</Alert>}
      </Stack>
    </Paper>
  );
}
