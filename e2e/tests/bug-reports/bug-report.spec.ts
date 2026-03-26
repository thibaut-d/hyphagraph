import { test, expect } from '@playwright/test';
import { loginAsAdminViaAPI, clearAuthState, getAccessToken } from '../../fixtures/auth-helpers';

test.describe('Bug Report', () => {
  test.afterEach(async ({ page }) => {
    await clearAuthState(page);
  });

  // US-BUG-01 — Bug report icon in toolbar
  test.describe('Toolbar icon', () => {
    test('should show bug report icon on every page (anonymous)', async ({ page }) => {
      for (const path of ['/', '/entities', '/sources', '/search']) {
        await page.goto(path, { waitUntil: 'networkidle' });
        await expect(page.getByRole('button', { name: /report a bug/i })).toBeVisible({ timeout: 10000 });
      }
    });

    test('should show bug report icon when authenticated', async ({ page }) => {
      await loginAsAdminViaAPI(page);
      await page.goto('/');
      await expect(page.getByRole('button', { name: /report a bug/i })).toBeVisible();
    });
  });

  // US-BUG-02 — Authenticated user flow
  test.describe('Authenticated user', () => {
    test.beforeEach(async ({ page }) => {
      await loginAsAdminViaAPI(page);
    });

    test('should open dialog on icon click', async ({ page }) => {
      await page.goto('/');
      await page.getByRole('button', { name: /report a bug/i }).click();
      await expect(page.getByRole('dialog')).toBeVisible({ timeout: 3000 });
      await expect(page.getByText(/report a bug/i).first()).toBeVisible();
    });

    test('should not show CAPTCHA for authenticated users', async ({ page }) => {
      await page.goto('/');
      await page.getByRole('button', { name: /report a bug/i }).click();
      await expect(page.getByRole('dialog')).toBeVisible({ timeout: 3000 });
      // CAPTCHA field is only shown for anonymous users
      await expect(page.getByText(/loading captcha/i)).not.toBeVisible();
      await expect(page.locator('[inputmode="numeric"]')).not.toBeVisible();
    });

    test('should show validation error when message is too short', async ({ page }) => {
      await page.goto('/');
      await page.getByRole('button', { name: /report a bug/i }).click();
      await expect(page.getByRole('dialog')).toBeVisible({ timeout: 3000 });
      await page.getByLabel(/describe the issue/i).fill('too short');
      await page.getByRole('button', { name: /submit report/i }).click();
      await expect(page.getByRole('alert')).toBeVisible({ timeout: 3000 });
      await expect(page.getByText(/10 characters/i)).toBeVisible();
    });

    test('should submit report and show success', async ({ page }) => {
      await page.goto('/');
      await page.getByRole('button', { name: /report a bug/i }).click();
      await expect(page.getByRole('dialog')).toBeVisible({ timeout: 3000 });
      await page.getByLabel(/describe the issue/i).fill('This is a test bug report with enough detail to pass validation.');
      await page.getByRole('button', { name: /submit report/i }).click();
      await expect(page.getByRole('alert').filter({ hasText: /thank you|submitted/i })).toBeVisible({ timeout: 5000 });
    });

    test('should close dialog after successful submission', async ({ page }) => {
      await page.goto('/');
      await page.getByRole('button', { name: /report a bug/i }).click();
      await expect(page.getByRole('dialog')).toBeVisible({ timeout: 3000 });
      await page.getByLabel(/describe the issue/i).fill('Bug report closed after success — enough text here.');
      await page.getByRole('button', { name: /submit report/i }).click();
      await expect(page.getByRole('alert').filter({ hasText: /thank you|submitted/i })).toBeVisible({ timeout: 5000 });
      await page.getByRole('button', { name: /close/i }).click();
      await expect(page.getByRole('dialog')).not.toBeVisible({ timeout: 2000 });
    });

    test('should appear in admin bug reports list after submission', async ({ page }) => {
      const API_URL = process.env.API_URL || 'http://localhost:8001';
      const message = `E2E-admin-report-${Date.now()}-enough-length`;

      await page.goto('/');
      await page.getByRole('button', { name: /report a bug/i }).click();
      await expect(page.getByRole('dialog')).toBeVisible({ timeout: 3000 });
      await page.getByLabel(/describe the issue/i).fill(message);
      await page.getByRole('button', { name: /submit report/i }).click();
      await expect(page.getByRole('alert').filter({ hasText: /thank you|submitted/i })).toBeVisible({ timeout: 5000 });

      // Verify it appears in the admin API
      const token = await getAccessToken(page);
      const resp = await page.request.get(`${API_URL}/api/bug-reports`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      expect(resp.ok()).toBeTruthy();
      const items: { message: string }[] = await resp.json();
      const found = items.some((r) => r.message === message);
      expect(found).toBeTruthy();
    });
  });

  // US-BUG-03 — Anonymous user flow
  test.describe('Anonymous user', () => {
    test('should open dialog on icon click', async ({ page }) => {
      await page.goto('/');
      await page.getByRole('button', { name: /report a bug/i }).click();
      await expect(page.getByRole('dialog')).toBeVisible({ timeout: 3000 });
    });

    test('should show CAPTCHA for anonymous users', async ({ page }) => {
      await page.goto('/');
      await page.getByRole('button', { name: /report a bug/i }).click();
      await expect(page.getByRole('dialog')).toBeVisible({ timeout: 3000 });
      // CAPTCHA field (numeric input) must appear
      await expect(page.locator('[inputmode="numeric"]')).toBeVisible({ timeout: 5000 });
    });

    test('should show validation error for too-short message', async ({ page }) => {
      await page.goto('/');
      await page.getByRole('button', { name: /report a bug/i }).click();
      await expect(page.getByRole('dialog')).toBeVisible({ timeout: 3000 });
      // Wait for CAPTCHA to load
      await expect(page.locator('[inputmode="numeric"]')).toBeVisible({ timeout: 5000 });
      await page.getByLabel(/describe the issue/i).fill('tiny');
      await page.getByRole('button', { name: /submit report/i }).click();
      await expect(page.getByRole('alert')).toBeVisible({ timeout: 3000 });
      await expect(page.getByText(/10 characters/i)).toBeVisible();
    });

    test('should submit report with correct CAPTCHA answer', async ({ page }) => {
      await page.goto('/');
      await page.getByRole('button', { name: /report a bug/i }).click();
      await expect(page.getByRole('dialog')).toBeVisible({ timeout: 3000 });

      // Wait for CAPTCHA to load and read the question from the label
      const captchaInput = page.locator('[inputmode="numeric"]');
      await expect(captchaInput).toBeVisible({ timeout: 5000 });

      // The label of the numeric input IS the math question (e.g. "What is 3 + 4?")
      // MUI TextField renders a <label for="..."> linked to the input id
      const label = await captchaInput.evaluate((el: HTMLElement) => {
        const id = el.id;
        if (id) {
          const labelEl = document.querySelector(`label[for="${id}"]`);
          if (labelEl) return labelEl.textContent;
        }
        return null;
      });

      // Parse "What is A op B?" and compute answer
      const match = (label ?? '').match(/(\d+)\s*([+\-*×x])\s*(\d+)/);
      let answer = '0';
      if (match) {
        const a = parseInt(match[1], 10);
        const op = match[2];
        const b = parseInt(match[3], 10);
        if (op === '+') answer = String(a + b);
        else if (op === '-') answer = String(a - b);
        else answer = String(a * b);
      }

      await page.getByLabel(/describe the issue/i).fill('Anonymous E2E test report with enough characters here.');
      await captchaInput.fill(answer);
      await page.getByRole('button', { name: /submit report/i }).click();
      await expect(page.getByRole('alert').filter({ hasText: /thank you|submitted/i })).toBeVisible({ timeout: 5000 });
    });

    test('should show error on wrong CAPTCHA answer', async ({ page }) => {
      await page.goto('/');
      await page.getByRole('button', { name: /report a bug/i }).click();
      await expect(page.getByRole('dialog')).toBeVisible({ timeout: 3000 });

      const captchaInput = page.locator('[inputmode="numeric"]');
      await expect(captchaInput).toBeVisible({ timeout: 5000 });

      await page.getByLabel(/describe the issue/i).fill('Wrong CAPTCHA test — this message is long enough to pass.');
      await captchaInput.fill('9999');
      await page.getByRole('button', { name: /submit report/i }).click();
      await expect(page.getByRole('alert').filter({ hasText: /failed|error|captcha/i })).toBeVisible({ timeout: 5000 });
    });
  });
});
