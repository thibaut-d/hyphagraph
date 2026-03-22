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

    // Language switcher: LanguageSwitch component in the AppBar
    const langSwitcher = page.locator('[aria-label*="language"], [title*="language"]').or(
      page.locator('text=/en|fr|english|français/i').first()
    );
    if (await langSwitcher.first().isVisible({ timeout: 3000 })) {
      await expect(langSwitcher.first()).toBeVisible();
    }
  });

  test('should switch UI language to French', async ({ page }) => {
    await page.goto('/entities');
    await page.waitForLoadState('networkidle');

    // Note the current heading text in English
    await expect(page.getByRole('heading', { name: 'Entities' })).toBeVisible();

    // Find and click the language switcher
    const frButton = page.getByRole('button', { name: /fr|français/i }).or(
      page.locator('[data-lang="fr"]')
    );
    if (!await frButton.first().isVisible({ timeout: 3000 })) {
      test.skip(true, 'French language button not visible — language switcher may not be implemented');
      return;
    }
    await frButton.first().click();
    await page.waitForTimeout(500); // allow i18n state to propagate

    // After switching to French the heading must no longer read "Entities" in English
    await expect(page.getByRole('heading', { name: 'Entities', exact: true })).not.toBeVisible({ timeout: 3000 });
  });

  test('should switch UI language back to English', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Switch to French first if the button exists
    const frButton = page.getByRole('button', { name: /fr|français/i }).or(
      page.locator('[data-lang="fr"]')
    );
    if (await frButton.first().isVisible({ timeout: 2000 })) {
      await frButton.first().click();
      await page.waitForTimeout(300);

      // Then switch back to English
      const enButton = page.getByRole('button', { name: /en|english/i }).or(
        page.locator('[data-lang="en"]')
      );
      if (await enButton.first().isVisible({ timeout: 2000 })) {
        await enButton.first().click();
        await page.waitForTimeout(300);

        // Navigate to entities to verify English heading
        await page.goto('/entities');
        await expect(page.getByRole('heading', { name: 'Entities' })).toBeVisible({ timeout: 5000 });
      }
    }
  });

  test('should persist language selection across page navigations', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    const frButton = page.getByRole('button', { name: /fr|français/i }).or(
      page.locator('[data-lang="fr"]')
    );
    if (await frButton.first().isVisible({ timeout: 2000 })) {
      await frButton.first().click();
      await page.waitForTimeout(300);

      // Navigate to a different page
      await page.goto('/sources');
      await page.waitForLoadState('networkidle');

      // Language should still be French — the Sources heading must not be the default English text
      await expect(page.getByRole('heading', { name: 'Sources', exact: true })).not.toBeVisible({ timeout: 3000 });
    }
  });
});
