/**
 * Tests for ExplanationView component.
 *
 * Tests explanation display, loading states, error handling,
 * and interaction with explanation data.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { BrowserRouter, Routes, Route } from 'react-router';
import { ExplanationView } from '../ExplanationView';
import type { ExplanationRead } from '../../api/explanations';

// Mock the explanations API
vi.mock('../../api/explanations', () => ({
  getExplanation: vi.fn(),
}));

import { getExplanation } from '../../api/explanations';

// Helper to render with router and params
const renderWithRouter = (entityId: string, roleType: string) => {
  return render(
    <BrowserRouter>
      <Routes>
        <Route path="/explain/:entityId/:roleType" element={<ExplanationView />} />
      </Routes>
    </BrowserRouter>,
    { wrapper: ({ children }) => {
      // Set up location to match the route
      window.history.pushState({}, '', `/explain/${entityId}/${roleType}`);
      return <>{children}</>;
    }}
  );
};

describe('ExplanationView', () => {
  const mockExplanation: ExplanationRead = {
    entity_id: '123e4567-e89b-12d3-a456-426614174000',
    role_type: 'drug',
    score: 0.75,
    confidence: 0.85,
    disagreement: 0.15,
    summary: 'Based on 3 sources, this shows a strong positive effect (score: 0.75) with high confidence (85%). Some contradictions detected among sources.',
    confidence_factors: [
      {
        factor: 'Coverage',
        value: 2.7,
        explanation: 'Total information coverage from 3 sources',
      },
      {
        factor: 'Confidence',
        value: 0.85,
        explanation: 'Confidence based on coverage (exponential saturation model)',
      },
      {
        factor: 'Disagreement',
        value: 0.15,
        explanation: 'Measure of contradiction between sources (higher = more disagreement)',
      },
    ],
    contradictions: {
      supporting_sources: [],
      contradicting_sources: [],
      disagreement_score: 0.15,
    },
    source_chain: [
      {
        source_id: 'source-1',
        source_title: 'Study 1',
        source_authors: ['Author A'],
        source_year: 2020,
        source_kind: 'study',
        source_trust: 0.8,
        source_url: 'https://example.com/1',
        relation_id: 'rel-1',
        relation_kind: 'effect',
        relation_direction: 'supports',
        relation_confidence: 0.9,
        relation_scope: null,
        role_weight: 0.9,
        contribution_percentage: 100.0,
      },
    ],
    scope_filter: null,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Loading state', () => {
    it('shows loading spinner initially', async () => {
      (getExplanation as any).mockImplementation(() => new Promise(() => {})); // Never resolves

      renderWithRouter('123e4567-e89b-12d3-a456-426614174000', 'drug');

      expect(screen.getByRole('progressbar')).toBeInTheDocument();
      expect(screen.getByText(/generating explanation/i)).toBeInTheDocument();
    });
  });

  describe('Error state', () => {
    it('displays error message when API call fails', async () => {
      (getExplanation as any).mockRejectedValue(new Error('Failed to load'));

      renderWithRouter('123e4567-e89b-12d3-a456-426614174000', 'drug');

      await waitFor(() => {
        expect(screen.getByText(/failed to load/i)).toBeInTheDocument();
      });
    });

    it('displays error when entity ID is missing', async () => {
      render(
        <BrowserRouter>
          <ExplanationView />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText(/missing entity id or role type/i)).toBeInTheDocument();
      });
    });
  });

  describe('Successful explanation display', () => {
    beforeEach(() => {
      (getExplanation as any).mockResolvedValue(mockExplanation);
    });

    it('displays explanation header', async () => {
      renderWithRouter('123e4567-e89b-12d3-a456-426614174000', 'drug');

      await waitFor(() => {
        const headers = screen.getAllByText(/inference explanation/i);
        expect(headers.length).toBeGreaterThan(0);
        expect(screen.getByText('drug')).toBeInTheDocument();
      });
    });

    it('displays score chip with value', async () => {
      renderWithRouter('123e4567-e89b-12d3-a456-426614174000', 'drug');

      await waitFor(() => {
        const scores = screen.getAllByText(/Score.*0.75/i);
        expect(scores.length).toBeGreaterThan(0);
      });
    });

    it('displays confidence chip with percentage', async () => {
      renderWithRouter('123e4567-e89b-12d3-a456-426614174000', 'drug');

      await waitFor(() => {
        const confidences = screen.getAllByText(/Confidence.*85%/i);
        expect(confidences.length).toBeGreaterThan(0);
      });
    });

    it('displays disagreement chip', async () => {
      renderWithRouter('123e4567-e89b-12d3-a456-426614174000', 'drug');

      await waitFor(() => {
        expect(screen.getByText(/Disagreement.*15%/i)).toBeInTheDocument();
      });
    });

    it('displays natural language summary', async () => {
      renderWithRouter('123e4567-e89b-12d3-a456-426614174000', 'drug');

      await waitFor(() => {
        expect(screen.getByText(/Based on 3 sources/i)).toBeInTheDocument();
      });
    });

    it('displays confidence breakdown section', async () => {
      renderWithRouter('123e4567-e89b-12d3-a456-426614174000', 'drug');

      await waitFor(() => {
        expect(screen.getByText(/confidence breakdown/i)).toBeInTheDocument();
        expect(screen.getByText('Coverage')).toBeInTheDocument();
        expect(screen.getByText('2.70')).toBeInTheDocument();
      });
    });

    it('displays all confidence factors', async () => {
      renderWithRouter('123e4567-e89b-12d3-a456-426614174000', 'drug');

      await waitFor(() => {
        expect(screen.getByText('Coverage')).toBeInTheDocument();
        const confidences = screen.getAllByText('Confidence');
        expect(confidences.length).toBeGreaterThan(0);
        expect(screen.getByText('Disagreement')).toBeInTheDocument();
      });
    });

    it('displays source evidence section', async () => {
      renderWithRouter('123e4567-e89b-12d3-a456-426614174000', 'drug');

      await waitFor(() => {
        expect(screen.getByText(/source evidence/i)).toBeInTheDocument();
      });
    });

    it('renders EvidenceTrace component', async () => {
      renderWithRouter('123e4567-e89b-12d3-a456-426614174000', 'drug');

      await waitFor(() => {
        // Should render the source chain table
        expect(screen.getByRole('table')).toBeInTheDocument();
      });
    });
  });

  describe('Score color coding', () => {
    it('shows success color for positive score > 0.3', async () => {
      const positiveExplanation = {
        ...mockExplanation,
        score: 0.75,
      };

      (getExplanation as any).mockResolvedValue(positiveExplanation);

      renderWithRouter('123e4567-e89b-12d3-a456-426614174000', 'drug');

      await waitFor(() => {
        const scores = screen.getAllByText(/Score.*0.75/i);
        const scoreChip = scores[0].closest('.MuiChip-root');
        expect(scoreChip).toHaveClass('MuiChip-colorSuccess');
      });
    });

    it('shows error color for negative score < -0.3', async () => {
      const negativeExplanation = {
        ...mockExplanation,
        score: -0.75,
      };

      (getExplanation as any).mockResolvedValue(negativeExplanation);

      renderWithRouter('123e4567-e89b-12d3-a456-426614174000', 'drug');

      await waitFor(() => {
        const scoreChip = screen.getByText(/Score.*-0.75/i).closest('.MuiChip-root');
        expect(scoreChip).toHaveClass('MuiChip-colorError');
      });
    });

    it('shows warning color for neutral score', async () => {
      const neutralExplanation = {
        ...mockExplanation,
        score: 0.1,
      };

      (getExplanation as any).mockResolvedValue(neutralExplanation);

      renderWithRouter('123e4567-e89b-12d3-a456-426614174000', 'drug');

      await waitFor(() => {
        const scoreChip = screen.getByText(/Score.*0.10/i).closest('.MuiChip-root');
        expect(scoreChip).toHaveClass('MuiChip-colorWarning');
      });
    });
  });

  describe('Confidence color coding', () => {
    it('shows success color for high confidence > 0.7', async () => {
      const highConfExplanation = {
        ...mockExplanation,
        confidence: 0.85,
      };

      (getExplanation as any).mockResolvedValue(highConfExplanation);

      renderWithRouter('123e4567-e89b-12d3-a456-426614174000', 'drug');

      await waitFor(() => {
        const confidences = screen.getAllByText(/Confidence.*85%/i);
        const confChip = confidences[0].closest('.MuiChip-root');
        expect(confChip).toHaveClass('MuiChip-colorSuccess');
      });
    });

    it('shows warning color for moderate confidence', async () => {
      const modConfExplanation = {
        ...mockExplanation,
        confidence: 0.6,
      };

      (getExplanation as any).mockResolvedValue(modConfExplanation);

      renderWithRouter('123e4567-e89b-12d3-a456-426614174000', 'drug');

      await waitFor(() => {
        const confChip = screen.getByText(/Confidence.*60%/i).closest('.MuiChip-root');
        expect(confChip).toHaveClass('MuiChip-colorWarning');
      });
    });
  });

  describe('Contradiction display', () => {
    it('shows contradiction warning for high disagreement > 0.5', async () => {
      const highDisagreement = {
        ...mockExplanation,
        disagreement: 0.6,
        contradictions: {
          supporting_sources: [],
          contradicting_sources: [],
          disagreement_score: 0.6,
        },
      };

      (getExplanation as any).mockResolvedValue(highDisagreement);

      renderWithRouter('123e4567-e89b-12d3-a456-426614174000', 'drug');

      await waitFor(() => {
        expect(screen.getByText(/contradictory evidence/i)).toBeInTheDocument();
        expect(screen.getByText(/high disagreement detected/i)).toBeInTheDocument();
      });
    });

    it('shows moderate contradiction warning for 0.1 < disagreement < 0.5', async () => {
      const moderateDisagreement = {
        ...mockExplanation,
        disagreement: 0.3,
        contradictions: {
          supporting_sources: [],
          contradicting_sources: [],
          disagreement_score: 0.3,
        },
      };

      (getExplanation as any).mockResolvedValue(moderateDisagreement);

      renderWithRouter('123e4567-e89b-12d3-a456-426614174000', 'drug');

      await waitFor(() => {
        expect(screen.getByText(/some disagreement detected/i)).toBeInTheDocument();
      });
    });

    it('hides contradiction section for low disagreement', async () => {
      const lowDisagreement = {
        ...mockExplanation,
        disagreement: 0.05,
        contradictions: null,
      };

      (getExplanation as any).mockResolvedValue(lowDisagreement);

      renderWithRouter('123e4567-e89b-12d3-a456-426614174000', 'drug');

      await waitFor(() => {
        expect(screen.queryByText(/contradictory evidence/i)).not.toBeInTheDocument();
      });
    });
  });

  describe('Scope filter display', () => {
    it('displays scope filter chips when filter is applied', async () => {
      const scopedExplanation = {
        ...mockExplanation,
        scope_filter: { population: 'adults', condition: 'chronic_pain' },
      };

      (getExplanation as any).mockResolvedValue(scopedExplanation);

      renderWithRouter('123e4567-e89b-12d3-a456-426614174000', 'drug');

      await waitFor(() => {
        expect(screen.getByText(/applied scope filter/i)).toBeInTheDocument();
        expect(screen.getByText(/population.*adults/i)).toBeInTheDocument();
        expect(screen.getByText(/condition.*chronic_pain/i)).toBeInTheDocument();
      });
    });

    it('hides scope filter section when no filter applied', async () => {
      const noScopeExplanation = {
        ...mockExplanation,
        scope_filter: null,
      };

      (getExplanation as any).mockResolvedValue(noScopeExplanation);

      renderWithRouter('123e4567-e89b-12d3-a456-426614174000', 'drug');

      await waitFor(() => {
        expect(screen.queryByText(/applied scope filter/i)).not.toBeInTheDocument();
      });
    });

    it('hides scope filter section for empty filter object', async () => {
      const emptyScopeExplanation = {
        ...mockExplanation,
        scope_filter: {},
      };

      (getExplanation as any).mockResolvedValue(emptyScopeExplanation);

      renderWithRouter('123e4567-e89b-12d3-a456-426614174000', 'drug');

      await waitFor(() => {
        expect(screen.queryByText(/applied scope filter/i)).not.toBeInTheDocument();
      });
    });
  });

  describe('Navigation', () => {
    beforeEach(() => {
      (getExplanation as any).mockResolvedValue(mockExplanation);
    });

    it('displays breadcrumb navigation', async () => {
      renderWithRouter('123e4567-e89b-12d3-a456-426614174000', 'drug');

      await waitFor(() => {
        expect(screen.getByText(/back to entity/i)).toBeInTheDocument();
      });
    });

    it('has link back to entity detail', async () => {
      renderWithRouter('123e4567-e89b-12d3-a456-426614174000', 'drug');

      await waitFor(() => {
        const backLink = screen.getByText(/back to entity/i).closest('a');
        expect(backLink).toHaveAttribute('href', '/entities/123e4567-e89b-12d3-a456-426614174000');
      });
    });

    it('has back arrow icon that navigates to entity', async () => {
      renderWithRouter('123e4567-e89b-12d3-a456-426614174000', 'drug');

      await waitFor(() => {
        // ArrowBackIcon should be present
        const svg = document.querySelector('[data-testid="ArrowBackIcon"]');
        expect(svg).toBeInTheDocument();
      });
    });
  });

  describe('Null score handling', () => {
    it('displays N/A for null score', async () => {
      const nullScoreExplanation = {
        ...mockExplanation,
        score: null,
      };

      (getExplanation as any).mockResolvedValue(nullScoreExplanation);

      renderWithRouter('123e4567-e89b-12d3-a456-426614174000', 'drug');

      await waitFor(() => {
        expect(screen.getByText(/Score.*N\/A/i)).toBeInTheDocument();
      });
    });
  });
});
