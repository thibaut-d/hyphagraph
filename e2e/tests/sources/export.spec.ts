import { test, expect } from '../../fixtures/test-fixtures';
import { loginAsAdminViaAPI, clearAuthState } from '../../fixtures/auth-helpers';

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
    await expect(page.getByRole('button', { name: /export sources/i })).toBeVisible({ timeout: 5000 });
  });

  test('should offer JSON download when export is triggered', async ({ page, cleanup, testLabel, testSlug }) => {
    const sourceTitle = testLabel('export-test');
    await page.goto('/sources/new');
    await page.waitForLoadState('domcontentloaded');
    await page.getByRole('textbox', { name: 'Title' }).fill(sourceTitle);
    await page.getByRole('textbox', { name: 'URL' }).fill(`https://example.com/${testSlug('url')}`);
    await page.getByRole('button', { name: /create|submit/i }).click();
    await page.waitForURL(/\/sources\/[a-f0-9-]+/);
    const sourceId = page.url().match(/\/sources\/([a-f0-9-]+)/)?.[1] ?? '';
    cleanup.track('source', sourceId);

    await page.goto('/sources');
    await expect(page.getByRole('heading', { name: 'Sources' })).toBeVisible();

    const exportButton = page.getByRole('button', { name: /export sources/i });
    await expect(exportButton).toBeVisible({ timeout: 5000 });
    await exportButton.click();

    const jsonOption = page.getByRole('menuitem', { name: /export as json/i });
    await expect(jsonOption).toBeVisible({ timeout: 3000 });
    const [download] = await Promise.all([
      page.waitForEvent('download', { timeout: 10000 }),
      jsonOption.click(),
    ]);

    expect(download).not.toBeNull();
    expect(download.suggestedFilename()).toMatch(/\.(json|csv)$/i);
  });

  // E2E-G7 — Export content validation: downloaded file must contain the seeded source
  test('should include seeded source title in exported JSON content', async ({ page, cleanup, testLabel, testSlug }) => {
    const sourceTitle = testLabel('export-content');
    await page.goto('/sources/new');
    await page.waitForLoadState('domcontentloaded');
    await page.getByRole('textbox', { name: 'Title' }).fill(sourceTitle);
    await page.getByRole('textbox', { name: 'URL' }).fill(`https://example.com/${testSlug('url')}`);
    await page.getByRole('button', { name: /create|submit/i }).click();
    await page.waitForURL(/\/sources\/[a-f0-9-]+/);
    const sourceId = page.url().match(/\/sources\/([a-f0-9-]+)/)?.[1] ?? '';
    cleanup.track('source', sourceId);

    await page.goto('/sources');
    await expect(page.getByRole('heading', { name: 'Sources' })).toBeVisible();

    const exportButton = page.getByRole('button', { name: /export sources/i });
    await expect(exportButton).toBeVisible({ timeout: 5000 });
    await exportButton.click();

    const jsonOption = page.getByRole('menuitem', { name: /export as json/i });
    await expect(jsonOption).toBeVisible({ timeout: 3000 });
    const [download] = await Promise.all([
      page.waitForEvent('download', { timeout: 10000 }),
      jsonOption.click(),
    ]);

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

    const csvOption = page.getByRole('menuitem', { name: /csv/i }).or(
      page.getByRole('button', { name: /csv/i })
    );
    await expect(csvOption).toBeVisible({ timeout: 3000 });
    const [download] = await Promise.all([
      page.waitForEvent('download', { timeout: 10000 }),
      csvOption.click(),
    ]);
    expect(download).not.toBeNull();
    expect(download.suggestedFilename()).toMatch(/\.csv$/i);
  });
});
