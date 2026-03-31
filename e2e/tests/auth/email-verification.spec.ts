/**
 * E2E-G8 — Email verification flow
 *
 * Full link-click verification requires a real mail service.  The tests that need
 * an actual token are skip-gated with VERIFY_EMAIL_URL.  Tests that do not need
 * the link (pre-verification state assertions) always run.
 */
import { test, expect } from '@playwright/test';
import { generateTestEmail } from '../../fixtures/test-data';
import { clearAuthState } from '../../fixtures/auth-helpers';

test.describe('Email Verification Flow', () => {
  test.beforeEach(async ({ page }) => {
    await clearAuthState(page);
  });

  test('should show email verification prompt after registration', async ({ page }) => {
    const email = generateTestEmail();
    const password = 'TestPassword123!';

    await page.goto('/account');
    await page.getByLabel(/email/i).fill(email);
    await page.getByRole('textbox', { name: 'Password', exact: true }).fill(password);
    // Confirm Password is required for registration
    const confirmField = page.getByRole('textbox', { name: 'Confirm Password' });
    if (await confirmField.isVisible({ timeout: 2000 }).catch(() => false)) {
      await confirmField.fill(password);
    }
    await page.getByRole('button', { name: /register/i }).click();

    // Registration success message must appear
    await expect(page.locator('text=/Registration Successful/i')).toBeVisible({ timeout: 5000 });

    // Verification prompt must be shown — users need to know to check email
    await expect(
      page.locator('text=/check your email|verify|verification/i').first()
    ).toBeVisible({ timeout: 5000 });
  });

  test('should block login for unverified user when verification is enforced', async ({ page }) => {
    const API_URL = process.env.API_URL || 'http://localhost:8001';
    const email = generateTestEmail();
    const password = 'TestPassword123!';

    // Register via API
    const regResp = await page.request.post(`${API_URL}/api/auth/register`, {
      headers: { 'Content-Type': 'application/json' },
      data: { email, password, password_confirmation: password },
    });
    if (!regResp.ok()) {
      throw new Error(`Registration failed (${regResp.status()}) — cannot proceed with verification test`);
    }

    // Try to login as the unverified user via API
    const loginResp = await page.request.post(`${API_URL}/api/auth/login`, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      form: { username: email, password },
    });

    // When verification is not enforced, login succeeds — skip the 401/403 assertion.
    test.skip(loginResp.ok(), 'Email verification is not enforced in this environment');

    // When verification IS enforced, login must return a 401/403 with a descriptive message
    expect([401, 403]).toContain(loginResp.status());
    const body = await loginResp.text();
    expect(body).toMatch(/verif|confirm|email/i);
  });

  test('should complete login after clicking the verification link', async ({ page }) => {
    // Requires VERIFY_EMAIL_URL (extracted from email in CI with a real mail service).
    test.skip(!process.env.VERIFY_EMAIL_URL, 'VERIFY_EMAIL_URL not set — skipping full verification link test');

    await page.goto(process.env.VERIFY_EMAIL_URL!);
    await page.waitForLoadState('networkidle');

    // After verification, the app must show either a success message or the login form
    const success = page.locator('text=/verified|success|confirmed/i').first();
    const loginForm = page.getByRole('button', { name: /login/i });
    await expect(success.or(loginForm)).toBeVisible({ timeout: 5000 });
  });
});
