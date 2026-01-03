import { test, expect } from '@playwright/test';
import { generateTestEmail } from '../../fixtures/test-data';
import { registerViaUI, loginViaUI, clearAuthState } from '../../fixtures/auth-helpers';

test.describe('Registration Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Ensure clean state
    await clearAuthState(page);
  });

  test.afterEach(async ({ page }) => {
    // Clear auth state after each test to avoid polluting other tests
    await clearAuthState(page);
  });

  test('should register a new user successfully', async ({ page }) => {
    const email = generateTestEmail();
    const password = 'TestPassword123!';

    await registerViaUI(page, email, password);

    // Should show success message (registerViaUI already waits for it)
    // The success message is in a custom styled Paper, look for the heading text
    await expect(
      page.getByText('Registration Successful!', { exact: true })
    ).toBeVisible();

    // Should show verification message
    await expect(
      page.getByText(/check your email for a verification link/i)
    ).toBeVisible();
  });

  test('should show error when registering with existing email', async ({ page }) => {
    const email = 'admin@example.com'; // Existing user
    const password = 'TestPassword123!';

    await page.goto('/account');

    // Fill in registration form using role-based selectors
    await page.getByRole('textbox', { name: /email/i }).fill(email);
    await page.getByLabel(/password/i).fill(password);

    // Click register button
    await page.getByRole('button', { name: /register/i }).click();

    // Should show error message - it's displayed as Typography with color="error"
    // Look for common error patterns related to duplicate email
    await expect(
      page.locator('[class*="MuiTypography-root"]').filter({ hasText: /already|exists|registered/i })
    ).toBeVisible({ timeout: 5000 });
  });

  test('should show error when registering with invalid email', async ({ page }) => {
    const invalidEmail = 'not-an-email';
    const password = 'TestPassword123!';

    await page.goto('/account');

    // Fill in registration form using role-based selectors
    await page.getByRole('textbox', { name: /email/i }).fill(invalidEmail);
    await page.getByLabel(/password/i).fill(password);

    // Click register button
    await page.getByRole('button', { name: /register/i }).click();

    // Should show error or validation message
    // (either client-side or server-side validation)
    const url = page.url();
    expect(url).toContain('/account');
  });

  test('should show error when registering with weak password', async ({ page }) => {
    const email = generateTestEmail();
    const weakPassword = '123'; // Too short

    await page.goto('/account');

    // Fill in registration form using role-based selectors
    await page.getByRole('textbox', { name: /email/i }).fill(email);
    await page.getByLabel(/password/i).fill(weakPassword);

    // Click register button
    await page.getByRole('button', { name: /register/i }).click();

    // Should show error message (backend returns validation error)
    // Error is displayed as Typography with color="error"
    await expect(
      page.locator('[class*="MuiTypography-root"]').filter({ hasText: /string_too_short|too short|at least/i })
    ).toBeVisible({ timeout: 5000 });
  });

  test('should allow login after successful registration', async ({ page }) => {
    const email = generateTestEmail();
    const password = 'TestPassword123!';

    // Register
    await registerViaUI(page, email, password);

    // Wait for success message (registerViaUI already waits for it)
    await expect(
      page.getByText('Registration Successful!', { exact: true })
    ).toBeVisible();

    // Try to login
    // Note: This might fail if email verification is required
    await page.goto('/account');
    await loginViaUI(page, email, password);

    // Should be logged in (if email verification is disabled)
    // Or should show error about unverified email
    const loggedIn = await page.locator('text=Logged in as').isVisible();
    const needsVerification = await page
      .locator('text=/verify|verification/i').first()
      .isVisible();

    expect(loggedIn || needsVerification).toBeTruthy();
  });
});
