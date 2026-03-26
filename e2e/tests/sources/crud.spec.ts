import { test, expect } from '../../fixtures/test-fixtures';
import { loginAsAdminViaAPI, clearAuthState } from '../../fixtures/auth-helpers';

test.describe('Source CRUD Operations', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdminViaAPI(page);
  });

  test.afterEach(async ({ page }) => {
    await clearAuthState(page);
  });

  test('should create a new source', async ({ page, cleanup, testLabel, testSlug }) => {
    const sourceTitle = testLabel('source');

    await page.goto('/sources/new');
    await expect(page.getByRole('heading', { name: 'Create Source' })).toBeVisible();
    await page.getByRole('textbox', { name: 'Title' }).fill(sourceTitle);
    await page.getByRole('textbox', { name: 'URL' }).fill(`https://example.com/${testSlug('url')}`);
    await page.getByRole('button', { name: /create|submit/i }).click();

    await expect(page).toHaveURL(/\/sources\/[a-f0-9-]+/, { timeout: 10000 });
    const sourceId = page.url().match(/\/sources\/([a-f0-9-]+)/)?.[1] ?? '';
    cleanup.track('source', sourceId);

    await expect(page.locator(`text=${sourceTitle}`)).toBeVisible();
  });

  test('should view source list', async ({ page }) => {
    await page.goto('/sources');
    await expect(page.getByRole('heading', { name: 'Sources' })).toBeVisible();
  });

  test('should view source detail', async ({ page, cleanup, testLabel, testSlug }) => {
    const sourceTitle = testLabel('view-test');

    await page.goto('/sources/new');
    await page.getByRole('textbox', { name: 'Title' }).fill(sourceTitle);
    await page.getByRole('textbox', { name: 'URL' }).fill(`https://example.com/${testSlug('url')}`);
    await page.getByRole('button', { name: /create|submit/i }).click();

    await page.waitForURL(/\/sources\/[a-f0-9-]+/);
    const sourceId = page.url().match(/\/sources\/([a-f0-9-]+)/)?.[1] ?? '';
    cleanup.track('source', sourceId);

    await expect(page.locator(`text=${sourceTitle}`)).toBeVisible();
  });

  test('should edit a source', async ({ page, cleanup, testLabel, testSlug }) => {
    const originalTitle = testLabel('edit-test');
    const updatedTitle = testLabel('edit-test-updated');

    await page.goto('/sources/new');
    await page.getByRole('textbox', { name: 'Title' }).fill(originalTitle);
    await page.getByRole('textbox', { name: 'URL' }).fill(`https://example.com/${testSlug('url')}`);
    await page.getByRole('button', { name: /create|submit/i }).click();

    await page.waitForURL(/\/sources\/[a-f0-9-]+/);
    const sourceId = page.url().match(/\/sources\/([a-f0-9-]+)/)?.[1] ?? '';
    cleanup.track('source', sourceId);

    await page.getByRole('link', { name: 'Edit', exact: true }).click();
    await expect(page).toHaveURL(/\/sources\/[a-f0-9-]+\/edit/);

    const titleField = page.getByRole('textbox', { name: 'Title' });
    await titleField.clear();
    await titleField.fill(updatedTitle);
    await page.getByRole('button', { name: /save|update/i }).click();

    await page.waitForURL(/\/sources\/[a-f0-9-]+$/);
    await expect(page.locator(`text=${updatedTitle}`)).toBeVisible();
  });

  test('should delete a source', async ({ page, cleanup, testLabel, testSlug }) => {
    const sourceTitle = testLabel('delete-test');

    await page.goto('/sources/new');
    await page.getByRole('textbox', { name: 'Title' }).fill(sourceTitle);
    await page.getByRole('textbox', { name: 'URL' }).fill(`https://example.com/${testSlug('url')}`);
    await page.getByRole('button', { name: /create|submit/i }).click();

    await page.waitForURL(/\/sources\/[a-f0-9-]+/);
    const sourceId = page.url().match(/\/sources\/([a-f0-9-]+)/)?.[1] ?? '';
    cleanup.track('source', sourceId); // Track even though test deletes it; 404 in cleanup is fine

    await page.getByRole('button', { name: /delete/i }).click();

    const dialog = page.locator('[role="dialog"]');
    if (await dialog.isVisible({ timeout: 2000 })) {
      await dialog.getByRole('button', { name: /confirm|yes|delete/i }).click();
    }

    await expect(page).toHaveURL(/\/sources$/);
  });

  test('should validate required fields', async ({ page }) => {
    await page.goto('/sources/new');

    const submitButton = page.getByRole('button', { name: /create|submit/i });
    await expect(submitButton).toBeDisabled();
    await expect(page.getByRole('heading', { name: 'Create Source' })).toBeVisible();
  });

  test('should search/filter sources', async ({ page, cleanup, testLabel, testSlug }) => {
    const source1Title = testLabel('wikipedia');
    const source2Title = testLabel('journal');

    for (const [title, urlSuffix] of [[source1Title, 'wiki'], [source2Title, 'journal']] as [string, string][]) {
      await page.goto('/sources/new');
      await page.getByRole('textbox', { name: 'Title' }).fill(title);
      await page.getByRole('textbox', { name: 'URL' }).fill(`https://example.com/${testSlug(urlSuffix)}`);
      await page.getByRole('button', { name: /create|submit/i }).click();
      await page.waitForURL(/\/sources\/[a-f0-9-]+/);
      const sourceId = page.url().match(/\/sources\/([a-f0-9-]+)/)?.[1] ?? '';
      cleanup.track('source', sourceId);
    }

    await page.goto('/sources');
    await expect(page.getByRole('heading', { name: 'Sources' })).toBeVisible();

    const filtersButton = page.getByRole('button', { name: /filters/i });
    if (await filtersButton.isVisible({ timeout: 2000 })) {
      await filtersButton.click();
    }

    const searchInput = page.getByPlaceholder(/search/i).first();
    await expect(searchInput).toBeVisible({ timeout: 5000 });
    await searchInput.fill(source1Title);

    await expect(page.locator(`text=${source1Title}`)).toBeVisible();
  });
});
