/**
 * Tests for CheckboxFilter component.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { CheckboxFilter } from '../CheckboxFilter';
import type { FilterOption } from '../../../types/filters';

// Mock i18n
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, defaultValue: string) => defaultValue,
  }),
}));

describe('CheckboxFilter', () => {
  const mockOptions: FilterOption[] = [
    { value: 'drug', label: 'Drug' },
    { value: 'disease', label: 'Disease' },
    { value: 'symptom', label: 'Symptom' },
  ];

  it('renders all checkbox options', () => {
    const onChange = vi.fn();
    render(<CheckboxFilter options={mockOptions} value={[]} onChange={onChange} />);

    expect(screen.getByLabelText('Drug')).toBeInTheDocument();
    expect(screen.getByLabelText('Disease')).toBeInTheDocument();
    expect(screen.getByLabelText('Symptom')).toBeInTheDocument();
  });

  it('shows checked state for selected values', () => {
    const onChange = vi.fn();
    render(
      <CheckboxFilter
        options={mockOptions}
        value={['drug', 'symptom']}
        onChange={onChange}
      />
    );

    const drugCheckbox = screen.getByLabelText('Drug');
    const diseaseCheckbox = screen.getByLabelText('Disease');
    const symptomCheckbox = screen.getByLabelText('Symptom');

    expect(drugCheckbox).toBeChecked();
    expect(diseaseCheckbox).not.toBeChecked();
    expect(symptomCheckbox).toBeChecked();
  });

  it('calls onChange with added value when unchecked box is clicked', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<CheckboxFilter options={mockOptions} value={['drug']} onChange={onChange} />);

    const diseaseCheckbox = screen.getByLabelText('Disease');
    await user.click(diseaseCheckbox);

    expect(onChange).toHaveBeenCalledWith(['drug', 'disease']);
  });

  it('calls onChange with removed value when checked box is clicked', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(
      <CheckboxFilter
        options={mockOptions}
        value={['drug', 'disease']}
        onChange={onChange}
      />
    );

    const drugCheckbox = screen.getByLabelText('Drug');
    await user.click(drugCheckbox);

    expect(onChange).toHaveBeenCalledWith(['disease']);
  });

  it('shows Select All and Deselect All buttons by default', () => {
    const onChange = vi.fn();
    render(<CheckboxFilter options={mockOptions} value={[]} onChange={onChange} />);

    expect(screen.getByText('Select All')).toBeInTheDocument();
    expect(screen.getByText('Deselect All')).toBeInTheDocument();
  });

  it('hides Select All buttons when showSelectAll is false', () => {
    const onChange = vi.fn();
    render(
      <CheckboxFilter
        options={mockOptions}
        value={[]}
        onChange={onChange}
        showSelectAll={false}
      />
    );

    expect(screen.queryByText('Select All')).not.toBeInTheDocument();
    expect(screen.queryByText('Deselect All')).not.toBeInTheDocument();
  });

  it('hides Select All buttons when only one option exists', () => {
    const onChange = vi.fn();
    const singleOption: FilterOption[] = [{ value: 'drug', label: 'Drug' }];
    render(
      <CheckboxFilter options={singleOption} value={[]} onChange={onChange} />
    );

    expect(screen.queryByText('Select All')).not.toBeInTheDocument();
    expect(screen.queryByText('Deselect All')).not.toBeInTheDocument();
  });

  it('selects all options when Select All is clicked', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<CheckboxFilter options={mockOptions} value={[]} onChange={onChange} />);

    const selectAllButton = screen.getByText('Select All');
    await user.click(selectAllButton);

    expect(onChange).toHaveBeenCalledWith(['drug', 'disease', 'symptom']);
  });

  it('deselects all options when Deselect All is clicked', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(
      <CheckboxFilter
        options={mockOptions}
        value={['drug', 'disease', 'symptom']}
        onChange={onChange}
      />
    );

    const deselectAllButton = screen.getByText('Deselect All');
    await user.click(deselectAllButton);

    expect(onChange).toHaveBeenCalledWith([]);
  });

  it('disables Select All when all options are selected', () => {
    const onChange = vi.fn();
    render(
      <CheckboxFilter
        options={mockOptions}
        value={['drug', 'disease', 'symptom']}
        onChange={onChange}
      />
    );

    const selectAllButton = screen.getByText('Select All');
    expect(selectAllButton).toBeDisabled();
  });

  it('disables Deselect All when no options are selected', () => {
    const onChange = vi.fn();
    render(<CheckboxFilter options={mockOptions} value={[]} onChange={onChange} />);

    const deselectAllButton = screen.getByText('Deselect All');
    expect(deselectAllButton).toBeDisabled();
  });

  it('handles numeric option values', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    const numericOptions: FilterOption[] = [
      { value: 1, label: 'Option 1' },
      { value: 2, label: 'Option 2' },
    ];
    render(<CheckboxFilter options={numericOptions} value={[1]} onChange={onChange} />);

    const option2 = screen.getByLabelText('Option 2');
    await user.click(option2);

    expect(onChange).toHaveBeenCalledWith([1, 2]);
  });

  it('handles empty options array', () => {
    const onChange = vi.fn();
    render(<CheckboxFilter options={[]} value={[]} onChange={onChange} />);

    // Should render without crashing
    expect(screen.queryByRole('checkbox')).not.toBeInTheDocument();
  });
});
