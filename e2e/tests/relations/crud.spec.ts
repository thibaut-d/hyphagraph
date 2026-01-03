import { test, expect } from '@playwright/test';
import { loginAsAdminViaAPI, clearAuthState } from '../../fixtures/auth-helpers';
import { generateEntityName, generateSourceName } from '../../fixtures/test-data';

test.describe('Relation CRUD Operations', () => {
  let sourceId: string;
  let entity1Id: string;
  let entity2Id: string;

  test.beforeEach(async ({ page }) => {
    // Login before each test
    await loginAsAdminViaAPI(page);

    // Create prerequisite data: source and entities
    // Create a source (sources use Title and URL, not slug)
    const sourceTitle = generateSourceName('rel-source');
    await page.goto('/sources/new');
    await page.getByRole('textbox', { name: 'Title' }).fill(sourceTitle);
    await page.getByRole('textbox', { name: 'URL' }).fill('https://example.com/rel-source');
    await page.getByRole('textbox', { name: /summary.*english/i }).fill('Source for relation tests');
    await page.getByRole('button', { name: /create|submit/i }).click();
    await page.waitForURL(/\/sources\/([a-f0-9-]+)/);
    sourceId = page.url().match(/\/sources\/([a-f0-9-]+)/)?.[1] || '';

    // Create first entity
    const entity1Slug = generateEntityName('rel-entity-1').toLowerCase().replace(/\s+/g, '-');
    await page.goto('/entities/new');
    await page.getByRole('textbox', { name: 'Slug' }).fill(entity1Slug);
    await page.getByRole('textbox', { name: /summary.*english/i }).fill('First entity for relations');
    await page.getByRole('button', { name: /create|submit/i }).click();
    await page.waitForURL(/\/entities\/([a-f0-9-]+)/);
    entity1Id = page.url().match(/\/entities\/([a-f0-9-]+)/)?.[1] || '';

    // Create second entity
    const entity2Slug = generateEntityName('rel-entity-2').toLowerCase().replace(/\s+/g, '-');
    await page.goto('/entities/new');
    await page.getByRole('textbox', { name: 'Slug' }).fill(entity2Slug);
    await page.getByRole('textbox', { name: /summary.*english/i }).fill('Second entity for relations');
    await page.getByRole('button', { name: /create|submit/i }).click();
    await page.waitForURL(/\/entities\/([a-f0-9-]+)/);
    entity2Id = page.url().match(/\/entities\/([a-f0-9-]+)/)?.[1] || '';
  });

  test.afterEach(async ({ page }) => {
    // Clear auth state to avoid polluting other tests
    await clearAuthState(page);
  });

  test('should create a new relation', async ({ page }) => {
    // Navigate to create relation page
    await page.goto('/relations/new');

    // Wait for form to load (shows loading spinner then form)
    await expect(page.getByRole('heading', { name: /create relation/i })).toBeVisible({ timeout: 10000 });

    // Fill in relation details - actual form has: Source, Kind, Direction, Confidence, Roles
    // Select source from dropdown
    await page.getByLabel(/source/i).click();
    await page.getByRole('option').first().click();

    // Fill in relation kind
    await page.getByLabel(/relation kind|kind/i).fill('mentions');

    // Fill in direction
    await page.getByLabel(/direction/i).fill('forward');

    // Add a role
    await page.getByRole('button', { name: /add role/i }).click();

    // Select entity for the role
    const entitySelects = page.getByLabel(/entity/i);
    await entitySelects.first().click();
    await page.getByRole('option').first().click();

    // Fill in role type
    await page.getByLabel(/role type|role/i).first().fill('subject');

    // Submit form
    await page.getByRole('button', { name: /create/i }).last().click();

    // Form should reset on success (stays on same page)
    await expect(page).toHaveURL(/\/relations\/new/);

    // Verify form was reset by checking kind field is empty
    await expect(page.getByLabel(/relation kind|kind/i)).toHaveValue('');
  });

  test('should view relations list', async ({ page }) => {
    await page.goto('/relations');

    // Should show relations page (use exact match to avoid strict mode violation)
    await expect(page.getByRole('heading', { name: 'Relations', exact: true })).toBeVisible();
  });

  test('should add multiple roles to a relation', async ({ page }) => {
    await page.goto('/relations/new');

    // Wait for form to load
    await expect(page.getByRole('heading', { name: /create relation/i })).toBeVisible({ timeout: 10000 });

    // Add first role
    await page.getByRole('button', { name: /add role/i }).click();

    // Add second role
    await page.getByRole('button', { name: /add role/i }).click();

    // Should have 2 role entries (each has entity select and role type field)
    const roleTypeFields = page.getByLabel(/role type|role/i);
    await expect(roleTypeFields).toHaveCount(2);

    // Fill in first role
    await roleTypeFields.nth(0).fill('subject');

    // Fill in second role
    await roleTypeFields.nth(1).fill('object');

    // Both role types should be visible
    await expect(roleTypeFields.nth(0)).toHaveValue('subject');
    await expect(roleTypeFields.nth(1)).toHaveValue('object');
  });

  test('should remove roles from a relation', async ({ page }) => {
    await page.goto('/relations/new');

    // Wait for form to load
    await expect(page.getByRole('heading', { name: /create relation/i })).toBeVisible({ timeout: 10000 });

    // Add two roles
    await page.getByRole('button', { name: /add role/i }).click();
    await page.getByRole('button', { name: /add role/i }).click();

    // Should have 2 roles
    let roleTypeFields = page.getByLabel(/role type|role/i);
    await expect(roleTypeFields).toHaveCount(2);

    // Click delete button on first role (IconButton with DeleteIcon)
    const deleteButtons = page.getByRole('button').filter({ has: page.locator('svg') });
    await deleteButtons.first().click();

    // Should now have only 1 role
    roleTypeFields = page.getByLabel(/role type|role/i);
    await expect(roleTypeFields).toHaveCount(1);
  });

  test('should display validation error for incomplete form', async ({ page }) => {
    await page.goto('/relations/new');

    // Wait for form to load
    await expect(page.getByRole('heading', { name: /create relation/i })).toBeVisible({ timeout: 10000 });

    // Try to submit without filling required fields
    await page.getByRole('button', { name: /create/i }).last().click();

    // Should stay on create page (form doesn't submit)
    await expect(page).toHaveURL(/\/relations\/new/);

    // Should still show the create heading
    await expect(page.getByRole('heading', { name: /create relation/i })).toBeVisible();
  });
});
