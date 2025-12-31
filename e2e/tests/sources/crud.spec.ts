import { test, expect } from '@playwright/test';
import { loginAsAdminViaAPI } from '../../fixtures/auth-helpers';
import { generateSourceName } from '../../fixtures/test-data';

test.describe('Source CRUD Operations', () => {
  test.beforeEach(async ({ page }) => {
    // Login before each test
    await loginAsAdminViaAPI(page);
  });

  test('should create a new source', async ({ page }) => {
    const sourceTitle = generateSourceName('Test Source');

    // Navigate to create source page
    await page.goto('/sources/new');

    // Wait for form to load
    await expect(page.getByRole('heading', { name: 'Create Source' })).toBeVisible();

    // Fill in source details
    await page.getByLabel(/title/i).fill(sourceTitle);
    await page.getByLabel(/summary.*english/i).fill('This is a test source');

    // Fill URL (required field)
    await page.getByLabel(/url/i).fill('https://example.com/test-source');

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
    const sourceTitle = generateSourceName('View Test Source');

    await page.goto('/sources/new');
    await page.getByLabel(/title/i).fill(sourceTitle);
    await page.getByLabel(/summary.*english/i).fill('Source for viewing');
    await page.getByLabel(/url/i).fill('https://example.com/view-test');
    await page.getByRole('button', { name: /create|submit/i }).click();

    // Wait for navigation to detail page
    await page.waitForURL(/\/sources\/[a-f0-9-]+/);

    // Should show source details
    await expect(page.locator(`text=${sourceTitle}`)).toBeVisible();
    await expect(page.locator('text=Source for viewing')).toBeVisible();
  });

  test('should edit a source', async ({ page }) => {
    // Create a source first
    const originalTitle = generateSourceName('Edit Test Source');
    const updatedSummary = 'Updated summary for source';

    await page.goto('/sources/new');
    await page.getByLabel(/title/i).fill(originalTitle);
    await page.getByLabel(/summary.*english/i).fill('Original summary');
    await page.getByLabel(/url/i).fill('https://example.com/edit-test');
    await page.getByRole('button', { name: /create|submit/i }).click();

    // Wait for navigation to detail page
    await page.waitForURL(/\/sources\/[a-f0-9-]+/);

    // Click edit link (it's a RouterLink, not a button)
    await page.getByRole('link', { name: /edit/i }).click();

    // Should navigate to edit page
    await expect(page).toHaveURL(/\/sources\/[a-f0-9-]+\/edit/);

    // Update the summary
    const summaryField = page.getByLabel(/summary.*english/i);
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
    const sourceTitle = generateSourceName('Delete Test Source');

    await page.goto('/sources/new');
    await page.getByLabel(/title/i).fill(sourceTitle);
    await page.getByLabel(/summary.*english/i).fill('Source to be deleted');
    await page.getByLabel(/url/i).fill('https://example.com/delete-test');
    await page.getByRole('button', { name: /create|submit/i }).click();

    // Wait for navigation to detail page
    await page.waitForURL(/\/sources\/[a-f0-9-]+/);

    // Click delete button (opens confirmation dialog)
    await page.getByRole('button', { name: /delete/i }).first().click();

    // Wait for confirmation dialog with specific text
    await expect(page.getByText(/are you sure|delete source|confirm/i)).toBeVisible({ timeout: 5000 });

    // Find and click the Delete button within the dialog (last one)
    await page.getByRole('button', { name: /delete/i }).last().click();

    // Should navigate back to sources list after deletion
    await expect(page).toHaveURL(/\/sources$/, { timeout: 10000 });
  });

  test('should validate required fields', async ({ page }) => {
    await page.goto('/sources/new');

    // Try to submit without filling required fields
    await page.getByRole('button', { name: /create|submit/i }).click();

    // Should show validation error in Alert component
    await expect(page.getByRole('alert')).toBeVisible({ timeout: 5000 });
    await expect(page.getByRole('alert')).toContainText(/required|error/i);
  });

  test('should search/filter sources', async ({ page }) => {
    // Create test sources
    const prefix = Date.now().toString();
    const source1Title = `Wikipedia Test ${prefix}`;
    const source2Title = `Journal Test ${prefix}`;

    for (const title of [source1Title, source2Title]) {
      await page.goto('/sources/new');
      await page.getByLabel(/title/i).fill(title);
      await page.getByLabel(/summary.*english/i).fill(`Test source ${title}`);
      await page.getByLabel(/url/i).fill(`https://example.com/${title.replace(/\s+/g, '-')}`);
      await page.getByRole('button', { name: /create|submit/i }).click();
      await page.waitForURL(/\/sources\/[a-f0-9-]+/);
    }

    // Go to sources list
    await page.goto('/sources');

    // Search for specific source
    const searchInput = page.getByPlaceholder(/search/i);
    if (await searchInput.isVisible({ timeout: 2000 })) {
      await searchInput.fill(source1Title);

      // Should show matching source
      await expect(page.locator(`text=${source1Title}`)).toBeVisible();
    }
  });
});
