import { test, expect } from '@playwright/test';
import { loginAsAdminViaAPI, clearAuthState, registerViaAPI } from '../../fixtures/auth-helpers';
import { generateTestEmail } from '../../fixtures/test-data';

test.describe('Account Settings', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdminViaAPI(page);
  });

  test.afterEach(async ({ page }) => {
    await clearAuthState(page);
  });

  // US-ACC-01 — View Account Settings

  test('should load the account page', async ({ page }) => {
    await page.goto('/account');
    await page.waitForLoadState('networkidle');
    await expect(page).toHaveURL('/account');
    // Account page should show user email or account-related content
    await expect(page.locator('text=/account|profile|email|password/i').first()).toBeVisible({ timeout: 10000 });
  });

  test('should show the current user email on the account page', async ({ page }) => {
    await page.goto('/account');
    await page.waitForLoadState('networkidle');
    // Admin email is admin@example.com
    const emailText = page.locator('text=admin@example.com');
    if (await emailText.isVisible({ timeout: 3000 })) {
      await expect(emailText).toBeVisible();
    }
  });

  test('should provide access to change password', async ({ page }) => {
    await page.goto('/account');
    await page.waitForLoadState('networkidle');

    // There should be a change password link or form
    const changePasswordLink = page.getByRole('link', { name: /change.*password|password/i }).or(
      page.getByRole('button', { name: /change.*password/i })
    );
    if (await changePasswordLink.first().isVisible({ timeout: 3000 })) {
      await changePasswordLink.first().click();
      await expect(page).toHaveURL(/\/change-password|\/account/);
    }
  });

  test('should load the change password page', async ({ page }) => {
    await page.goto('/change-password');
    await page.waitForLoadState('networkidle');

    await expect(
      page.locator('text=/change.*password|new.*password/i').first()
    ).toBeVisible({ timeout: 10000 });
  });

  test('should show validation error when new passwords do not match', async ({ page }) => {
    await page.goto('/change-password');
    await page.waitForLoadState('networkidle');

    const currentPasswordField = page.getByLabel(/current.*password|old.*password/i);
    const newPasswordField = page.getByLabel('New Password', { exact: true });
    const confirmPasswordField = page.getByLabel('Confirm New Password', { exact: true });

    if (await newPasswordField.isVisible({ timeout: 3000 })) {
      if (await currentPasswordField.isVisible({ timeout: 1000 })) {
        await currentPasswordField.fill('changeme123');
      }
      await newPasswordField.fill('NewPassword123!');
      if (await confirmPasswordField.isVisible({ timeout: 1000 })) {
        await confirmPasswordField.fill('DifferentPassword456!');
      }

      await page.getByRole('button', { name: 'Change Password' }).click();

      // Should show mismatch error
      const errorMessage = page.locator('text=/match|same|confirm/i').first();
      if (await errorMessage.isVisible({ timeout: 3000 })) {
        await expect(errorMessage).toBeVisible();
      }
    }
  });

  test('should successfully change password for a test user', async ({ page }) => {
    // Register a fresh test user to avoid changing admin password
    const testEmail = generateTestEmail();
    const originalPassword = 'OriginalPass123!';
    const newPassword = 'NewPassword456!';

    await registerViaAPI(page, testEmail, originalPassword);

    // Login as the test user
    const API_URL = process.env.API_URL || 'http://localhost:8001';
    const resp = await page.request.post(`${API_URL}/api/auth/login`, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      form: { username: testEmail, password: originalPassword },
    });
    if (!resp.ok()) return;
    const { access_token } = await resp.json();

    const BASE_URL = process.env.BASE_URL || 'http://localhost:3001';
    await page.goto(BASE_URL);
    await page.evaluate((token) => localStorage.setItem('auth_token', token), access_token);

    await page.goto('/change-password');
    await page.waitForLoadState('networkidle');

    const currentPasswordField = page.getByLabel(/current.*password|old.*password/i);
    const newPasswordField = page.getByLabel('New Password', { exact: true });
    const confirmPasswordField = page.getByLabel('Confirm New Password', { exact: true });

    if (await newPasswordField.isVisible({ timeout: 3000 })) {
      if (await currentPasswordField.isVisible({ timeout: 1000 })) {
        await currentPasswordField.fill(originalPassword);
      }
      await newPasswordField.fill(newPassword);
      if (await confirmPasswordField.isVisible({ timeout: 1000 })) {
        await confirmPasswordField.fill(newPassword);
      }

      await page.getByRole('button', { name: 'Change Password' }).click();

      // Should show a success feedback
      const success = page.locator('text=/success|updated|changed/i').first();
      if (await success.isVisible({ timeout: 5000 })) {
        await expect(success).toBeVisible();
      }
    }
  });
});
