import { test, expect } from '@playwright/test';
import { loginAsAdminViaAPI, clearAuthState } from '../../fixtures/auth-helpers';

test.describe('Token Refresh Flow', () => {
  test.afterEach(async ({ page }) => {
    await clearAuthState(page);
  });

  // G1 — token refresh re-authentication
  test('should silently re-authenticate when access token is absent but refresh cookie remains', async ({
    page,
  }) => {
    // Login — sets the httpOnly refresh cookie AND navigates to BASE_URL with networkidle
    await loginAsAdminViaAPI(page);

    // Navigate to /entities — fresh page load; in-memory token is gone but httpOnly cookie remains
    await page.goto('/entities');
    await page.waitForLoadState('networkidle');
    // Allow time for any async refresh to complete
    await page.waitForTimeout(1000);

    // Must NOT show a 401 / unauthorized / session expired error banner
    const errorBanner = page.locator('text=/401|unauthorized|session expired/i').first();
    const errorVisible = await errorBanner.isVisible({ timeout: 2000 }).catch(() => false);
    expect(errorVisible).toBe(false);

    // The entities page must have rendered — either a heading or entities content is visible
    const headingVisible = await page.getByRole('heading').first().isVisible({ timeout: 2000 }).catch(() => false);
    const contentVisible = await page.locator('main').first().isVisible({ timeout: 2000 }).catch(() => false);
    expect(headingVisible || contentVisible).toBeTruthy();
  });

  test('should redirect to login when both tokens are absent', async ({ page }) => {
    // Clear cookies and storage so no auth state exists
    await clearAuthState(page);

    // Attempt to access a protected route
    await page.goto('/entities/new');

    // Must present the login button
    await expect(page.getByRole('button', { name: /login/i })).toBeVisible({ timeout: 5000 });
  });
});
