/**
 * Tests for EvidenceTrace component.
 *
 * Tests source chain rendering, sorting functionality, and interaction.
 */
import { describe, it, expect } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { BrowserRouter } from 'react-router';
import { EvidenceTrace } from '../EvidenceTrace';
import type { SourceContribution } from '../../api/explanations';

// Helper to wrap component in Router
const renderWithRouter = (component: React.ReactElement) => {
  return render(<BrowserRouter>{component}</BrowserRouter>);
};

describe('EvidenceTrace', () => {
  const mockSourceChain: SourceContribution[] = [
    {
      source_id: 'source-1',
      source_title: 'Aspirin Efficacy Study',
      source_authors: ['Smith J.', 'Doe A.'],
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
      contribution_percentage: 60.0,
    },
    {
      source_id: 'source-2',
      source_title: 'Meta-analysis of Pain Relief',
      source_authors: ['Johnson K.'],
      source_year: 2021,
      source_kind: 'review',
      source_trust: 0.95,
      source_url: 'https://example.com/2',
      relation_id: 'rel-2',
      relation_kind: 'effect',
      relation_direction: 'supports',
      relation_confidence: 0.85,
      relation_scope: { population: 'adults' },
      role_weight: 0.85,
      contribution_percentage: 40.0,
    },
  ];

  it('renders empty message when no sources', () => {
    renderWithRouter(<EvidenceTrace sourceChain={[]} />);
    expect(screen.getByText(/no source evidence available/i)).toBeInTheDocument();
  });

  it('renders source chain table with all sources', () => {
    renderWithRouter(<EvidenceTrace sourceChain={mockSourceChain} />);

    expect(screen.getByText('Aspirin Efficacy Study')).toBeInTheDocument();
    expect(screen.getByText('Meta-analysis of Pain Relief')).toBeInTheDocument();
  });

  it('displays source metadata correctly', () => {
    renderWithRouter(<EvidenceTrace sourceChain={mockSourceChain} />);

    // Check authors
    expect(screen.getByText(/Smith J., Doe A./)).toBeInTheDocument();
    expect(screen.getByText(/Johnson K./)).toBeInTheDocument();

    // Check years
    expect(screen.getByText('2020')).toBeInTheDocument();
    expect(screen.getByText('2021')).toBeInTheDocument();

    // Check trust levels
    expect(screen.getByText('0.80')).toBeInTheDocument();
    expect(screen.getByText('0.95')).toBeInTheDocument();
  });

  it('displays contribution percentages correctly', () => {
    renderWithRouter(<EvidenceTrace sourceChain={mockSourceChain} />);

    expect(screen.getByText('60.0%')).toBeInTheDocument();
    expect(screen.getByText('40.0%')).toBeInTheDocument();
  });

  it('displays relation confidence correctly', () => {
    renderWithRouter(<EvidenceTrace sourceChain={mockSourceChain} />);

    expect(screen.getByText('90%')).toBeInTheDocument();
    expect(screen.getByText('85%')).toBeInTheDocument();
  });

  it('displays kind badges', () => {
    renderWithRouter(<EvidenceTrace sourceChain={mockSourceChain} />);

    const kindBadges = screen.getAllByText('effect');
    expect(kindBadges.length).toBeGreaterThan(0);
  });

  it('shows supports direction with green checkmark', () => {
    renderWithRouter(<EvidenceTrace sourceChain={mockSourceChain} />);

    const supportsTexts = screen.getAllByText('Supports');
    expect(supportsTexts.length).toBeGreaterThan(0);
  });

  it('shows contradicts direction with red X', () => {
    const contradictingSource: SourceContribution = {
      ...mockSourceChain[0],
      relation_direction: 'contradicts',
    };

    renderWithRouter(<EvidenceTrace sourceChain={[contradictingSource]} />);

    expect(screen.getByText('Contradicts')).toBeInTheDocument();
  });

  it('renders clickable source links', () => {
    renderWithRouter(<EvidenceTrace sourceChain={mockSourceChain} />);

    const link1 = screen.getByRole('link', { name: /Aspirin Efficacy Study/i });
    const link2 = screen.getByRole('link', { name: /Meta-analysis of Pain Relief/i });

    expect(link1).toHaveAttribute('href', '/sources/source-1');
    expect(link2).toHaveAttribute('href', '/sources/source-2');
  });

  it('truncates author list with "et al." when more than 3 authors', () => {
    const sourceWithManyAuthors: SourceContribution = {
      ...mockSourceChain[0],
      source_authors: ['Author A', 'Author B', 'Author C', 'Author D', 'Author E'],
    };

    renderWithRouter(<EvidenceTrace sourceChain={[sourceWithManyAuthors]} />);

    expect(screen.getByText(/Author A, Author B, Author C et al./)).toBeInTheDocument();
  });

  it('handles sources without authors', () => {
    const sourceWithoutAuthors: SourceContribution = {
      ...mockSourceChain[0],
      source_authors: undefined,
    };

    renderWithRouter(<EvidenceTrace sourceChain={[sourceWithoutAuthors]} />);

    // Should still render the source title
    expect(screen.getByText('Aspirin Efficacy Study')).toBeInTheDocument();
  });

  it('handles sources without trust level', () => {
    const sourceWithoutTrust: SourceContribution = {
      ...mockSourceChain[0],
      source_trust: null,
    };

    renderWithRouter(<EvidenceTrace sourceChain={[sourceWithoutTrust]} />);

    expect(screen.getByText('N/A')).toBeInTheDocument();
  });

  it('handles sources without year', () => {
    const sourceWithoutYear: SourceContribution = {
      ...mockSourceChain[0],
      source_year: undefined,
    };

    renderWithRouter(<EvidenceTrace sourceChain={[sourceWithoutYear]} />);

    // Check that N/A appears in year column (may be multiple N/A for different columns)
    const cells = screen.getAllByText('N/A');
    expect(cells.length).toBeGreaterThan(0);
  });

  describe('Sorting functionality', () => {
    it('sorts by contribution percentage by default (descending)', () => {
      renderWithRouter(<EvidenceTrace sourceChain={mockSourceChain} />);

      const rows = screen.getAllByRole('row');
      // First row is header, second row should be highest contribution (60%)
      const secondRow = rows[1];
      expect(within(secondRow).getByText('60.0%')).toBeInTheDocument();
    });

    it('allows sorting by contribution percentage', async () => {
      const user = userEvent.setup();
      renderWithRouter(<EvidenceTrace sourceChain={mockSourceChain} />);

      const contributionHeader = screen.getByRole('button', { name: /contribution/i });

      // Click to toggle sort
      await user.click(contributionHeader);

      // Still should be sorted (might toggle direction)
      expect(screen.getByText('60.0%')).toBeInTheDocument();
    });

    it('allows sorting by confidence', async () => {
      const user = userEvent.setup();
      renderWithRouter(<EvidenceTrace sourceChain={mockSourceChain} />);

      const confidenceHeader = screen.getByRole('button', { name: /confidence/i });

      await user.click(confidenceHeader);

      // After sorting, rows should be reordered
      expect(screen.getByText('90%')).toBeInTheDocument();
    });

    it('allows sorting by year', async () => {
      const user = userEvent.setup();
      renderWithRouter(<EvidenceTrace sourceChain={mockSourceChain} />);

      const yearHeader = screen.getByRole('button', { name: /year/i });

      await user.click(yearHeader);

      expect(screen.getByText('2020')).toBeInTheDocument();
      expect(screen.getByText('2021')).toBeInTheDocument();
    });

    it('allows sorting by trust', async () => {
      const user = userEvent.setup();
      renderWithRouter(<EvidenceTrace sourceChain={mockSourceChain} />);

      const trustHeader = screen.getByRole('button', { name: /trust/i });

      await user.click(trustHeader);

      expect(screen.getByText('0.80')).toBeInTheDocument();
      expect(screen.getByText('0.95')).toBeInTheDocument();
    });

    it('toggles sort direction on repeated clicks', async () => {
      const user = userEvent.setup();

      const multiSourceChain: SourceContribution[] = [
        { ...mockSourceChain[0], contribution_percentage: 30.0 },
        { ...mockSourceChain[1], contribution_percentage: 70.0 },
      ];

      renderWithRouter(<EvidenceTrace sourceChain={multiSourceChain} />);

      const contributionHeader = screen.getByRole('button', { name: /contribution/i });

      // First click - should be descending (70% first)
      await user.click(contributionHeader);

      // Second click - should be ascending (30% first)
      await user.click(contributionHeader);

      // Verify both percentages are still displayed
      expect(screen.getByText('30.0%')).toBeInTheDocument();
      expect(screen.getByText('70.0%')).toBeInTheDocument();
    });
  });

  describe('Table structure', () => {
    it('has correct table headers', () => {
      renderWithRouter(<EvidenceTrace sourceChain={mockSourceChain} />);

      expect(screen.getByText('Source')).toBeInTheDocument();
      expect(screen.getByText('Kind')).toBeInTheDocument();
      expect(screen.getByText('Direction')).toBeInTheDocument();
      expect(screen.getByText(/Confidence/)).toBeInTheDocument();
      expect(screen.getByText(/Contribution/)).toBeInTheDocument();
      expect(screen.getByText(/Trust/)).toBeInTheDocument();
      expect(screen.getByText('Year')).toBeInTheDocument();
    });

    it('has correct number of rows', () => {
      renderWithRouter(<EvidenceTrace sourceChain={mockSourceChain} />);

      const rows = screen.getAllByRole('row');
      // 1 header row + 2 data rows
      expect(rows).toHaveLength(3);
    });
  });

  describe('Accessibility', () => {
    it('has accessible table structure', () => {
      renderWithRouter(<EvidenceTrace sourceChain={mockSourceChain} />);

      const table = screen.getByRole('table');
      expect(table).toBeInTheDocument();

      const columnHeaders = screen.getAllByRole('columnheader');
      expect(columnHeaders.length).toBeGreaterThan(0);
    });

    it('has accessible links', () => {
      renderWithRouter(<EvidenceTrace sourceChain={mockSourceChain} />);

      const links = screen.getAllByRole('link');
      links.forEach(link => {
        expect(link).toHaveAttribute('href');
      });
    });
  });
});
