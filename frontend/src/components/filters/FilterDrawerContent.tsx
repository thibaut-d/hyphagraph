/**
 * FilterDrawerContent - Scrollable content area for filter drawer.
 */

import { Box } from '@mui/material';

export interface FilterDrawerContentProps {
  /** Filter components to render */
  children: React.ReactNode;
}

/**
 * Scrollable content wrapper for filter drawer.
 */
export function FilterDrawerContent({ children }: FilterDrawerContentProps) {
  return (
    <Box
      sx={{
        flexGrow: 1,
        overflowY: 'auto',
        p: 2,
      }}
    >
      {children}
    </Box>
  );
}
