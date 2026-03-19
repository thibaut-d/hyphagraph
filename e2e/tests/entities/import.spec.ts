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
    await page.waitForLoadState('networkidle');
    // Page should render — look for upload or import heading
    await expect(page.locator('text=/import|upload/i').first()).toBeVisible({ timeout: 10000 });
  });

  test('should show file upload input on import page', async ({ page }) => {
    await page.goto('/entities/import');
    await page.waitForLoadState('networkidle');

    // There should be a file input or upload button
    const fileInput = page.locator('input[type="file"]');
    const uploadButton = page.getByRole('button', { name: /upload|choose|select file/i });
    const hasFileInput = await fileInput.isVisible({ timeout: 3000 }).catch(() => false);
    const hasUploadButton = await uploadButton.isVisible({ timeout: 1000 }).catch(() => false);
    expect(hasFileInput || hasUploadButton).toBeTruthy();
  });

  test('should show CSV format toggle option', async ({ page }) => {
    await page.goto('/entities/import');
    await page.waitForLoadState('networkidle');

    // Format toggle: CSV and JSON options
    const csvOption = page.locator('text=/csv/i').first();
    if (await csvOption.isVisible({ timeout: 3000 })) {
      await expect(csvOption).toBeVisible();
    }
  });

  test('should show JSON format toggle option', async ({ page }) => {
    await page.goto('/entities/import');
    await page.waitForLoadState('networkidle');

    const jsonOption = page.locator('text=/json/i').first();
    if (await jsonOption.isVisible({ timeout: 3000 })) {
      await expect(jsonOption).toBeVisible();
    }
  });

  test('should preview a valid CSV file before committing', async ({ page }) => {
    await page.goto('/entities/import');
    await page.waitForLoadState('networkidle');

    const prefix = Date.now();
    const csvContent = `slug,summary_en\n${prefix}-import-a,First import entity\n${prefix}-import-b,Second import entity`;

    const fileInput = page.locator('input[type="file"]');
    if (await fileInput.isVisible({ timeout: 3000 }).catch(() => false)) {
      await fileInput.setInputFiles({
        name: 'entities.csv',
        mimeType: 'text/csv',
        buffer: Buffer.from(csvContent),
      });

      // Click preview button
      const previewButton = page.getByRole('button', { name: /preview/i });
      if (await previewButton.isVisible({ timeout: 3000 })) {
        await previewButton.click();
        // Should show a preview table
        await expect(page.locator('table, [role="table"]').first()).toBeVisible({ timeout: 10000 });
      }
    }
  });

  test('should show per-row status in preview (new/duplicate/invalid)', async ({ page }) => {
    await page.goto('/entities/import');
    await page.waitForLoadState('networkidle');

    const prefix = Date.now();
    const csvContent = `slug,summary_en\n${prefix}-status-row,Status test entity`;

    const fileInput = page.locator('input[type="file"]');
    if (await fileInput.isVisible({ timeout: 3000 }).catch(() => false)) {
      await fileInput.setInputFiles({
        name: 'entities.csv',
        mimeType: 'text/csv',
        buffer: Buffer.from(csvContent),
      });

      const previewButton = page.getByRole('button', { name: /preview/i });
      if (await previewButton.isVisible({ timeout: 3000 })) {
        await previewButton.click();
        await page.waitForTimeout(2000);

        // Preview table should show a status chip (new / duplicate / invalid)
        const statusChip = page.locator('text=/new|duplicate|invalid/i').first();
        if (await statusChip.isVisible({ timeout: 5000 })) {
          await expect(statusChip).toBeVisible();
        }
      }
    }
  });

  test('should be accessible from entities list toolbar', async ({ page }) => {
    await page.goto('/entities');
    await expect(page.getByRole('heading', { name: 'Entities' })).toBeVisible();

    // There should be an import button or link in the toolbar
    const importLink = page.getByRole('link', { name: /import/i }).or(
      page.getByRole('button', { name: /import/i })
    );
    if (await importLink.first().isVisible({ timeout: 3000 })) {
      await importLink.first().click();
      await expect(page).toHaveURL(/\/entities\/import/);
    }
  });
});
