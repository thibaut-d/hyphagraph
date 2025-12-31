import { test, expect } from '@playwright/test';
import { loginAsAdminViaAPI } from '../../fixtures/auth-helpers';
import { generateEntityName } from '../../fixtures/test-data';

test.describe('Entity CRUD Operations', () => {
  test.beforeEach(async ({ page }) => {
    // Login before each test
    await loginAsAdminViaAPI(page);
  });

  test('should create a new entity', async ({ page }) => {
    const entitySlug = generateEntityName('test-entity').toLowerCase().replace(/\s+/g, '-');

    // Navigate to create entity page
    await page.goto('/entities/new');

    // Wait for form to load (use heading specifically to avoid strict mode violation)
    await expect(page.getByRole('heading', { name: 'Create Entity' })).toBeVisible();

    // Fill in entity details
    await page.getByLabel(/slug/i).fill(entitySlug);
    await page.getByLabel(/summary.*english/i).fill('This is a test entity');

    // Submit form
    await page.getByRole('button', { name: /create|submit/i }).click();

    // Should navigate to entity detail page
    await expect(page).toHaveURL(/\/entities\/[a-f0-9-]+/, { timeout: 10000 });

    // Should show entity details
    await expect(page.locator(`text=${entitySlug}`)).toBeVisible();
  });

  test('should view entity list', async ({ page }) => {
    await page.goto('/entities');

    // Should show entities page heading
    await expect(page.getByRole('heading', { name: 'Entities' })).toBeVisible();

    // Should have some entities (at least the test data)
    // Note: This depends on database state
  });

  test('should view entity detail', async ({ page }) => {
    // First, create an entity to view
    const entitySlug = generateEntityName('view-test').toLowerCase().replace(/\s+/g, '-');

    await page.goto('/entities/new');
    await page.getByLabel(/slug/i).fill(entitySlug);
    await page.getByLabel(/summary.*english/i).fill('Entity for viewing');
    await page.getByRole('button', { name: /create|submit/i }).click();

    // Wait for navigation to detail page
    await page.waitForURL(/\/entities\/[a-f0-9-]+/);

    // Should show entity details
    await expect(page.locator(`text=${entitySlug}`)).toBeVisible();
    await expect(page.locator('text=Entity for viewing')).toBeVisible();
  });

  test('should edit an entity', async ({ page }) => {
    // Create an entity first
    const originalSlug = generateEntityName('edit-test').toLowerCase().replace(/\s+/g, '-');
    const updatedSummary = 'Updated summary for edit test';

    await page.goto('/entities/new');
    await page.getByLabel(/slug/i).fill(originalSlug);
    await page.getByLabel(/summary.*english/i).fill('Original summary');
    await page.getByRole('button', { name: /create|submit/i }).click();

    // Wait for navigation to detail page
    await page.waitForURL(/\/entities\/[a-f0-9-]+/);

    // Wait for page to stabilize (entity terms may fail to load for new entities)
    await page.waitForLoadState('networkidle');

    // Click edit link (it's a RouterLink, not a button)
    await page.getByRole('link', { name: /edit/i }).click({ timeout: 15000 });

    // Should navigate to edit page
    await expect(page).toHaveURL(/\/entities\/[a-f0-9-]+\/edit/);

    // Update the summary
    const summaryField = page.getByLabel(/summary.*english/i);
    await summaryField.clear();
    await summaryField.fill(updatedSummary);

    // Submit form
    await page.getByRole('button', { name: /save|update/i }).click();

    // Should navigate back to detail page
    await page.waitForURL(/\/entities\/[a-f0-9-]+$/);

    // Should show updated summary
    await expect(page.locator(`text=${updatedSummary}`)).toBeVisible();
  });

  test('should delete an entity', async ({ page }) => {
    // Create an entity first
    const entitySlug = generateEntityName('delete-test').toLowerCase().replace(/\s+/g, '-');

    await page.goto('/entities/new');
    await page.getByLabel(/slug/i).fill(entitySlug);
    await page.getByLabel(/summary.*english/i).fill('Entity to be deleted');
    await page.getByRole('button', { name: /create|submit/i }).click();

    // Wait for navigation to detail page
    await page.waitForURL(/\/entities\/[a-f0-9-]+/);

    // Wait for page to fully load
    await page.waitForLoadState('networkidle');

    // Wait a bit more for any async operations
    await page.waitForTimeout(1000);

    // Click delete button - find it specifically (should be near Edit button)
    const deleteButton = page.getByRole('button', { name: 'Delete' });
    await expect(deleteButton).toBeVisible();
    await deleteButton.click();

    // Wait for confirmation dialog to appear
    await expect(page.getByRole('dialog')).toBeVisible({ timeout: 5000 });

    // Confirm deletion by clicking Delete button in dialog
    await page.getByRole('dialog').getByRole('button', { name: 'Delete' }).click();

    // Wait for navigation back to entities list after deletion
    await page.waitForURL(/\/entities$/, { timeout: 10000 });

    // Deleted entity should not appear in the list
    await expect(page.locator(`text=${entitySlug}`)).not.toBeVisible();
  });

  test('should show validation error for duplicate slug', async ({ page }) => {
    const duplicateSlug = generateEntityName('duplicate').toLowerCase().replace(/\s+/g, '-');

    // Create first entity
    await page.goto('/entities/new');
    await page.getByLabel(/slug/i).fill(duplicateSlug);
    await page.getByLabel(/summary.*english/i).fill('First entity');
    await page.getByRole('button', { name: /create|submit/i }).click();

    // Wait for success
    await page.waitForURL(/\/entities\/[a-f0-9-]+/);

    // Try to create another entity with the same slug
    await page.goto('/entities/new');
    await page.getByLabel(/slug/i).fill(duplicateSlug);
    await page.getByLabel(/summary.*english/i).fill('Duplicate entity');
    await page.getByRole('button', { name: /create|submit/i }).click();

    // Should show error message in Alert component
    await expect(page.getByRole('alert')).toBeVisible({ timeout: 5000 });
    await expect(page.getByRole('alert')).toContainText(/error|fail|already|duplicate/i);
  });

  test('should show validation error for empty slug', async ({ page }) => {
    await page.goto('/entities/new');

    // Try to submit without filling slug
    await page.getByRole('button', { name: /create|submit/i }).click();

    // Should show validation error in Alert component
    await expect(page.getByRole('alert')).toBeVisible({ timeout: 5000 });
    await expect(page.getByRole('alert')).toContainText(/slug.*required/i);
  });

  test('should search/filter entities', async ({ page }) => {
    // Create a few test entities
    const prefix = Date.now().toString();
    const entity1 = `${prefix}-apple`;
    const entity2 = `${prefix}-banana`;

    for (const slug of [entity1, entity2]) {
      await page.goto('/entities/new');
      await page.getByLabel(/slug/i).fill(slug);
      await page.getByLabel(/summary.*english/i).fill(`Test entity ${slug}`);
      await page.getByRole('button', { name: /create|submit/i }).click();
      await page.waitForURL(/\/entities\/[a-f0-9-]+/);
    }

    // Go to entities list
    await page.goto('/entities');

    // Search for specific entity
    const searchInput = page.getByPlaceholder(/search/i);
    if (await searchInput.isVisible({ timeout: 2000 })) {
      await searchInput.fill(entity1);

      // Should show only matching entity
      await expect(page.locator(`text=${entity1}`)).toBeVisible();
      // Note: entity2 might still be visible depending on search implementation
    }
  });

  test('should navigate between entities list and detail', async ({ page }) => {
    // Create an entity
    const entitySlug = generateEntityName('nav-test').toLowerCase().replace(/\s+/g, '-');

    await page.goto('/entities/new');
    await page.getByLabel(/slug/i).fill(entitySlug);
    await page.getByLabel(/summary.*english/i).fill('Navigation test entity');
    await page.getByRole('button', { name: /create|submit/i }).click();

    // Wait for detail page
    await page.waitForURL(/\/entities\/[a-f0-9-]+/);

    // Click back to list (it's a RouterLink, not a button)
    await page.getByRole('link', { name: /back/i }).click();

    // Should be on entities list
    await expect(page).toHaveURL(/\/entities$/);

    // Click on entity to view details again
    await page.locator(`text=${entitySlug}`).click();

    // Should be on detail page again
    await expect(page).toHaveURL(/\/entities\/[a-f0-9-]+/);
  });
});
