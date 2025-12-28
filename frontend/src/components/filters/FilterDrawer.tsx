/**
 * FilterDrawer - Main filter drawer component.
 *
 * Combines Header, Content, and Actions into a complete drawer.
 */

import { Drawer } from '@mui/material';
import { FilterDrawerHeader } from './FilterDrawerHeader';
import { FilterDrawerContent } from './FilterDrawerContent';
import { FilterDrawerActions } from './FilterDrawerActions';

export interface FilterDrawerProps {
  /** Whether drawer is open */
  open: boolean;

  /** Called when drawer should close */
  onClose: () => void;

  /** Drawer title */
  title: string;

  /** Filter components to render */
  children: React.ReactNode;

  /** Number of active filters */
  activeFilterCount: number;

  /** Called when clear all button clicked */
  onClearAll: () => void;

  /** Drawer anchor side */
  anchor?: 'left' | 'right';
}

/**
 * Filter drawer with header, scrollable content, and actions.
 */
export function FilterDrawer({
  open,
  onClose,
  title,
  children,
  activeFilterCount,
  onClearAll,
  anchor = 'right',
}: FilterDrawerProps) {
  return (
    <Drawer
      anchor={anchor}
      open={open}
      onClose={onClose}
      sx={{
        '& .MuiDrawer-paper': {
          width: {
            xs: '100%', // Full width on mobile
            sm: 360, // 360px on desktop
          },
          display: 'flex',
          flexDirection: 'column',
        },
      }}
    >
      <FilterDrawerHeader
        title={title}
        activeFilterCount={activeFilterCount}
        onClose={onClose}
      />

      <FilterDrawerContent>{children}</FilterDrawerContent>

      <FilterDrawerActions
        onClearAll={onClearAll}
        onClose={onClose}
        hasActiveFilters={activeFilterCount > 0}
      />
    </Drawer>
  );
}
