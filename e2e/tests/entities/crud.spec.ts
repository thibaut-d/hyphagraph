import { test, expect } from '../../fixtures/test-fixtures';
import { loginAsAdminViaAPI, clearAuthState, getAccessToken } from '../../fixtures/auth-helpers';

test.describe('Entity CRUD Operations', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdminViaAPI(page);
  });

  test.afterEach(async ({ page }) => {
    await clearAuthState(page);
  });

  test('should create a new entity', async ({ page, cleanup, testSlug }) => {
    const entitySlug = testSlug('entity');

    await page.goto('/entities/new');
    await expect(page.getByRole('heading', { name: 'Create Entity' })).toBeVisible();
    await page.getByLabel(/slug/i).fill(entitySlug);
    await page.getByLabel(/summary.*english/i).fill('This is a test entity');
    await page.getByRole('button', { name: /create|submit/i }).click();

    await expect(page).toHaveURL(/\/entities\/[a-f0-9-]+/, { timeout: 10000 });
    const entityId = page.url().match(/\/entities\/([a-f0-9-]+)/)?.[1] ?? '';
    cleanup.track('entity', entityId);

    await expect(page.locator(`text=${entitySlug}`)).toBeVisible();
  });

  test('should view entity list', async ({ page }) => {
    await page.goto('/entities');
    await expect(page.getByRole('heading', { name: 'Entities' })).toBeVisible();
  });

  test('should view entity detail', async ({ page, cleanup, testSlug }) => {
    const entitySlug = testSlug('view-test');

    await page.goto('/entities/new');
    await page.getByLabel(/slug/i).fill(entitySlug);
    await page.getByLabel(/summary.*english/i).fill('Entity for viewing');
    await page.getByRole('button', { name: /create|submit/i }).click();

    await page.waitForURL(/\/entities\/[a-f0-9-]+/);
    const entityId = page.url().match(/\/entities\/([a-f0-9-]+)/)?.[1] ?? '';
    cleanup.track('entity', entityId);

    await expect(page.locator(`text=${entitySlug}`)).toBeVisible();
    await expect(page.locator('text=Entity for viewing')).toBeVisible();
  });

  test('should edit an entity', async ({ page, cleanup, testSlug }) => {
    const originalSlug = testSlug('edit-test');
    const updatedSummary = 'Updated summary for edit test';

    await page.goto('/entities/new');
    await page.getByLabel(/slug/i).fill(originalSlug);
    await page.getByLabel(/summary.*english/i).fill('Original summary');
    await page.getByRole('button', { name: /create|submit/i }).click();

    await page.waitForURL(/\/entities\/[a-f0-9-]+/);
    const entityId = page.url().match(/\/entities\/([a-f0-9-]+)/)?.[1] ?? '';
    cleanup.track('entity', entityId);

    await page.waitForLoadState('domcontentloaded');
    await page.getByRole('link', { name: /edit/i }).click({ timeout: 15000 });
    await expect(page).toHaveURL(/\/entities\/[a-f0-9-]+\/edit/);

    const summaryField = page.getByLabel(/summary.*english/i);
    await summaryField.clear();
    await summaryField.fill(updatedSummary);
    await page.getByRole('button', { name: /save|update/i }).click();

    await page.waitForURL(/\/entities\/[a-f0-9-]+$/);
    await expect(page.locator(`text=${updatedSummary}`)).toBeVisible();
  });

  test('should delete an entity', async ({ page, cleanup, testSlug }) => {
    const entitySlug = testSlug('delete-test');

    await page.goto('/entities/new');
    await page.getByLabel(/slug/i).fill(entitySlug);
    await page.getByLabel(/summary.*english/i).fill('Entity to be deleted');
    await page.getByRole('button', { name: /create|submit/i }).click();

    await page.waitForURL(/\/entities\/[a-f0-9-]+/);
    const entityId = page.url().match(/\/entities\/([a-f0-9-]+)/)?.[1] ?? '';
    cleanup.track('entity', entityId); // Track even though test deletes it; 404 in cleanup is fine

    await page.waitForLoadState('domcontentloaded');

    const deleteButton = page.getByRole('button', { name: 'Delete' });
    await expect(deleteButton).toBeVisible();
    await deleteButton.click();

    await expect(page.locator('[role="dialog"]')).toBeVisible({ timeout: 5000 });
    await page.locator('[role="dialog"]').getByRole('button', { name: 'Delete' }).click();

    await page.waitForURL(/\/entities$/, { timeout: 10000 });
    await expect(page.getByRole('heading', { name: 'Entities' })).toBeVisible();
  });

  test('should show validation error for duplicate slug', async ({ page, cleanup, testSlug }) => {
    const duplicateSlug = testSlug('duplicate');

    // Create first entity
    await page.goto('/entities/new');
    await page.getByLabel(/slug/i).fill(duplicateSlug);
    await page.getByLabel(/summary.*english/i).fill('First entity');
    await page.getByRole('button', { name: /create|submit/i }).click();
    await page.waitForURL(/\/entities\/[a-f0-9-]+/);
    const entityId = page.url().match(/\/entities\/([a-f0-9-]+)/)?.[1] ?? '';
    cleanup.track('entity', entityId);

    // Try to create a duplicate — stays on form, no ID to track
    await page.goto('/entities/new');
    await page.getByLabel(/slug/i).fill(duplicateSlug);
    await page.getByLabel(/summary.*english/i).fill('Duplicate entity');
    await page.getByRole('button', { name: /create|submit/i}).click();

    await expect(page.getByRole('alert').first()).toBeVisible({ timeout: 5000 });
    await expect(page.getByRole('alert').first()).toContainText(/already exists|duplicate/i);
  });

  test('should prevent submission with empty slug (HTML5 validation)', async ({ page }) => {
    await page.goto('/entities/new');
    await page.getByRole('button', { name: /create|submit/i }).click();

    await expect(page).toHaveURL('/entities/new');
    await expect(page.getByLabel(/slug/i)).toBeVisible();
  });

  test('should search/filter entities', async ({ page, cleanup, testSlug }) => {
    const API_URL = process.env.API_URL || 'http://localhost:8001';
    const token = await getAccessToken(page);

    const entity1 = testSlug('apple');
    const entity2 = testSlug('banana');

    for (const slug of [entity1, entity2]) {
      const resp = await page.request.post(`${API_URL}/api/entities/`, {
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        data: { slug, summary: { en: `Test entity ${slug}` } },
      });
      expect(resp.ok()).toBeTruthy();
      const { id } = await resp.json();
      cleanup.track('entity', id);
    }

    await page.goto('/entities');
    const searchInput = page.getByPlaceholder(/search/i);
    await expect(searchInput).toBeVisible({ timeout: 5000 });
    await searchInput.fill(entity1);

    const listbox = page.getByRole('listbox');
    await expect(listbox).toBeVisible({ timeout: 5000 });
    await expect(listbox.getByRole('option', { name: new RegExp(entity1) })).toBeVisible();
    await listbox.getByRole('option', { name: new RegExp(entity1) }).first().click();

    await expect(page).toHaveURL(new RegExp(`/entities/.*`));
  });

  test('should navigate between entities list and detail', async ({ page, cleanup, testSlug }) => {
    const entitySlug = testSlug('nav-test');

    await page.goto('/entities/new');
    await page.getByLabel(/slug/i).fill(entitySlug);
    await page.getByLabel(/summary.*english/i).fill('Navigation test entity');
    await page.getByRole('button', { name: /create|submit/i }).click();

    await page.waitForURL(/\/entities\/[a-f0-9-]+/);
    const entityId = page.url().match(/\/entities\/([a-f0-9-]+)/)?.[1] ?? '';
    cleanup.track('entity', entityId);

    await page.getByRole('link', { name: /back/i }).click();
    await expect(page).toHaveURL(/\/entities$/);
    await expect(page.getByRole('heading', { name: 'Entities' })).toBeVisible({ timeout: 10000 });

    await page.goto(`/entities/${entityId}`);
    await expect(page).toHaveURL(/\/entities\/[a-f0-9-]+/, { timeout: 10000 });
    await expect(page.locator(`text=${entitySlug}`)).toBeVisible();
  });

  // E2E-G9 — Unknown ID 404 handling
  test('should show a not-found state for an unknown entity ID', async ({ page }) => {
    const nonExistentId = '00000000-0000-0000-0000-000000000000';
    await page.goto(`/entities/${nonExistentId}`);
    await page.waitForLoadState('domcontentloaded');

    await expect(
      page.locator('text=/not found|does not exist|couldn\'t find|no entity/i').first()
        .or(page.getByRole('heading', { name: /404/i }))
    ).toBeVisible({ timeout: 5000 });
  });
});
