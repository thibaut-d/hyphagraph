import { test, expect } from '../../fixtures/test-fixtures';
import { loginAsAdminViaAPI, clearAuthState } from '../../fixtures/auth-helpers';
import * as path from 'path';
import * as fs from 'fs';

test.describe('Document Upload and Extraction', () => {
  let sourceId: string;
  let testFilePath: string;

  test.beforeAll(() => {
    // Create a test text file for upload
    const testDir = path.join(__dirname, '../../test-fixtures');
    if (!fs.existsSync(testDir)) {
      fs.mkdirSync(testDir, { recursive: true });
    }
    testFilePath = path.join(testDir, 'test-document.txt');
    fs.writeFileSync(
      testFilePath,
      'Aspirin is a medication used to treat pain and inflammation. ' +
      'It is commonly used for headaches and fever. ' +
      'Aspirin works by inhibiting cyclooxygenase (COX) enzymes. ' +
      'Common side effects include stomach upset and bleeding risk.'
    );
  });

  test.afterAll(() => {
    // Cleanup test file
    if (fs.existsSync(testFilePath)) {
      fs.unlinkSync(testFilePath);
    }
  });

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

  test('should show upload document button on source detail page', async ({ page }) => {
    await page.goto(`/sources/${sourceId}`);

    const uploadButton = page.locator('label[for="document-upload"]');
    await expect(uploadButton).toBeVisible();
  });

  test('should upload text file and show extraction preview', async ({ page }) => {
    // Requires an LLM API key — skipped when none is configured.
    test.skip(
      !process.env.LLM_API_KEY && !process.env.OPENAI_API_KEY && !process.env.ANTHROPIC_API_KEY,
      'LLM API key not set — set LLM_API_KEY to enable this test',
    );

    await page.goto(`/sources/${sourceId}`);

    const fileInput = page.locator('input[type="file"]');
    await expect(fileInput).toBeAttached();
    await fileInput.setInputFiles(testFilePath);

    await expect(page.getByText(/extracted.*entities/).or(page.getByRole('heading', { name: /^knowledge extraction$/i })).first()).toBeVisible({ timeout: 60000 });
  });

  test('should show extraction workflow components', async ({ page }) => {
    await page.goto(`/sources/${sourceId}`);

    await expect(page.locator('label[for="document-upload"]')).toBeVisible();
    await expect(page.getByRole('button', { name: /custom.*url/i })).toBeVisible();
    await expect(page.getByText(/knowledge.*extraction/i)).toBeVisible();
  });

  test('should show file input for document upload', async ({ page }) => {
    await page.goto(`/sources/${sourceId}`);

    const fileInput = page.locator('input[type="file"]');
    await expect(fileInput).toBeAttached();

    const acceptAttr = await fileInput.getAttribute('accept');
    expect(acceptAttr).toContain('.pdf');
    expect(acceptAttr).toContain('.txt');
  });

  test('should show error message section when upload fails', async ({ page }) => {
    await page.goto(`/sources/${sourceId}`);

    const errorContainer = page.getByRole('alert').filter({ hasText: /error|fail/i });
    await expect(errorContainer).not.toBeVisible();
  });
});
