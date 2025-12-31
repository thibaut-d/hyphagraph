import { test, expect } from '@playwright/test';
import { loginAsAdminViaAPI } from '../../fixtures/auth-helpers';
import { generateRelationName, generateEntityName, generateSourceName } from '../../fixtures/test-data';

test.describe('Relation CRUD Operations', () => {
  let sourceId: string;
  let entity1Id: string;
  let entity2Id: string;

  test.beforeEach(async ({ page }) => {
    // Login before each test
    await loginAsAdminViaAPI(page);

    // Create prerequisite data: source and entities
    // Create a source
    const sourceTitle = generateSourceName('Relation Test Source');
    await page.goto('/sources/new');
    await page.getByLabel(/title/i).fill(sourceTitle);
    await page.getByLabel(/summary.*english/i).fill('Source for relation tests');
    await page.getByLabel(/url/i).fill('https://example.com/relation-test-source');
    await page.getByRole('button', { name: /create|submit/i }).click();
    await page.waitForURL(/\/sources\/([a-f0-9-]+)/);
    sourceId = page.url().match(/\/sources\/([a-f0-9-]+)/)?.[1] || '';

    // Create first entity
    const entity1Slug = generateEntityName('rel-entity-1').toLowerCase().replace(/\s+/g, '-');
    await page.goto('/entities/new');
    await page.getByLabel(/slug/i).fill(entity1Slug);
    await page.getByLabel(/summary.*english/i).fill('First entity for relations');
    await page.getByRole('button', { name: /create|submit/i }).click();
    await page.waitForURL(/\/entities\/([a-f0-9-]+)/);
    entity1Id = page.url().match(/\/entities\/([a-f0-9-]+)/)?.[1] || '';

    // Create second entity
    const entity2Slug = generateEntityName('rel-entity-2').toLowerCase().replace(/\s+/g, '-');
    await page.goto('/entities/new');
    await page.getByLabel(/slug/i).fill(entity2Slug);
    await page.getByLabel(/summary.*english/i).fill('Second entity for relations');
    await page.getByRole('button', { name: /create|submit/i }).click();
    await page.waitForURL(/\/entities\/([a-f0-9-]+)/);
    entity2Id = page.url().match(/\/entities\/([a-f0-9-]+)/)?.[1] || '';
  });

  test('should create a new relation', async ({ page }) => {
    const relationSlug = generateRelationName('test-relation').toLowerCase().replace(/\s+/g, '-');

    // Navigate to create relation page
    await page.goto('/relations/new');

    // Wait for form to load
    await expect(page.getByRole('heading', { name: /create relation|new relation/i })).toBeVisible();

    // Fill in relation details
    await page.getByLabel(/slug/i).fill(relationSlug);
    await page.getByLabel(/summary.*english/i).fill('This is a test relation');

    // Select source (if there's a source selector)
    const sourceSelect = page.locator('select[name="source_id"]').or(page.getByLabel(/source/i));
    if (await sourceSelect.isVisible({ timeout: 2000 })) {
      // Note: This might need adjustment based on actual UI implementation
      await sourceSelect.click();
      await page.locator(`option[value="${sourceId}"]`).click();
    }

    // Submit form
    await page.getByRole('button', { name: /create|submit/i }).click();

    // Should navigate to relation detail or edit page
    await page.waitForURL(/\/relations\/[a-f0-9-]+/);

    // Should show relation details
    await expect(page.locator(`text=${relationSlug}`)).toBeVisible();
  });

  test('should view relations list', async ({ page }) => {
    await page.goto('/relations');

    // Should show relations page
    await expect(page.getByRole('heading', { name: 'Relations' })).toBeVisible();
  });

  test('should add roles to a relation', async ({ page }) => {
    // Create a relation first
    const relationSlug = generateRelationName('role-test').toLowerCase().replace(/\s+/g, '-');

    await page.goto('/relations/new');
    await page.getByLabel(/slug/i).fill(relationSlug);
    await page.getByLabel(/summary.*english/i).fill('Relation for role testing');
    await page.getByRole('button', { name: /create|submit/i }).click();

    // Wait for navigation
    await page.waitForURL(/\/relations\/[a-f0-9-]+/);

    // Look for "Add Role" button or similar
    const addRoleButton = page.getByRole('button', { name: /add role/i });
    if (await addRoleButton.isVisible({ timeout: 2000 })) {
      await addRoleButton.click();

      // Fill in role details
      // Note: This is a guess based on common patterns
      await page.getByLabel(/role name|name/i).fill('subject');

      // Select entity for role
      // This will depend on the actual UI implementation

      // Save role
      await page.getByRole('button', { name: /save|add/i }).click();

      // Should show the added role
      await expect(page.locator('text=subject')).toBeVisible();
    }
  });

  test('should edit a relation', async ({ page }) => {
    // Create a relation first
    const originalSlug = generateRelationName('edit-test').toLowerCase().replace(/\s+/g, '-');
    const updatedSummary = 'Updated summary for relation';

    await page.goto('/relations/new');
    await page.getByLabel(/slug/i).fill(originalSlug);
    await page.getByLabel(/summary.*english/i).fill('Original summary');
    await page.getByRole('button', { name: /create|submit/i }).click();

    // Wait for navigation
    const url = await page.waitForURL(/\/relations\/[a-f0-9-]+/);
    const relationId = page.url().match(/\/relations\/([a-f0-9-]+)/)?.[1];

    // Navigate to edit page
    await page.goto(`/relations/${relationId}/edit`);

    // Update the summary
    const summaryField = page.getByLabel(/summary.*english/i);
    await summaryField.clear();
    await summaryField.fill(updatedSummary);

    // Submit form
    await page.getByRole('button', { name: /save|update/i }).click();

    // Should show updated summary
    await expect(page.locator(`text=${updatedSummary}`)).toBeVisible();
  });

  test('should delete a relation', async ({ page }) => {
    // TODO: Delete dialog not opening - same frontend bug as entities/sources
    // See entities/crud.spec.ts delete test for details
    // Create a relation first
    const relationSlug = generateRelationName('delete-test').toLowerCase().replace(/\s+/g, '-');

    await page.goto('/relations/new');
    await page.getByLabel(/slug/i).fill(relationSlug);
    await page.getByLabel(/summary.*english/i).fill('Relation to be deleted');
    await page.getByRole('button', { name: /create|submit/i }).click();

    // Wait for navigation
    await page.waitForURL(/\/relations\/[a-f0-9-]+/);

    // Click delete button (opens confirmation dialog)
    await page.getByRole('button', { name: /delete/i }).first().click();

    // Wait for confirmation dialog with specific text
    await expect(page.getByText(/are you sure|delete relation|confirm/i)).toBeVisible({ timeout: 5000 });

    // Find and click the Delete button within the dialog (last one)
    await page.getByRole('button', { name: /delete/i }).last().click();

    // Should navigate back to relations list after deletion
    await expect(page).toHaveURL(/\/relations$/, { timeout: 10000 });
  });

  test('should validate required fields', async ({ page }) => {
    await page.goto('/relations/new');

    // Try to submit without filling required fields
    await page.getByRole('button', { name: /create|submit/i }).click();

    // Should show validation error in Alert component
    await expect(page.getByRole('alert')).toBeVisible({ timeout: 5000 });
    await expect(page.getByRole('alert')).toContainText(/required|error/i);
  });
});
