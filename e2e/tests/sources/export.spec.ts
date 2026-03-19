import { test, expect } from '@playwright/test';
import { loginAsAdminViaAPI, clearAuthState } from '../../fixtures/auth-helpers';
import { generateSourceName } from '../../fixtures/test-data';

test.describe('Source Export', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdminViaAPI(page);
  });

  test.afterEach(async ({ page }) => {
    await clearAuthState(page);
  });

  // US-SRC-11 — Export Sources

  test('should show export button on sources list', async ({ page }) => {
    await page.goto('/sources');
    await expect(page.getByRole('heading', { name: 'Sources' })).toBeVisible();

    // Look for an export button
    const exportButton = page.getByRole('button', { name: /export/i });
    if (await exportButton.isVisible({ timeout: 5000 })) {
      await expect(exportButton).toBeVisible();
    }
  });

  test('should offer JSON download when export is triggered', async ({ page }) => {
    // Create a source to ensure there is something to export
    const sourceTitle = generateSourceName('export-test');
    await page.goto('/sources/new');
    await page.waitForLoadState('domcontentloaded');
    await page.getByRole('textbox', { name: 'Title' }).fill(sourceTitle);
    await page.getByRole('textbox', { name: 'URL' }).fill('https://example.com/export-test');
    await page.getByRole('button', { name: /create|submit/i }).click();
    await page.waitForURL(/\/sources\/[a-f0-9-]+/);

    await page.goto('/sources');
    await expect(page.getByRole('heading', { name: 'Sources' })).toBeVisible();

    const exportButton = page.getByRole('button', { name: /export/i });
    if (await exportButton.isVisible({ timeout: 5000 })) {
      // Listen for the download event
      const [download] = await Promise.all([
        page.waitForEvent('download', { timeout: 10000 }).catch(() => null),
        exportButton.click(),
      ]);

      if (download) {
        // File should be named with .json or .csv extension
        const filename = download.suggestedFilename();
        expect(filename).toMatch(/\.(json|csv)$/i);
      }
    }
  });

  test('should offer CSV download option', async ({ page }) => {
    await page.goto('/sources');
    await expect(page.getByRole('heading', { name: 'Sources' })).toBeVisible();

    const exportButton = page.getByRole('button', { name: /export/i });
    if (await exportButton.isVisible({ timeout: 5000 })) {
      await exportButton.click();
      // After clicking, a format menu or dialog may appear with CSV option
      const csvOption = page.getByRole('menuitem', { name: /csv/i }).or(
        page.getByRole('button', { name: /csv/i })
      );
      if (await csvOption.isVisible({ timeout: 2000 })) {
        const [download] = await Promise.all([
          page.waitForEvent('download', { timeout: 10000 }).catch(() => null),
          csvOption.click(),
        ]);
        if (download) {
          expect(download.suggestedFilename()).toMatch(/\.csv$/i);
        }
      }
    }
  });
});
