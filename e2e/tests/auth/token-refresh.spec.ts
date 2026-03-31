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

  // G1b — refresh token rotation: old token rejected after rotation
  test('should reject the original refresh token after it has been rotated', async ({ page }) => {
    const API_URL = process.env.API_URL || 'http://localhost:8001';
    const adminEmail = process.env.ADMIN_EMAIL || 'admin@example.com';
    const adminPassword = process.env.ADMIN_PASSWORD || 'admin';

    // Login to obtain a refresh token via the httpOnly cookie path
    const loginResp = await page.request.post(`${API_URL}/api/auth/login`, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      form: { username: adminEmail, password: adminPassword },
    });
    if (!loginResp.ok()) {
      throw new Error(`Login failed (${loginResp.status()}) — check admin credentials`);
    }

    // Extract the Set-Cookie refresh_token value from the login response
    const setCookieHeader = loginResp.headers()['set-cookie'] ?? '';
    const match = setCookieHeader.match(/refresh_token=([^;]+)/);
    if (!match) {
      test.skip(true, 'refresh_token not exposed as a readable cookie in this environment');
      return;
    }
    const originalToken = match[1];

    // First refresh — rotates the token, original becomes revoked
    const firstResp = await page.request.post(`${API_URL}/api/auth/refresh`, {
      headers: { Cookie: `refresh_token=${originalToken}` },
    });
    expect(firstResp.ok()).toBe(true);

    // Second refresh using the original (now-revoked) token must be rejected
    const secondResp = await page.request.post(`${API_URL}/api/auth/refresh`, {
      headers: { Cookie: `refresh_token=${originalToken}` },
    });
    expect([401, 403]).toContain(secondResp.status());
  });
});
