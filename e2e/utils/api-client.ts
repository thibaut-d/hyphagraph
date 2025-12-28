/**
 * API Client Utilities for E2E Tests
 *
 * Provides helper functions for making authenticated API requests
 */

const API_URL = process.env.API_URL || 'http://localhost:8000';

export interface ApiRequestOptions {
  method?: string;
  headers?: Record<string, string>;
  body?: any;
  token?: string;
}

/**
 * Make an authenticated API request
 */
export async function apiRequest(
  endpoint: string,
  options: ApiRequestOptions = {}
): Promise<Response> {
  const { method = 'GET', headers = {}, body, token } = options;

  const requestHeaders: Record<string, string> = {
    'Content-Type': 'application/json',
    ...headers,
  };

  if (token) {
    requestHeaders['Authorization'] = `Bearer ${token}`;
  }

  const requestOptions: RequestInit = {
    method,
    headers: requestHeaders,
  };

  if (body && method !== 'GET' && method !== 'HEAD') {
    requestOptions.body = JSON.stringify(body);
  }

  return fetch(`${API_URL}${endpoint}`, requestOptions);
}

/**
 * Create an entity via API
 */
export async function createEntity(
  token: string,
  data: { name: string; description?: string }
): Promise<any> {
  const response = await apiRequest('/api/entities/', {
    method: 'POST',
    token,
    body: data,
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Failed to create entity: ${error}`);
  }

  return response.json();
}

/**
 * Create a source via API
 */
export async function createSource(
  token: string,
  data: { name: string; url?: string; description?: string }
): Promise<any> {
  const response = await apiRequest('/api/sources/', {
    method: 'POST',
    token,
    body: data,
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Failed to create source: ${error}`);
  }

  return response.json();
}

/**
 * Create a relation via API
 */
export async function createRelation(
  token: string,
  data: {
    source_id: string;
    name: string;
    description?: string;
    roles?: Array<{ name: string; entity_id: string }>;
  }
): Promise<any> {
  const response = await apiRequest('/api/relations/', {
    method: 'POST',
    token,
    body: data,
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Failed to create relation: ${error}`);
  }

  return response.json();
}

/**
 * Delete an entity via API
 */
export async function deleteEntity(token: string, id: string): Promise<void> {
  const response = await apiRequest(`/api/entities/${id}`, {
    method: 'DELETE',
    token,
  });

  if (!response.ok && response.status !== 404) {
    throw new Error('Failed to delete entity');
  }
}

/**
 * Delete a source via API
 */
export async function deleteSource(token: string, id: string): Promise<void> {
  const response = await apiRequest(`/api/sources/${id}`, {
    method: 'DELETE',
    token,
  });

  if (!response.ok && response.status !== 404) {
    throw new Error('Failed to delete source');
  }
}

/**
 * Delete a relation via API
 */
export async function deleteRelation(token: string, id: string): Promise<void> {
  const response = await apiRequest(`/api/relations/${id}`, {
    method: 'DELETE',
    token,
  });

  if (!response.ok && response.status !== 404) {
    throw new Error('Failed to delete relation');
  }
}
