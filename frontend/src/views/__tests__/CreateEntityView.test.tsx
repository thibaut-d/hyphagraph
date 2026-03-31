/**
 * Tests for CreateEntityView component.
 *
 * Tests form validation and submission flow.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router';
import { CreateEntityView } from '../CreateEntityView';
import { NotificationProvider } from '../../notifications/NotificationContext';
import * as entityApi from '../../api/entities';

const translate = (key: string, defaultValueOrOptions?: string | { defaultValue?: string }) => {
  if (typeof defaultValueOrOptions === 'string') {
    return defaultValueOrOptions;
  }
  return defaultValueOrOptions?.defaultValue || key;
};

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: translate,
    i18n: { language: 'en' },
  }),
  initReactI18next: { type: '3rdParty', init: () => {} },
}));

// Mock the API module
vi.mock('../../api/entities');

// Mock react-router navigation
const mockNavigate = vi.fn();
vi.mock('react-router', async () => {
  const actual = await vi.importActual('react-router');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

const renderWithProviders = () =>
  render(
    <NotificationProvider>
      <BrowserRouter>
        <CreateEntityView />
      </BrowserRouter>
    </NotificationProvider>
  );

describe('CreateEntityView', () => {
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
  });

  it('renders form with required fields', async () => {
    renderWithProviders();

    expect(screen.getByLabelText(/slug/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /create/i })).toBeInTheDocument();
    await waitFor(() => {
      expect(entityApi.getEntityFilterOptions).toHaveBeenCalled();
    });
  });

  it('validates required slug field', async () => {
    renderWithProviders();

    const submitButton = screen.getByRole('button', { name: /create/i });
    fireEvent.click(submitButton);

    // Form should not submit without slug
    await waitFor(() => {
      expect(entityApi.createEntity).not.toHaveBeenCalled();
    });
  });

  it('submits form with valid data', async () => {
    const mockEntity = {
      id: '123',
      slug: 'aspirin',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      status: 'confirmed' as const,
    };

    vi.mocked(entityApi.createEntity).mockResolvedValue(mockEntity);

    renderWithProviders();

    // Fill form
    const slugInput = screen.getByLabelText(/slug/i);

    fireEvent.change(slugInput, { target: { value: 'aspirin' } });

    // Submit
    const submitButton = screen.getByRole('button', { name: /create/i });
    fireEvent.click(submitButton);

    // Verify API call
    await waitFor(() => {
      expect(entityApi.createEntity).toHaveBeenCalledWith({
        slug: 'aspirin',
        summary: undefined,
      });
    });

    // Verify navigation
    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalled();
    });
  });

  it('handles API errors gracefully', async () => {
    vi.mocked(entityApi.createEntity).mockRejectedValue(
      new Error('Creation failed')
    );

    renderWithProviders();

    const slugInput = screen.getByLabelText(/slug/i);

    fireEvent.change(slugInput, { target: { value: 'test' } });

    const submitButton = screen.getByRole('button', { name: /create/i });
    fireEvent.click(submitButton);

    // Should not navigate on error
    await waitFor(() => {
      expect(mockNavigate).not.toHaveBeenCalled();
    });
  });

  it('renders UI category picker', async () => {
    renderWithProviders();

    // Wait for filter options to load
    await waitFor(() => {
      expect(screen.getByLabelText(/category/i)).toBeInTheDocument();
    });
  });

  it('shows a user-facing error when category options fail to load', async () => {
    vi.mocked(entityApi.getEntityFilterOptions).mockRejectedValue(
      new Error('Category bootstrap failed')
    );

    renderWithProviders();

    await waitFor(() => {
      expect(
        screen.getByText('Failed to load entity category options')
      ).toBeInTheDocument();
    });
  });

  it('submits form with selected UI category', async () => {
    const mockEntity = {
      id: '123',
      slug: 'aspirin',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      status: 'confirmed' as const,
    };

    vi.mocked(entityApi.createEntity).mockResolvedValue(mockEntity);

    renderWithProviders();

    // Wait for category options to load
    await waitFor(() => {
      expect(screen.getByLabelText(/category/i)).toBeInTheDocument();
    });

    // Fill slug
    const slugInput = screen.getByLabelText(/slug/i);
    fireEvent.change(slugInput, { target: { value: 'aspirin' } });

    // Select category
    const categoryInput = screen.getByLabelText(/category/i);
    fireEvent.change(categoryInput, { target: { value: 'Drugs' } });
    fireEvent.keyDown(categoryInput, { key: 'ArrowDown' });
    fireEvent.keyDown(categoryInput, { key: 'Enter' });

    // Submit
    const submitButton = screen.getByRole('button', { name: /create/i });
    fireEvent.click(submitButton);

    // Verify API call includes ui_category_id
    await waitFor(() => {
      expect(entityApi.createEntity).toHaveBeenCalledWith(
        expect.objectContaining({
          slug: 'aspirin',
        })
      );
    });
  });

  it('submits form without category when none selected', async () => {
    const mockEntity = {
      id: '123',
      slug: 'aspirin',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      status: 'confirmed' as const,
    };

    vi.mocked(entityApi.createEntity).mockResolvedValue(mockEntity);

    renderWithProviders();

    // Fill slug
    const slugInput = screen.getByLabelText(/slug/i);
    fireEvent.change(slugInput, { target: { value: 'aspirin' } });

    // Submit without selecting category
    const submitButton = screen.getByRole('button', { name: /create/i });
    fireEvent.click(submitButton);

    // Verify API call does not include ui_category_id
    await waitFor(() => {
      expect(entityApi.createEntity).toHaveBeenCalledWith({
        slug: 'aspirin',
        summary: undefined,
        ui_category_id: undefined,
      });
    });
  });
});
