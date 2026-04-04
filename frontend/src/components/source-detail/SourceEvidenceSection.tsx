import { Link as RouterLink } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  Alert,
  Box,
  Chip,
  Divider,
  Link,
  Paper,
  Stack,
  Typography,
} from "@mui/material";
import FormatQuoteIcon from "@mui/icons-material/FormatQuote";

import type { RelationRead } from "../../types/relation";
import type { SourceRead } from "../../types/source";

interface SourceEvidenceSectionProps {
  source: SourceRead;
  relations: RelationRead[];
}

interface EvidenceStatement {
  relationId: string;
  relationKind: string;
  direction: string;
  text: string;
}

function resolveLocalizedText(
  value: string | Record<string, string> | null | undefined,
  preferredLanguage: string,
) {
  if (!value) {
    return null;
  }

  if (typeof value === "string") {
    return value;
  }

  return value[preferredLanguage] || value.en || Object.values(value)[0] || null;
}

function buildEvidenceStatements(
  relations: RelationRead[],
  t: (key: string, defaultValue?: string) => string,
  preferredLanguage: string,
) {
  const seen = new Set<string>();
  const statements: EvidenceStatement[] = [];

  relations.forEach((relation) => {
    const text = resolveLocalizedText(relation.notes, preferredLanguage)?.trim();
    if (!text) {
      return;
    }

    const dedupeKey = `${relation.id}:${text}`;
    if (seen.has(dedupeKey)) {
      return;
    }

    seen.add(dedupeKey);
    statements.push({
      relationId: relation.id,
      relationKind: relation.kind || t("sources.unknown_relation_kind", "Uncategorized"),
      direction: relation.direction || t("relation.no_direction", "No direction"),
      text,
    });
  });

  return statements;
}

export function SourceEvidenceSection({
  source,
  relations,
}: SourceEvidenceSectionProps) {
  const { t, i18n } = useTranslation();
  const preferredLanguage = i18n?.language || "en";
  const sourceSummary = resolveLocalizedText(source.summary, preferredLanguage);
  const statements = buildEvidenceStatements(relations, t, preferredLanguage);
  const hasEvidence = Boolean(sourceSummary) || statements.length > 0;

  return (
    <Paper sx={{ p: 3 }}>
      <Stack spacing={2.5}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          <FormatQuoteIcon color="primary" />
          <Typography variant="h5">
            {t("sources.evidence_statements", "Source-backed statements")}
          </Typography>
        </Box>

        <Typography variant="body2" color="text.secondary">
          {t(
            "sources.evidence_statements_description",
            "Read the document-grounded summary and recorded statements before curating new extractions."
          )}
        </Typography>

        {!hasEvidence ? (
          <Alert severity="info">
            {t(
              "sources.no_evidence_statements",
              "No source-backed summary or statement excerpts are recorded yet. Review the linked relations below or extract new evidence."
            )}
          </Alert>
        ) : (
          <Stack spacing={2}>
            {sourceSummary && (
              <Box>
                <Typography variant="subtitle2" sx={{ mb: 1 }}>
                  {t("sources.document_summary", "Document summary")}
                </Typography>
                <Paper variant="outlined" sx={{ p: 2, bgcolor: "background.default" }}>
                  <Typography variant="body1">{sourceSummary}</Typography>
                </Paper>
              </Box>
            )}

            {sourceSummary && statements.length > 0 && <Divider />}

            {statements.length > 0 && (
              <Box>
                <Typography variant="subtitle2" sx={{ mb: 1 }}>
                  {t("sources.recorded_statements", "Recorded statements")}
                </Typography>
                <Stack spacing={1.5}>
                  {statements.map((statement) => (
                    <Paper
                      key={`${statement.relationId}-${statement.text}`}
                      variant="outlined"
                      sx={{ p: 2, bgcolor: "background.default" }}
                    >
                      <Stack spacing={1}>
                        <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1 }}>
                          <Chip label={statement.relationKind} size="small" />
                          <Chip label={statement.direction} size="small" variant="outlined" />
                        </Box>
                        <Typography variant="body2" sx={{ fontStyle: "italic" }}>
                          "{statement.text}"
                        </Typography>
                        <Link
                          component={RouterLink}
                          to={`/relations/${statement.relationId}`}
                          underline="hover"
                          sx={{ width: "fit-content" }}
                        >
                          {t("sources.open_statement_relation", "Open relation evidence")}
                        </Link>
                      </Stack>
                    </Paper>
                  ))}
                </Stack>
              </Box>
            )}
          </Stack>
        )}
      </Stack>
    </Paper>
  );
}
