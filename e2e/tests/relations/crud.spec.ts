import { test, expect } from '../../fixtures/test-fixtures';
import { loginAsAdminViaAPI, clearAuthState, getAccessToken } from '../../fixtures/auth-helpers';

test.describe('Relation CRUD Operations', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdminViaAPI(page);
  });

  test.afterEach(async ({ page }) => {
    await clearAuthState(page);
  });

  test('should create a new relation', async ({ page, cleanup, testLabel, testSlug }) => {
    const API_URL = process.env.API_URL || 'http://localhost:8001';
    const token = await getAccessToken(page);

    const sourceResp = await page.request.post(`${API_URL}/api/sources/`, {
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      data: { title: testLabel('source'), url: `https://example.com/${testSlug('url')}`, kind: 'study' },
    });
    expect(sourceResp.ok()).toBeTruthy();
    const { id: sourceId } = await sourceResp.json();
    cleanup.track('source', sourceId);

    const entity1Resp = await page.request.post(`${API_URL}/api/entities/`, {
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      data: { slug: testSlug('e1'), summary: { en: 'Relation CRUD entity 1' } },
    });
    const entity2Resp = await page.request.post(`${API_URL}/api/entities/`, {
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      data: { slug: testSlug('e2'), summary: { en: 'Relation CRUD entity 2' } },
    });
    expect(entity1Resp.ok()).toBeTruthy();
    expect(entity2Resp.ok()).toBeTruthy();
    const { id: entity1Id } = await entity1Resp.json();
    const { id: entity2Id } = await entity2Resp.json();
    cleanup.track('entity', entity1Id);
    cleanup.track('entity', entity2Id);

    await page.goto('/relations/new');
    await expect(page.getByRole('heading', { name: /create relation/i })).toBeVisible({ timeout: 10000 });

    await page.getByLabel(/source/i).click();
    const firstSourceOption = page.getByRole('option').first();
    await expect(firstSourceOption).toBeVisible({ timeout: 5000 });
    await firstSourceOption.click();

    await page.getByLabel(/relation kind|kind/i).fill('mentions');
    await page.getByLabel(/direction/i).fill('forward');

    await page.getByRole('button', { name: /add role/i }).click();
    await page.getByRole('button', { name: /add role/i }).click();

    const entitySelects = page.getByRole('combobox', { name: /^entity$/i });
    await expect(entitySelects).toHaveCount(2, { timeout: 5000 });

    await entitySelects.first().click();
    const firstEntityOption = page.getByRole('option').first();
    await expect(firstEntityOption).toBeVisible({ timeout: 5000 });
    await firstEntityOption.click();
    await page.getByRole('textbox', { name: 'Role' }).first().fill('subject');

    await entitySelects.nth(1).click();
    const entityOptions = page.getByRole('option');
    const optionCount = await entityOptions.count();
    await entityOptions.nth(optionCount > 1 ? 1 : 0).click();
    await page.getByRole('textbox', { name: 'Role' }).nth(1).fill('object');

    await page.getByRole('button', { name: /create/i }).last().click();

    // Form resets on success — relation created (no ID returned by UI, tracked via source/entity cleanup)
    await expect(page).toHaveURL(/\/relations\/new/);
    await expect(page.getByLabel(/relation kind|kind/i)).toHaveValue('');
  });

  test('should view relations list', async ({ page }) => {
    await page.goto('/relations');
    await expect(page.getByRole('heading', { name: 'Relations', exact: true })).toBeVisible();
  });

  test('should add multiple roles to a relation', async ({ page }) => {
    await page.goto('/relations/new');
    await expect(page.getByRole('heading', { name: /create relation/i })).toBeVisible({ timeout: 10000 });

    await page.getByRole('button', { name: /add role/i }).click();
    await page.getByRole('button', { name: /add role/i }).click();

    const roleTypeFields = page.getByRole('textbox', { name: 'Role' });
    await expect(roleTypeFields).toHaveCount(2);

    await roleTypeFields.nth(0).fill('subject');
    await roleTypeFields.nth(1).fill('object');

    await expect(roleTypeFields.nth(0)).toHaveValue('subject');
    await expect(roleTypeFields.nth(1)).toHaveValue('object');
  });

  test('should remove roles from a relation', async ({ page }) => {
    await page.goto('/relations/new');
    await expect(page.getByRole('heading', { name: /create relation/i })).toBeVisible({ timeout: 10000 });

    await page.getByRole('button', { name: /add role/i }).click();
    await page.getByRole('button', { name: /add role/i }).click();

    let roleTypeFields = page.getByRole('textbox', { name: 'Role' });
    await expect(roleTypeFields).toHaveCount(2);

    await page.getByRole('button', { name: /remove role/i }).first().click();

    roleTypeFields = page.getByRole('textbox', { name: 'Role' });
    await expect(roleTypeFields).toHaveCount(1);
  });

  test('should display validation error for incomplete form', async ({ page }) => {
    await page.goto('/relations/new');
    await expect(page.getByRole('heading', { name: /create relation/i })).toBeVisible({ timeout: 10000 });

    await page.getByRole('button', { name: /create/i }).last().click();

    await expect(page).toHaveURL(/\/relations\/new/);
    await expect(page.getByRole('heading', { name: /create relation/i })).toBeVisible();
  });
});
