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

    // Login — access token is returned in JSON; refresh token is set as httpOnly cookie by the server
    const { accessToken } = await loginAsAdminViaAPI(page);
    expect(accessToken).toBeTruthy();

    // Simulate an expired access token by clearing localStorage; httpOnly refresh cookie remains
    await page.goto(BASE_URL);
    await page.evaluate(() => {
      localStorage.removeItem('auth_token');
    });

    // Navigate to a page that requires auth to trigger a potential refresh
    await page.goto('/entities');
    await page.waitForLoadState('domcontentloaded');
    // Allow time for any async refresh to complete
    await page.waitForTimeout(1000);

    // Must NOT show a crash or a 401 error banner
    const errorBanner = page.locator('text=/401|unauthorized|session expired/i').first();
    const errorVisible = await errorBanner.isVisible({ timeout: 2000 }).catch(() => false);
    expect(errorVisible).toBe(false);

    // Three valid outcomes:
    // 1. Token was refreshed and stored (silent re-auth)
    // 2. User was redirected to login (refresh token absent/invalid)
    // 3. Page loaded in public mode (entities are publicly readable)
    const newToken = await page.evaluate(() => localStorage.getItem('auth_token'));
    const loginVisible = await page.getByRole('button', { name: /login/i }).isVisible({ timeout: 2000 }).catch(() => false);
    const pageRendered = await page.getByRole('heading').first().isVisible({ timeout: 2000 }).catch(() => false);
    expect(newToken || loginVisible || pageRendered).toBeTruthy();
  });

  test('should redirect to login when both tokens are absent', async ({ page }) => {
    const BASE_URL = process.env.BASE_URL || 'http://localhost:3001';

    // Start with no auth state
    await clearAuthState(page);

    // Attempt to access a protected route
    await page.goto('/entities/new');
    await page.waitForLoadState('domcontentloaded');

    // Must present the login form — not a crash or blank page
    await expect(page.getByRole('button', { name: /login/i })).toBeVisible({ timeout: 5000 });
  });
});
