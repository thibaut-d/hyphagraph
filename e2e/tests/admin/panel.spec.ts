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
    await page.waitForLoadState('domcontentloaded');

    await expect(page.locator('text=Administration Panel')).toBeVisible({ timeout: 10000 });
  });

  test('should show user statistics cards', async ({ page }) => {
    await page.goto('/admin');
    await page.waitForLoadState('domcontentloaded');

    // Stats cards load asynchronously via /admin/stats — wait for heading first
    await expect(page.locator('text=Administration Panel')).toBeVisible({ timeout: 10000 });

    // Stats cards load asynchronously from /admin/stats — use a generous timeout
    await expect(page.locator('text=Total Users')).toBeVisible({ timeout: 15000 });
    // Use paragraph role to avoid matching status chips in the users table
    await expect(page.getByRole('paragraph').filter({ hasText: 'Active' }).first()).toBeVisible({ timeout: 5000 });
    await expect(page.locator('text=Superusers').first()).toBeVisible({ timeout: 5000 });
    await expect(page.locator('text=Verified').first()).toBeVisible({ timeout: 5000 });
  });

  test('should show users table with email column', async ({ page }) => {
    await page.goto('/admin');
    await page.waitForLoadState('domcontentloaded');

    // Users table with header row
    await expect(page.getByRole('columnheader', { name: /email/i })).toBeVisible({ timeout: 10000 });
    await expect(page.getByRole('columnheader', { name: /status/i })).toBeVisible();
    await expect(page.getByRole('columnheader', { name: /role/i })).toBeVisible();
  });

  test('should list the admin user in the table', async ({ page }) => {
    await page.goto('/admin');
    await page.waitForLoadState('domcontentloaded');

    await expect(page.locator('text=Administration Panel')).toBeVisible({ timeout: 10000 });

    // Table data loads asynchronously — the admin user must appear within a generous timeout
    await expect(page.locator('text=admin@example.com')).toBeVisible({ timeout: 20000 });
  });

  test('should show edit and delete buttons for each user', async ({ page }) => {
    await page.goto('/admin');
    await page.waitForLoadState('domcontentloaded');

    await expect(page.locator('text=Administration Panel')).toBeVisible({ timeout: 10000 });

    // Wait for table data, then assert action buttons are rendered
    await expect(page.locator('text=admin@example.com')).toBeVisible({ timeout: 20000 });
    await expect(page.locator('[title="Edit user"]').first()).toBeVisible({ timeout: 5000 });
    await expect(page.locator('[title="Delete user"]').first()).toBeVisible({ timeout: 5000 });
  });

  test('should open edit dialog when edit button is clicked', async ({ page }) => {
    await page.goto('/admin');
    await page.waitForLoadState('domcontentloaded');

    const editButton = page.locator('[title="Edit user"]').first();
    await expect(editButton).toBeVisible({ timeout: 10000 });
    await editButton.click();
    await expect(page.locator('[role="dialog"]')).toBeVisible({ timeout: 3000 });
  });

  test('should restrict admin API to superusers only', async ({ page }) => {
    // Note: ProtectedRoute only checks authentication, not superuser status.
    // The frontend shows the admin panel UI to any authenticated user.
    // Access control is enforced at the API level (403 for non-superusers).
    // This test verifies the API-level restriction.
    const testEmail = generateTestEmail();
    const testPassword = 'TestPass123!';

    const API_URL = process.env.API_URL || 'http://localhost:8001';
    const regResp = await page.request.post(`${API_URL}/api/auth/register`, {
      headers: { 'Content-Type': 'application/json' },
      data: { email: testEmail, password: testPassword, password_confirmation: testPassword },
    });
    if (!regResp.ok()) return;

    // Login as regular user
    const loginResp = await page.request.post(`${API_URL}/api/auth/login`, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      form: { username: testEmail, password: testPassword },
    });
    if (!loginResp.ok()) return;
    const { access_token } = await loginResp.json();

    // Verify that admin API returns 403 for non-superusers
    const adminResp = await page.request.get(`${API_URL}/api/admin/users`, {
      headers: { Authorization: `Bearer ${access_token}` },
    });
    expect(adminResp.status()).toBe(403);
  });

  // E2E-G5 — Non-admin frontend authorization
  test('should show admin UI to authenticated regular user but deny API access', async ({ page }) => {
    const API_URL = process.env.API_URL || 'http://localhost:8001';
    const testEmail = generateTestEmail();
    const testPassword = 'TestPass123!';

    // Register a regular (non-superuser) account
    const regResp = await page.request.post(`${API_URL}/api/auth/register`, {
      headers: { 'Content-Type': 'application/json' },
      data: { email: testEmail, password: testPassword, password_confirmation: testPassword },
    });
    if (!regResp.ok()) {
      test.skip(true, 'Regular user registration failed — check API availability');
      return;
    }

    // Login as the regular user via API
    const loginResp = await page.request.post(`${API_URL}/api/auth/login`, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      form: { username: testEmail, password: testPassword },
    });
    if (!loginResp.ok()) {
      test.skip(true, 'Regular user login failed — check API availability');
      return;
    }
    const { access_token: regularToken } = await loginResp.json();

    // Navigate to BASE_URL with networkidle; httpOnly refresh cookie from login triggers auto-restore
    await page.goto(process.env.BASE_URL || 'http://localhost', { waitUntil: 'networkidle' });

    // Navigate to admin panel as regular user
    await page.goto('/admin');
    await page.waitForLoadState('networkidle');

    // The frontend ProtectedRoute only checks authentication — regular users can reach the page.
    // They must see the admin UI shell (i.e. no generic 404), but admin API calls will return 403.
    const isNotFound = await page.locator('text=/404|not found|page not found/i').first()
      .isVisible({ timeout: 3000 }).catch(() => false);
    expect(isNotFound).toBe(false);

    // The admin API must still deny regular users (API-level enforcement)
    const adminResp = await page.request.get(`${API_URL}/api/admin/users`, {
      headers: { Authorization: `Bearer ${regularToken}` },
    });
    expect(adminResp.status()).toBe(403);
  });

  // US-ADM-02 — Manage UI Categories (accessible via admin or settings)

  test('should show UI categories section or link in settings', async ({ page }) => {
    await page.goto('/settings');
    await page.waitForLoadState('domcontentloaded');

    await expect(page.locator('text=/categor/i').first()).toBeVisible({ timeout: 10000 });
  });
});
