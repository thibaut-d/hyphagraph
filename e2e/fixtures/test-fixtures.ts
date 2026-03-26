/**
 * Custom Playwright test fixtures for HyphaGraph E2E tests.
 *
 * Provides three fixtures:
 *  - cleanup   — tracks DB items created during a test and deletes them in teardown
 *  - testLabel — produces a readable display name embedding the test title
 *  - testSlug  — produces a URL-safe slug embedding the test title (for entity slugs)
 *
 * Usage:
 *
 *   import { test, expect } from '../../fixtures/test-fixtures';
 *
 *   test('should create an entity', async ({ page, cleanup, testSlug, testLabel }) => {
 *     const slug = testSlug('entity');          // e.g. e2e-should-create-an-entity-entity-12345678
 *     const title = testLabel('my source');     // e.g. [e2e] Suite > Test: my source
 *
 *     await page.goto('/entities/new');
 *     await page.getByLabel(/slug/i).fill(slug);
 *     await page.getByRole('button', { name: /create/i }).click();
 *     await page.waitForURL(/\/entities\/([a-f0-9-]+)/);
 *     const entityId = page.url().match(/\/entities\/([a-f0-9-]+)/)?.[1] ?? '';
 *     cleanup.track('entity', entityId);        // auto-deleted after the test
 *   });
 *
 * Cleanup order: relations → sources → entities (respects FK constraints).
 * Items that a test deletes itself are silently skipped (404 ignored).
 * Cleanup uses a fresh admin login, so it works even after clearAuthState().
 */

import { test as base } from '@playwright/test';
import type { TestInfo } from '@playwright/test';
import { ADMIN_USER } from './test-data';

const API_URL = process.env.API_URL || 'http://localhost:8001';

export type ResourceType = 'entity' | 'source' | 'relation';

export interface CleanupTracker {
  track(type: ResourceType, id: string): void;
}

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

function sanitize(str: string, maxLen: number): string {
  return str
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, maxLen);
}

/**
 * Human-readable display name for source titles, relation kinds, etc.
 * Format: "[e2e] Suite Name > test name: label"
 */
function makeTestLabel(testInfo: TestInfo, label: string): string {
  const suite = testInfo.titlePath.slice(0, -1).join(' > ');
  return `[e2e] ${suite} > ${testInfo.title}: ${label}`;
}

/**
 * URL-safe slug embedding the test name and a timestamp for uniqueness.
 * Format: "e2e-{sanitized-test-title}-{sanitized-label}-{8-digit-ts}"
 */
function makeTestSlug(testInfo: TestInfo, label: string): string {
  const testPart = sanitize(testInfo.title, 40);
  const labelPart = sanitize(label, 20);
  const ts = Date.now().toString().slice(-8);
  return `e2e-${testPart}-${labelPart}-${ts}`;
}

/** Fresh admin login — used in teardown after clearAuthState() clears cookies. */
async function loginForCleanup(page: import('@playwright/test').Page): Promise<string | null> {
  try {
    const resp = await page.request.post(`${API_URL}/api/auth/login`, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      form: { username: ADMIN_USER.email, password: ADMIN_USER.password },
    });
    if (!resp.ok()) return null;
    const { access_token } = await resp.json();
    return access_token;
  } catch {
    return null;
  }
}

async function deleteItem(
  page: import('@playwright/test').Page,
  token: string,
  type: ResourceType,
  id: string,
): Promise<void> {
  const pathMap: Record<ResourceType, string> = {
    entity: `/api/entities/${id}`,
    source: `/api/sources/${id}`,
    relation: `/api/relations/${id}`,
  };
  try {
    await page.request.delete(`${API_URL}${pathMap[type]}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    // 404 = already deleted by the test — that's fine; other errors are ignored silently
  } catch {
    // Network errors during cleanup are non-fatal
  }
}

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

export const test = base.extend<{
  cleanup: CleanupTracker;
  testLabel: (label: string) => string;
  testSlug: (label: string) => string;
}>({
  /**
   * Track created DB resources and auto-delete them after the test.
   * Track resources as soon as their ID is known:
   *   cleanup.track('entity', entityId);
   *   cleanup.track('source', sourceId);
   *   cleanup.track('relation', relationId);
   */
  cleanup: async ({ page }, use, testInfo) => {
    const resources: Array<{ type: ResourceType; id: string }> = [];

    await use({
      track(type: ResourceType, id: string) {
        if (id) resources.push({ type, id });
      },
    });

    if (resources.length === 0) return;

    // Fresh login — afterEach may have already cleared auth cookies
    const token = await loginForCleanup(page);
    if (!token) {
      console.warn(
        `[e2e cleanup] Could not authenticate for "${testInfo.title}" — ${resources.length} item(s) not cleaned up`,
      );
      return;
    }

    // Delete in FK-safe order: relations first, then sources, then entities
    const ordered = [
      ...resources.filter(r => r.type === 'relation'),
      ...resources.filter(r => r.type === 'source'),
      ...resources.filter(r => r.type === 'entity'),
    ];

    for (const r of ordered) {
      await deleteItem(page, token, r.type, r.id);
    }
  },

  /**
   * Returns a human-readable display name that embeds the current test title.
   * Use for source titles, descriptions, etc. where spaces and brackets are fine.
   *
   * Example: testLabel('source') → "[e2e] Source CRUD > should create: source"
   */
  testLabel: async ({}, use, testInfo) => {
    await use((label: string) => makeTestLabel(testInfo, label));
  },

  /**
   * Returns a URL-safe, unique slug that embeds the current test title.
   * Use for entity slugs and anything that must be URL-safe and DB-unique.
   *
   * Example: testSlug('entity') → "e2e-should-create-a-new-entity-entity-12345678"
   */
  testSlug: async ({}, use, testInfo) => {
    await use((label: string) => makeTestSlug(testInfo, label));
  },
});

export { expect } from '@playwright/test';
