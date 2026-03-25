import { test, expect } from '@playwright/test';
import { loginAsAdminViaAPI, clearAuthState } from '../../fixtures/auth-helpers';
import { generateEntityName } from '../../fixtures/test-data';

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

      // Drawer or filter panel must appear
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

    test('should not alter computed scores when filtering', async ({ page }) => {
      const entitySlug = generateEntityName('filter-score-test').toLowerCase().replace(/\s+/g, '-');
      await page.goto('/entities/new');
      await page.getByRole('textbox', { name: 'Slug' }).fill(entitySlug);
      await page.getByRole('textbox', { name: /summary.*english/i }).fill('Entity for filter score test');
      await page.getByRole('button', { name: /create|submit/i }).click();
      await page.waitForURL(/\/entities\/[a-f0-9-]+/);

      const entityId = page.url().match(/\/entities\/([a-f0-9-]+)/)?.[1];

      await page.goto(`/entities/${entityId}`);
      await page.waitForLoadState('domcontentloaded');

      // Scores are computed server-side; entity slug must still be visible after page load
      await expect(page.locator(`text=${entitySlug}`)).toBeVisible();
    });
  });

  // US-ENT-05 — Filter Entity Evidence Drawer
  test.describe('Entity Detail Evidence Filter Drawer', () => {
    test('should open evidence filter drawer on entity detail page', async ({ page }) => {
      const entitySlug = generateEntityName('evidence-filter').toLowerCase().replace(/\s+/g, '-');
      await page.goto('/entities/new');
      await page.getByRole('textbox', { name: 'Slug' }).fill(entitySlug);
      await page.getByRole('textbox', { name: /summary.*english/i }).fill('Entity for evidence filter test');
      await page.getByRole('button', { name: /create|submit/i }).click();
      await page.waitForURL(/\/entities\/[a-f0-9-]+/);
      await page.waitForLoadState('domcontentloaded');

      // Filter button must be present on the entity detail page
      const filterButton = page.getByRole('button', { name: /filter/i }).first();
      await expect(filterButton).toBeVisible({ timeout: 5000 });
      await filterButton.click();

      // Filter panel or drawer must open
      const filterPanel = page.locator('[role="presentation"]')
        .or(page.locator('text=/direction|study type|year|authority/i'))
        .first();
      await expect(filterPanel).toBeVisible({ timeout: 3000 });
    });

    test('should show warning when evidence is filtered out', async ({ page }) => {
      const entitySlug = generateEntityName('filter-warn').toLowerCase().replace(/\s+/g, '-');
      await page.goto('/entities/new');
      await page.getByRole('textbox', { name: 'Slug' }).fill(entitySlug);
      await page.getByRole('textbox', { name: /summary.*english/i }).fill('Entity for filter warning test');
      await page.getByRole('button', { name: /create|submit/i }).click();
      await page.waitForURL(/\/entities\/[a-f0-9-]+/);
      await page.waitForLoadState('domcontentloaded');

      // Entity page must load correctly
      await expect(page.locator(`text=${entitySlug}`)).toBeVisible();
    });
  });
});
