/**
 * Tests for YearRangeFilter component.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { YearRangeFilter } from '../YearRangeFilter';

// Mock i18n
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, defaultValue: string) => defaultValue,
  }),
}));

describe('YearRangeFilter', () => {
  it('renders with integer year values', () => {
    const onChange = vi.fn();
    render(
      <YearRangeFilter min={2000} max={2024} value={[2010, 2020]} onChange={onChange} />
    );

    // Should show years as integers
    expect(screen.getByText('2000')).toBeInTheDocument();
    expect(screen.getByText('2024')).toBeInTheDocument();
    expect(screen.getByText(/Min.*2010/)).toBeInTheDocument();
    expect(screen.getByText(/Max.*2020/)).toBeInTheDocument();
  });

  it('uses step size of 1 for years', () => {
    const onChange = vi.fn();
    const { container } = render(
      <YearRangeFilter min={2000} max={2024} value={[2000, 2024]} onChange={onChange} />
    );

    const sliders = container.querySelectorAll('[role="slider"]');
    sliders.forEach((slider) => {
      expect(slider).toHaveAttribute('step', '1');
    });
  });

  it('formats values as rounded integers', () => {
    const onChange = vi.fn();
    render(
      <YearRangeFilter
        min={1990}
        max={2024}
        value={[2000.7, 2020.3]}
        onChange={onChange}
      />
    );

    // Years should be displayed as rounded integers
    expect(screen.getByText(/Min.*2001/)).toBeInTheDocument();
    expect(screen.getByText(/Max.*2020/)).toBeInTheDocument();
  });

  it('handles historical year ranges', () => {
    const onChange = vi.fn();
    render(
      <YearRangeFilter min={1800} max={1900} value={[1850, 1875]} onChange={onChange} />
    );

    expect(screen.getByText('1800')).toBeInTheDocument();
    expect(screen.getByText('1900')).toBeInTheDocument();
    expect(screen.getByText(/Min.*1850/)).toBeInTheDocument();
    expect(screen.getByText(/Max.*1875/)).toBeInTheDocument();
  });

  it('handles future year ranges', () => {
    const onChange = vi.fn();
    render(
      <YearRangeFilter min={2024} max={2100} value={[2024, 2050]} onChange={onChange} />
    );

    // Use getAllByText since 2024 appears multiple times (min label and min value)
    const year2024Elements = screen.getAllByText('2024');
    expect(year2024Elements.length).toBeGreaterThan(0);
    expect(screen.getByText('2100')).toBeInTheDocument();
    expect(screen.getByText(/Min.*2024/)).toBeInTheDocument();
    expect(screen.getByText(/Max.*2050/)).toBeInTheDocument();
  });

  it('handles single year range', () => {
    const onChange = vi.fn();
    render(
      <YearRangeFilter min={2024} max={2024} value={[2024, 2024]} onChange={onChange} />
    );

    // Use getAllByText since 2024 appears many times (labels, values, etc.)
    const year2024Elements = screen.getAllByText('2024');
    expect(year2024Elements.length).toBeGreaterThan(0);
    expect(screen.getByText(/Min.*2024/)).toBeInTheDocument();
    expect(screen.getByText(/Max.*2024/)).toBeInTheDocument();
  });
});
