/**
 * Authentication Helpers for E2E Tests
 *
 * Provides reusable authentication flows for Playwright tests
 */

import { Page } from '@playwright/test';
import { ADMIN_USER } from './test-data';

const BASE_URL = process.env.BASE_URL || 'http://localhost';

async function waitForAuthenticatedIndicator(page: Page, email?: string): Promise<void> {
  await page.waitForSelector('text=/Logged in as/i', { timeout: 20000 });

  if (email) {
    await page.waitForSelector(`text=${email}`, { timeout: 10000 });
  }
}

async function waitForAuthenticatedAccount(page: Page, email?: string): Promise<void> {
  await page.goto('/account', { waitUntil: 'networkidle' });
  await waitForAuthenticatedIndicator(page, email);
}

/**
 * Login via the UI
 */
export async function loginViaUI(
  page: Page,
  email: string,
  password: string
): Promise<void> {
  // Navigate to account page (where login form is)
  await page.goto('/account', { waitUntil: 'networkidle' });

  // Fill in credentials using role-based selectors
  const emailField = page.getByRole('textbox', { name: /email/i });
  const passwordField = page.getByRole('textbox', { name: 'Password', exact: true });
  const loginButton = page.getByRole('button', { name: /login/i });

  // Wait for fields to be visible and interactable
  await emailField.waitFor({ state: 'visible', timeout: 10000 });
  await passwordField.waitFor({ state: 'visible', timeout: 10000 });
  await loginButton.waitFor({ state: 'visible', timeout: 10000 });

  // Fill credentials
  await emailField.fill(email);
  await passwordField.fill(password);

  // Wait a moment for any validation to complete
  await page.waitForTimeout(500);

  // Click login button
  await loginButton.click();

  await waitForAuthenticatedIndicator(page, email);
}

/**
 * Login as admin via the UI
 */
export async function loginAsAdmin(page: Page): Promise<void> {
  await loginViaUI(page, ADMIN_USER.email, ADMIN_USER.password);
}

/**
 * Login via API and set auth state.
 *
 * Calls the login endpoint (which sets the httpOnly refresh cookie on the
 * browser context), then navigates to the app so the AuthContext can restore
 * the session via the refresh cookie. This is faster than UI login for tests
 * that don't need to exercise the login form.
 */
export async function loginViaAPI(
  page: Page,
  email: string,
  password: string
): Promise<{ accessToken: string; refreshToken: null }> {
  const API_URL = process.env.API_URL || 'http://localhost';

  // Login via API — the server sets the httpOnly refresh cookie on the browser context.
  const response = await page.request.post(`${API_URL}/api/auth/login`, {
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    form: {
      username: email,
      password: password,
    },
    timeout: 30000,
  });

  if (!response.ok()) {
    throw new Error(`Login failed: ${response.status()} ${await response.text()}`);
  }

  const { access_token } = await response.json();

  // Navigate to the authenticated account screen and wait for the session to be
  // fully restored via the refresh cookie before tests continue.
  await waitForAuthenticatedAccount(page, email);

  return {
    accessToken: access_token,
    refreshToken: null, // httpOnly cookie — not accessible via JS
  };
}

/**
 * Login as admin via API
 */
export async function loginAsAdminViaAPI(page: Page): Promise<{ accessToken: string; refreshToken: null }> {
  return loginViaAPI(page, ADMIN_USER.email, ADMIN_USER.password);
}

/**
 * Get a fresh access token by calling the refresh endpoint.
 *
 * Use this in tests that need to add an Authorization: Bearer header to a
 * direct page.request.* API call. The httpOnly refresh cookie must already
 * be set (i.e., the user must be logged in via loginViaAPI or loginAsAdminViaAPI).
 */
export async function getAccessToken(page: Page): Promise<string> {
  const API_URL = process.env.API_URL || 'http://localhost:8001';
  const resp = await page.request.post(`${API_URL}/api/auth/refresh`);
  if (!resp.ok()) {
    throw new Error(`getAccessToken: refresh failed with status ${resp.status()}`);
  }
  const { access_token } = await resp.json();
  return access_token;
}

/**
 * Logout via the UI
 */
export async function logoutViaUI(page: Page): Promise<void> {
  await waitForAuthenticatedAccount(page);

  await page.getByRole('button', { name: /logout/i }).click();

  await page.goto('/account', { waitUntil: 'networkidle' });
  await page.getByRole('button', { name: /login/i }).waitFor({
    state: 'visible',
    timeout: 10000,
  });
}

/**
 * Clear authentication state
 */
export async function clearAuthState(page: Page): Promise<void> {
  // Clear all storage
  await page.context().clearCookies();
  await page.goto(BASE_URL);
  await page.evaluate(() => {
    localStorage.clear();
    sessionStorage.clear();
  });
  await page.goto('/account');
  await page.waitForLoadState('domcontentloaded');
  await page.getByRole('button', { name: /login/i }).waitFor({
    state: 'visible',
    timeout: 10000,
  });
}

/**
 * Check if user is authenticated by checking UI state
 */
export async function isAuthenticated(page: Page): Promise<boolean> {
  const logoutButton = page.getByRole('button', { name: /logout/i });
  const loggedInBanner = page.locator('text=/Logged in as/i');

  if (await logoutButton.isVisible().catch(() => false)) {
    return true;
  }

  if (await loggedInBanner.isVisible().catch(() => false)) {
    return true;
  }

  await page.goto('/account', { waitUntil: 'networkidle' });
  return logoutButton.isVisible().catch(() => false);
}

/**
 * Register a new user via the UI
 */
export async function registerViaUI(
  page: Page,
  email: string,
  password: string
): Promise<void> {
  // Navigate to account page
  await page.goto('/account');

  // Fill in registration form using role-based selectors
  await page.getByRole('textbox', { name: /email/i }).fill(email);
  await page.getByRole('textbox', { name: 'Password', exact: true }).fill(password);
  await page.getByRole('textbox', { name: 'Confirm Password' }).fill(password);

  // Click register button
  await page.getByRole('button', { name: /register/i }).click();

  // Wait for success message - exact text match for better reliability
  await page.getByText('Registration Successful!', { exact: true }).waitFor({ state: 'visible', timeout: 5000 });
}

/**
 * Register a new user via API
 */
export async function registerViaAPI(
  page: Page,
  email: string,
  password: string
): Promise<{ id: string; email: string }> {
  const API_URL = process.env.API_URL || 'http://localhost';

  const response = await page.request.post(`${API_URL}/api/auth/register`, {
    headers: {
      'Content-Type': 'application/json',
    },
    data: {
      email,
      password,
      password_confirmation: password,
    },
  });

  if (!response.ok()) {
    const error = await response.text();
    throw new Error(`Registration failed: ${error}`);
  }

  return response.json();
}
