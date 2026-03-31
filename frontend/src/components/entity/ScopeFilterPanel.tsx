import { useMemo, useState } from "react";
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Box,
  Button,
  Chip,
  MenuItem,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import FilterListIcon from "@mui/icons-material/FilterList";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import { useTranslation } from "react-i18next";

import type { ScopeFilter } from "../../api/inferences";
import {
  formatScopeFilterLabel,
  formatScopeFilterOptionLabel,
  SCOPE_FILTER_SUGGESTIONS,
} from "../../utils/relationPresentation";

const CUSTOM_FILTER_KEY = "__custom__";

export interface ScopeFilterPanelProps {
  scopeFilter: ScopeFilter;
  newFilterKey: string;
  newFilterValue: string;
  onKeyChange: (value: string) => void;
  onValueChange: (value: string) => void;
  onAddFilter: () => void;
  onRemoveFilter: (key: string) => void;
  onClearFilters: () => void;
}

export function ScopeFilterPanel({
  scopeFilter,
  newFilterKey,
  newFilterValue,
  onKeyChange,
  onValueChange,
  onAddFilter,
  onRemoveFilter,
  onClearFilters,
}: ScopeFilterPanelProps) {
  const { t } = useTranslation();
  const [customMode, setCustomMode] = useState(false);
  const activeFilterCount = Object.keys(scopeFilter).length;

  const suggestionByKey = useMemo(
    () => new Set(SCOPE_FILTER_SUGGESTIONS.map((suggestion) => suggestion.key)),
    [],
  );

  const selectorValue = customMode
    ? CUSTOM_FILTER_KEY
    : newFilterKey && suggestionByKey.has(newFilterKey)
      ? newFilterKey
      : "";

  const selectedSuggestion = SCOPE_FILTER_SUGGESTIONS.find((suggestion) => suggestion.key === newFilterKey);

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      onAddFilter();
    }
  };

  const handleSelectorChange = (value: string) => {
    if (value === CUSTOM_FILTER_KEY) {
      setCustomMode(true);
      onKeyChange("");
      return;
    }

    setCustomMode(false);
    onKeyChange(value);
  };

  return (
    <Accordion>
      <AccordionSummary expandIcon={<ExpandMoreIcon />}>
        <Stack direction="row" spacing={1} alignItems="center">
          <FilterListIcon fontSize="small" />
          <Typography>
            {t("scope_filter.title", "Scope Filter")}
            {activeFilterCount > 0 &&
              t("scope_filter.active_count", {
                defaultValue: " ({{count}} active)",
                count: activeFilterCount,
              })}
          </Typography>
        </Stack>
      </AccordionSummary>
      <AccordionDetails>
        <Stack spacing={2}>
          <AlertIntro />

          {activeFilterCount > 0 && (
            <Box>
              <Stack direction="row" justifyContent="space-between" alignItems="center" mb={1}>
                <Typography variant="caption" color="text.secondary">
                  {t("scope_filter.active_filters", "Active Filters:")}
                </Typography>
                <Button size="small" onClick={onClearFilters}>
                  {t("scope_filter.clear_all", "Clear all")}
                </Button>
              </Stack>
              <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                {Object.entries(scopeFilter).map(([key, value]) => (
                  <Chip
                    key={key}
                    label={formatScopeFilterLabel(key, String(value))}
                    onDelete={() => onRemoveFilter(key)}
                    size="small"
                    color="primary"
                  />
                ))}
              </Stack>
            </Box>
          )}

          <Box>
            <Typography variant="caption" color="text.secondary" gutterBottom>
              {t("scope_filter.add_filter", "Add Filter:")}
            </Typography>
            <Stack spacing={1.5} sx={{ mt: 1 }}>
              <TextField
                select
                size="small"
                label={t("scope_filter.dimension_label", "Scope dimension")}
                value={selectorValue}
                onChange={(event) => handleSelectorChange(event.target.value)}
              >
                <MenuItem value="">
                  {t("scope_filter.dimension_placeholder", "Choose a common dimension")}
                </MenuItem>
                {SCOPE_FILTER_SUGGESTIONS.map((suggestion) => (
                  <MenuItem key={suggestion.key} value={suggestion.key}>
                    {formatScopeFilterOptionLabel(suggestion.key)}
                  </MenuItem>
                ))}
                <MenuItem value={CUSTOM_FILTER_KEY}>
                  {t("scope_filter.custom_dimension", "Custom dimension")}
                </MenuItem>
              </TextField>

              {customMode && (
                <TextField
                  size="small"
                  label={t("scope_filter.attribute_label", "Custom attribute")}
                  value={newFilterKey}
                  onChange={(event) => onKeyChange(event.target.value)}
                  onKeyDown={handleKeyPress}
                  placeholder={t("scope_filter.attribute_placeholder", "e.g., disease_stage")}
                />
              )}

              <TextField
                size="small"
                label={t("scope_filter.value_label", "Value")}
                value={newFilterValue}
                onChange={(event) => onValueChange(event.target.value)}
                onKeyDown={handleKeyPress}
                placeholder={
                  selectedSuggestion
                    ? selectedSuggestion.example
                    : t("scope_filter.value_placeholder", "e.g., adults")
                }
              />

              <Button
                variant="contained"
                onClick={onAddFilter}
                disabled={!newFilterKey.trim() || !newFilterValue.trim()}
              >
                {t("scope_filter.add_button", "Apply scope filter")}
              </Button>
            </Stack>
          </Box>

          <Box>
            <Typography variant="caption" color="text.secondary" display="block" gutterBottom>
              {t("scope_filter.common_dimensions", "Common dimensions")}
            </Typography>
            <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
              {SCOPE_FILTER_SUGGESTIONS.map((suggestion) => (
                <Chip
                  key={suggestion.key}
                  label={`${formatScopeFilterOptionLabel(suggestion.key)}: ${suggestion.example}`}
                  variant="outlined"
                  onClick={() => handleSelectorChange(suggestion.key)}
                />
              ))}
            </Stack>
          </Box>
        </Stack>
      </AccordionDetails>
    </Accordion>
  );
}

function AlertIntro() {
  const { t } = useTranslation();

  return (
    <Typography variant="caption" color="text.secondary">
      {t(
        "scope_filter.help_text",
        "Use scope filters to change the analytical point of view for this entity, for example by population, condition, dosage, tissue, or timeframe. Filters narrow the evidence included in the inference; they do not rewrite the underlying data."
      )}
    </Typography>
  );
}
