/**
 * Tests for InferenceBlock component.
 *
 * Tests inference display logic.
 */
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { InferenceBlock } from '../InferenceBlock';

describe('InferenceBlock', () => {
  it('renders empty state when no relations', () => {
    const mockInference = {
      entity_id: '123',
      relations_by_kind: {},
    };

    render(
      <BrowserRouter>
        <InferenceBlock inference={mockInference} />
      </BrowserRouter>
    );

    expect(screen.getByText(/no inferred/i)).toBeInTheDocument();
  });

  it('groups relations by kind', () => {
    const mockInference = {
      entity_id: '123',
      relations_by_kind: {
        effect: [
          {
            id: '1',
            source_id: 's1',
            kind: 'effect',
            direction: 'positive',
            roles: [],
            created_at: new Date().toISOString(),
          },
          {
            id: '2',
            source_id: 's1',
            kind: 'effect',
            direction: 'negative',
            roles: [],
            created_at: new Date().toISOString(),
          },
        ],
        mechanism: [
          {
            id: '3',
            source_id: 's2',
            kind: 'mechanism',
            direction: 'positive',
            roles: [],
            created_at: new Date().toISOString(),
          },
        ],
      },
    };

    render(
      <BrowserRouter>
        <InferenceBlock inference={mockInference} />
      </BrowserRouter>
    );

    // Should show both kinds
    expect(screen.getByText(/effect/i)).toBeInTheDocument();
    expect(screen.getByText(/mechanism/i)).toBeInTheDocument();

    // Should show counts
    expect(screen.getByText(/2/)).toBeInTheDocument(); // 2 effects
    expect(screen.getByText(/1/)).toBeInTheDocument(); // 1 mechanism
  });

  it('handles null inference gracefully', () => {
    render(
      <BrowserRouter>
        <InferenceBlock inference={null} />
      </BrowserRouter>
    );

    // Should not crash
    expect(screen.queryByText(/effect/i)).not.toBeInTheDocument();
  });
});
