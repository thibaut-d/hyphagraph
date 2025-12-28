/**
 * Tests for RangeFilter component.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { RangeFilter } from '../RangeFilter';

// Mock i18n
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, defaultValue: string) => defaultValue,
  }),
}));

describe('RangeFilter', () => {
  it('renders slider with min and max labels', () => {
    const onChange = vi.fn();
    render(
      <RangeFilter min={0} max={100} value={[25, 75]} onChange={onChange} />
    );

    // Check for sliders (MUI range slider has 2 slider inputs)
    const sliders = screen.getAllByRole('slider');
    expect(sliders).toHaveLength(2);

    // Check for min/max labels
    expect(screen.getByText('0')).toBeInTheDocument();
    expect(screen.getByText('100')).toBeInTheDocument();
  });

  it('displays current min and max values', () => {
    const onChange = vi.fn();
    render(
      <RangeFilter min={0} max={100} value={[25, 75]} onChange={onChange} />
    );

    expect(screen.getByText(/Min.*25/)).toBeInTheDocument();
    expect(screen.getByText(/Max.*75/)).toBeInTheDocument();
  });

  it('uses custom formatValue function when provided', () => {
    const onChange = vi.fn();
    const formatValue = (v: number) => `$${v.toFixed(2)}`;

    render(
      <RangeFilter
        min={0}
        max={100}
        value={[25, 75]}
        onChange={onChange}
        formatValue={formatValue}
      />
    );

    expect(screen.getByText('$0.00')).toBeInTheDocument();
    expect(screen.getByText('$100.00')).toBeInTheDocument();
    expect(screen.getByText(/Min.*\$25.00/)).toBeInTheDocument();
    expect(screen.getByText(/Max.*\$75.00/)).toBeInTheDocument();
  });

  it('applies custom step value', () => {
    const onChange = vi.fn();
    const { container } = render(
      <RangeFilter min={0} max={100} value={[0, 100]} onChange={onChange} step={5} />
    );

    const sliders = container.querySelectorAll('[role="slider"]');
    sliders.forEach((slider) => {
      expect(slider).toHaveAttribute('step', '5');
    });
  });

  it('uses default step value of 0.1', () => {
    const onChange = vi.fn();
    const { container } = render(
      <RangeFilter min={0} max={100} value={[0, 100]} onChange={onChange} />
    );

    const sliders = container.querySelectorAll('[role="slider"]');
    sliders.forEach((slider) => {
      expect(slider).toHaveAttribute('step', '0.1');
    });
  });

  it('handles decimal ranges', () => {
    const onChange = vi.fn();
    render(
      <RangeFilter
        min={0}
        max={1}
        value={[0.2, 0.8]}
        onChange={onChange}
        step={0.1}
        formatValue={(v) => v.toFixed(1)}
      />
    );

    expect(screen.getByText('0.0')).toBeInTheDocument();
    expect(screen.getByText('1.0')).toBeInTheDocument();
    expect(screen.getByText(/Min.*0.2/)).toBeInTheDocument();
    expect(screen.getByText(/Max.*0.8/)).toBeInTheDocument();
  });

  it('displays value correctly when min equals max', () => {
    const onChange = vi.fn();
    render(
      <RangeFilter min={50} max={50} value={[50, 50]} onChange={onChange} />
    );

    // Use getAllByText since 50 appears multiple times (labels and values)
    const value50Elements = screen.getAllByText('50');
    expect(value50Elements.length).toBeGreaterThan(0);
    expect(screen.getByText(/Min.*50/)).toBeInTheDocument();
    expect(screen.getByText(/Max.*50/)).toBeInTheDocument();
  });

  it('handles negative ranges', () => {
    const onChange = vi.fn();
    render(
      <RangeFilter min={-100} max={100} value={[-50, 50]} onChange={onChange} />
    );

    expect(screen.getByText('-100')).toBeInTheDocument();
    expect(screen.getByText('100')).toBeInTheDocument();
    expect(screen.getByText(/Min.*-50/)).toBeInTheDocument();
    expect(screen.getByText(/Max.*50/)).toBeInTheDocument();
  });

  it('handles large number ranges', () => {
    const onChange = vi.fn();
    const formatValue = (v: number) => v.toLocaleString('en-US');

    render(
      <RangeFilter
        min={0}
        max={1000000}
        value={[250000, 750000]}
        onChange={onChange}
        formatValue={formatValue}
      />
    );

    // Check for formatted numbers (note: toLocaleString may produce different results)
    const formattedMin = formatValue(0);
    const formattedMax = formatValue(1000000);
    expect(screen.getByText(formattedMin)).toBeInTheDocument();
    expect(screen.getByText(formattedMax)).toBeInTheDocument();
  });
});
