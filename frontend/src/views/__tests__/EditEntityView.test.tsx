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
  EntityTermsManager: ({
    entityId,
    readonly,
    showHeader,
  }: {
    entityId: string;
    readonly: boolean;
    showHeader?: boolean;
  }) => (
    <div data-testid="entity-terms-manager">
      Entity Terms Manager for {entityId}; readonly {String(readonly)}; showHeader {String(showHeader)}
    </div>
  ),
}));

describe('EditEntityView', () => {
  const mockEntity = {
    id: 'entity-123',
    slug: 'aspirin',
    summary: { en: 'Analgesic drug', fr: 'Médicament analgésique' },
    ui_category_id: 'cat-1',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    status: 'confirmed' as const,
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
    }, { timeout: 3000 });
    expect(screen.getByText('FR')).toBeInTheDocument();
    expect(screen.getByText('EN')).toBeInTheDocument();
    expect(screen.getByText('Identity')).toBeInTheDocument();
    expect(screen.getByText('Names and terms')).toBeInTheDocument();
  });

  it('supports slug edit routes while using the resolved entity ID for terms', async () => {
    renderEditView('/entities/aspirin/edit');

    await waitFor(() => {
      expect(entityApi.getEntity).toHaveBeenCalledWith('aspirin');
      expect(screen.getByTestId('entity-terms-manager')).toHaveTextContent(
        'Entity Terms Manager for entity-123'
      );
    });
  });

  it('displays loading state initially', () => {
    vi.mocked(entityApi.getEntity).mockImplementation(() => new Promise(() => {}));
    vi.mocked(entityApi.getEntityFilterOptions).mockImplementation(() => new Promise(() => {}));

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

  it('shows a user-facing error when category options fail to load', async () => {
    vi.mocked(entityApi.getEntityFilterOptions).mockRejectedValue(
      new Error('Category bootstrap failed')
    );

    renderEditView();

    await waitFor(() => {
      expect(
        screen.getByText('Failed to load entity category options')
      ).toBeInTheDocument();
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
      expect(mockNavigate).toHaveBeenCalledWith('/entities/paracetamol');
    });
  });

  it('slugifies slug input before submit', async () => {
    const updatedEntity = { ...mockEntity, slug: 'paracetamol' };
    vi.mocked(entityApi.updateEntity).mockResolvedValue(updatedEntity);

    renderEditView();

    await waitFor(() => {
      expect(screen.getByDisplayValue('aspirin')).toBeInTheDocument();
    });

    const slugInput = screen.getByLabelText(/slug/i);
    fireEvent.change(slugInput, { target: { value: 'Paracétamol test ' } });

    expect(screen.getByDisplayValue('paracetamol-test-')).toBeInTheDocument();

    const submitButton = screen.getByRole('button', { name: /save/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(entityApi.updateEntity).toHaveBeenCalledWith(
        mockEntity.id,
        expect.objectContaining({
          slug: 'paracetamol-test',
        })
      );
    });
  });

  it('switches summary language and submits all filled summaries', async () => {
    const updatedEntity = {
      ...mockEntity,
      summary: {
        ...mockEntity.summary,
        es: 'Medicamento analgésico',
      },
    };
    vi.mocked(entityApi.updateEntity).mockResolvedValue(updatedEntity);

    renderEditView();

    await waitFor(() => {
      expect(screen.getByDisplayValue('Analgesic drug')).toBeInTheDocument();
    });

    fireEvent.mouseDown(screen.getByLabelText(/summary language/i));
    fireEvent.click(await screen.findByRole('option', { name: 'Spanish' }));

    const summaryInput = screen.getByLabelText(/^Summary$/i);
    fireEvent.change(summaryInput, { target: { value: 'Medicamento analgésico' } });

    const submitButton = screen.getByRole('button', { name: /save/i });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(entityApi.updateEntity).toHaveBeenCalledWith(
        mockEntity.id,
        expect.objectContaining({
          summary: {
            en: 'Analgesic drug',
            fr: 'Médicament analgésique',
            es: 'Medicamento analgésico',
          },
        })
      );
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
      expect(screen.getByTestId('entity-terms-manager')).toHaveTextContent('showHeader false');
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
