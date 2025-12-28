/**
 * FilterDrawerActions - Action buttons for filter drawer.
 */

import { Box, Button, Stack } from '@mui/material';
import { useTranslation } from 'react-i18next';

export interface FilterDrawerActionsProps {
  /** Called when clear all button clicked */
  onClearAll: () => void;

  /** Called when close button clicked */
  onClose: () => void;

  /** Whether there are any active filters to clear */
  hasActiveFilters?: boolean;
}

/**
 * Action buttons for filter drawer (Clear All, Close).
 */
export function FilterDrawerActions({
  onClearAll,
  onClose,
  hasActiveFilters = true,
}: FilterDrawerActionsProps) {
  const { t } = useTranslation();

  return (
    <Box
      sx={{
        p: 2,
        borderTop: 1,
        borderColor: 'divider',
      }}
    >
      <Stack direction="row" spacing={2}>
        <Button
          variant="outlined"
          onClick={onClearAll}
          disabled={!hasActiveFilters}
          fullWidth
        >
          {t('filters.clear_all', 'Clear All')}
        </Button>
        <Button variant="contained" onClick={onClose} fullWidth>
          {t('common.close', 'Close')}
        </Button>
      </Stack>
    </Box>
  );
}
