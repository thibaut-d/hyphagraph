import { Link as RouterLink } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Grid,
  Link,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import ThumbDownIcon from "@mui/icons-material/ThumbDown";
import ThumbUpIcon from "@mui/icons-material/ThumbUp";

import type { DisagreementGroupRead } from "../../types/inference";
import type { RelationRead } from "../../types/relation";

export type DisagreementGroup = DisagreementGroupRead;

interface DisagreementsGroupsSectionProps {
  groups: DisagreementGroup[];
  onViewExplanation: (roleType: string) => void;
}

function EvidenceTable({
  title,
  titleColor,
  icon,
  emptyLabel,
  relations,
  fallbackKind,
}: {
  title: string;
  titleColor: "success.main" | "error.main";
  icon: React.ReactNode;
  emptyLabel?: string;
  relations: RelationRead[];
  fallbackKind: string;
}) {
  const { t } = useTranslation();

  return (
    <Card sx={{ borderColor: titleColor, borderWidth: 1, borderStyle: "solid" }}>
      <CardContent>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 2 }}>
          {icon}
          <Typography variant="h6" color={titleColor}>
            {title}
          </Typography>
        </Box>

        {relations.length > 0 ? (
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>{t("disagreements.table.kind", "Kind")}</TableCell>
                  <TableCell>{t("disagreements.table.confidence", "Confidence")}</TableCell>
                  <TableCell>{t("disagreements.table.source", "Source")}</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {relations.map((relation, index) => (
                  <TableRow key={index}>
                    <TableCell>{relation.kind || fallbackKind}</TableCell>
                    <TableCell>
                      {relation.confidence != null
                        ? `${Math.round(relation.confidence * 100)}%`
                        : "-"}
                    </TableCell>
                    <TableCell>
                      <Link component={RouterLink} to={`/sources/${relation.source_id}`} variant="body2">
                        {t("disagreements.table.view_source", "View Source")}
                      </Link>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        ) : (
          <Typography variant="body2" color="text.secondary">
            {emptyLabel}
          </Typography>
        )}
      </CardContent>
    </Card>
  );
}

export function DisagreementsGroupsSection({
  groups,
  onViewExplanation,
}: DisagreementsGroupsSectionProps) {
  const { t } = useTranslation();

  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        {t("disagreements.groups.title", "Contradictions by Relation Type")}
      </Typography>
      <Typography variant="body2" color="text.secondary" paragraph>
        {t(
          "disagreements.groups.description",
          "Each section shows supporting evidence vs. contradicting evidence side-by-side."
        )}
      </Typography>

      <Stack spacing={2}>
        {groups.map((group, index) => (
          <Accordion key={index} defaultExpanded={index === 0}>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Box sx={{ display: "flex", alignItems: "center", gap: 2, width: "100%" }}>
                <Typography variant="h6" sx={{ flexGrow: 1 }}>
                  {group.kind}
                </Typography>
                <Chip
                  icon={<ThumbUpIcon />}
                  label={t("disagreements.group.supporting_count", {
                    defaultValue: "{{count}} supporting",
                    count: group.supporting.length,
                  })}
                  color="success"
                  size="small"
                />
                <Chip
                  icon={<ThumbDownIcon />}
                  label={t("disagreements.group.contradicting_count", {
                    defaultValue: "{{count}} contradicting",
                    count: group.contradicting.length,
                  })}
                  color="error"
                  size="small"
                />
                <Chip
                  label={t("disagreements.group.confidence", {
                    defaultValue: "{{value}}% confidence",
                    value: Math.round(group.confidence * 100),
                  })}
                  size="small"
                  variant="outlined"
                />
              </Box>
            </AccordionSummary>
            <AccordionDetails>
              <Grid container spacing={2}>
                <Grid size={{ xs: 12, md: 6 }}>
                  <EvidenceTable
                    title={t("disagreements.supporting", "Supporting ({{count}})", { count: group.supporting.length })}
                    titleColor="success.main"
                    icon={<ThumbUpIcon color="success" />}
                    emptyLabel={t("disagreements.no_supporting", "No supporting evidence")}
                    relations={group.supporting}
                    fallbackKind={group.kind}
                  />
                </Grid>

                <Grid size={{ xs: 12, md: 6 }}>
                  <EvidenceTable
                    title={t("disagreements.contradicting", "Contradicting ({{count}})", { count: group.contradicting.length })}
                    titleColor="error.main"
                    icon={<ThumbDownIcon color="error" />}
                    relations={group.contradicting}
                    fallbackKind={group.kind}
                  />
                </Grid>
              </Grid>

              <Box sx={{ mt: 2, display: "flex", justifyContent: "center" }}>
                <Button variant="outlined" onClick={() => onViewExplanation(group.kind)}>
                  {t("disagreements.view_explanation", "View Detailed Explanation")}
                </Button>
              </Box>
            </AccordionDetails>
          </Accordion>
        ))}
      </Stack>
    </Box>
  );
}
