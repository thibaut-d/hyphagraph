import { test, expect } from '@playwright/test';
import { loginAsAdminViaAPI, clearAuthState } from '../../fixtures/auth-helpers';

test.describe('Entity Bulk Import', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdminViaAPI(page);
  });

  test.afterEach(async ({ page }) => {
    await clearAuthState(page);
  });

  test('should load the import page at /entities/import', async ({ page }) => {
    await page.goto('/entities/import');
    await page.waitForLoadState('domcontentloaded');
    await expect(page.getByRole('heading', { name: /import/i })).toBeVisible({ timeout: 10000 });
  });

  test('should show file upload input on import page', async ({ page }) => {
    await page.goto('/entities/import');
    await page.waitForLoadState('domcontentloaded');

    // File input is visually hidden — detect via the visible "Choose file…" button
    const chooseFileButton = page.getByRole('button', { name: /choose file/i });
    await expect(chooseFileButton).toBeVisible({ timeout: 5000 });
  });

  test('should show CSV format toggle option', async ({ page }) => {
    await page.goto('/entities/import');
    await page.waitForLoadState('domcontentloaded');

    await expect(page.locator('text=/csv/i').first()).toBeVisible({ timeout: 5000 });
  });

  test('should show JSON format toggle option', async ({ page }) => {
    await page.goto('/entities/import');
    await page.waitForLoadState('domcontentloaded');

    await expect(page.locator('text=/json/i').first()).toBeVisible({ timeout: 5000 });
  });

  test('should preview a valid CSV file before committing', async ({ page }) => {
    await page.goto('/entities/import');
    await page.waitForLoadState('domcontentloaded');

    const prefix = Date.now();
    const csvContent = `slug,summary_en\n${prefix}-import-a,First import entity\n${prefix}-import-b,Second import entity`;

    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles({
      name: 'entities.csv',
      mimeType: 'text/csv',
      buffer: Buffer.from(csvContent),
    });

    const previewButton = page.getByRole('button', { name: /preview/i });
    await expect(previewButton).toBeEnabled({ timeout: 5000 });
    await previewButton.click();

    // Should show a preview table
    await expect(page.locator('table, [role="table"]').first()).toBeVisible({ timeout: 10000 });
  });

  test('should show per-row status in preview (new/duplicate/invalid)', async ({ page }) => {
    await page.goto('/entities/import');
    await page.waitForLoadState('domcontentloaded');

    const prefix = Date.now();
    const csvContent = `slug,summary_en\n${prefix}-status-row,Status test entity`;

    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles({
      name: 'entities.csv',
      mimeType: 'text/csv',
      buffer: Buffer.from(csvContent),
    });

    const previewButton = page.getByRole('button', { name: /preview/i });
    await expect(previewButton).toBeEnabled({ timeout: 5000 });
    await previewButton.click();

    // Preview table should show a status chip (new / duplicate / invalid)
    await expect(page.locator('text=/new|duplicate|invalid/i').first()).toBeVisible({ timeout: 10000 });
  });

  test('should be accessible from entities list toolbar', async ({ page }) => {
    await page.goto('/entities');
    await expect(page.getByRole('heading', { name: 'Entities' })).toBeVisible();

    const importLink = page.getByRole('link', { name: /import/i }).or(
      page.getByRole('button', { name: /import/i })
    );
    await expect(importLink.first()).toBeVisible({ timeout: 5000 });
    await importLink.first().click();
    await expect(page).toHaveURL(/\/entities\/import/);
  });
});
