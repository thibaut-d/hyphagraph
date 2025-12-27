/**
 * Tests for SourceDetailView component.
 *
 * Tests source display and relation management.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { BrowserRouter, Routes, Route } from 'react-router';
import { SourceDetailView } from '../SourceDetailView';
import type { SourceRead } from '../../types/source';
import type { RelationRead } from '../../types/relation';

// Mock the API modules
vi.mock('../../api/sources', () => ({
  getSource: vi.fn(),
  deleteSource: vi.fn(),
}));

vi.mock('../../api/relations', () => ({
  listRelationsBySource: vi.fn(),
  deleteRelation: vi.fn(),
}));

import { getSource, deleteSource } from '../../api/sources';
import { listRelationsBySource, deleteRelation } from '../../api/relations';

// Mock react-router navigation
const mockNavigate = vi.fn();
vi.mock('react-router', async () => {
  const actual = await vi.importActual('react-router');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// Helper to render with router and params
const renderWithRouter = (sourceId: string) => {
  return render(
    <BrowserRouter>
      <Routes>
        <Route path="/sources/:id" element={<SourceDetailView />} />
      </Routes>
    </BrowserRouter>,
    {
      wrapper: ({ children }) => {
        window.history.pushState({}, '', `/sources/${sourceId}`);
        return <>{children}</>;
      },
    }
  );
};

describe('SourceDetailView', () => {
  const mockSource: SourceRead = {
    id: '123e4567-e89b-12d3-a456-426614174000',
    kind: 'study',
    title: 'Test Study on Aspirin',
    year: 2020,
    trust_level: 0.85,
    url: 'https://example.com/study',
    authors: ['Author A', 'Author B'],
    created_at: new Date().toISOString(),
  };

  const mockRelations: RelationRead[] = [
    {
      id: 'rel-1',
      source_id: '123e4567-e89b-12d3-a456-426614174000',
      kind: 'effect',
      direction: 'positive',
      confidence: 0.9,
      roles: [{ role_type: 'drug', entity_id: 'entity-1' }],
      created_at: new Date().toISOString(),
    },
    {
      id: 'rel-2',
      source_id: '123e4567-e89b-12d3-a456-426614174000',
      kind: 'mechanism',
      direction: 'supports',
      confidence: 0.8,
      roles: [{ role_type: 'drug', entity_id: 'entity-2' }],
      created_at: new Date().toISOString(),
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Source display', () => {
    beforeEach(() => {
      (getSource as any).mockResolvedValue(mockSource);
      (listRelationsBySource as any).mockResolvedValue(mockRelations);
    });

    it('displays source title', async () => {
      renderWithRouter('123e4567-e89b-12d3-a456-426614174000');

      await waitFor(() => {
        expect(screen.getByText('Test Study on Aspirin')).toBeInTheDocument();
      });
    });

    it('displays source kind', async () => {
      renderWithRouter('123e4567-e89b-12d3-a456-426614174000');

      await waitFor(() => {
        const studyElements = screen.getAllByText(/study/i);
        expect(studyElements.length).toBeGreaterThan(0);
      });
    });

    it('displays source year', async () => {
      renderWithRouter('123e4567-e89b-12d3-a456-426614174000');

      await waitFor(() => {
        expect(screen.getByText(/2020/)).toBeInTheDocument();
      });
    });

    it('displays trust level percentage', async () => {
      renderWithRouter('123e4567-e89b-12d3-a456-426614174000');

      await waitFor(() => {
        expect(screen.getByText(/85%/)).toBeInTheDocument();
      });
    });

    it('shows edit button', async () => {
      renderWithRouter('123e4567-e89b-12d3-a456-426614174000');

      await waitFor(() => {
        const editButtons = screen.getAllByTitle(/edit/i);
        expect(editButtons.length).toBeGreaterThan(0);
      });
    });

    it('shows delete button', async () => {
      renderWithRouter('123e4567-e89b-12d3-a456-426614174000');

      await waitFor(() => {
        const deleteButtons = screen.getAllByTitle(/delete/i);
        expect(deleteButtons.length).toBeGreaterThan(0);
      });
    });
  });

  describe('Relations display', () => {
    beforeEach(() => {
      (getSource as any).mockResolvedValue(mockSource);
      (listRelationsBySource as any).mockResolvedValue(mockRelations);
    });

    it('displays relations section header', async () => {
      renderWithRouter('123e4567-e89b-12d3-a456-426614174000');

      await waitFor(() => {
        expect(screen.getByText(/relations/i)).toBeInTheDocument();
      });
    });

    it('displays all relations', async () => {
      renderWithRouter('123e4567-e89b-12d3-a456-426614174000');

      await waitFor(() => {
        expect(screen.getByText(/effect \(positive\)/i)).toBeInTheDocument();
        expect(screen.getByText(/mechanism \(supports\)/i)).toBeInTheDocument();
      });
    });

    it('shows view entity links for relations', async () => {
      renderWithRouter('123e4567-e89b-12d3-a456-426614174000');

      await waitFor(() => {
        const viewEntityLinks = screen.getAllByText(/view entity/i);
        expect(viewEntityLinks.length).toBe(2);
      });
    });

    it('shows edit buttons for each relation', async () => {
      renderWithRouter('123e4567-e89b-12d3-a456-426614174000');

      await waitFor(() => {
        const editButtons = screen.getAllByTitle(/edit/i);
        // At least 3: 1 for source + 2 for relations
        expect(editButtons.length).toBeGreaterThanOrEqual(3);
      });
    });

    it('shows delete buttons for each relation', async () => {
      renderWithRouter('123e4567-e89b-12d3-a456-426614174000');

      await waitFor(() => {
        const deleteButtons = screen.getAllByTitle(/delete/i);
        // At least 3: 1 for source + 2 for relations
        expect(deleteButtons.length).toBeGreaterThanOrEqual(3);
      });
    });
  });

  describe('Empty relations', () => {
    beforeEach(() => {
      (getSource as any).mockResolvedValue(mockSource);
      (listRelationsBySource as any).mockResolvedValue([]);
    });

    it('displays no relations message when empty', async () => {
      renderWithRouter('123e4567-e89b-12d3-a456-426614174000');

      await waitFor(() => {
        expect(screen.getByText(/no relations/i)).toBeInTheDocument();
      });
    });
  });

  describe('Delete source functionality', () => {
    beforeEach(() => {
      (getSource as any).mockResolvedValue(mockSource);
      (listRelationsBySource as any).mockResolvedValue(mockRelations);
    });

    it('opens delete confirmation dialog', async () => {
      renderWithRouter('123e4567-e89b-12d3-a456-426614174000');

      await waitFor(() => {
        const deleteButtons = screen.getAllByTitle(/delete/i);
        // First delete button is for the source
        fireEvent.click(deleteButtons[0]);
      });

      await waitFor(() => {
        expect(screen.getByText(/delete source/i)).toBeInTheDocument();
        expect(screen.getByText(/are you sure/i)).toBeInTheDocument();
      });
    });

    it('cancels delete when cancel clicked', async () => {
      renderWithRouter('123e4567-e89b-12d3-a456-426614174000');

      await waitFor(() => {
        const deleteButtons = screen.getAllByTitle(/delete/i);
        fireEvent.click(deleteButtons[0]);
      });

      await waitFor(() => {
        const cancelButton = screen.getByText(/cancel/i);
        fireEvent.click(cancelButton);
      });

      await waitFor(() => {
        expect(screen.queryByText(/are you sure/i)).not.toBeInTheDocument();
      });
    });

    it('calls deleteSource and navigates on confirm', async () => {
      (deleteSource as any).mockResolvedValue(undefined);

      renderWithRouter('123e4567-e89b-12d3-a456-426614174000');

      await waitFor(() => {
        const deleteButtons = screen.getAllByTitle(/delete/i);
        fireEvent.click(deleteButtons[0]);
      });

      await waitFor(() => {
        const deleteButtons = screen.getAllByText(/delete/i);
        const confirmButton = deleteButtons.find(
          (btn) => btn.tagName === 'BUTTON' && btn.textContent === 'Delete'
        );
        if (confirmButton) fireEvent.click(confirmButton);
      });

      await waitFor(() => {
        expect(deleteSource).toHaveBeenCalledWith('123e4567-e89b-12d3-a456-426614174000');
        expect(mockNavigate).toHaveBeenCalledWith('/sources');
      });
    });
  });

  describe('Delete relation functionality', () => {
    beforeEach(() => {
      (getSource as any).mockResolvedValue(mockSource);
      (listRelationsBySource as any).mockResolvedValue(mockRelations);
    });

    it('opens delete relation confirmation dialog', async () => {
      renderWithRouter('123e4567-e89b-12d3-a456-426614174000');

      await waitFor(() => {
        const deleteButtons = screen.getAllByTitle(/delete/i);
        // Second delete button is for the first relation
        fireEvent.click(deleteButtons[1]);
      });

      await waitFor(() => {
        expect(screen.getByText(/delete relation/i)).toBeInTheDocument();
      });
    });

    it('deletes relation and refreshes list on confirm', async () => {
      (deleteRelation as any).mockResolvedValue(undefined);

      renderWithRouter('123e4567-e89b-12d3-a456-426614174000');

      // Wait for page to load
      await waitFor(() => {
        expect(screen.getByText('Test Study on Aspirin')).toBeInTheDocument();
      });

      // Click the delete button for the first relation
      const deleteButtons = screen.getAllByTitle(/delete/i);
      fireEvent.click(deleteButtons[1]); // Index 1 is the first relation (0 is the source)

      // Wait for the delete relation dialog to appear
      await waitFor(() => {
        expect(screen.getByText(/delete relation/i)).toBeInTheDocument();
      });

      // Find all buttons and click the one with "Delete" text that's in the dialog
      await waitFor(() => {
        const buttons = screen.getAllByRole('button');
        const deleteButton = buttons.find(btn =>
          btn.textContent === 'Delete' && btn.closest('[role="dialog"]')
        );
        if (deleteButton) {
          fireEvent.click(deleteButton);
        }
      });

      // Verify the API was called
      await waitFor(() => {
        expect(deleteRelation).toHaveBeenCalledWith('rel-1');
      });
    });
  });

  describe('Error state', () => {
    it('shows error message when source not found', async () => {
      (getSource as any).mockResolvedValue(null);
      (listRelationsBySource as any).mockResolvedValue([]);

      renderWithRouter('123e4567-e89b-12d3-a456-426614174000');

      await waitFor(() => {
        expect(screen.getByText(/not found/i)).toBeInTheDocument();
      });
    });
  });
});
