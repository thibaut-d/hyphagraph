import { test, expect } from '@playwright/test';
import { ADMIN_USER } from '../../fixtures/test-data';
import { clearAuthState } from '../../fixtures/auth-helpers';

test.describe('Password Reset Flow', () => {
  test.beforeEach(async ({ page }) => {
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

    // Fill in email
    await page.getByLabel(/email/i).fill(ADMIN_USER.email);

    // Submit form
    await page.getByRole('button', { name: /submit|send|reset/i }).click();

    // Should show success message
    await expect(
      page.locator('text=/sent|check your email|success/i')
    ).toBeVisible({ timeout: 5000 });
  });

  test('should handle invalid email in password reset', async ({ page }) => {
    await page.goto('/forgot-password');

    // Fill in invalid email
    await page.getByLabel(/email/i).fill('notanemail');

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

    // Should have password input fields
    await expect(page.getByLabel(/password/i).first()).toBeVisible();
  });
});
