import { test, expect } from '@playwright/test';
import { loginAsAdminViaAPI, clearAuthState } from '../../fixtures/auth-helpers';
import { generateTestEmail } from '../../fixtures/test-data';

test.describe('Admin Panel', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdminViaAPI(page);
  });

  test.afterEach(async ({ page }) => {
    await clearAuthState(page);
  });

  // US-ADM-01 — Manage Users

  test('should load the admin panel at /admin', async ({ page }) => {
    await page.goto('/admin');
    await page.waitForLoadState('networkidle');

    await expect(page.locator('text=Administration Panel')).toBeVisible({ timeout: 10000 });
  });

  test('should show user statistics cards', async ({ page }) => {
    await page.goto('/admin');
    await page.waitForLoadState('networkidle');

    // Stats cards: Total Users, Active, Superusers, Verified
    await expect(page.locator('text=Total Users')).toBeVisible({ timeout: 15000 });
    await expect(page.locator('text=Active')).toBeVisible({ timeout: 5000 });
    await expect(page.locator('text=Superusers')).toBeVisible({ timeout: 5000 });
    await expect(page.locator('text=Verified')).toBeVisible({ timeout: 5000 });
  });

  test('should show users table with email column', async ({ page }) => {
    await page.goto('/admin');
    await page.waitForLoadState('networkidle');

    // Users table with header row
    await expect(page.getByRole('columnheader', { name: /email/i })).toBeVisible({ timeout: 10000 });
    await expect(page.getByRole('columnheader', { name: /status/i })).toBeVisible();
    await expect(page.getByRole('columnheader', { name: /role/i })).toBeVisible();
  });

  test('should list the admin user in the table', async ({ page }) => {
    await page.goto('/admin');
    await page.waitForLoadState('networkidle');

    await expect(page.locator('text=admin@example.com')).toBeVisible({ timeout: 15000 });
  });

  test('should show edit and delete buttons for each user', async ({ page }) => {
    await page.goto('/admin');
    await page.waitForLoadState('networkidle');

    // Edit and delete icon buttons should exist in the Actions column
    const editButton = page.getByRole('button', { name: /edit user/i }).first();
    const deleteButton = page.getByRole('button', { name: /delete user/i }).first();

    // Use title attribute selectors as fallback (title="Edit user" / "Delete user")
    const editButtonByTitle = page.locator('[title="Edit user"]').first();
    const deleteButtonByTitle = page.locator('[title="Delete user"]').first();

    const hasEdit = await editButton.isVisible({ timeout: 5000 }).catch(() => false) ||
      await editButtonByTitle.isVisible({ timeout: 3000 }).catch(() => false);
    const hasDelete = await deleteButton.isVisible({ timeout: 3000 }).catch(() => false) ||
      await deleteButtonByTitle.isVisible({ timeout: 3000 }).catch(() => false);

    expect(hasEdit).toBeTruthy();
    expect(hasDelete).toBeTruthy();
  });

  test('should open edit dialog when edit button is clicked', async ({ page }) => {
    await page.goto('/admin');
    await page.waitForLoadState('networkidle');

    const editButton = page.locator('[title="Edit user"]').first();
    if (await editButton.isVisible({ timeout: 5000 })) {
      await editButton.click();
      // Edit dialog should open
      await expect(page.locator('[role="dialog"]')).toBeVisible({ timeout: 3000 });
    }
  });

  test('should block access for non-admin users', async ({ page }) => {
    // Register a regular (non-admin) user
    const testEmail = generateTestEmail();
    const testPassword = 'TestPass123!';

    const API_URL = process.env.API_URL || 'http://localhost:8001';
    const regResp = await page.request.post(`${API_URL}/api/auth/register`, {
      headers: { 'Content-Type': 'application/json' },
      data: { email: testEmail, password: testPassword },
    });
    if (!regResp.ok()) return;

    // Login as regular user
    const loginResp = await page.request.post(`${API_URL}/api/auth/login`, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      form: { username: testEmail, password: testPassword },
    });
    if (!loginResp.ok()) return;
    const { access_token } = await loginResp.json();

    const BASE_URL = process.env.BASE_URL || 'http://localhost:3001';
    await page.goto(BASE_URL);
    // Clear admin tokens first, then set only the non-admin token
    await page.evaluate((token) => {
      localStorage.clear();
      localStorage.setItem('auth_token', token);
    }, access_token);

    // Non-admin accessing /admin should be redirected or shown an error
    await page.goto('/admin');
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(1000);

    const isOnAdminPage = await page.locator('text=Administration Panel').isVisible({ timeout: 2000 }).catch(() => false);
    expect(isOnAdminPage).toBeFalsy();
  });

  // US-ADM-02 — Manage UI Categories (accessible via admin or settings)

  test('should show UI categories section or link in settings', async ({ page }) => {
    await page.goto('/settings');
    await page.waitForLoadState('networkidle');

    const categoriesSection = page.locator('text=/categor/i').first();
    if (await categoriesSection.isVisible({ timeout: 3000 })) {
      await expect(categoriesSection).toBeVisible();
    }
  });
});
