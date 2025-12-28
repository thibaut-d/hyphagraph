/**
 * FilterDrawerHeader - Header section for filter drawer.
 */

import { Box, Typography, IconButton, Badge } from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';

export interface FilterDrawerHeaderProps {
  /** Header title */
  title: string;

  /** Number of active filters for badge */
  activeFilterCount: number;

  /** Called when close button clicked */
  onClose: () => void;
}

/**
 * Filter drawer header with title, badge, and close button.
 */
export function FilterDrawerHeader({
  title,
  activeFilterCount,
  onClose,
}: FilterDrawerHeaderProps) {
  return (
    <Box
      sx={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        p: 2,
        borderBottom: 1,
        borderColor: 'divider',
      }}
    >
      <Badge badgeContent={activeFilterCount} color="primary">
        <Typography variant="h6" fontWeight={600}>
          {title}
        </Typography>
      </Badge>

      <IconButton onClick={onClose} size="small" edge="end">
        <CloseIcon />
      </IconButton>
    </Box>
  );
}
