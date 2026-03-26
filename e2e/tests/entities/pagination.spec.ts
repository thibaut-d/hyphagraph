import { test, expect } from '../../fixtures/test-fixtures';
import { loginAsAdminViaAPI, clearAuthState, getAccessToken } from '../../fixtures/auth-helpers';

const PAGE_SIZE = 50; // Must match frontend EntitiesView PAGE_SIZE

test.describe('Entity List Pagination', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdminViaAPI(page);
  });

  test.afterEach(async ({ page }) => {
    await clearAuthState(page);
  });

  // E2E-G6 — Pagination correctness: more entities load when the sentinel is reached
  test('should load additional entities when scrolling past first page', async ({ page, cleanup, testSlug }) => {
    const API_URL = process.env.API_URL || 'http://localhost:8001';
    const token = await getAccessToken(page);

    // Check current entity count; create just enough to exceed PAGE_SIZE
    const countResp = await page.request.get(`${API_URL}/api/entities/?limit=1&offset=0`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(countResp.ok()).toBe(true);
    const countData = await countResp.json();
    const existingCount = countData.total ?? countData.count ?? 0;

    const needed = Math.max(0, PAGE_SIZE + 1 - existingCount);

    // Create enough entities via API to exceed PAGE_SIZE, track each for cleanup
    for (let i = 0; i < needed; i++) {
      const resp = await page.request.post(`${API_URL}/api/entities/`, {
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        data: { slug: testSlug(`p${i}`) },
      });
      if (!resp.ok()) {
        throw new Error(`Entity creation ${i} failed: ${resp.status()} ${await resp.text()}`);
      }
      const { id } = await resp.json();
      cleanup.track('entity', id);
    }

    // Navigate to entities list and wait for first batch
    await page.goto('/entities');
    await expect(page.getByRole('heading', { name: 'Entities' })).toBeVisible();

    const rows = page.locator('main').getByRole('listitem');
    await expect(rows.first()).toBeVisible({ timeout: 10000 });

    // Scroll to the bottom — triggers IntersectionObserver-based infinite scroll
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));

    const loadMoreButton = page.getByRole('button', { name: /load more/i });
    const buttonVisible = await loadMoreButton.isVisible({ timeout: 1000 }).catch(() => false);
    if (buttonVisible) {
      await loadMoreButton.click();
    }

    await page.waitForLoadState('networkidle');

    // Total entities shown must exceed PAGE_SIZE
    const totalShown = await rows.count();
    expect(totalShown).toBeGreaterThan(PAGE_SIZE);
  });
});
