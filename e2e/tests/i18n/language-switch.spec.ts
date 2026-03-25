import { test, expect } from '@playwright/test';
import { loginAsAdminViaAPI, clearAuthState } from '../../fixtures/auth-helpers';

test.describe('Language Switch (i18n)', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdminViaAPI(page);
  });

  test.afterEach(async ({ page }) => {
    await clearAuthState(page);
  });

  // US-I18N-01 — Switch Language

  test('should show language switcher in the navigation on desktop', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // LanguageSwitch component in the AppBar — shows "FR" button (to switch to French)
    const langSwitcher = page.getByRole('button', { name: /^(fr|en)$/i });
    await expect(langSwitcher.first()).toBeVisible({ timeout: 5000 });
  });

  test('should switch UI language to French', async ({ page }) => {
    await page.goto('/entities');
    await page.waitForLoadState('networkidle');

    // Note the current heading text in English
    await expect(page.getByRole('heading', { name: 'Entities' })).toBeVisible();

    // Find and click the FR button (language switcher shows next lang to switch to)
    const frButton = page.getByRole('button', { name: /^fr$/i });
    await expect(frButton.first()).toBeVisible({ timeout: 5000 });
    await frButton.first().click();

    // After switching to French the heading must no longer read "Entities" in English
    await expect(page.getByRole('heading', { name: 'Entities', exact: true })).not.toBeVisible({ timeout: 3000 });
  });

  test('should switch UI language back to English', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Switch to French first
    const frButton = page.getByRole('button', { name: /^fr$/i });
    await expect(frButton.first()).toBeVisible({ timeout: 5000 });
    await frButton.first().click();

    // Then switch back to English
    const enButton = page.getByRole('button', { name: /^en$/i });
    await expect(enButton.first()).toBeVisible({ timeout: 3000 });
    await enButton.first().click();

    // Navigate to entities to verify English heading
    await page.goto('/entities');
    await expect(page.getByRole('heading', { name: 'Entities' })).toBeVisible({ timeout: 5000 });
  });

  test('should persist language selection across page navigations', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    const frButton = page.getByRole('button', { name: /^fr$/i });
    await expect(frButton.first()).toBeVisible({ timeout: 5000 });
    await frButton.first().click();

    // Navigate to a different page
    await page.goto('/sources');
    await page.waitForLoadState('networkidle');

    // Language should still be French — the Sources heading must not be the default English text
    await expect(page.getByRole('heading', { name: 'Sources', exact: true })).not.toBeVisible({ timeout: 3000 });
  });
});
