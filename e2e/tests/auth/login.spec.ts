import { test, expect } from '@playwright/test';
import { ADMIN_USER, generateTestEmail } from '../../fixtures/test-data';
import {
  loginViaUI,
  loginAsAdmin,
  loginAsAdminViaAPI,
  logoutViaUI,
  clearAuthState,
  isAuthenticated,
  registerViaAPI,
} from '../../fixtures/auth-helpers';

test.describe('Login Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Ensure clean state
    await clearAuthState(page);
  });

  test.afterEach(async ({ page }) => {
    // Clear auth state after each test to avoid polluting other tests
    await clearAuthState(page);
  });

  test('should login successfully with valid credentials', async ({ page }) => {
    await loginViaUI(page, ADMIN_USER.email, ADMIN_USER.password);

    // Should be redirected to home page or account page
    await expect(page.locator('text=Logged in as')).toBeVisible();
    await expect(page.locator(`text=${ADMIN_USER.email}`)).toBeVisible();

    // Check that auth token is set
    const authenticated = await isAuthenticated(page);
    expect(authenticated).toBe(true);
  });

  test('should show error with invalid credentials', async ({ page }) => {
    await page.goto('/account');

    // Fill in invalid credentials using role-based selectors
    await page.getByRole('textbox', { name: /email/i }).fill('invalid@example.com');
    await page.getByLabel(/password/i).fill('wrongpassword');

    // Click login button
    await page.getByRole('button', { name: /login/i }).click();

    // Should show error message
    await expect(page.locator('text=/incorrect|error|invalid|failed/i')).toBeVisible({
      timeout: 5000,
    });

    // Should not be authenticated
    const authenticated = await isAuthenticated(page);
    expect(authenticated).toBe(false);
  });

  test('should show error with empty credentials', async ({ page }) => {
    await page.goto('/account');

    // Click login button without filling credentials
    await page.getByRole('button', { name: /login/i }).click();

    // Should still be on login page (validation should prevent submission)
    const url = page.url();
    expect(url).toContain('/account');
  });

  test('should logout successfully', async ({ page }) => {
    // Login first
    await loginAsAdmin(page);

    // Verify logged in
    const authenticatedBefore = await isAuthenticated(page);
    expect(authenticatedBefore).toBe(true);

    // Logout
    await logoutViaUI(page);

    // Should be logged out
    const authenticatedAfter = await isAuthenticated(page);
    expect(authenticatedAfter).toBe(false);

    // Navigate to account page to verify login form is shown
    await page.goto('/account');
    await expect(page.getByRole('button', { name: /login/i })).toBeVisible({ timeout: 5000 });
  });

  test('should persist login across page refreshes', async ({ page }) => {
    // Use UI login instead of API to avoid timeout issues
    await loginAsAdmin(page);

    // Verify logged in
    await expect(page.locator('text=Logged in as')).toBeVisible({ timeout: 10000 });

    // Refresh the page
    await page.reload();

    // Should still be logged in after refresh
    await expect(page.locator('text=Logged in as')).toBeVisible({ timeout: 10000 });

    const authenticated = await isAuthenticated(page);
    expect(authenticated).toBe(true);
  });

  test('should redirect to account page when accessing protected route without auth', async ({
    page,
  }) => {
    // Ensure not authenticated
    await clearAuthState(page);

    // Try to access a protected route
    await page.goto('/entities/new');

    // Should show login form or be blocked
    // (ProtectedRoute component should handle this)
    const url = page.url();
    const hasLoginForm = await page.getByRole('button', { name: /login/i }).isVisible();

    // Either redirected to login or shows login prompt
    expect(hasLoginForm || url.includes('account')).toBeTruthy();
  });
});
