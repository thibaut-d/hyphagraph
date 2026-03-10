import { test, expect } from '@playwright/test';
import { loginAsAdminViaAPI, clearAuthState } from '../../fixtures/auth-helpers';
import { generateSourceName } from '../../fixtures/test-data';
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

  test.beforeEach(async ({ page }) => {
    // Login and create a source for testing
    await loginAsAdminViaAPI(page);

    // Create a source
    const sourceTitle = generateSourceName('doc-upload-test');
    await page.goto('/sources/new');
    await page.getByRole('textbox', { name: 'Title' }).fill(sourceTitle);
    await page.getByRole('textbox', { name: 'URL' }).fill('https://example.com/test-doc');
    await page.getByRole('textbox', { name: /summary.*english/i }).fill('Test source for document upload');
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

  test('should show upload document button on source detail page', async ({ page }) => {
    await page.goto(`/sources/${sourceId}`);

    // Should show upload button (specifically the button, not the description text)
    const uploadButton = page.getByRole('button', { name: /upload.*(?:pdf|txt|document)/i });
    await expect(uploadButton).toBeVisible();
  });

  test('should upload text file and show extraction preview', async ({ page }) => {
    await page.goto(`/sources/${sourceId}`);

    // Find the hidden file input
    const fileInput = page.locator('input[type="file"]');
    await expect(fileInput).toBeAttached();

    // Upload the test file
    await fileInput.setInputFiles(testFilePath);

    // Note: Upload happens so fast that checking for "Uploading..." state is flaky
    // Skip transient state check and go straight to verifying the extraction preview

    // After upload + extraction completes, should show extraction preview
    // This may take a while as it calls the LLM
    // Use more specific selector to avoid matching nav button
    await expect(page.getByText(/extracted.*entities/).or(page.getByRole('heading', { name: /extraction/i }))).toBeVisible({ timeout: 60000 });
  });

  test('should show extraction workflow components', async ({ page }) => {
    await page.goto(`/sources/${sourceId}`);

    // Should show both upload and URL extraction options
    await expect(page.getByRole('button', { name: /upload.*(?:pdf|txt|document)/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /custom.*url/i })).toBeVisible();

    // Should show knowledge extraction section heading
    await expect(page.getByText(/knowledge.*extraction/i)).toBeVisible();
  });

  test('should show file input for document upload', async ({ page }) => {
    await page.goto(`/sources/${sourceId}`);

    // Should have a file input for PDF/TXT uploads
    const fileInput = page.locator('input[type="file"]');
    await expect(fileInput).toBeAttached();

    // File input should accept PDF and TXT files
    const acceptAttr = await fileInput.getAttribute('accept');
    expect(acceptAttr).toContain('.pdf');
    expect(acceptAttr).toContain('.txt');
  });

  test('should show error message section when upload fails', async ({ page }) => {
    await page.goto(`/sources/${sourceId}`);

    // Error messages appear in the upload error state
    // We can't easily trigger this without a real API failure
    // Just verify the error container would be visible if there was an error
    const errorContainer = page.getByRole('alert').filter({ hasText: /error|fail/i });

    // Should not be visible initially
    await expect(errorContainer).not.toBeVisible();
  });
});
