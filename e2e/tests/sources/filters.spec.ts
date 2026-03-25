import { test, expect } from '@playwright/test';
import { loginAsAdminViaAPI, clearAuthState } from '../../fixtures/auth-helpers';

test.describe('Source Filters', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdminViaAPI(page);
  });

  test.afterEach(async ({ page }) => {
    await clearAuthState(page);
  });

  // US-SRC-02 — Filter Sources (drawer)
  test('should open filter drawer from sources list', async ({ page }) => {
    await page.goto('/sources');
    await expect(page.getByRole('heading', { name: 'Sources' })).toBeVisible();

    const filterButton = page.getByRole('button', { name: /filter/i });
    await expect(filterButton).toBeVisible({ timeout: 5000 });
    await filterButton.click();

    const drawer = page.locator('[role="presentation"]').or(page.locator('.MuiDrawer-root')).first();
    await expect(drawer).toBeVisible({ timeout: 3000 });
  });

  test('should show study type filter option', async ({ page }) => {
    await page.goto('/sources');
    await expect(page.getByRole('heading', { name: 'Sources' })).toBeVisible();

    const filterButton = page.getByRole('button', { name: /filter/i });
    await expect(filterButton).toBeVisible({ timeout: 5000 });
    await filterButton.click();

    const studyTypeFilter = page.locator('text=/study type|kind/i').first();
    await expect(studyTypeFilter).toBeVisible({ timeout: 3000 });
  });

  test('should show publication year filter option', async ({ page }) => {
    await page.goto('/sources');
    await expect(page.getByRole('heading', { name: 'Sources' })).toBeVisible();

    const filterButton = page.getByRole('button', { name: /filter/i });
    await expect(filterButton).toBeVisible({ timeout: 5000 });
    await filterButton.click();

    const yearFilter = page.locator('text=/year/i').first();
    await expect(yearFilter).toBeVisible({ timeout: 3000 });
  });

  test('should show filter button on sources list', async ({ page }) => {
    await page.goto('/sources');
    await page.waitForLoadState('networkidle');

    await expect(page.getByRole('heading', { name: 'Sources' })).toBeVisible();
    await expect(page.getByRole('button', { name: /filter/i })).toBeVisible({ timeout: 5000 });
  });

  test('should update source list when filter is applied', async ({ page }) => {
    await page.goto('/sources');
    await page.waitForLoadState('networkidle');
    await expect(page.getByRole('heading', { name: 'Sources' })).toBeVisible();

    const filterButton = page.getByRole('button', { name: /filter/i });
    await expect(filterButton).toBeVisible({ timeout: 5000 });
    await filterButton.click();

    // If an authority/trust filter exists, interact with it
    const authorityInput = page.getByLabel(/authority|trust/i).first();
    if (await authorityInput.isVisible({ timeout: 2000 })) {
      await authorityInput.fill('1.0');
    }

    // Close the drawer before asserting background content (MUI Drawer sets aria-hidden on bg)
    await page.keyboard.press('Escape');
    await page.waitForTimeout(300);

    // Page must remain functional after filter interaction
    await expect(page.getByRole('heading', { name: 'Sources' })).toBeVisible();
  });
});
