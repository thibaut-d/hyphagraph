/**
 * Unit tests for explanations API client.
 *
 * Tests API call construction, request formatting, and error handling
 * for explainability endpoints.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { getExplanation } from '../explanations';

// Mock the apiFetch function
vi.mock('../client', () => ({
  apiFetch: vi.fn(),
}));

import { apiFetch } from '../client';

describe('Explanations API Client', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('getExplanation', () => {
    it('should fetch explanation without scope filter', async () => {
      const mockResponse = {
        entity_id: '123e4567-e89b-12d3-a456-426614174000',
        role_type: 'drug',
        score: 0.75,
        confidence: 0.85,
        disagreement: 0.1,
        summary: 'Test summary',
        confidence_factors: [],
        source_chain: [],
      };

      (apiFetch as any).mockResolvedValue(mockResponse);

      const result = await getExplanation(
        '123e4567-e89b-12d3-a456-426614174000',
        'drug'
      );

      expect(apiFetch).toHaveBeenCalledWith(
        '/explain/inference/123e4567-e89b-12d3-a456-426614174000/drug'
      );
      expect(result).toEqual(mockResponse);
    });

    it('should fetch explanation with scope filter', async () => {
      const mockResponse = {
        entity_id: '123e4567-e89b-12d3-a456-426614174000',
        role_type: 'drug',
        score: 0.75,
        confidence: 0.85,
        disagreement: 0.1,
        summary: 'Test summary',
        confidence_factors: [],
        source_chain: [],
        scope_filter: { population: 'adults' },
      };

      (apiFetch as any).mockResolvedValue(mockResponse);

      const result = await getExplanation(
        '123e4567-e89b-12d3-a456-426614174000',
        'drug',
        { population: 'adults' }
      );

      expect(apiFetch).toHaveBeenCalledWith(
        '/explain/inference/123e4567-e89b-12d3-a456-426614174000/drug?scope=%7B%22population%22%3A%22adults%22%7D'
      );
      expect(result).toEqual(mockResponse);
    });

    it('should fetch explanation with complex scope filter', async () => {
      const mockResponse = {
        entity_id: '123e4567-e89b-12d3-a456-426614174000',
        role_type: 'effect',
        score: 0.5,
        confidence: 0.7,
        disagreement: 0.2,
        summary: 'Test summary',
        confidence_factors: [],
        source_chain: [],
        scope_filter: { population: 'adults', condition: 'chronic_pain' },
      };

      (apiFetch as any).mockResolvedValue(mockResponse);

      const result = await getExplanation(
        '123e4567-e89b-12d3-a456-426614174000',
        'effect',
        { population: 'adults', condition: 'chronic_pain' }
      );

      expect(apiFetch).toHaveBeenCalled();
      const url = (apiFetch as any).mock.calls[0][0];
      expect(url).toContain('/explain/inference/123e4567-e89b-12d3-a456-426614174000/effect');
      expect(url).toContain('scope=');
      expect(result).toEqual(mockResponse);
    });

    it('should handle empty scope filter', async () => {
      const mockResponse = {
        entity_id: '123e4567-e89b-12d3-a456-426614174000',
        role_type: 'drug',
        score: 0.75,
        confidence: 0.85,
        disagreement: 0.1,
        summary: 'Test summary',
        confidence_factors: [],
        source_chain: [],
      };

      (apiFetch as any).mockResolvedValue(mockResponse);

      const result = await getExplanation(
        '123e4567-e89b-12d3-a456-426614174000',
        'drug',
        {}
      );

      // Empty scope filter should not add query params
      expect(apiFetch).toHaveBeenCalledWith(
        '/explain/inference/123e4567-e89b-12d3-a456-426614174000/drug'
      );
      expect(result).toEqual(mockResponse);
    });

    it('should handle API errors', async () => {
      const errorMessage = 'Role type not found';
      (apiFetch as any).mockRejectedValue(new Error(errorMessage));

      await expect(
        getExplanation('123e4567-e89b-12d3-a456-426614174000', 'nonexistent')
      ).rejects.toThrow(errorMessage);
    });

    it('should handle network errors', async () => {
      (apiFetch as any).mockRejectedValue(new Error('Network error'));

      await expect(
        getExplanation('123e4567-e89b-12d3-a456-426614174000', 'drug')
      ).rejects.toThrow('Network error');
    });

    it('should return complete explanation response structure', async () => {
      const mockResponse = {
        entity_id: '123e4567-e89b-12d3-a456-426614174000',
        role_type: 'drug',
        score: 0.75,
        confidence: 0.85,
        disagreement: 0.15,
        summary: 'Based on 3 sources, this shows a strong positive effect',
        confidence_factors: [
          {
            factor: 'Coverage',
            value: 2.7,
            explanation: 'Total information coverage from 3 sources',
          },
          {
            factor: 'Confidence',
            value: 0.85,
            explanation: 'Confidence based on coverage',
          },
        ],
        source_chain: [
          {
            source_id: 'source-1',
            source_title: 'Study 1',
            source_authors: ['Smith J.'],
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

      (apiFetch as any).mockResolvedValue(mockResponse);

      const result = await getExplanation(
        '123e4567-e89b-12d3-a456-426614174000',
        'drug'
      );

      expect(result).toHaveProperty('entity_id');
      expect(result).toHaveProperty('role_type');
      expect(result).toHaveProperty('score');
      expect(result).toHaveProperty('confidence');
      expect(result).toHaveProperty('disagreement');
      expect(result).toHaveProperty('summary');
      expect(result).toHaveProperty('confidence_factors');
      expect(result).toHaveProperty('source_chain');

      expect(Array.isArray(result.confidence_factors)).toBe(true);
      expect(Array.isArray(result.source_chain)).toBe(true);
    });
  });
});
