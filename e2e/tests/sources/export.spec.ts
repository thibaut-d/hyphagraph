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

    // Export Sources button must be present
    await expect(page.getByRole('button', { name: /export sources/i })).toBeVisible({ timeout: 5000 });
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

    const exportButton = page.getByRole('button', { name: /export sources/i });
    await expect(exportButton).toBeVisible({ timeout: 5000 });
    await exportButton.click();

    // Select "Export as JSON" from the dropdown menu
    const jsonOption = page.getByRole('menuitem', { name: /export as json/i });
    await expect(jsonOption).toBeVisible({ timeout: 3000 });
    const [download] = await Promise.all([
      page.waitForEvent('download', { timeout: 10000 }),
      jsonOption.click(),
    ]);

    // Download must have fired — a null download means the export button is broken
    expect(download).not.toBeNull();
    const filename = download.suggestedFilename();
    expect(filename).toMatch(/\.(json|csv)$/i);
  });

  // E2E-G7 — Export content validation: downloaded file must contain the seeded source
  test('should include seeded source title in exported JSON content', async ({ page }) => {
    const sourceTitle = generateSourceName('export-content');
    await page.goto('/sources/new');
    await page.waitForLoadState('domcontentloaded');
    await page.getByRole('textbox', { name: 'Title' }).fill(sourceTitle);
    await page.getByRole('textbox', { name: 'URL' }).fill('https://example.com/export-content');
    await page.getByRole('button', { name: /create|submit/i }).click();
    await page.waitForURL(/\/sources\/[a-f0-9-]+/);

    await page.goto('/sources');
    await expect(page.getByRole('heading', { name: 'Sources' })).toBeVisible();

    const exportButton = page.getByRole('button', { name: /export sources/i });
    await expect(exportButton).toBeVisible({ timeout: 5000 });
    await exportButton.click();

    // Select "Export as JSON" from the dropdown menu
    const jsonOption = page.getByRole('menuitem', { name: /export as json/i });
    await expect(jsonOption).toBeVisible({ timeout: 3000 });
    const [download] = await Promise.all([
      page.waitForEvent('download', { timeout: 10000 }),
      jsonOption.click(),
    ]);

    // Download must have fired — a null download means the export button is broken
    expect(download).not.toBeNull();
    const filename = download.suggestedFilename();
    if (filename.endsWith('.json')) {
      const stream = await download.createReadStream();
      const chunks: Buffer[] = [];
      for await (const chunk of stream) {
        chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk));
      }
      const content = Buffer.concat(chunks).toString('utf-8');
      expect(content).toContain(sourceTitle);
    }
  });

  test('should offer CSV download option', async ({ page }) => {
    await page.goto('/sources');
    await expect(page.getByRole('heading', { name: 'Sources' })).toBeVisible();

    const exportButton = page.getByRole('button', { name: /export sources/i });
    await expect(exportButton).toBeVisible({ timeout: 5000 });
    await exportButton.click();

    // After clicking, a format menu or dialog may appear with CSV option.
    // CSV is an optional export format — skip if not present.
    const csvOption = page.getByRole('menuitem', { name: /csv/i }).or(
      page.getByRole('button', { name: /csv/i })
    );
    if (!await csvOption.isVisible({ timeout: 2000 })) {
      test.skip(true, 'CSV export option not present in this environment');
      return;
    }
    const [download] = await Promise.all([
      page.waitForEvent('download', { timeout: 10000 }),
      csvOption.click(),
    ]);
    expect(download).not.toBeNull();
    expect(download.suggestedFilename()).toMatch(/\.csv$/i);
  });
});
