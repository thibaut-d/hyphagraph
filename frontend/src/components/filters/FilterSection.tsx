/**
 * FilterSection - Collapsible section wrapper for filter groups.
 *
 * Uses MUI Accordion for expandable/collapsible sections.
 */

import { Accordion, AccordionSummary, AccordionDetails, Typography } from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';

export interface FilterSectionProps {
  /** Section title */
  title: string;

  /** Filter components to render inside */
  children: React.ReactNode;

  /** Whether section is expanded by default */
  defaultExpanded?: boolean;
}

/**
 * Collapsible section for grouping related filters.
 */
export function FilterSection({
  title,
  children,
  defaultExpanded = true,
}: FilterSectionProps) {
  return (
    <Accordion defaultExpanded={defaultExpanded} disableGutters elevation={0}>
      <AccordionSummary
        expandIcon={<ExpandMoreIcon />}
        sx={{
          minHeight: 48,
          '&.Mui-expanded': {
            minHeight: 48,
          },
        }}
      >
        <Typography variant="subtitle2" fontWeight={600}>
          {title}
        </Typography>
      </AccordionSummary>
      <AccordionDetails sx={{ pt: 0 }}>{children}</AccordionDetails>
    </Accordion>
  );
}
