/**
 * Tests for CreateRelationView component.
 *
 * Tests dynamic role management and relation creation flow.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router';
import { CreateRelationView } from '../CreateRelationView';
import type { EntityRead } from '../../types/entity';
import type { SourceRead } from '../../types/source';

// Mock the API modules
vi.mock('../../api/entities', () => ({
  listEntities: vi.fn(),
}));

vi.mock('../../api/sources', () => ({
  listSources: vi.fn(),
}));

vi.mock('../../api/relations', () => ({
  createRelation: vi.fn(),
}));

import { listEntities } from '../../api/entities';
import { listSources } from '../../api/sources';
import { createRelation } from '../../api/relations';

describe('CreateRelationView', () => {
  const mockEntities: EntityRead[] = [
    {
      id: 'entity-1',
      slug: 'aspirin',
      label: 'Aspirin',
      kind: 'drug',
      summaries: {},
      created_at: new Date().toISOString(),
    },
    {
      id: 'entity-2',
      slug: 'headache',
      label: 'Headache',
      kind: 'condition',
      summaries: {},
      created_at: new Date().toISOString(),
    },
  ];

  const mockSources: SourceRead[] = [
    {
      id: 'source-1',
      kind: 'study',
      title: 'Study on Aspirin',
      trust_level: 0.9,
      created_at: new Date().toISOString(),
    },
    {
      id: 'source-2',
      kind: 'article',
      title: 'Medical Article',
      trust_level: 0.8,
      created_at: new Date().toISOString(),
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    (listEntities as any).mockResolvedValue(mockEntities);
    (listSources as any).mockResolvedValue(mockSources);
  });

  describe('Loading state', () => {
    it('shows loading spinner while fetching data', async () => {
      (listEntities as any).mockImplementation(
        () => new Promise((resolve) => setTimeout(() => resolve(mockEntities), 100))
      );
      (listSources as any).mockImplementation(
        () => new Promise((resolve) => setTimeout(() => resolve(mockSources), 100))
      );

      render(
        <BrowserRouter>
          <CreateRelationView />
        </BrowserRouter>
      );

      expect(screen.getByRole('progressbar')).toBeInTheDocument();

      await waitFor(() => {
        expect(screen.queryByRole('progressbar')).not.toBeInTheDocument();
      });
    });

    it('loads entities and sources on mount', async () => {
      render(
        <BrowserRouter>
          <CreateRelationView />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(listEntities).toHaveBeenCalled();
        expect(listSources).toHaveBeenCalled();
      });
    });
  });

  describe('Form rendering', () => {
    it('renders all relation fields', async () => {
      render(
        <BrowserRouter>
          <CreateRelationView />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByLabelText(/source/i)).toBeInTheDocument();
        expect(screen.getByLabelText(/relation kind/i)).toBeInTheDocument();
        expect(screen.getByLabelText(/direction/i)).toBeInTheDocument();
        expect(screen.getByLabelText(/confidence/i)).toBeInTheDocument();
      });
    });

    it('renders create button', async () => {
      render(
        <BrowserRouter>
          <CreateRelationView />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /create/i })).toBeInTheDocument();
      });
    });

    it('renders add role button', async () => {
      render(
        <BrowserRouter>
          <CreateRelationView />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /add role/i })).toBeInTheDocument();
      });
    });

    it('has default confidence of 0.5', async () => {
      render(
        <BrowserRouter>
          <CreateRelationView />
        </BrowserRouter>
      );

      await waitFor(() => {
        const confidenceInput = screen.getByLabelText(/confidence/i) as HTMLInputElement;
        expect(confidenceInput.value).toBe('0.5');
      });
    });
  });

  describe('Source selection', () => {
    it('populates source dropdown with loaded sources', async () => {
      render(
        <BrowserRouter>
          <CreateRelationView />
        </BrowserRouter>
      );

      await waitFor(() => {
        const sourceSelect = screen.getByLabelText(/source/i);
        fireEvent.mouseDown(sourceSelect);
      });

      await waitFor(() => {
        expect(screen.getByText('Study on Aspirin')).toBeInTheDocument();
        expect(screen.getByText('Medical Article')).toBeInTheDocument();
      });
    });

    it('allows selecting a source', async () => {
      render(
        <BrowserRouter>
          <CreateRelationView />
        </BrowserRouter>
      );

      await waitFor(() => {
        const sourceSelect = screen.getByLabelText(/source/i);
        fireEvent.mouseDown(sourceSelect);
      });

      await waitFor(() => {
        fireEvent.click(screen.getByText('Study on Aspirin'));
      });

      // Verify that the selected text is displayed
      await waitFor(() => {
        expect(screen.getAllByText('Study on Aspirin').length).toBeGreaterThan(0);
      });
    });
  });

  describe('Role management', () => {
    it('adds a new role when add role button clicked', async () => {
      render(
        <BrowserRouter>
          <CreateRelationView />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.queryByLabelText(/entity/i)).not.toBeInTheDocument();
      });

      const addRoleButton = screen.getByRole('button', { name: /add role/i });
      fireEvent.click(addRoleButton);

      await waitFor(() => {
        expect(screen.getByLabelText(/entity/i)).toBeInTheDocument();
        expect(screen.getByLabelText(/role/i)).toBeInTheDocument();
      });
    });

    it('adds multiple roles', async () => {
      render(
        <BrowserRouter>
          <CreateRelationView />
        </BrowserRouter>
      );

      await waitFor(() => {
        const addRoleButton = screen.getByRole('button', { name: /add role/i });
        fireEvent.click(addRoleButton);
        fireEvent.click(addRoleButton);
      });

      await waitFor(() => {
        const entityInputs = screen.getAllByLabelText(/entity/i);
        expect(entityInputs).toHaveLength(2);
      });
    });

    it('removes a role when delete button clicked', async () => {
      render(
        <BrowserRouter>
          <CreateRelationView />
        </BrowserRouter>
      );

      await waitFor(() => {
        const addRoleButton = screen.getByRole('button', { name: /add role/i });
        fireEvent.click(addRoleButton);
        fireEvent.click(addRoleButton);
      });

      await waitFor(() => {
        const deleteButtons = screen.getAllByRole('button', { name: '' });
        const roleDeleteButtons = deleteButtons.filter(
          (btn) => btn.querySelector('[data-testid="DeleteIcon"]')
        );
        expect(roleDeleteButtons.length).toBe(2);
      });

      const deleteButtons = screen.getAllByRole('button', { name: '' });
      const roleDeleteButtons = deleteButtons.filter(
        (btn) => btn.querySelector('[data-testid="DeleteIcon"]')
      );
      fireEvent.click(roleDeleteButtons[0]);

      await waitFor(() => {
        const entityInputs = screen.getAllByLabelText(/entity/i);
        expect(entityInputs).toHaveLength(1);
      });
    });

    it('populates entity dropdown in role', async () => {
      render(
        <BrowserRouter>
          <CreateRelationView />
        </BrowserRouter>
      );

      await waitFor(() => {
        const addRoleButton = screen.getByRole('button', { name: /add role/i });
        fireEvent.click(addRoleButton);
      });

      await waitFor(() => {
        const entitySelect = screen.getByLabelText(/entity/i);
        fireEvent.mouseDown(entitySelect);
      });

      await waitFor(() => {
        expect(screen.getByText('Aspirin')).toBeInTheDocument();
        expect(screen.getByText('Headache')).toBeInTheDocument();
      });
    });

    it('updates role entity', async () => {
      render(
        <BrowserRouter>
          <CreateRelationView />
        </BrowserRouter>
      );

      await waitFor(() => {
        const addRoleButton = screen.getByRole('button', { name: /add role/i });
        fireEvent.click(addRoleButton);
      });

      await waitFor(() => {
        const entitySelect = screen.getByLabelText(/entity/i);
        fireEvent.mouseDown(entitySelect);
      });

      await waitFor(() => {
        fireEvent.click(screen.getByText('Aspirin'));
      });

      // Verify that the selected text is displayed
      await waitFor(() => {
        expect(screen.getAllByText('Aspirin').length).toBeGreaterThan(0);
      });
    });

    it('updates role type', async () => {
      render(
        <BrowserRouter>
          <CreateRelationView />
        </BrowserRouter>
      );

      await waitFor(() => {
        const addRoleButton = screen.getByRole('button', { name: /add role/i });
        fireEvent.click(addRoleButton);
      });

      await waitFor(() => {
        const roleTypeInput = screen.getByLabelText(/role/i);
        fireEvent.change(roleTypeInput, { target: { value: 'drug' } });
      });

      const roleTypeField = screen.getByLabelText(/role/i) as HTMLInputElement;
      expect(roleTypeField.value).toBe('drug');
    });
  });

  describe('Form submission', () => {
    it('submits relation with all fields', async () => {
      (createRelation as any).mockResolvedValue({
        id: 'rel-1',
        source_id: 'source-1',
        kind: 'effect',
        direction: 'positive',
        confidence: 0.9,
        roles: [{ entity_id: 'entity-1', role_type: 'drug' }],
        created_at: new Date().toISOString(),
      });

      render(
        <BrowserRouter>
          <CreateRelationView />
        </BrowserRouter>
      );

      // Wait for data to load
      await waitFor(() => {
        expect(screen.getByLabelText(/source/i)).toBeInTheDocument();
      });

      // Select source
      const sourceSelect = screen.getByLabelText(/source/i);
      fireEvent.mouseDown(sourceSelect);
      await waitFor(() => {
        fireEvent.click(screen.getByText('Study on Aspirin'));
      });

      // Fill relation fields
      const kindInput = screen.getByLabelText(/relation kind/i);
      const directionInput = screen.getByLabelText(/direction/i);
      const confidenceInput = screen.getByLabelText(/confidence/i);

      fireEvent.change(kindInput, { target: { value: 'effect' } });
      fireEvent.change(directionInput, { target: { value: 'positive' } });
      fireEvent.change(confidenceInput, { target: { value: '0.9' } });

      // Add a role
      const addRoleButton = screen.getByRole('button', { name: /add role/i });
      fireEvent.click(addRoleButton);

      await waitFor(() => {
        const entitySelect = screen.getByLabelText(/entity/i);
        fireEvent.mouseDown(entitySelect);
      });

      await waitFor(() => {
        fireEvent.click(screen.getByText('Aspirin'));
      });

      const roleTypeInput = screen.getByLabelText(/role/i);
      fireEvent.change(roleTypeInput, { target: { value: 'drug' } });

      // Submit
      const submitButton = screen.getByRole('button', { name: /create/i });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(createRelation).toHaveBeenCalledWith({
          source_id: 'source-1',
          kind: 'effect',
          direction: 'positive',
          confidence: 0.9,
          roles: [{ entity_id: 'entity-1', role_type: 'drug' }],
        });
      });
    });

    it('resets form after successful submission', async () => {
      (createRelation as any).mockResolvedValue({
        id: 'rel-1',
        source_id: 'source-1',
        kind: 'effect',
        direction: 'positive',
        confidence: 0.5,
        roles: [],
        created_at: new Date().toISOString(),
      });

      render(
        <BrowserRouter>
          <CreateRelationView />
        </BrowserRouter>
      );

      await waitFor(() => {
        const kindInput = screen.getByLabelText(/relation kind/i);
        fireEvent.change(kindInput, { target: { value: 'effect' } });
      });

      const submitButton = screen.getByRole('button', { name: /create/i });
      fireEvent.click(submitButton);

      await waitFor(() => {
        const kindInput = screen.getByLabelText(/relation kind/i) as HTMLInputElement;
        expect(kindInput.value).toBe('');
      });
    });

    it('displays error message on submission failure', async () => {
      (createRelation as any).mockRejectedValue(new Error('Submission failed'));

      render(
        <BrowserRouter>
          <CreateRelationView />
        </BrowserRouter>
      );

      await waitFor(() => {
        const kindInput = screen.getByLabelText(/relation kind/i);
        fireEvent.change(kindInput, { target: { value: 'effect' } });
      });

      const submitButton = screen.getByRole('button', { name: /create/i });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText(/submission failed/i)).toBeInTheDocument();
      });
    });

    it('disables submit button while submitting', async () => {
      (createRelation as any).mockImplementation(
        () => new Promise((resolve) => setTimeout(resolve, 1000))
      );

      render(
        <BrowserRouter>
          <CreateRelationView />
        </BrowserRouter>
      );

      await waitFor(() => {
        const kindInput = screen.getByLabelText(/relation kind/i);
        fireEvent.change(kindInput, { target: { value: 'effect' } });
      });

      const submitButton = screen.getByRole('button', { name: /create/i });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(submitButton).toBeDisabled();
      });
    });
  });

  describe('Query parameter pre-fill', () => {
    it('pre-fills role from entity_id query parameter', async () => {
      const { container } = render(
        <BrowserRouter>
          <CreateRelationView />
        </BrowserRouter>
      );

      // Simulate URL with query parameter
      window.history.pushState({}, '', '?entity_id=entity-1');

      // Re-render to trigger useEffect
      container.remove();
      render(
        <BrowserRouter>
          <CreateRelationView />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.queryByLabelText(/entity/i)).toBeInTheDocument();
      });
    });
  });

  describe('Relation fields', () => {
    it('updates kind field', async () => {
      render(
        <BrowserRouter>
          <CreateRelationView />
        </BrowserRouter>
      );

      await waitFor(() => {
        const kindInput = screen.getByLabelText(/relation kind/i);
        fireEvent.change(kindInput, { target: { value: 'mechanism' } });
      });

      const kindField = screen.getByLabelText(/relation kind/i) as HTMLInputElement;
      expect(kindField.value).toBe('mechanism');
    });

    it('updates direction field', async () => {
      render(
        <BrowserRouter>
          <CreateRelationView />
        </BrowserRouter>
      );

      await waitFor(() => {
        const directionInput = screen.getByLabelText(/direction/i);
        fireEvent.change(directionInput, { target: { value: 'negative' } });
      });

      const directionField = screen.getByLabelText(/direction/i) as HTMLInputElement;
      expect(directionField.value).toBe('negative');
    });

    it('updates confidence field', async () => {
      render(
        <BrowserRouter>
          <CreateRelationView />
        </BrowserRouter>
      );

      await waitFor(() => {
        const confidenceInput = screen.getByLabelText(/confidence/i);
        fireEvent.change(confidenceInput, { target: { value: '0.75' } });
      });

      const confidenceField = screen.getByLabelText(/confidence/i) as HTMLInputElement;
      expect(confidenceField.value).toBe('0.75');
    });
  });
});
