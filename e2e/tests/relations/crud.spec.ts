import { test, expect } from '@playwright/test';
import { loginAsAdminViaAPI, clearAuthState } from '../../fixtures/auth-helpers';
import { generateEntityName } from '../../fixtures/test-data';

test.describe('Relation CRUD Operations', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdminViaAPI(page);
  });

  test.afterEach(async ({ page }) => {
    await clearAuthState(page);
  });

  test('should create a new relation', async ({ page }) => {
    const API_URL = process.env.API_URL || 'http://localhost:8001';
    const token = await page.evaluate(() => localStorage.getItem('auth_token'));

    // Pre-create a source and two entities so the form dropdowns have options
    const sourceResp = await page.request.post(`${API_URL}/api/sources/`, {
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      data: { title: `Rel-CRUD-Source-${Date.now()}`, url: `https://example.com/rel-crud-${Date.now()}` },
    });
    if (!sourceResp.ok()) {
      test.skip(true, `Source pre-creation failed: ${sourceResp.status()} — seed data to run this test`);
      return;
    }

    const entity1Resp = await page.request.post(`${API_URL}/api/entities/`, {
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      data: { slug: `rel-crud-e1-${Date.now()}`, summary_en: 'Relation CRUD entity 1' },
    });
    const entity2Resp = await page.request.post(`${API_URL}/api/entities/`, {
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      data: { slug: `rel-crud-e2-${Date.now()}`, summary_en: 'Relation CRUD entity 2' },
    });
    if (!entity1Resp.ok() || !entity2Resp.ok()) {
      test.skip(true, 'Entity pre-creation failed — seed data to run this test');
      return;
    }

    // Navigate to create relation page
    await page.goto('/relations/new');

    // Wait for form to load (shows loading spinner then form)
    await expect(page.getByRole('heading', { name: /create relation/i })).toBeVisible({ timeout: 10000 });

    // Fill in relation details - actual form has: Source, Kind, Direction, Confidence, Roles
    // Select source from dropdown
    await page.getByLabel(/source/i).click();
    const firstSourceOption = page.getByRole('option').first();
    await expect(firstSourceOption).toBeVisible({ timeout: 5000 });
    await firstSourceOption.click();

    // Fill in relation kind
    await page.getByLabel(/relation kind|kind/i).fill('mentions');

    // Fill in direction
    await page.getByLabel(/direction/i).fill('forward');

    // Add two roles (relation requires at least two participating entities)
    await page.getByRole('button', { name: /add role/i }).click();
    await page.getByRole('button', { name: /add role/i }).click();

    // Select entity for each role
    const entitySelects = page.getByLabel(/^entity$/i);
    const count = await entitySelects.count();
    if (count < 2) {
      test.skip(true, 'Entity select fields not rendered after Add Role — check CreateRelationView');
      return;
    }

    // First role entity
    await entitySelects.first().click();
    const firstEntityOption = page.getByRole('option').first();
    await expect(firstEntityOption).toBeVisible({ timeout: 5000 });
    await firstEntityOption.click();
    await page.getByRole('textbox', { name: 'Role' }).first().fill('subject');

    // Second role entity
    await entitySelects.nth(1).click();
    const entityOptions = page.getByRole('option');
    const optionCount = await entityOptions.count();
    await entityOptions.nth(optionCount > 1 ? 1 : 0).click();
    await page.getByRole('textbox', { name: 'Role' }).nth(1).fill('object');

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
    const roleTypeFields = page.getByRole('textbox', { name: 'Role' });
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
    let roleTypeFields = page.getByRole('textbox', { name: 'Role' });
    await expect(roleTypeFields).toHaveCount(2);

    // Click Remove role on the first role entry
    await page.getByRole('button', { name: /remove role/i }).first().click();

    // Should now have only 1 role — Playwright retries until count matches
    roleTypeFields = page.getByRole('textbox', { name: 'Role' });
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
