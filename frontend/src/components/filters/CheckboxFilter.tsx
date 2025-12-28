/**
 * CheckboxFilter - Multi-select checkbox filter.
 *
 * Supports select all/deselect all functionality.
 */

import { FormGroup, FormControlLabel, Checkbox, Button, Stack } from '@mui/material';
import { useTranslation } from 'react-i18next';
import type { FilterOption } from '../../types/filters';

export interface CheckboxFilterProps {
  /** Available options */
  options: FilterOption[];

  /** Currently selected values */
  value: Array<string | number>;

  /** Called when selection changes */
  onChange: (value: Array<string | number>) => void;

  /** Show select all/deselect all buttons */
  showSelectAll?: boolean;
}

/**
 * Multi-select checkbox filter component.
 */
export function CheckboxFilter({
  options,
  value,
  onChange,
  showSelectAll = true,
}: CheckboxFilterProps) {
  const { t } = useTranslation();

  const handleToggle = (optionValue: string | number) => {
    const newValue = value.includes(optionValue)
      ? value.filter((v) => v !== optionValue)
      : [...value, optionValue];
    onChange(newValue);
  };

  const handleSelectAll = () => {
    onChange(options.map((opt) => opt.value));
  };

  const handleDeselectAll = () => {
    onChange([]);
  };

  const allSelected = value.length === options.length;
  const noneSelected = value.length === 0;

  return (
    <Stack spacing={1}>
      {showSelectAll && options.length > 1 && (
        <Stack direction="row" spacing={1}>
          <Button
            size="small"
            onClick={handleSelectAll}
            disabled={allSelected}
            sx={{ textTransform: 'none' }}
          >
            {t('filters.select_all', 'Select All')}
          </Button>
          <Button
            size="small"
            onClick={handleDeselectAll}
            disabled={noneSelected}
            sx={{ textTransform: 'none' }}
          >
            {t('filters.deselect_all', 'Deselect All')}
          </Button>
        </Stack>
      )}

      <FormGroup>
        {options.map((option) => (
          <FormControlLabel
            key={String(option.value)}
            control={
              <Checkbox
                checked={value.includes(option.value)}
                onChange={() => handleToggle(option.value)}
                size="small"
              />
            }
            label={option.label}
          />
        ))}
      </FormGroup>
    </Stack>
  );
}
