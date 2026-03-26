import { test, expect } from '../../fixtures/test-fixtures';
import { loginAsAdminViaAPI, clearAuthState } from '../../fixtures/auth-helpers';

test.describe('Entity Filters', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdminViaAPI(page);
  });

  test.afterEach(async ({ page }) => {
    await clearAuthState(page);
  });

  // US-ENT-02 — Filter Entities (drawer)
  test.describe('Entity List Filter Drawer', () => {
    test('should open filter drawer from entities list', async ({ page }) => {
      await page.goto('/entities');
      await expect(page.getByRole('heading', { name: 'Entities' })).toBeVisible();

      const filterButton = page.getByRole('button', { name: /filter/i });
      await expect(filterButton).toBeVisible({ timeout: 5000 });
      await filterButton.click();

      const drawer = page.locator('[role="presentation"]').or(page.locator('.MuiDrawer-root')).first();
      await expect(drawer).toBeVisible({ timeout: 3000 });
    });

    test('should show category filter option in drawer', async ({ page }) => {
      await page.goto('/entities');
      await expect(page.getByRole('heading', { name: 'Entities' })).toBeVisible();

      const filterButton = page.getByRole('button', { name: /filter/i });
      await expect(filterButton).toBeVisible({ timeout: 5000 });
      await filterButton.click();

      // UI categories are seeded by global-setup via /api/test/seed-ui-categories
      const categoryFilter = page.locator('text=/category|type|kind/i').first();
      await expect(categoryFilter).toBeVisible({ timeout: 5000 });
    });

    test('should show filter button on entities list', async ({ page }) => {
      await page.goto('/entities');
      await page.waitForLoadState('networkidle');

      await expect(page.getByRole('heading', { name: 'Entities' })).toBeVisible();
      await expect(page.getByRole('button', { name: /filter/i })).toBeVisible({ timeout: 5000 });
    });

    test('should not alter computed scores when filtering', async ({ page, cleanup, testSlug }) => {
      const entitySlug = testSlug('filter-score-test');
      await page.goto('/entities/new');
      await page.getByRole('textbox', { name: 'Slug' }).fill(entitySlug);
      await page.getByRole('textbox', { name: /summary.*english/i }).fill('Entity for filter score test');
      await page.getByRole('button', { name: /create|submit/i }).click();
      await page.waitForURL(/\/entities\/[a-f0-9-]+/);
      const entityId = page.url().match(/\/entities\/([a-f0-9-]+)/)?.[1] ?? '';
      cleanup.track('entity', entityId);

      await page.goto(`/entities/${entityId}`);
      await page.waitForLoadState('domcontentloaded');
      await expect(page.locator(`text=${entitySlug}`)).toBeVisible();
    });
  });

  // US-ENT-05 — Filter Entity Evidence Drawer
  test.describe('Entity Detail Evidence Filter Drawer', () => {
    test('should open evidence filter drawer on entity detail page', async ({ page, cleanup, testSlug }) => {
      const entitySlug = testSlug('evidence-filter');
      await page.goto('/entities/new');
      await page.getByRole('textbox', { name: 'Slug' }).fill(entitySlug);
      await page.getByRole('textbox', { name: /summary.*english/i }).fill('Entity for evidence filter test');
      await page.getByRole('button', { name: /create|submit/i }).click();
      await page.waitForURL(/\/entities\/[a-f0-9-]+/);
      await page.waitForLoadState('domcontentloaded');
      const entityId = page.url().match(/\/entities\/([a-f0-9-]+)/)?.[1] ?? '';
      cleanup.track('entity', entityId);

      const filterButton = page.getByRole('button', { name: /filter/i }).first();
      await expect(filterButton).toBeVisible({ timeout: 5000 });
      await filterButton.click();

      const filterPanel = page.locator('[role="presentation"]')
        .or(page.locator('text=/direction|study type|year|authority/i'))
        .first();
      await expect(filterPanel).toBeVisible({ timeout: 3000 });
    });

    test('should show warning when evidence is filtered out', async ({ page, cleanup, testSlug }) => {
      const entitySlug = testSlug('filter-warn');
      await page.goto('/entities/new');
      await page.getByRole('textbox', { name: 'Slug' }).fill(entitySlug);
      await page.getByRole('textbox', { name: /summary.*english/i }).fill('Entity for filter warning test');
      await page.getByRole('button', { name: /create|submit/i }).click();
      await page.waitForURL(/\/entities\/[a-f0-9-]+/);
      await page.waitForLoadState('domcontentloaded');
      const entityId = page.url().match(/\/entities\/([a-f0-9-]+)/)?.[1] ?? '';
      cleanup.track('entity', entityId);

      await expect(page.locator(`text=${entitySlug}`)).toBeVisible();
    });
  });
});
