import { test, expect } from '@playwright/test';
import { ADMIN_USER } from '../../fixtures/test-data';
import { clearAuthState } from '../../fixtures/auth-helpers';

test.describe('Password Reset Flow', () => {
  test.beforeEach(async ({ page }) => {
    await clearAuthState(page);
  });

  test.afterEach(async ({ page }) => {
    // Clear auth state after each test to avoid polluting other tests
    await clearAuthState(page);
  });

  test('should navigate to forgot password page', async ({ page }) => {
    await page.goto('/account');

    // Click forgot password link
    await page.getByRole('link', { name: /forgot password/i }).click();

    // Should navigate to forgot password page
    await expect(page).toHaveURL(/forgot-password/);
  });

  test('should submit password reset request', async ({ page }) => {
    await page.goto('/forgot-password');

    // Fill in email using role-based selector
    await page.getByRole('textbox', { name: /email/i }).fill(ADMIN_USER.email);

    // Submit form
    await page.getByRole('button', { name: /submit|send|reset/i }).click();

    // Should show success message (increase timeout for backend delays)
    await expect(
      page.getByRole('heading', { name: /check your email/i })
    ).toBeVisible({ timeout: 20000 });
  });

  test('should handle invalid email in password reset', async ({ page }) => {
    await page.goto('/forgot-password');

    // Fill in invalid email using role-based selector
    await page.getByRole('textbox', { name: /email/i }).fill('notanemail');

    // Submit form
    await page.getByRole('button', { name: /submit|send|reset/i }).click();

    // Should show error or stay on page
    const url = page.url();
    expect(url).toContain('forgot-password');
  });

  test('should navigate to reset password page with token', async ({ page }) => {
    // Simulate clicking a reset link with token
    const fakeToken = 'test-token-123';
    await page.goto(`/reset-password?token=${fakeToken}`);

    // Should be on reset password page
    await expect(page).toHaveURL(/reset-password/);

    // Should have password input fields (labels are not linked to inputs, use placeholders)
    await expect(page.getByPlaceholder(/enter new password/i)).toBeVisible();
    await expect(page.getByPlaceholder(/confirm new password/i)).toBeVisible();
  });
});
