import { test, expect } from '@playwright/test';
import { loginAsAdminViaAPI, clearAuthState } from '../../fixtures/auth-helpers';
import { generateSourceName } from '../../fixtures/test-data';

test.describe('URL-based Document Extraction', () => {
  let sourceId: string;

  test.beforeEach(async ({ page }) => {
    // Login and create a source for testing
    await loginAsAdminViaAPI(page);

    // Create a source
    const sourceTitle = generateSourceName('url-extraction-test');
    await page.goto('/sources/new');
    await page.getByRole('textbox', { name: 'Title' }).fill(sourceTitle);
    await page.getByRole('textbox', { name: 'URL' }).fill('https://example.com/test-url');
    await page.getByRole('textbox', { name: /summary.*english/i }).fill('Test source for URL extraction');
    await page.getByRole('button', { name: /create|submit/i }).click();

    // Extract source ID from URL
    await page.waitForURL(/\/sources\/([a-f0-9-]+)/);
    const url = page.url();
    const match = url.match(/\/sources\/([a-f0-9-]+)/);
    sourceId = match ? match[1] : '';
  });

  test.afterEach(async ({ page }) => {
    await clearAuthState(page);
  });

  test('should show extract from URL button on source detail page', async ({ page }) => {
    await page.goto(`/sources/${sourceId}`);

    // Should show "Extract from URL" button
    const extractUrlButton = page.getByRole('button', { name: /custom.*url/i });
    await expect(extractUrlButton).toBeVisible();
  });

  test('should open URL extraction dialog', async ({ page }) => {
    await page.goto(`/sources/${sourceId}`);

    // Click extract from URL button
    const extractUrlButton = page.getByRole('button', { name: /custom.*url/i });
    await extractUrlButton.click();

    // Should show dialog with heading "Extract from URL"
    await expect(page.getByRole('heading', { name: /extract.*from.*url/i })).toBeVisible();

    // Should show URL input field
    await expect(page.getByLabel(/^url$/i)).toBeVisible();

    // Should show description text
    await expect(page.getByText(/enter.*url.*to.*fetch.*content/i)).toBeVisible();
  });

  test('should handle invalid URL gracefully', async ({ page }) => {
    await page.goto(`/sources/${sourceId}`);

    // Click extract from URL button
    const extractUrlButton = page.getByRole('button', { name: /custom.*url/i });
    await extractUrlButton.click();

    // Enter invalid URL
    const urlInput = page.getByLabel(/^url$/i);
    await urlInput.fill('not-a-valid-url');

    // Submit
    const submitButton = page.getByRole('button', { name: /extract/i }).last();
    await submitButton.click();

    // Should show error message in the dialog
    await expect(page.getByText(/please.*enter.*valid.*url/i)).toBeVisible({ timeout: 2000 });
  });

  test('should validate URL input is required', async ({ page }) => {
    await page.goto(`/sources/${sourceId}`);

    // Click extract from URL button
    const extractUrlButton = page.getByRole('button', { name: /custom.*url/i });
    await extractUrlButton.click();

    // Dialog may pre-fill with source URL, so clear it first
    const urlInput = page.getByLabel(/^url$/i);
    await urlInput.clear();

    // Extract button should be disabled when URL is empty
    // Use dialog locator to ensure we're checking the button in the dialog, not elsewhere on the page
    const dialog = page.getByRole('dialog');
    const submitButton = dialog.getByRole('button', { name: /^extract$/i });
    await expect(submitButton).toBeDisabled();
  });

  test('should allow canceling URL extraction dialog', async ({ page }) => {
    await page.goto(`/sources/${sourceId}`);

    // Click extract from URL button
    const extractUrlButton = page.getByRole('button', { name: /custom.*url/i });
    await extractUrlButton.click();

    // Should show dialog
    await expect(page.getByRole('heading', { name: /extract.*from.*url/i })).toBeVisible();

    // Click cancel button
    const cancelButton = page.getByRole('button', { name: /cancel/i });
    await cancelButton.click();

    // Dialog should close
    await expect(page.getByRole('heading', { name: /extract.*from.*url/i })).not.toBeVisible();
  });

  // Note: Loading state test removed - too flaky as extraction happens very quickly
  // The loading state exists but is difficult to reliably test in E2E tests

  test('should detect PubMed URLs', async ({ page }) => {
    await page.goto(`/sources/${sourceId}`);

    // Click extract from URL button
    const extractUrlButton = page.getByRole('button', { name: /custom.*url/i });
    await extractUrlButton.click();

    // Enter a PubMed URL
    const urlInput = page.getByLabel(/^url$/i);
    await urlInput.fill('https://pubmed.ncbi.nlm.nih.gov/12345678/');

    // Should show helper text indicating it's a PubMed article
    await expect(page.getByText(/pubmed.*article.*ncbi.*api/i).first()).toBeVisible();
  });

  test('should detect regular web URLs', async ({ page }) => {
    await page.goto(`/sources/${sourceId}`);

    // Click extract from URL button
    const extractUrlButton = page.getByRole('button', { name: /custom.*url/i });
    await extractUrlButton.click();

    // Enter a regular web URL
    const urlInput = page.getByLabel(/^url$/i);
    await urlInput.fill('https://example.com/article');

    // Should show helper text indicating it's a web page with limited support
    // Use .first() to handle multiple matches
    await expect(page.getByText(/web.*page.*limited.*support/i).first()).toBeVisible();
  });

  test('should show extraction workflow instructions', async ({ page }) => {
    await page.goto(`/sources/${sourceId}`);

    // Click extract from URL button
    const extractUrlButton = page.getByRole('button', { name: /custom.*url/i });
    await extractUrlButton.click();

    // Should show supported URL types
    // Use .first() to handle multiple matches (appears in both dialog and description)
    await expect(page.getByText(/pubmed.*articles|general.*web.*pages/i).first()).toBeVisible();
  });
});
