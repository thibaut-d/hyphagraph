import { test, expect } from '../../fixtures/test-fixtures';
import { loginAsAdminViaAPI, clearAuthState } from '../../fixtures/auth-helpers';

test.describe('URL-based Document Extraction', () => {
  let sourceId: string;

  test.beforeEach(async ({ page, cleanup, testLabel, testSlug }) => {
    await loginAsAdminViaAPI(page);

    const sourceTitle = testLabel('source');
    await page.goto('/sources/new');
    await page.getByRole('textbox', { name: 'Title' }).fill(sourceTitle);
    await page.getByRole('textbox', { name: 'URL' }).fill(`https://example.com/${testSlug('url')}`);
    await page.getByRole('button', { name: /create|submit/i }).click();

    await page.waitForURL(/\/sources\/([a-f0-9-]+)/);
    sourceId = page.url().match(/\/sources\/([a-f0-9-]+)/)?.[1] ?? '';
    cleanup.track('source', sourceId);
  });

  test.afterEach(async ({ page }) => {
    await clearAuthState(page);
  });

  test('should show extract from URL button on source detail page', async ({ page }) => {
    await page.goto(`/sources/${sourceId}`);

    const extractUrlButton = page.getByRole('button', { name: /custom.*url/i });
    await expect(extractUrlButton).toBeVisible();
  });

  test('should open URL extraction dialog', async ({ page }) => {
    await page.goto(`/sources/${sourceId}`);

    const extractUrlButton = page.getByRole('button', { name: /custom.*url/i });
    await extractUrlButton.click();

    await expect(page.getByRole('heading', { name: /extract.*from.*url/i })).toBeVisible();
    await expect(page.getByLabel(/^url$/i)).toBeVisible();
    await expect(page.getByText(/enter.*url.*to.*fetch.*content/i)).toBeVisible();
  });

  test('should handle invalid URL gracefully', async ({ page }) => {
    await page.goto(`/sources/${sourceId}`);

    const extractUrlButton = page.getByRole('button', { name: /custom.*url/i });
    await extractUrlButton.click();

    const urlInput = page.getByLabel(/^url$/i);
    await urlInput.fill('not-a-valid-url');

    const submitButton = page.getByRole('button', { name: /extract/i }).last();
    await submitButton.click();

    await expect(page.getByLabel(/^url$/i)).toHaveAccessibleDescription(
      /please.*enter.*valid.*url|invalid.*url|url.*invalid/i,
      { timeout: 5000 }
    );
  });

  test('should validate URL input is required', async ({ page }) => {
    await page.goto(`/sources/${sourceId}`);

    const extractUrlButton = page.getByRole('button', { name: /custom.*url/i });
    await extractUrlButton.click();

    const urlInput = page.getByLabel(/^url$/i);
    await urlInput.clear();

    const dialog = page.getByRole('dialog');
    const submitButton = dialog.getByRole('button', { name: /^extract$/i });
    await expect(submitButton).toBeDisabled();
  });

  test('should allow canceling URL extraction dialog', async ({ page }) => {
    await page.goto(`/sources/${sourceId}`);

    const extractUrlButton = page.getByRole('button', { name: /custom.*url/i });
    await extractUrlButton.click();

    await expect(page.getByRole('heading', { name: /extract.*from.*url/i })).toBeVisible();

    const cancelButton = page.getByRole('button', { name: /cancel/i });
    await cancelButton.click();

    await expect(page.getByRole('heading', { name: /extract.*from.*url/i })).not.toBeVisible();
  });

  test('should detect PubMed URLs', async ({ page }) => {
    await page.goto(`/sources/${sourceId}`);

    const extractUrlButton = page.getByRole('button', { name: /custom.*url/i });
    await extractUrlButton.click();

    const urlInput = page.getByLabel(/^url$/i);
    await urlInput.fill('https://pubmed.ncbi.nlm.nih.gov/12345678/');

    await expect(page.getByText(/pubmed.*article.*ncbi.*api/i).first()).toBeVisible();
  });

  test('should detect regular web URLs', async ({ page }) => {
    await page.goto(`/sources/${sourceId}`);

    const extractUrlButton = page.getByRole('button', { name: /custom.*url/i });
    await extractUrlButton.click();

    const urlInput = page.getByLabel(/^url$/i);
    await urlInput.fill('https://example.com/article');

    await expect(page.getByText(/web.*page.*limited.*support/i).first()).toBeVisible();
  });

  test('should show extraction workflow instructions', async ({ page }) => {
    await page.goto(`/sources/${sourceId}`);

    const extractUrlButton = page.getByRole('button', { name: /custom.*url/i });
    await extractUrlButton.click();

    await expect(page.getByText(/pubmed.*articles|general.*web.*pages/i).first()).toBeVisible();
  });
});
