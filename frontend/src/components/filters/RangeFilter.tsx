/**
 * RangeFilter - Min/max range slider filter.
 */

import { Slider, Typography, Stack, Box } from '@mui/material';
import { useTranslation } from 'react-i18next';

export interface RangeFilterProps {
  /** Minimum value */
  min: number;

  /** Maximum value */
  max: number;

  /** Current [min, max] value */
  value: [number, number];

  /** Called when range changes */
  onChange: (value: [number, number]) => void;

  /** Step size for slider */
  step?: number;

  /** Optional value formatter for display */
  formatValue?: (value: number) => string;
}

/**
 * Range slider filter component.
 */
export function RangeFilter({
  min,
  max,
  value,
  onChange,
  step = 0.1,
  formatValue = (v) => String(v),
}: RangeFilterProps) {
  const { t } = useTranslation();

  const handleChange = (_event: Event, newValue: number | number[]) => {
    if (Array.isArray(newValue) && newValue.length === 2) {
      onChange([newValue[0], newValue[1]]);
    }
  };

  return (
    <Stack spacing={1}>
      <Box sx={{ px: 1 }}>
        <Slider
          value={value}
          onChange={handleChange}
          min={min}
          max={max}
          step={step}
          valueLabelDisplay="auto"
          valueLabelFormat={formatValue}
          marks={[
            { value: min, label: formatValue(min) },
            { value: max, label: formatValue(max) },
          ]}
        />
      </Box>

      <Stack direction="row" justifyContent="space-between" sx={{ px: 1 }}>
        <Typography variant="caption" color="text.secondary">
          {t('filters.min', 'Min')}: {formatValue(value[0])}
        </Typography>
        <Typography variant="caption" color="text.secondary">
          {t('filters.max', 'Max')}: {formatValue(value[1])}
        </Typography>
      </Stack>
    </Stack>
  );
}
