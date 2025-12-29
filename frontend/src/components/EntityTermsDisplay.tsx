/**
 * EntityTermsDisplay
 *
 * Read-only display component for entity terms.
 * Shows alternative names/aliases in a compact, readable format.
 * Used in entity detail views where editing is not needed.
 */

import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import {
  Box,
  Typography,
  Chip,
  Stack,
  CircularProgress,
  Alert,
} from "@mui/material";
import TranslateIcon from "@mui/icons-material/Translate";

import { listEntityTerms, EntityTermRead } from "../api/entityTerms";

interface EntityTermsDisplayProps {
  entityId: string;
  compact?: boolean;
}

export function EntityTermsDisplay({
  entityId,
  compact = false,
}: EntityTermsDisplayProps) {
  const { t } = useTranslation();

  const [terms, setTerms] = useState<EntityTermRead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadTerms = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await listEntityTerms(entityId);
        setTerms(data);
      } catch (err) {
        console.error("Failed to load terms:", err);
        setError("Failed to load terms");
      } finally {
        setLoading(false);
      }
    };

    loadTerms();
  }, [entityId]);

  if (loading) {
    return (
      <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
        <CircularProgress size={16} />
        <Typography variant="caption" color="text.secondary">
          {t("entityTerms.loading", "Loading terms...")}
        </Typography>
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ py: 0.5 }}>
        {error}
      </Alert>
    );
  }

  if (terms.length === 0) {
    return null; // Don't show anything if no terms
  }

  const getLanguageLabel = (code: string | null): string => {
    if (!code) return "";
    const labels: Record<string, string> = {
      en: "EN",
      fr: "FR",
      es: "ES",
      de: "DE",
      it: "IT",
      pt: "PT",
      zh: "ZH",
      ja: "JA",
    };
    return labels[code] || code.toUpperCase();
  };

  if (compact) {
    // Compact mode: Just show terms as chips in a single row
    return (
      <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5 }}>
        {terms.map((term) => (
          <Chip
            key={term.id}
            label={term.term}
            size="small"
            variant="outlined"
            icon={term.language ? undefined : <TranslateIcon />}
          />
        ))}
      </Box>
    );
  }

  // Full mode: Show with language labels and section header
  return (
    <Box>
      <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1 }}>
        <TranslateIcon fontSize="small" color="action" />
        <Typography variant="subtitle2" color="text.secondary">
          {t("entityTerms.alsoKnownAs", "Also known as")}
        </Typography>
      </Box>

      <Stack spacing={1}>
        {terms.map((term) => (
          <Box
            key={term.id}
            sx={{
              display: "flex",
              alignItems: "center",
              gap: 1,
              pl: 1,
              py: 0.5,
              borderLeft: 2,
              borderColor: "divider",
            }}
          >
            <Typography variant="body2">{term.term}</Typography>
            {term.language && (
              <Chip
                label={getLanguageLabel(term.language)}
                size="small"
                variant="outlined"
                sx={{ fontSize: "0.7rem", height: 18 }}
              />
            )}
          </Box>
        ))}
      </Stack>
    </Box>
  );
}
