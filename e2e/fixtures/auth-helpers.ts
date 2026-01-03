/**
 * Authentication Helpers for E2E Tests
 *
 * Provides reusable authentication flows for Playwright tests
 */

import { Page } from '@playwright/test';
import { ADMIN_USER } from './test-data';

const BASE_URL = process.env.BASE_URL || 'http://localhost';

/**
 * Login via the UI
 */
export async function loginViaUI(
  page: Page,
  email: string,
  password: string
): Promise<void> {
  // Navigate to account page (where login form is)
  await page.goto('/account');

  // Fill in credentials using role-based selectors
  await page.getByRole('textbox', { name: /email/i }).fill(email);
  await page.getByLabel(/password/i).fill(password);

  // Click login button
  await page.getByRole('button', { name: /login/i }).click();

  // Wait for successful login (user info should appear on account page)
  await page.waitForSelector('text=/Logged in as/i', { timeout: 10000 });
}

/**
 * Login as admin via the UI
 */
export async function loginAsAdmin(page: Page): Promise<void> {
  await loginViaUI(page, ADMIN_USER.email, ADMIN_USER.password);
}

/**
 * Login via API and set auth state
 * This is faster than UI login for tests that don't need to test the login flow
 */
export async function loginViaAPI(
  page: Page,
  email: string,
  password: string
): Promise<{ accessToken: string; refreshToken: string }> {
  const API_URL = process.env.API_URL || 'http://localhost';

  // Login via API with extended timeout
  const response = await page.request.post(`${API_URL}/api/auth/login`, {
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    form: {
      username: email,
      password: password,
    },
    timeout: 30000, // 30 seconds timeout for API requests
  });

  if (!response.ok()) {
    throw new Error(`Login failed: ${response.status()}`);
  }

  const { access_token, refresh_token } = await response.json();

  // Set auth state in localStorage
  await page.goto(BASE_URL);
  await page.evaluate(
    ({ accessToken, refreshToken }) => {
      localStorage.setItem('auth_token', accessToken);
      localStorage.setItem('refresh_token', refreshToken);
    },
    { accessToken: access_token, refreshToken: refresh_token }
  );

  return {
    accessToken: access_token,
    refreshToken: refresh_token,
  };
}

/**
 * Login as admin via API
 */
export async function loginAsAdminViaAPI(page: Page): Promise<{ accessToken: string; refreshToken: string }> {
  return loginViaAPI(page, ADMIN_USER.email, ADMIN_USER.password);
}

/**
 * Logout via the UI
 */
export async function logoutViaUI(page: Page): Promise<void> {
  // Go to account page
  await page.goto('/account');

  // Click logout button
  await page.getByRole('button', { name: /logout/i }).click();

  // Wait for redirect to home page or login form
  await page.waitForURL(/\/(account)?$/, { timeout: 5000 });

  // Give time for auth state to clear
  await page.waitForTimeout(500);
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
  // Wait for any pending requests to complete
  await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {
    // Ignore timeout - sometimes there are long-polling requests
  });
  await page.waitForTimeout(500);
}

/**
 * Check if user is authenticated
 */
export async function isAuthenticated(page: Page): Promise<boolean> {
  await page.goto(BASE_URL);
  const hasToken = await page.evaluate(() => {
    return !!localStorage.getItem('auth_token');
  });
  return hasToken;
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
  await page.getByLabel(/password/i).fill(password);

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
    },
  });

  if (!response.ok()) {
    const error = await response.text();
    throw new Error(`Registration failed: ${error}`);
  }

  return response.json();
}
