/**
 * Tests for EntityDetailView component.
 *
 * Tests entity display, edit/delete actions, and scope filtering.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { BrowserRouter, Routes, Route } from 'react-router';
import { EntityDetailView } from '../EntityDetailView';
import type { EntityRead } from '../../types/entity';
import type { InferenceRead } from '../../types/inference';

// Mock the API modules
vi.mock('../../api/entities', () => ({
  getEntity: vi.fn(),
  deleteEntity: vi.fn(),
}));

vi.mock('../../api/inferences', () => ({
  getInferenceForEntity: vi.fn(),
}));

import { getEntity, deleteEntity } from '../../api/entities';
import { getInferenceForEntity } from '../../api/inferences';

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
const renderWithRouter = (entityId: string) => {
  return render(
    <BrowserRouter>
      <Routes>
        <Route path="/entities/:id" element={<EntityDetailView />} />
      </Routes>
    </BrowserRouter>,
    {
      wrapper: ({ children }) => {
        // Set up location to match the route
        window.history.pushState({}, '', `/entities/${entityId}`);
        return <>{children}</>;
      },
    }
  );
};

describe('EntityDetailView', () => {
  const mockEntity: EntityRead = {
    id: '123e4567-e89b-12d3-a456-426614174000',
    slug: 'aspirin',
    kind: 'drug',
    label: 'Aspirin',
    label_i18n: {},
    summaries: {},
    created_at: new Date().toISOString(),
  };

  const mockInference: InferenceRead = {
    entity_id: '123e4567-e89b-12d3-a456-426614174000',
    relations_by_kind: {
      effect: [
        {
          id: 'rel-1',
          source_id: 'src-1',
          kind: 'effect',
          direction: 'positive',
          confidence: 0.9,
          roles: [],
          created_at: new Date().toISOString(),
        },
      ],
    },
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Loading state', () => {
    it('shows loading spinner initially', () => {
      (getEntity as any).mockImplementation(() => new Promise(() => {})); // Never resolves
      (getInferenceForEntity as any).mockImplementation(() => new Promise(() => {}));

      renderWithRouter('123e4567-e89b-12d3-a456-426614174000');

      expect(screen.getByRole('progressbar')).toBeInTheDocument();
    });
  });

  describe('Entity display', () => {
    beforeEach(() => {
      (getEntity as any).mockResolvedValue(mockEntity);
      (getInferenceForEntity as any).mockResolvedValue(mockInference);
    });

    it('displays entity slug and kind', async () => {
      renderWithRouter('123e4567-e89b-12d3-a456-426614174000');

      await waitFor(() => {
        expect(screen.getByText('aspirin')).toBeInTheDocument();
        expect(screen.getByText('drug')).toBeInTheDocument();
      });
    });

    it('shows edit button', async () => {
      renderWithRouter('123e4567-e89b-12d3-a456-426614174000');

      await waitFor(() => {
        const editButton = screen.getByRole('link', { name: /edit/i });
        expect(editButton).toBeInTheDocument();
      });
    });

    it('shows delete button', async () => {
      renderWithRouter('123e4567-e89b-12d3-a456-426614174000');

      await waitFor(() => {
        const deleteButton = screen.getByRole('button', { name: /delete/i });
        expect(deleteButton).toBeInTheDocument();
      });
    });

    it('shows create relation button', async () => {
      renderWithRouter('123e4567-e89b-12d3-a456-426614174000');

      await waitFor(() => {
        const createButton = screen.getByText(/create relation/i);
        expect(createButton).toBeInTheDocument();
      });
    });

    it('displays inference section', async () => {
      renderWithRouter('123e4567-e89b-12d3-a456-426614174000');

      await waitFor(() => {
        expect(screen.getByText(/related assertions/i)).toBeInTheDocument();
      });
    });
  });

  describe('Delete functionality', () => {
    beforeEach(() => {
      (getEntity as any).mockResolvedValue(mockEntity);
      (getInferenceForEntity as any).mockResolvedValue(mockInference);
    });

    it('opens delete confirmation dialog', async () => {
      renderWithRouter('123e4567-e89b-12d3-a456-426614174000');

      await waitFor(() => {
        const deleteButton = screen.getByRole('button', { name: /delete/i });
        fireEvent.click(deleteButton);
      });

      await waitFor(() => {
        expect(screen.getByText(/delete entity/i)).toBeInTheDocument();
        expect(screen.getByText(/are you sure/i)).toBeInTheDocument();
      });
    });

    it('cancels delete when cancel clicked', async () => {
      renderWithRouter('123e4567-e89b-12d3-a456-426614174000');

      await waitFor(() => {
        const deleteButton = screen.getByRole('button', { name: /delete/i });
        fireEvent.click(deleteButton);
      });

      await waitFor(() => {
        const cancelButton = screen.getByText(/cancel/i);
        fireEvent.click(cancelButton);
      });

      await waitFor(() => {
        expect(screen.queryByText(/are you sure/i)).not.toBeInTheDocument();
      });
    });

    it('calls deleteEntity and navigates on confirm', async () => {
      (deleteEntity as any).mockResolvedValue(undefined);

      renderWithRouter('123e4567-e89b-12d3-a456-426614174000');

      // Click the main delete button to open dialog
      await waitFor(() => {
        const deleteButton = screen.getByRole('button', { name: /delete/i });
        fireEvent.click(deleteButton);
      });

      // Wait for dialog to open and click the confirm delete button
      await waitFor(() => {
        expect(screen.getByText(/delete entity/i)).toBeInTheDocument();
      });

      const deleteButtons = screen.getAllByRole('button', { name: /delete/i });
      // The confirm button is the second one (first is the main delete button, second is in dialog)
      const confirmButton = deleteButtons[deleteButtons.length - 1];
      fireEvent.click(confirmButton);

      await waitFor(() => {
        expect(deleteEntity).toHaveBeenCalledWith('123e4567-e89b-12d3-a456-426614174000');
        expect(mockNavigate).toHaveBeenCalledWith('/entities');
      });
    });
  });

  describe('Scope filtering', () => {
    beforeEach(() => {
      (getEntity as any).mockResolvedValue(mockEntity);
      (getInferenceForEntity as any).mockResolvedValue(mockInference);
    });

    it('displays scope filter accordion', async () => {
      renderWithRouter('123e4567-e89b-12d3-a456-426614174000');

      await waitFor(() => {
        expect(screen.getByText(/scope filter/i)).toBeInTheDocument();
      });
    });

    it('shows filter input fields when accordion expanded', async () => {
      renderWithRouter('123e4567-e89b-12d3-a456-426614174000');

      await waitFor(() => {
        const accordion = screen.getByText(/scope filter/i);
        fireEvent.click(accordion);
      });

      await waitFor(() => {
        expect(screen.getByLabelText(/attribute/i)).toBeInTheDocument();
        expect(screen.getByLabelText(/value/i)).toBeInTheDocument();
      });
    });

    it('adds filter when Add button clicked', async () => {
      renderWithRouter('123e4567-e89b-12d3-a456-426614174000');

      // Expand accordion
      await waitFor(() => {
        fireEvent.click(screen.getByText(/scope filter/i));
      });

      // Fill in filter
      await waitFor(() => {
        const attributeInput = screen.getByLabelText(/attribute/i);
        const valueInput = screen.getByLabelText(/value/i);

        fireEvent.change(attributeInput, { target: { value: 'population' } });
        fireEvent.change(valueInput, { target: { value: 'adults' } });

        const addButton = screen.getByText('Add');
        fireEvent.click(addButton);
      });

      // Should reload inference with filter
      await waitFor(() => {
        expect(getInferenceForEntity).toHaveBeenCalledWith(
          '123e4567-e89b-12d3-a456-426614174000',
          { population: 'adults' }
        );
      });
    });

    it('displays active filter chips', async () => {
      renderWithRouter('123e4567-e89b-12d3-a456-426614174000');

      // Add a filter
      await waitFor(() => {
        fireEvent.click(screen.getByText(/scope filter/i));
      });

      await waitFor(() => {
        fireEvent.change(screen.getByLabelText(/attribute/i), {
          target: { value: 'population' },
        });
        fireEvent.change(screen.getByLabelText(/value/i), {
          target: { value: 'adults' },
        });
        fireEvent.click(screen.getByText('Add'));
      });

      // Should show chip
      await waitFor(() => {
        expect(screen.getByText(/population: adults/i)).toBeInTheDocument();
      });
    });

    it('removes filter when chip deleted', async () => {
      renderWithRouter('123e4567-e89b-12d3-a456-426614174000');

      // Add a filter first
      await waitFor(() => {
        fireEvent.click(screen.getByText(/scope filter/i));
      });

      await waitFor(() => {
        fireEvent.change(screen.getByLabelText(/attribute/i), {
          target: { value: 'population' },
        });
        fireEvent.change(screen.getByLabelText(/value/i), {
          target: { value: 'adults' },
        });
        fireEvent.click(screen.getByText('Add'));
      });

      // Clear the filter count
      vi.clearAllMocks();

      // Click delete on chip
      await waitFor(() => {
        const chip = screen.getByText(/population: adults/i);
        const deleteIcon = chip.parentElement?.querySelector('[data-testid="CancelIcon"]');
        if (deleteIcon) fireEvent.click(deleteIcon);
      });

      // Should reload without filter
      await waitFor(() => {
        expect(getInferenceForEntity).toHaveBeenCalledWith(
          '123e4567-e89b-12d3-a456-426614174000',
          {}
        );
      });
    });
  });

  describe('Error state', () => {
    it('shows error message when entity not found', async () => {
      (getEntity as any).mockResolvedValue(null);
      (getInferenceForEntity as any).mockResolvedValue(null);

      renderWithRouter('123e4567-e89b-12d3-a456-426614174000');

      await waitFor(() => {
        expect(screen.getByText(/not found/i)).toBeInTheDocument();
      });
    });
  });
});
