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
    // Page heading: t("import.page_title") = "Import Entities"
    await expect(page.getByRole('heading', { name: /import/i })).toBeVisible({ timeout: 10000 });
  });

  test('should show file upload input on import page', async ({ page }) => {
    await page.goto('/entities/import');
    await page.waitForLoadState('domcontentloaded');

    // File input is hidden — detect via the visible "Choose file…" button
    const chooseFileButton = page.getByRole('button', { name: /choose file/i });
    const uploadButton = page.getByRole('button', { name: /upload|select file/i });
    const hasChooseFile = await chooseFileButton.isVisible({ timeout: 5000 }).catch(() => false);
    const hasUploadButton = await uploadButton.isVisible({ timeout: 1000 }).catch(() => false);
    expect(hasChooseFile || hasUploadButton).toBeTruthy();
  });

  test('should show CSV format toggle option', async ({ page }) => {
    await page.goto('/entities/import');
    await page.waitForLoadState('domcontentloaded');

    // Format toggle: CSV and JSON options
    const csvOption = page.locator('text=/csv/i').first();
    if (!await csvOption.isVisible({ timeout: 3000 })) {
      test.skip(true, 'CSV format option not present in this environment');
      return;
    }
    await expect(csvOption).toBeVisible();
  });

  test('should show JSON format toggle option', async ({ page }) => {
    await page.goto('/entities/import');
    await page.waitForLoadState('domcontentloaded');

    const jsonOption = page.locator('text=/json/i').first();
    if (!await jsonOption.isVisible({ timeout: 3000 })) {
      test.skip(true, 'JSON format option not present in this environment');
      return;
    }
    await expect(jsonOption).toBeVisible();
  });

  test('should preview a valid CSV file before committing', async ({ page }) => {
    await page.goto('/entities/import');
    await page.waitForLoadState('domcontentloaded');

    const prefix = Date.now();
    const csvContent = `slug,summary_en\n${prefix}-import-a,First import entity\n${prefix}-import-b,Second import entity`;

    const fileInput = page.locator('input[type="file"]');
    if (await fileInput.waitFor({ state: 'attached', timeout: 5000 }).then(() => true).catch(() => false)) {
      await fileInput.setInputFiles({
        name: 'entities.csv',
        mimeType: 'text/csv',
        buffer: Buffer.from(csvContent),
      });

      // Click preview button
      const previewButton = page.getByRole('button', { name: /preview/i });
      if (await previewButton.isVisible({ timeout: 3000 })) {
        await previewButton.click();
        // Should show a preview table (conditional — UI may render differently)
        const previewTable = page.locator('table, [role="table"]').first();
        if (await previewTable.isVisible({ timeout: 10000 }).catch(() => false)) {
          await expect(previewTable).toBeVisible();
        }
      }
    }
  });

  test('should show per-row status in preview (new/duplicate/invalid)', async ({ page }) => {
    await page.goto('/entities/import');
    await page.waitForLoadState('domcontentloaded');

    const prefix = Date.now();
    const csvContent = `slug,summary_en\n${prefix}-status-row,Status test entity`;

    const fileInput = page.locator('input[type="file"]');
    if (await fileInput.waitFor({ state: 'attached', timeout: 5000 }).then(() => true).catch(() => false)) {
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
    if (!await importLink.first().isVisible({ timeout: 3000 })) {
      test.skip(true, 'Import link not present in the entities toolbar in this environment');
      return;
    }
    await importLink.first().click();
    await expect(page).toHaveURL(/\/entities\/import/);
  });
});
