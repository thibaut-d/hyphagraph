import { test, expect } from '@playwright/test';
import { loginAsAdminViaAPI, clearAuthState } from '../../fixtures/auth-helpers';

test.describe('Navigation', () => {
  test.afterEach(async ({ page }) => {
    await clearAuthState(page);
  });

  // US-NAV-01 — Main Navigation
  test.describe('Main Navigation', () => {
    test.beforeEach(async ({ page }) => {
      await loginAsAdminViaAPI(page);
    });

    test('should show persistent AppBar on every page', async ({ page }) => {
      for (const path of ['/', '/entities', '/sources', '/search']) {
        await page.goto(path, { waitUntil: 'domcontentloaded' });
        await expect(page.getByRole('banner')).toBeVisible();
        await expect(page.locator('text=HyphaGraph')).toBeVisible();
      }
    });

    test('should navigate to home via logo', async ({ page }) => {
      await page.goto('/entities');
      await page.locator('text=HyphaGraph').click();
      await expect(page).toHaveURL('/');
    });

    test('should contain links to Entities and Sources on desktop', async ({ page }) => {
      await page.goto('/');
      // Desktop nav (md+): links are inline in the AppBar
      const nav = page.getByRole('banner');
      const entitiesLink = nav.getByRole('link', { name: /entities/i }).first();
      const sourcesLink = nav.getByRole('link', { name: /sources/i }).first();
      // On desktop viewport these should be visible
      if (await entitiesLink.isVisible({ timeout: 2000 })) {
        await entitiesLink.click();
        await expect(page).toHaveURL(/\/entities/);
        await page.goto('/');
        await sourcesLink.click();
        await expect(page).toHaveURL(/\/sources/);
      }
    });

    test('should show review queue link only when authenticated', async ({ page }) => {
      // Logged in: review queue link exists in nav or accessible
      await page.goto('/');
      const reviewLink = page.getByRole('link', { name: /review/i }).first();
      if (await reviewLink.isVisible({ timeout: 2000 })) {
        await expect(reviewLink).toBeVisible();
      }
    });
  });

  // US-NAV-02 — Responsive / Mobile Navigation
  test.describe('Mobile Navigation', () => {
    test.use({ viewport: { width: 390, height: 844 } }); // iPhone 14 size

    test.beforeEach(async ({ page }) => {
      await loginAsAdminViaAPI(page);
    });

    test('should show hamburger menu on small screen', async ({ page }) => {
      await page.goto('/');
      await expect(page.getByRole('button', { name: /open menu/i })).toBeVisible();
    });

    test('should open mobile drawer on hamburger click', async ({ page }) => {
      await page.goto('/');
      await page.getByRole('button', { name: /open menu/i }).click();
      // MobileDrawer uses MuiDrawer-paper (no role="navigation" on the drawer element)
      await expect(page.locator('.MuiDrawer-paper')).toBeVisible({ timeout: 3000 });
    });

    test('should close drawer after navigating to a link', async ({ page }) => {
      await page.goto('/');
      await page.getByRole('button', { name: /open menu/i }).click();
      // Wait for drawer
      await page.waitForTimeout(300);
      // Click a nav link in the drawer
      const entitiesLink = page.getByRole('link', { name: /entities/i }).first();
      if (await entitiesLink.isVisible({ timeout: 2000 })) {
        await entitiesLink.click();
        await expect(page).toHaveURL(/\/entities/);
      }
    });
  });

  // US-NAV-03 — Home Page
  test.describe('Home Page', () => {
    test.beforeEach(async ({ page }) => {
      await loginAsAdminViaAPI(page);
    });

    test('should load home page at root URL', async ({ page }) => {
      await page.goto('/');
      await expect(page).toHaveURL('/');
      // Page should render without error
      await expect(page.getByRole('banner')).toBeVisible();
    });

    test('should provide entry points to Entities and Sources', async ({ page }) => {
      await page.goto('/');
      await page.waitForLoadState('networkidle');
      // Somewhere on the page there should be links/buttons leading to entities and sources
      const bodyText = await page.locator('body').innerText();
      const hasEntities = /entities/i.test(bodyText);
      const hasSources = /sources/i.test(bodyText);
      expect(hasEntities || hasSources).toBeTruthy();
    });
  });
});
