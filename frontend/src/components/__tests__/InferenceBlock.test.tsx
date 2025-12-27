/**
 * Tests for InferenceBlock component.
 *
 * Tests inference display logic.
 */
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router';
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

    // Should show Source Evidence header but no relation cards
    expect(screen.getByText(/source evidence/i)).toBeInTheDocument();
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
            confidence: 0.8,
            roles: [],
            created_at: new Date().toISOString(),
          },
          {
            id: '2',
            source_id: 's1',
            kind: 'effect',
            direction: 'negative',
            confidence: 0.7,
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
            confidence: 0.9,
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

    // Should show confidence values
    expect(screen.getByText(/confidence: 0.8/i)).toBeInTheDocument();
    expect(screen.getByText(/confidence: 0.7/i)).toBeInTheDocument();
    expect(screen.getByText(/confidence: 0.9/i)).toBeInTheDocument();
  });

  it('handles null inference gracefully', () => {
    render(
      <BrowserRouter>
        <InferenceBlock inference={null} />
      </BrowserRouter>
    );

    // Should not crash - component returns null for null inference
    expect(screen.queryByText(/source evidence/i)).not.toBeInTheDocument();
  });
});
