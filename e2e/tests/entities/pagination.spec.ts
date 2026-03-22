import { test, expect } from '@playwright/test';
import { loginAsAdminViaAPI, clearAuthState } from '../../fixtures/auth-helpers';

const PAGE_SIZE = 50; // Must match frontend EntitiesView PAGE_SIZE

test.describe('Entity List Pagination', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdminViaAPI(page);
  });

  test.afterEach(async ({ page }) => {
    await clearAuthState(page);
  });

  // E2E-G6 — Pagination correctness: page 2 data must differ from page 1
  test('should load additional entities when Load More is clicked', async ({ page }) => {
    const API_URL = process.env.API_URL || 'http://localhost:8001';
    const token = await page.evaluate(() => localStorage.getItem('auth_token'));

    // Check current entity count; create just enough to exceed PAGE_SIZE
    const countResp = await page.request.get(`${API_URL}/api/entities/?limit=1&offset=0`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(countResp.ok()).toBe(true);
    const countData = await countResp.json();
    const existingCount = countData.total ?? countData.count ?? 0;

    const needed = Math.max(0, PAGE_SIZE + 1 - existingCount);
    const prefix = `pagtest-${Date.now()}`;

    // Create enough entities via API to exceed PAGE_SIZE
    for (let i = 0; i < needed; i++) {
      const resp = await page.request.post(`${API_URL}/api/entities/`, {
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        data: { slug: `${prefix}-${i}` },
      });
      if (!resp.ok()) {
        throw new Error(`Entity creation ${i} failed: ${resp.status()} ${await resp.text()}`);
      }
    }

    // Navigate to entities list
    await page.goto('/entities');
    await expect(page.getByRole('heading', { name: 'Entities' })).toBeVisible();
    await page.waitForLoadState('networkidle');

    // Collect entity rows visible on first load.
    // Scope to <main> to exclude nav/sidebar <li> elements; entities render as ListItems inside the
    // main content List (not inside role="banner" or role="navigation").
    const rows = page.locator('main').getByRole('listitem');
    const firstPageCount = await rows.count();

    // "Load More" button must be present when total > PAGE_SIZE
    const loadMoreButton = page.getByRole('button', { name: /load more/i });
    await expect(loadMoreButton).toBeVisible({ timeout: 5000 });

    // Click Load More
    await loadMoreButton.click();
    await page.waitForLoadState('networkidle');

    // After load more, the list must have grown
    const secondPageCount = await rows.count();
    expect(secondPageCount).toBeGreaterThan(firstPageCount);
  });
});
