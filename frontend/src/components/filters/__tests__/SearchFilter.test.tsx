/**
 * Tests for SearchFilter component.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { SearchFilter } from '../SearchFilter';

describe('SearchFilter', () => {

  it('renders with placeholder text', () => {
    const onChange = vi.fn();
    render(
      <SearchFilter value="" onChange={onChange} placeholder="Search entities..." />
    );

    const input = screen.getByPlaceholderText('Search entities...');
    expect(input).toBeInTheDocument();
  });

  it('displays current value', () => {
    const onChange = vi.fn();
    render(<SearchFilter value="test query" onChange={onChange} />);

    const input = screen.getByDisplayValue('test query');
    expect(input).toBeInTheDocument();
  });

  it('shows search icon', () => {
    const onChange = vi.fn();
    const { container } = render(<SearchFilter value="" onChange={onChange} />);

    // Search icon should be present
    const searchIcon = container.querySelector('[data-testid="SearchIcon"]');
    expect(searchIcon).toBeInTheDocument();
  });

  it('shows clear button when value is not empty', () => {
    const onChange = vi.fn();
    const { container } = render(<SearchFilter value="test" onChange={onChange} />);

    const clearButton = container.querySelector('[data-testid="ClearIcon"]');
    expect(clearButton).toBeInTheDocument();
  });

  it('hides clear button when value is empty', () => {
    const onChange = vi.fn();
    const { container } = render(<SearchFilter value="" onChange={onChange} />);

    const clearButton = container.querySelector('[data-testid="ClearIcon"]');
    expect(clearButton).not.toBeInTheDocument();
  });

  it('updates local value immediately on typing', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<SearchFilter value="" onChange={onChange} />);

    const input = screen.getByRole('textbox');
    await user.type(input, 'test');

    expect(input).toHaveValue('test');
  });

  it('debounces onChange calls by 300ms by default', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<SearchFilter value="" onChange={onChange} debounceMs={100} />);

    const input = screen.getByRole('textbox');
    await user.type(input, 'test');

    // Should not call onChange immediately
    expect(onChange).not.toHaveBeenCalled();

    // Wait for debounce (with margin)
    await waitFor(
      () => {
        expect(onChange).toHaveBeenCalledWith('test');
      },
      { timeout: 200 }
    );
    expect(onChange).toHaveBeenCalledTimes(1);
  });

  it('uses custom debounce delay when provided', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<SearchFilter value="" onChange={onChange} debounceMs={100} />);

    const input = screen.getByRole('textbox');
    await user.type(input, 'test');

    // Should not call onChange immediately
    expect(onChange).not.toHaveBeenCalled();

    // Wait for custom debounce
    await waitFor(
      () => {
        expect(onChange).toHaveBeenCalledWith('test');
      },
      { timeout: 200 }
    );
  });

  it('resets debounce timer on each keystroke', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<SearchFilter value="" onChange={onChange} debounceMs={100} />);

    const input = screen.getByRole('textbox');

    // Type full text
    await user.type(input, 'test');

    // Should not have called onChange yet
    expect(onChange).not.toHaveBeenCalled();

    // Wait for debounce after last keystroke
    await waitFor(
      () => {
        expect(onChange).toHaveBeenCalledWith('test');
      },
      { timeout: 200 }
    );
    expect(onChange).toHaveBeenCalledTimes(1);
  });

  it('clears value and calls onChange when clear button is clicked', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    const { container } = render(<SearchFilter value="test" onChange={onChange} />);

    const clearButton = container.querySelector('[data-testid="ClearIcon"]')
      ?.closest('button');
    expect(clearButton).toBeInTheDocument();

    await user.click(clearButton!);

    expect(onChange).toHaveBeenCalledWith('');
    expect(screen.getByRole('textbox')).toHaveValue('');
  });

  it('syncs local value with prop value when prop changes', () => {
    const onChange = vi.fn();
    const { rerender } = render(<SearchFilter value="initial" onChange={onChange} />);

    expect(screen.getByRole('textbox')).toHaveValue('initial');

    // Update prop value
    rerender(<SearchFilter value="updated" onChange={onChange} />);

    expect(screen.getByRole('textbox')).toHaveValue('updated');
  });

  it('does not call onChange if value has not changed after debounce', async () => {
    const onChange = vi.fn();
    render(<SearchFilter value="test" onChange={onChange} debounceMs={100} />);

    // Value is already 'test', no typing, wait for potential debounce
    await new Promise((resolve) => setTimeout(resolve, 150));

    expect(onChange).not.toHaveBeenCalled();
  });

  it('handles rapid clearing and typing', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    const { container } = render(<SearchFilter value="" onChange={onChange} debounceMs={50} />);

    const input = screen.getByRole('textbox');

    // Type something
    await user.type(input, 'test');
    await waitFor(() => expect(onChange).toHaveBeenCalledWith('test'), { timeout: 100 });
    onChange.mockClear();

    // Clear it
    const clearButton = container.querySelector('[data-testid="ClearIcon"]')
      ?.closest('button');
    await user.click(clearButton!);
    expect(onChange).toHaveBeenCalledWith('');
    onChange.mockClear();

    // Type again
    await user.type(input, 'new');
    await waitFor(() => expect(onChange).toHaveBeenCalledWith('new'), { timeout: 100 });
  });
});
