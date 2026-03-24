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

  // E2E-G6 — Pagination correctness: more entities load when the sentinel is reached
  test('should load additional entities when scrolling past first page', async ({ page }) => {
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

    // Navigate to entities list and wait for first batch
    await page.goto('/entities');
    await expect(page.getByRole('heading', { name: 'Entities' })).toBeVisible();

    // Wait for at least one entity row to appear (first page loaded)
    // Scope to <main> to exclude nav/sidebar <li> elements
    const rows = page.locator('main').getByRole('listitem');
    await expect(rows.first()).toBeVisible({ timeout: 10000 });

    // Scroll to the bottom — this triggers IntersectionObserver-based infinite scroll
    // (or makes the "Load More" button visible as a fallback)
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));

    // Allow either infinite scroll or Load More button to load the next page
    const loadMoreButton = page.getByRole('button', { name: /load more/i });
    const buttonVisible = await loadMoreButton.isVisible({ timeout: 1000 }).catch(() => false);
    if (buttonVisible) {
      await loadMoreButton.click();
    }

    // Wait for any in-flight requests from pagination to finish
    await page.waitForLoadState('networkidle');

    // Total entities shown must exceed PAGE_SIZE — pagination delivered more than the first page
    const totalShown = await rows.count();
    expect(totalShown).toBeGreaterThan(PAGE_SIZE);
  });
});
