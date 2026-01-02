import { test, expect } from '@playwright/test';
import { loginAsAdminViaAPI, clearAuthState } from '../../fixtures/auth-helpers';
import { generateSourceName } from '../../fixtures/test-data';

test.describe('Source CRUD Operations', () => {
  test.beforeEach(async ({ page }) => {
    // Login before each test
    await loginAsAdminViaAPI(page);
  });

  test.afterEach(async ({ page }) => {
    // Clear auth state to avoid polluting other tests
    await clearAuthState(page);
  });

  test('should create a new source', async ({ page }) => {
    const sourceTitle = generateSourceName('test-source');

    // Navigate to create source page
    await page.goto('/sources/new');

    // Wait for form to load
    await expect(page.getByRole('heading', { name: 'Create Source' })).toBeVisible();

    // Fill in source details (sources use Title and URL, not slug)
    await page.getByRole('textbox', { name: 'Title' }).fill(sourceTitle);
    await page.getByRole('textbox', { name: 'URL' }).fill('https://example.com/test-source');
    await page.getByRole('textbox', { name: /summary.*english/i }).fill('This is a test source');

    // Submit form
    await page.getByRole('button', { name: /create|submit/i }).click();

    // Should navigate to source detail page
    await expect(page).toHaveURL(/\/sources\/[a-f0-9-]+/, { timeout: 10000 });

    // Should show source details
    await expect(page.locator(`text=${sourceTitle}`)).toBeVisible();
  });

  test('should view source list', async ({ page }) => {
    await page.goto('/sources');

    // Should show sources page
    await expect(page.getByRole('heading', { name: 'Sources' })).toBeVisible();
  });

  test('should view source detail', async ({ page }) => {
    // Create a source first
    const sourceTitle = generateSourceName('view-test');

    await page.goto('/sources/new');
    await page.getByRole('textbox', { name: 'Title' }).fill(sourceTitle);
    await page.getByRole('textbox', { name: 'URL' }).fill('https://example.com/view-test');
    await page.getByRole('textbox', { name: /summary.*english/i }).fill('Source for viewing');
    await page.getByRole('button', { name: /create|submit/i }).click();

    // Wait for navigation to detail page
    await page.waitForURL(/\/sources\/[a-f0-9-]+/);

    // Should show source details
    await expect(page.locator(`text=${sourceTitle}`)).toBeVisible();
    await expect(page.locator('text=Source for viewing')).toBeVisible();
  });

  test('should edit a source', async ({ page }) => {
    // Create a source first
    const originalTitle = generateSourceName('edit-test');
    const updatedSummary = 'Updated summary for source';

    await page.goto('/sources/new');
    await page.getByRole('textbox', { name: 'Title' }).fill(originalTitle);
    await page.getByRole('textbox', { name: 'URL' }).fill('https://example.com/edit-test');
    await page.getByRole('textbox', { name: /summary.*english/i }).fill('Original summary');
    await page.getByRole('button', { name: /create|submit/i }).click();

    // Wait for navigation to detail page
    await page.waitForURL(/\/sources\/[a-f0-9-]+/);

    // Click edit button
    await page.getByRole('button', { name: /edit/i }).click();

    // Should navigate to edit page
    await expect(page).toHaveURL(/\/sources\/[a-f0-9-]+\/edit/);

    // Update the summary
    const summaryField = page.getByRole('textbox', { name: /summary.*english/i });
    await summaryField.clear();
    await summaryField.fill(updatedSummary);

    // Submit form
    await page.getByRole('button', { name: /save|update/i }).click();

    // Should navigate back to detail page
    await page.waitForURL(/\/sources\/[a-f0-9-]+$/);

    // Should show updated summary
    await expect(page.locator(`text=${updatedSummary}`)).toBeVisible();
  });

  test('should delete a source', async ({ page }) => {
    // Create a source first
    const sourceTitle = generateSourceName('delete-test');

    await page.goto('/sources/new');
    await page.getByRole('textbox', { name: 'Title' }).fill(sourceTitle);
    await page.getByRole('textbox', { name: 'URL' }).fill('https://example.com/delete-test');
    await page.getByRole('textbox', { name: /summary.*english/i }).fill('Source to be deleted');
    await page.getByRole('button', { name: /create|submit/i }).click();

    // Wait for navigation to detail page
    await page.waitForURL(/\/sources\/[a-f0-9-]+/);

    // Click delete button
    await page.getByRole('button', { name: /delete/i }).click();

    // Confirm deletion (if there's a confirmation dialog)
    const confirmButton = page.getByRole('button', { name: /confirm|yes|delete/i });
    if (await confirmButton.isVisible({ timeout: 2000 })) {
      await confirmButton.click();
    }

    // Should navigate back to sources list
    await expect(page).toHaveURL(/\/sources$/);
  });

  test('should validate required fields', async ({ page }) => {
    await page.goto('/sources/new');

    // Try to submit without filling required fields
    await page.getByRole('button', { name: /create|submit/i }).click();

    // Should show validation error
    await expect(page.locator('text=/required|error/i')).toBeVisible({
      timeout: 5000,
    });
  });

  test('should search/filter sources', async ({ page }) => {
    // Create test sources
    const prefix = Date.now().toString();
    const source1 = `${prefix}-wikipedia`;
    const source2 = `${prefix}-journal`;

    for (const title of [source1, source2]) {
      await page.goto('/sources/new');
      await page.getByRole('textbox', { name: 'Title' }).fill(title);
      await page.getByRole('textbox', { name: 'URL' }).fill(`https://example.com/${title}`);
      await page.getByRole('textbox', { name: /summary.*english/i }).fill(`Test source ${title}`);
      await page.getByRole('button', { name: /create|submit/i }).click();
      await page.waitForURL(/\/sources\/[a-f0-9-]+/);
    }

    // Go to sources list
    await page.goto('/sources');

    // Search for specific source
    const searchInput = page.getByPlaceholder(/search/i);
    if (await searchInput.isVisible({ timeout: 2000 })) {
      await searchInput.fill(source1);

      // Should show matching source
      await expect(page.locator(`text=${source1}`)).toBeVisible();
    }
  });
});
