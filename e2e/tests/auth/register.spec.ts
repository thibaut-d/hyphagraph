import { test, expect } from '@playwright/test';
import { generateTestEmail } from '../../fixtures/test-data';
import { registerViaUI, loginViaUI, clearAuthState } from '../../fixtures/auth-helpers';

test.describe('Registration Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Ensure clean state
    await clearAuthState(page);
  });

  test('should register a new user successfully', async ({ page }) => {
    const email = generateTestEmail();
    const password = 'TestPassword123!';

    await registerViaUI(page, email, password);

    // Should show success message (registerViaUI already waits for it)
    await expect(page.locator('text=/Registration Successful/i')).toBeVisible();

    // Should show verification message (using .first() since there are multiple matches)
    await expect(
      page.locator('text=/check your email|verify|verification/i').first()
    ).toBeVisible();
  });

  test('should show error when registering with existing email', async ({ page }) => {
    const email = 'admin@example.com'; // Existing user
    const password = 'TestPassword123!';

    await page.goto('/account');

    // Fill in registration form
    await page.getByLabel(/email/i).fill(email);
    await page.getByRole('textbox', { name: 'Password', exact: true }).fill(password);
    await page.getByRole('textbox', { name: 'Confirm Password' }).fill(password);

    // Click register button
    await page.getByRole('button', { name: /register/i }).click();

    // Should show error message — backend returns "Registration failed" for duplicate emails
    // (displayed as Typography with color="error" or as an Alert)
    await expect(
      page.locator('[class*="MuiTypography-root"]').filter({ hasText: /already|exists|registered|failed|Registration/i })
        .or(page.getByRole('alert').filter({ hasText: /already|exists|registered|failed/i }))
        .first()
    ).toBeVisible({ timeout: 5000 });
  });

  test('should show error when registering with invalid email', async ({ page }) => {
    const invalidEmail = 'not-an-email';
    const password = 'TestPassword123!';

    await page.goto('/account');

    await page.getByLabel(/email/i).fill(invalidEmail);
    await page.getByRole('textbox', { name: 'Password', exact: true }).fill(password);
    await page.getByRole('textbox', { name: 'Confirm Password' }).fill(password);
    await page.getByRole('button', { name: /register/i }).click();

    // A validation error must be visible — either from client-side HTML5 validation
    // (field stays invalid) or from a rendered error message
    const errorMsg = page.locator('[class*="MuiTypography-root"]').filter({ hasText: /invalid|not.*valid|email/i })
      .or(page.locator('[role="alert"]'))
      .first();
    const fieldInvalid = page.getByLabel(/email/i);

    const hasError = await errorMsg.isVisible({ timeout: 3000 }).catch(() => false);
    const isInvalidField = await fieldInvalid.evaluate(
      (el) => (el as HTMLInputElement).validity?.valid === false
    ).catch(() => false);

    expect(hasError || isInvalidField).toBe(true);
  });

  test('should show error when registering with weak password', async ({ page }) => {
    const email = generateTestEmail();
    const weakPassword = '123'; // Too short

    await page.goto('/account');

    // Fill in registration form
    await page.getByLabel(/email/i).fill(email);
    await page.getByRole('textbox', { name: 'Password', exact: true }).fill(weakPassword);
    await page.getByRole('textbox', { name: 'Confirm Password' }).fill(weakPassword);

    // Click register button
    await page.getByRole('button', { name: /register/i }).click();

    // Should show a user-facing error message about password length
    await expect(
      page.locator('[class*="MuiTypography-root"]').filter({ hasText: /too short|at least|minimum/i })
        .or(page.locator('[role="alert"]').filter({ hasText: /password/i }))
        .first()
    ).toBeVisible({ timeout: 5000 });
  });

  test('should allow login after successful registration', async ({ page }) => {
    const email = generateTestEmail();
    const password = 'TestPassword123!';

    // Register
    await registerViaUI(page, email, password);

    // Wait for success message (registerViaUI already waits for it)
    await expect(page.locator('text=/Registration Successful/i')).toBeVisible();

    // Try to login
    // Note: This might fail if email verification is required
    await page.goto('/account');
    await loginViaUI(page, email, password);

    // Either the user is logged in, or a specific email-verification message is shown.
    // We check both explicitly so one false-positive cannot mask a third failure mode.
    const loggedIn = await page.locator('text=Logged in as').isVisible({ timeout: 5000 }).catch(() => false);
    if (loggedIn) {
      await expect(page.locator('text=Logged in as')).toBeVisible();
      return;
    }
    // Email verification required — must show a specific verification prompt, not a generic error
    await expect(
      page.locator('text=/check your email|verification email|please verify/i').first()
    ).toBeVisible({ timeout: 5000 });
  });
});
