/**
 * ClaimsList component
 *
 * Displays extracted claims with evidence strength indicators and allows
 * user to select which claims to save.
 */
import React from "react";
import {
  Box,
  Card,
  CardContent,
  Typography,
  Chip,
  Checkbox,
  Stack,
  Alert,
} from "@mui/material";
import {
  Science as ScienceIcon,
  LocalHospital as LocalHospitalIcon,
  Psychology as PsychologyIcon,
  Biotech as BiotechIcon,
  Info as InfoIcon,
  VerifiedUser as VerifiedUserIcon,
  Warning as WarningIcon,
  HelpOutline as HelpOutlineIcon,
} from "@mui/icons-material";
import type {
  ExtractedClaim,
  ClaimType,
  EvidenceStrength,
  ConfidenceLevel,
} from "../types/extraction";

interface ClaimsListProps {
  claims: ExtractedClaim[];
  selectedClaims: Set<string>;
  onToggle: (claimText: string) => void;
}

const confidenceColors: Record<ConfidenceLevel, "success" | "warning" | "error"> = {
  high: "success",
  medium: "warning",
  low: "error",
};

const claimTypeLabels: Record<ClaimType, string> = {
  efficacy: "Efficacy",
  safety: "Safety",
  mechanism: "Mechanism",
  epidemiology: "Epidemiology",
  other: "Other",
};

const claimTypeIcons: Record<ClaimType, React.ReactElement> = {
  efficacy: <LocalHospitalIcon fontSize="small" />,
  safety: <WarningIcon fontSize="small" />,
  mechanism: <PsychologyIcon fontSize="small" />,
  epidemiology: <BiotechIcon fontSize="small" />,
  other: <InfoIcon fontSize="small" />,
};

const evidenceStrengthLabels: Record<EvidenceStrength, string> = {
  strong: "Strong Evidence",
  moderate: "Moderate Evidence",
  weak: "Weak Evidence",
  anecdotal: "Anecdotal",
};

const evidenceStrengthIcons: Record<EvidenceStrength, React.ReactElement> = {
  strong: <VerifiedUserIcon fontSize="small" />,
  moderate: <ScienceIcon fontSize="small" />,
  weak: <WarningIcon fontSize="small" />,
  anecdotal: <HelpOutlineIcon fontSize="small" />,
};

const evidenceStrengthColors: Record<
  EvidenceStrength,
  "success" | "info" | "warning" | "default"
> = {
  strong: "success",
  moderate: "info",
  weak: "warning",
  anecdotal: "default",
};

export const ClaimsList: React.FC<ClaimsListProps> = ({
  claims,
  selectedClaims,
  onToggle,
}) => {
  if (claims.length === 0) {
    return (
      <Alert severity="info">
        No claims were extracted from the document.
      </Alert>
    );
  }

  return (
    <Stack spacing={2}>
      {claims.map((claim) => {
        const isSelected = selectedClaims.has(claim.claim_text);

        return (
          <Card
            key={claim.claim_text}
            variant="outlined"
            sx={{
              opacity: isSelected ? 1 : 0.6,
              transition: "opacity 0.2s",
              "&:hover": { opacity: 1 },
            }}
          >
            <CardContent>
              <Stack spacing={2}>
                {/* Claim header with checkbox */}
                <Box sx={{ display: "flex", alignItems: "flex-start", gap: 2 }}>
                  <Checkbox
                    checked={isSelected}
                    onChange={() => onToggle(claim.claim_text)}
                    sx={{ mt: -1 }}
                  />

                  <Box sx={{ flex: 1 }}>
                    {/* Claim text */}
                    <Typography variant="body1" fontWeight="medium">
                      {claim.claim_text}
                    </Typography>

                    {/* Involved entities */}
                    {claim.entities_involved.length > 0 && (
                      <Box sx={{ mt: 1, display: "flex", gap: 1, flexWrap: "wrap" }}>
                        <Typography
                          variant="caption"
                          color="text.secondary"
                          sx={{ mr: 0.5 }}
                        >
                          Entities:
                        </Typography>
                        {claim.entities_involved.map((entity) => (
                          <Chip
                            key={entity}
                            label={entity}
                            size="small"
                            variant="outlined"
                            sx={{ height: 20, fontSize: "0.7rem" }}
                          />
                        ))}
                      </Box>
                    )}
                  </Box>

                  {/* Type and confidence chips */}
                  <Stack direction="column" spacing={0.5} alignItems="flex-end">
                    <Chip
                      icon={claimTypeIcons[claim.claim_type]}
                      label={claimTypeLabels[claim.claim_type]}
                      size="small"
                      variant="outlined"
                    />
                    <Chip
                      label={claim.confidence}
                      size="small"
                      color={confidenceColors[claim.confidence]}
                    />
                  </Stack>
                </Box>

                {/* Evidence strength */}
                <Box sx={{ ml: 5 }}>
                  <Chip
                    icon={evidenceStrengthIcons[claim.evidence_strength]}
                    label={evidenceStrengthLabels[claim.evidence_strength]}
                    size="small"
                    color={evidenceStrengthColors[claim.evidence_strength]}
                    sx={{ fontWeight: "medium" }}
                  />
                </Box>

                {/* Text span (source quote) */}
                <Box
                  sx={{
                    p: 1.5,
                    bgcolor: "grey.50",
                    borderRadius: 1,
                    borderLeft: "3px solid",
                    borderColor: evidenceStrengthColors[claim.evidence_strength] + ".main",
                    ml: 5, // Align with content (after checkbox)
                  }}
                >
                  <Typography variant="caption" color="text.secondary" sx={{ mb: 0.5 }}>
                    Source quote:
                  </Typography>
                  <Typography variant="body2" sx={{ fontStyle: "italic" }}>
                    "{claim.text_span}"
                  </Typography>
                </Box>
              </Stack>
            </CardContent>
          </Card>
        );
      })}
    </Stack>
  );
};
