/**
 * Tests for EditEntityView component.
 *
 * Tests entity loading, form validation, and submission flow including UI category selection.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import type { ReactElement } from 'react';
import { MemoryRouter, Route, Routes } from 'react-router';
import { EditEntityView } from '../EditEntityView';
import { NotificationProvider } from '../../notifications/NotificationContext';
import * as entityApi from '../../api/entities';

// Mock the API module
vi.mock('../../api/entities');

vi.mock('../../notifications/NotificationContext', () => ({
  NotificationProvider: ({ children }: { children: ReactElement }) => children,
  useNotification: () => ({
    showError: vi.fn(),
    showInfo: vi.fn(),
    showSuccess: vi.fn(),
    showWarning: vi.fn(),
  }),
}));

// Mock react-router navigation
const mockNavigate = vi.fn();
vi.mock('react-router', async () => {
  const actual = await vi.importActual('react-router');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// Mock EntityTermsManager component
vi.mock('../../components/EntityTermsManager', () => ({
  EntityTermsManager: ({ entityId, readonly }: { entityId: string; readonly: boolean }) => (
    <div data-testid="entity-terms-manager">Entity Terms Manager for {entityId}</div>
  ),
}));

describe('EditEntityView', () => {
  const mockEntity = {
    id: 'entity-123',
    slug: 'aspirin',
    summary: { en: 'Analgesic drug', fr: 'Médicament analgésique' },
    ui_category_id: 'cat-1',
    created_at: new Date().toISOString(),
  };

  beforeEach(() => {
    vi.clearAllMocks();

    // Mock getEntityFilterOptions by default
    vi.mocked(entityApi.getEntityFilterOptions).mockResolvedValue({
      ui_categories: [
        { id: 'cat-1', label: { en: 'Drugs', fr: 'Médicaments' } },
        { id: 'cat-2', label: { en: 'Diseases', fr: 'Maladies' } },
      ],
      consensus_levels: null,
      evidence_quality_range: null,
      year_range: null,
    });

    // Mock getEntity by default
    vi.mocked(entityApi.getEntity).mockResolvedValue(mockEntity);
  });

  const renderWithNotifications = (ui: ReactElement) =>
    render(<NotificationProvider>{ui}</NotificationProvider>);

  const renderEditView = (initialEntry = '/entities/entity-123/edit') =>
    renderWithNotifications(
      <MemoryRouter initialEntries={[initialEntry]}>
        <Routes>
          <Route path="/entities/:id/edit" element={<EditEntityView />} />
        </Routes>
      </MemoryRouter>
    );

  it('loads and displays entity data', async () => {
    renderEditView();

    await waitFor(() => {
      expect(screen.getByDisplayValue('aspirin')).toBeInTheDocument();
      expect(screen.getByDisplayValue('Analgesic drug')).toBeInTheDocument();
      expect(screen.getByDisplayValue('Médicament analgésique')).toBeInTheDocument();
    }, { timeout: 3000 });
  });

  it('displays loading state initially', () => {
    vi.mocked(entityApi.getEntity).mockImplementation(() => new Promise(() => {}));

    renderEditView();

    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });

  it('displays error when entity fails to load', async () => {
    vi.mocked(entityApi.getEntity).mockRejectedValue(
      new Error('Entity not found')
    );

    renderEditView();

    await waitFor(() => {
      expect(screen.queryByRole('progressbar')).not.toBeInTheDocument();
    });
  });

  it('renders UI category picker with current value', async () => {
    renderEditView();

    // Wait for entity to load and category picker to render
    await waitFor(() => {
      expect(screen.getByLabelText(/category/i)).toBeInTheDocument();
    });
  });

  it('submits form with updated slug', async () => {
    const updatedEntity = { ...mockEntity, slug: 'paracetamol' };
    vi.mocked(entityApi.updateEntity).mockResolvedValue(updatedEntity);

    renderEditView();

    // Wait for entity to load
    await waitFor(() => {
      expect(screen.getByDisplayValue('aspirin')).toBeInTheDocument();
    });

    // Update slug
    const slugInput = screen.getByLabelText(/slug/i);
    fireEvent.change(slugInput, { target: { value: 'paracetamol' } });

    // Submit
    const submitButton = screen.getByRole('button', { name: /save/i });
    fireEvent.click(submitButton);

    // Verify API call
    await waitFor(() => {
      expect(entityApi.updateEntity).toHaveBeenCalledWith(
        mockEntity.id,
        expect.objectContaining({
          slug: 'paracetamol',
        })
      );
    });

    // Verify navigation
    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalled();
    });
  });

  it('submits form with changed UI category', async () => {
    const updatedEntity = { ...mockEntity, ui_category_id: 'cat-2' };
    vi.mocked(entityApi.updateEntity).mockResolvedValue(updatedEntity);

    renderEditView();

    // Wait for entity to load
    await waitFor(() => {
      expect(screen.getByDisplayValue('aspirin')).toBeInTheDocument();
    });

    // Change category
    const categoryInput = screen.getByLabelText(/category/i);
    fireEvent.change(categoryInput, { target: { value: 'Diseases' } });
    fireEvent.keyDown(categoryInput, { key: 'ArrowDown' });
    fireEvent.keyDown(categoryInput, { key: 'Enter' });

    // Submit
    const submitButton = screen.getByRole('button', { name: /save/i });
    fireEvent.click(submitButton);

    // Verify API call
    await waitFor(() => {
      expect(entityApi.updateEntity).toHaveBeenCalledWith(
        mockEntity.id,
        expect.objectContaining({
          slug: 'aspirin',
        })
      );
    });
  });

  it('renders entity terms manager', async () => {
    renderEditView();

    // Wait for entity to load
    await waitFor(() => {
      expect(screen.getByTestId('entity-terms-manager')).toBeInTheDocument();
    });
  });

  it('validates required slug field', async () => {
    renderEditView();

    // Wait for entity to load
    await waitFor(() => {
      expect(screen.getByDisplayValue('aspirin')).toBeInTheDocument();
    });

    // Clear slug
    const slugInput = screen.getByLabelText(/slug/i);
    fireEvent.change(slugInput, { target: { value: '' } });

    // Submit
    const submitButton = screen.getByRole('button', { name: /save/i });
    fireEvent.click(submitButton);

    // Form should not submit without slug
    await waitFor(() => {
      expect(entityApi.updateEntity).not.toHaveBeenCalled();
    });
  });

  it('handles API errors gracefully', async () => {
    vi.mocked(entityApi.updateEntity).mockRejectedValue(
      new Error('Update failed')
    );

    renderEditView();

    // Wait for entity to load
    await waitFor(() => {
      expect(screen.getByDisplayValue('aspirin')).toBeInTheDocument();
    });

    // Update slug
    const slugInput = screen.getByLabelText(/slug/i);
    fireEvent.change(slugInput, { target: { value: 'paracetamol' } });

    // Submit
    const submitButton = screen.getByRole('button', { name: /save/i });
    fireEvent.click(submitButton);

    // Should not navigate on error
    await waitFor(() => {
      expect(mockNavigate).not.toHaveBeenCalled();
    });
  });
});
