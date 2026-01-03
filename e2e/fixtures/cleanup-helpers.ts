/**
 * Cleanup Helpers for E2E Tests
 *
 * Provides functions to clean up test data and ensure test isolation
 */

import { Page } from '@playwright/test';

const API_URL = process.env.API_URL || 'http://localhost:8001';

/**
 * Get auth token from localStorage
 */
async function getAuthToken(page: Page): Promise<string | null> {
  await page.goto(process.env.BASE_URL || 'http://localhost:3001');
  return page.evaluate(() => localStorage.getItem('auth_token'));
}

/**
 * Delete all entities created during tests
 * Note: This only deletes entities visible to the authenticated user
 */
export async function deleteAllTestEntities(page: Page): Promise<void> {
  const token = await getAuthToken(page);
  if (!token) {
    console.warn('No auth token found, skipping entity cleanup');
    return;
  }

  try {
    // Get all entities
    const response = await page.request.get(`${API_URL}/api/entities?limit=1000`, {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });

    if (!response.ok()) {
      console.warn(`Failed to fetch entities: ${response.status()}`);
      return;
    }

    const data = await response.json();
    const entities = data.items || [];

    // Delete each entity
    for (const entity of entities) {
      await page.request.delete(`${API_URL}/api/entities/${entity.id}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
    }

    console.log(`Cleaned up ${entities.length} test entities`);
  } catch (error) {
    console.warn('Error during entity cleanup:', error);
  }
}

/**
 * Delete all sources created during tests
 */
export async function deleteAllTestSources(page: Page): Promise<void> {
  const token = await getAuthToken(page);
  if (!token) {
    console.warn('No auth token found, skipping source cleanup');
    return;
  }

  try {
    // Get all sources
    const response = await page.request.get(`${API_URL}/api/sources?limit=1000`, {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });

    if (!response.ok()) {
      console.warn(`Failed to fetch sources: ${response.status()}`);
      return;
    }

    const data = await response.json();
    const sources = data.items || [];

    // Delete each source
    for (const source of sources) {
      await page.request.delete(`${API_URL}/api/sources/${source.id}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
    }

    console.log(`Cleaned up ${sources.length} test sources`);
  } catch (error) {
    console.warn('Error during source cleanup:', error);
  }
}

/**
 * Delete all relations created during tests
 */
export async function deleteAllTestRelations(page: Page): Promise<void> {
  const token = await getAuthToken(page);
  if (!token) {
    console.warn('No auth token found, skipping relation cleanup');
    return;
  }

  try {
    // Get all relations
    const response = await page.request.get(`${API_URL}/api/relations?limit=1000`, {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });

    if (!response.ok()) {
      console.warn(`Failed to fetch relations: ${response.status()}`);
      return;
    }

    const data = await response.json();
    const relations = data.items || [];

    // Delete each relation
    for (const relation of relations) {
      await page.request.delete(`${API_URL}/api/relations/${relation.id}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
    }

    console.log(`Cleaned up ${relations.length} test relations`);
  } catch (error) {
    console.warn('Error during relation cleanup:', error);
  }
}

/**
 * Clean up all test data (relations, sources, entities in that order)
 * Relations must be deleted first due to foreign key constraints
 */
export async function cleanupAllTestData(page: Page): Promise<void> {
  console.log('Starting test data cleanup...');

  // Delete in order: relations → sources → entities (to respect foreign keys)
  await deleteAllTestRelations(page);
  await deleteAllTestSources(page);
  await deleteAllTestEntities(page);

  console.log('Test data cleanup complete');
}

/**
 * Reset database to clean state for testing
 * This is a lighter version that only removes user-created data
 */
export async function resetTestDatabase(page: Page): Promise<void> {
  await cleanupAllTestData(page);
}
