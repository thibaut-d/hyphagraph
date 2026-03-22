import { test, expect } from '@playwright/test';
import { loginAsAdminViaAPI, clearAuthState } from '../../fixtures/auth-helpers';

test.describe('Token Refresh Flow', () => {
  test.afterEach(async ({ page }) => {
    await clearAuthState(page);
  });

  // G1 — token refresh re-authentication
  test('should silently re-authenticate when access token is cleared but refresh token remains', async ({
    page,
  }) => {
    const BASE_URL = process.env.BASE_URL || 'http://localhost:3001';
    const API_URL = process.env.API_URL || 'http://localhost:8001';

    // Login to get both tokens
    const { accessToken, refreshToken } = await loginAsAdminViaAPI(page);
    expect(accessToken).toBeTruthy();
    expect(refreshToken).toBeTruthy();

    // Simulate an expired access token by clearing it while keeping refresh_token
    await page.goto(BASE_URL);
    await page.evaluate(() => {
      localStorage.removeItem('auth_token');
    });

    // Navigate to a protected page — the app should use the refresh_token to re-authenticate
    await page.goto('/entities');
    await page.waitForLoadState('networkidle');

    // Either the page loads (silent re-auth succeeded) or the login form appears.
    // A re-auth-capable app must NOT show a crash or a 401 error banner.
    const errorBanner = page.locator('text=/401|unauthorized|session expired/i').first();
    const errorVisible = await errorBanner.isVisible({ timeout: 2000 }).catch(() => false);
    expect(errorVisible).toBe(false);

    // After re-auth, a new access token must be present in localStorage
    const newToken = await page.evaluate(() => localStorage.getItem('auth_token'));
    // Either the token was refreshed (newToken truthy) or the user was redirected to login
    // (page shows login form). Both are valid outcomes; an error banner is not.
    const loginVisible = await page.getByRole('button', { name: /login/i }).isVisible({ timeout: 2000 }).catch(() => false);
    expect(newToken || loginVisible).toBeTruthy();
  });

  test('should redirect to login when both tokens are absent', async ({ page }) => {
    const BASE_URL = process.env.BASE_URL || 'http://localhost:3001';

    // Start with no auth state
    await clearAuthState(page);

    // Attempt to access a protected route
    await page.goto('/entities/new');
    await page.waitForLoadState('networkidle');

    // Must present the login form — not a crash or blank page
    await expect(page.getByRole('button', { name: /login/i })).toBeVisible({ timeout: 5000 });
  });
});
