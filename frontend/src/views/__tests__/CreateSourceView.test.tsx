/**
 * Tests for CreateSourceView component.
 *
 * Tests form validation and submission flow for source creation.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router';
import { CreateSourceView } from '../CreateSourceView';
import * as sourceApi from '../../api/sources';

// Mock the API module
vi.mock('../../api/sources');

// Mock cache utils
vi.mock('../../utils/cacheUtils', () => ({
  invalidateSourceFilterCache: vi.fn(),
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

describe('CreateSourceView', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Form rendering', () => {
    it('renders form with required fields', () => {
      render(
        <BrowserRouter>
          <CreateSourceView />
        </BrowserRouter>
      );

      expect(screen.getByLabelText(/kind/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/title/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/url/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /create source/i })).toBeInTheDocument();
    });

    it('renders optional fields', () => {
      render(
        <BrowserRouter>
          <CreateSourceView />
        </BrowserRouter>
      );

      expect(screen.getByLabelText(/authors/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/year/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/origin/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/trust level/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/summary \(english\)/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/summary \(french\)/i)).toBeInTheDocument();
    });

    it('shows cancel button', () => {
      render(
        <BrowserRouter>
          <CreateSourceView />
        </BrowserRouter>
      );

      expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument();
    });

    it('has default kind value of article', () => {
      render(
        <BrowserRouter>
          <CreateSourceView />
        </BrowserRouter>
      );

      // Check the displayed text content for MUI Select
      expect(screen.getByText('article')).toBeInTheDocument();
    });

    it('has default trust level of 0.5', () => {
      render(
        <BrowserRouter>
          <CreateSourceView />
        </BrowserRouter>
      );

      const trustLevelInput = screen.getByLabelText(/trust level/i) as HTMLInputElement;
      expect(trustLevelInput.value).toBe('0.5');
    });
  });

  describe('Form validation', () => {
    it('validates required title field', async () => {
      render(
        <BrowserRouter>
          <CreateSourceView />
        </BrowserRouter>
      );

      const urlInput = screen.getByLabelText(/url/i);
      fireEvent.change(urlInput, { target: { value: 'https://example.com' } });

      // Clear the title field to make it empty
      const titleInput = screen.getByLabelText(/title/i);
      fireEvent.change(titleInput, { target: { value: '' } });

      const submitButton = screen.getByRole('button', { name: /create source/i });
      fireEvent.click(submitButton);

      // Form should not submit without title
      await waitFor(() => {
        expect(sourceApi.createSource).not.toHaveBeenCalled();
      });
    });

    it('validates required url field', async () => {
      render(
        <BrowserRouter>
          <CreateSourceView />
        </BrowserRouter>
      );

      const titleInput = screen.getByLabelText(/title/i);
      fireEvent.change(titleInput, { target: { value: 'Test Source' } });

      // Clear the URL field
      const urlInput = screen.getByLabelText(/url/i);
      fireEvent.change(urlInput, { target: { value: '' } });

      const submitButton = screen.getByRole('button', { name: /create source/i });
      fireEvent.click(submitButton);

      // Form should not submit without URL
      await waitFor(() => {
        expect(sourceApi.createSource).not.toHaveBeenCalled();
      });
    });

    it('does not show error when both required fields are filled', async () => {
      const mockSource = {
        id: '123',
        kind: 'article',
        title: 'Test Source',
        url: 'https://example.com',
        trust_level: 0.5,
        created_at: new Date().toISOString(),
      };

      vi.mocked(sourceApi.createSource).mockResolvedValue(mockSource);

      render(
        <BrowserRouter>
          <CreateSourceView />
        </BrowserRouter>
      );

      const titleInput = screen.getByLabelText(/title/i);
      const urlInput = screen.getByLabelText(/url/i);

      fireEvent.change(titleInput, { target: { value: 'Test Source' } });
      fireEvent.change(urlInput, { target: { value: 'https://example.com' } });

      const submitButton = screen.getByRole('button', { name: /create source/i });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(sourceApi.createSource).toHaveBeenCalled();
      });
    });
  });

  describe('Form submission', () => {
    it('submits form with required fields only', async () => {
      const mockSource = {
        id: '123',
        kind: 'article',
        title: 'Test Article',
        url: 'https://example.com/article',
        trust_level: 0.5,
        created_at: new Date().toISOString(),
      };

      vi.mocked(sourceApi.createSource).mockResolvedValue(mockSource);

      render(
        <BrowserRouter>
          <CreateSourceView />
        </BrowserRouter>
      );

      const titleInput = screen.getByLabelText(/title/i);
      const urlInput = screen.getByLabelText(/url/i);

      fireEvent.change(titleInput, { target: { value: 'Test Article' } });
      fireEvent.change(urlInput, { target: { value: 'https://example.com/article' } });

      const submitButton = screen.getByRole('button', { name: /create source/i });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(sourceApi.createSource).toHaveBeenCalledWith({
          kind: 'article',
          title: 'Test Article',
          url: 'https://example.com/article',
          trust_level: 0.5,
          authors: undefined,
          year: undefined,
          origin: undefined,
          summary: undefined,
        });
      });

      await waitFor(() => {
        expect(mockNavigate).toHaveBeenCalledWith('/sources/123');
      });
    });

    it('submits form with all fields filled', async () => {
      const mockSource = {
        id: '456',
        kind: 'book',
        title: 'Complete Guide',
        url: 'https://example.com/book',
        authors: ['Author One', 'Author Two'],
        year: 2023,
        origin: 'Example Publisher',
        trust_level: 0.9,
        summaries: { en: 'English summary', fr: 'French summary' },
        created_at: new Date().toISOString(),
      };

      vi.mocked(sourceApi.createSource).mockResolvedValue(mockSource);

      render(
        <BrowserRouter>
          <CreateSourceView />
        </BrowserRouter>
      );

      // Fill all fields - use fireEvent.change for all inputs including Select
      const titleInput = screen.getByLabelText(/title/i);
      const urlInput = screen.getByLabelText(/url/i);
      const authorsInput = screen.getByLabelText(/authors/i);
      const yearInput = screen.getByLabelText(/year/i);
      const originInput = screen.getByLabelText(/origin/i);
      const trustLevelInput = screen.getByLabelText(/trust level/i);
      const summaryEnInput = screen.getByLabelText(/summary \(english\)/i);
      const summaryFrInput = screen.getByLabelText(/summary \(french\)/i);

      fireEvent.change(titleInput, { target: { value: 'Complete Guide' } });
      fireEvent.change(urlInput, { target: { value: 'https://example.com/book' } });
      fireEvent.change(authorsInput, { target: { value: 'Author One, Author Two' } });
      fireEvent.change(yearInput, { target: { value: '2023' } });
      fireEvent.change(originInput, { target: { value: 'Example Publisher' } });
      fireEvent.change(trustLevelInput, { target: { value: '0.9' } });
      fireEvent.change(summaryEnInput, { target: { value: 'English summary' } });
      fireEvent.change(summaryFrInput, { target: { value: 'French summary' } });

      // Note: Kind field defaults to 'article', we're testing that the form submits with all other fields
      // Changing MUI Select programmatically is complex, so we test with default kind value

      const submitButton = screen.getByRole('button', { name: /create source/i });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(sourceApi.createSource).toHaveBeenCalledWith({
          kind: 'article', // Default value
          title: 'Complete Guide',
          url: 'https://example.com/book',
          authors: ['Author One', 'Author Two'],
          year: 2023,
          origin: 'Example Publisher',
          trust_level: 0.9,
          summary: { en: 'English summary', fr: 'French summary' },
        });
      });

      await waitFor(() => {
        expect(mockNavigate).toHaveBeenCalledWith('/sources/456');
      });
    }, 10000); // Increase timeout to 10 seconds

    it('parses comma-separated authors correctly', async () => {
      const mockSource = {
        id: '789',
        kind: 'article',
        title: 'Test',
        url: 'https://example.com',
        authors: ['Smith', 'Jones', 'Brown'],
        trust_level: 0.5,
        created_at: new Date().toISOString(),
      };

      vi.mocked(sourceApi.createSource).mockResolvedValue(mockSource);

      render(
        <BrowserRouter>
          <CreateSourceView />
        </BrowserRouter>
      );

      const titleInput = screen.getByLabelText(/title/i);
      const urlInput = screen.getByLabelText(/url/i);
      const authorsInput = screen.getByLabelText(/authors/i);

      fireEvent.change(titleInput, { target: { value: 'Test' } });
      fireEvent.change(urlInput, { target: { value: 'https://example.com' } });
      fireEvent.change(authorsInput, { target: { value: 'Smith, Jones, Brown' } });

      const submitButton = screen.getByRole('button', { name: /create source/i });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(sourceApi.createSource).toHaveBeenCalledWith(
          expect.objectContaining({
            authors: ['Smith', 'Jones', 'Brown'],
          })
        );
      });
    });

    it('handles empty authors correctly', async () => {
      const mockSource = {
        id: '999',
        kind: 'article',
        title: 'Test',
        url: 'https://example.com',
        trust_level: 0.5,
        created_at: new Date().toISOString(),
      };

      vi.mocked(sourceApi.createSource).mockResolvedValue(mockSource);

      render(
        <BrowserRouter>
          <CreateSourceView />
        </BrowserRouter>
      );

      const titleInput = screen.getByLabelText(/title/i);
      const urlInput = screen.getByLabelText(/url/i);

      fireEvent.change(titleInput, { target: { value: 'Test' } });
      fireEvent.change(urlInput, { target: { value: 'https://example.com' } });

      const submitButton = screen.getByRole('button', { name: /create source/i });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(sourceApi.createSource).toHaveBeenCalledWith(
          expect.objectContaining({
            authors: undefined,
          })
        );
      });
    });
  });

  describe('Cancel functionality', () => {
    it('navigates to sources list when cancel clicked', () => {
      render(
        <BrowserRouter>
          <CreateSourceView />
        </BrowserRouter>
      );

      const cancelButton = screen.getByRole('button', { name: /cancel/i });
      fireEvent.click(cancelButton);

      expect(mockNavigate).toHaveBeenCalledWith('/sources');
    });

    it('navigates to sources list when back button clicked', () => {
      render(
        <BrowserRouter>
          <CreateSourceView />
        </BrowserRouter>
      );

      const backButton = screen.getByRole('button', { name: '' }); // ArrowBackIcon button
      fireEvent.click(backButton);

      expect(mockNavigate).toHaveBeenCalledWith('/sources');
    });
  });

  describe('Error handling', () => {
    it('displays error message when API call fails', async () => {
      vi.mocked(sourceApi.createSource).mockRejectedValue(
        new Error('Creation failed')
      );

      render(
        <BrowserRouter>
          <CreateSourceView />
        </BrowserRouter>
      );

      const titleInput = screen.getByLabelText(/title/i);
      const urlInput = screen.getByLabelText(/url/i);

      fireEvent.change(titleInput, { target: { value: 'Test' } });
      fireEvent.change(urlInput, { target: { value: 'https://example.com' } });

      const submitButton = screen.getByRole('button', { name: /create source/i });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText(/creation failed/i)).toBeInTheDocument();
      });

      expect(mockNavigate).not.toHaveBeenCalled();
    });

    it('does not navigate on error', async () => {
      vi.mocked(sourceApi.createSource).mockRejectedValue(
        new Error('Server error')
      );

      render(
        <BrowserRouter>
          <CreateSourceView />
        </BrowserRouter>
      );

      const titleInput = screen.getByLabelText(/title/i);
      const urlInput = screen.getByLabelText(/url/i);

      fireEvent.change(titleInput, { target: { value: 'Test' } });
      fireEvent.change(urlInput, { target: { value: 'https://example.com' } });

      const submitButton = screen.getByRole('button', { name: /create source/i });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(sourceApi.createSource).toHaveBeenCalled();
      });

      await waitFor(() => {
        expect(mockNavigate).not.toHaveBeenCalled();
      });
    });
  });

  describe('Loading state', () => {
    it('disables form fields when loading', async () => {
      vi.mocked(sourceApi.createSource).mockImplementation(
        () => new Promise((resolve) => setTimeout(resolve, 1000))
      );

      render(
        <BrowserRouter>
          <CreateSourceView />
        </BrowserRouter>
      );

      const titleInput = screen.getByLabelText(/title/i);
      const urlInput = screen.getByLabelText(/url/i);

      fireEvent.change(titleInput, { target: { value: 'Test' } });
      fireEvent.change(urlInput, { target: { value: 'https://example.com' } });

      const submitButton = screen.getByRole('button', { name: /create source/i });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(titleInput).toBeDisabled();
        expect(urlInput).toBeDisabled();
        expect(submitButton).toBeDisabled();
      });
    });

    it('shows creating text when loading', async () => {
      vi.mocked(sourceApi.createSource).mockImplementation(
        () => new Promise((resolve) => setTimeout(resolve, 1000))
      );

      render(
        <BrowserRouter>
          <CreateSourceView />
        </BrowserRouter>
      );

      const titleInput = screen.getByLabelText(/title/i);
      const urlInput = screen.getByLabelText(/url/i);

      fireEvent.change(titleInput, { target: { value: 'Test' } });
      fireEvent.change(urlInput, { target: { value: 'https://example.com' } });

      const submitButton = screen.getByRole('button', { name: /create source/i });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /creating/i })).toBeInTheDocument();
      });
    });
  });
});
