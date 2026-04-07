/**
 * Tests for EntityDetailView component.
 *
 * Tests entity display, edit/delete actions, and scope filtering.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import type { ReactNode } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router';
import { EntityDetailView } from '../EntityDetailView';
import { NotificationProvider } from '../../notifications/NotificationContext';
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

vi.mock('../../notifications/NotificationContext', () => ({
  NotificationProvider: ({ children }: { children: ReactNode }) => children,
  useNotification: () => ({
    showError: vi.fn(),
    showInfo: vi.fn(),
    showSuccess: vi.fn(),
    showWarning: vi.fn(),
  }),
}));

vi.mock('../../api/sources', () => ({
  getSource: vi.fn().mockResolvedValue({
    id: 'src-1',
    kind: 'paper',
    title: 'Mock source',
    trust_level: 0.8,
  }),
}));

vi.mock('../../components/entity/EntityDetailHeader', () => ({
  EntityDetailHeader: ({
    entity,
    onDeleteClick,
  }: {
    entity: { slug: string; id: string };
    onDeleteClick: () => void;
  }) => (
    <div>
      <div>{entity.slug}</div>
      <a href={`/entities/${entity.id}/edit`}>Edit</a>
      <button type="button" onClick={onDeleteClick}>
        Delete
      </button>
      <div>Create relation</div>
    </div>
  ),
}));

vi.mock('../../components/entity/InferenceSection', () => ({
  InferenceSection: ({
    scopeFilterPanel,
  }: {
    scopeFilterPanel: ReactNode;
  }) => (
    <section>
      <h2>Related assertions</h2>
      {scopeFilterPanel}
    </section>
  ),
}));

vi.mock('../../components/entity/EntityDeleteDialog', () => ({
  EntityDeleteDialog: ({
    open,
    onClose,
    onConfirm,
  }: {
    open: boolean;
    onClose: () => void;
    onConfirm: () => void;
  }) =>
    open ? (
      <div>
        <div>Delete entity</div>
        <div>Are you sure</div>
        <button type="button" onClick={onClose}>
          Cancel
        </button>
        <button type="button" onClick={onConfirm}>
          Delete
        </button>
      </div>
    ) : null,
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
    <NotificationProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/entities/:id" element={<EntityDetailView />} />
        </Routes>
      </BrowserRouter>
    </NotificationProvider>,
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
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    status: 'confirmed' as const,
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
          updated_at: new Date().toISOString(),
          status: 'confirmed' as const,
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

    it('displays entity slug', async () => {
      renderWithRouter('123e4567-e89b-12d3-a456-426614174000');

      await waitFor(() => {
        expect(screen.getByText('aspirin')).toBeInTheDocument();
      });
    });

    it('loads entity data by slug and fetches inference by resolved UUID', async () => {
      renderWithRouter('aspirin');

      await waitFor(() => {
        expect(getEntity).toHaveBeenCalledWith('aspirin', expect.any(AbortSignal));
        expect(getInferenceForEntity).toHaveBeenCalledWith(
          '123e4567-e89b-12d3-a456-426614174000',
          {}
        );
      });

      expect(mockNavigate).not.toHaveBeenCalledWith(
        '/entities/aspirin',
        expect.objectContaining({ replace: true })
      );
    });

    it('redirects UUID detail URLs to the canonical slug URL', async () => {
      renderWithRouter('123e4567-e89b-12d3-a456-426614174000');

      await waitFor(() => {
        expect(mockNavigate).toHaveBeenCalledWith('/entities/aspirin', { replace: true });
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

    it('shows fetch errors instead of a misleading not found state', async () => {
      (getEntity as any).mockRejectedValue(new Error('Server error while loading entity'));
      (getInferenceForEntity as any).mockResolvedValue(mockInference);

      renderWithRouter('123e4567-e89b-12d3-a456-426614174000');

      await waitFor(() => {
        expect(screen.getByText('Server error while loading entity')).toBeInTheDocument();
      });

      expect(screen.queryByText(/not found/i)).not.toBeInTheDocument();
    });

    it('shows an inline inference error when the inference request fails', async () => {
      (getEntity as any).mockResolvedValue(mockEntity);
      (getInferenceForEntity as any).mockRejectedValue(new Error('Inference service unavailable'));

      renderWithRouter('123e4567-e89b-12d3-a456-426614174000');

      await waitFor(() => {
        expect(screen.getByText('Inference service unavailable')).toBeInTheDocument();
      });

      expect(screen.getByText(/related assertions/i)).toBeInTheDocument();
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
        expect(screen.getByText(/^scope filter$/i)).toBeInTheDocument();
      });
    });

    it('shows filter input fields when accordion expanded', async () => {
      renderWithRouter('123e4567-e89b-12d3-a456-426614174000');

      await waitFor(() => {
        const accordion = screen.getByText(/^scope filter$/i);
        fireEvent.click(accordion);
      });

      await waitFor(() => {
        expect(screen.getByLabelText(/scope dimension/i)).toBeInTheDocument();
        expect(screen.getByLabelText(/value/i)).toBeInTheDocument();
      });
    });

    it('adds filter when Add button clicked', async () => {
      renderWithRouter('123e4567-e89b-12d3-a456-426614174000');

      // Expand accordion
      await waitFor(() => {
        fireEvent.click(screen.getByText(/^scope filter$/i));
      });

      // Fill in filter
      await waitFor(() => {
        fireEvent.click(screen.getByText(/population: adults/i));
        const valueInput = screen.getByLabelText(/value/i);

        fireEvent.change(valueInput, { target: { value: 'adults' } });

        const addButton = screen.getByText('Apply scope filter');
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
        fireEvent.click(screen.getByText(/^scope filter$/i));
      });

      await waitFor(() => {
        fireEvent.click(screen.getByText(/population: adults/i));
        fireEvent.change(screen.getByLabelText(/value/i), {
          target: { value: 'adults' },
        });
        fireEvent.click(screen.getByText('Apply scope filter'));
      });

      // Should show chip
      await waitFor(() => {
        expect(screen.getByText('Population: adults')).toBeInTheDocument();
      });
    });

    it('removes filter when chip deleted', async () => {
      renderWithRouter('123e4567-e89b-12d3-a456-426614174000');

      // Add a filter first
      await waitFor(() => {
        fireEvent.click(screen.getByText(/^scope filter$/i));
      });

      await waitFor(() => {
        fireEvent.click(screen.getByText(/population: adults/i));
        fireEvent.change(screen.getByLabelText(/value/i), {
          target: { value: 'adults' },
        });
        fireEvent.click(screen.getByText('Apply scope filter'));
      });

      // Clear the filter count
      vi.clearAllMocks();

      // Click delete on chip
      await waitFor(() => {
        const chip = screen.getByText('Population: adults');
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
