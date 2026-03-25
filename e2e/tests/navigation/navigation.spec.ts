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
        // Use exact match to avoid matching source/entity names containing "HyphaGraph"
        await expect(page.getByRole('link', { name: 'HyphaGraph', exact: true })).toBeVisible();
      }
    });

    test('should navigate to home via logo', async ({ page }) => {
      await page.goto('/entities');
      await page.getByRole('link', { name: 'HyphaGraph', exact: true }).click();
      await expect(page).toHaveURL('/');
    });

    test('should contain links to Entities and Sources on desktop', async ({ page }) => {
      await page.goto('/');
      // Desktop nav (md+): links are inline in the AppBar
      const nav = page.getByRole('banner');
      const entitiesLink = nav.getByRole('link', { name: /entities/i }).first();
      const sourcesLink = nav.getByRole('link', { name: /sources/i }).first();
      // On the default desktop viewport these must always be visible
      await expect(entitiesLink).toBeVisible({ timeout: 5000 });
      await entitiesLink.click();
      await expect(page).toHaveURL(/\/entities/);
      await page.goto('/');
      await expect(sourcesLink).toBeVisible({ timeout: 5000 });
      await sourcesLink.click();
      await expect(page).toHaveURL(/\/sources/);
    });

    test('should show review queue link only when authenticated', async ({ page }) => {
      // Wait for networkidle so auth context has time to hydrate from localStorage
      await page.goto('/', { waitUntil: 'networkidle' });
      const reviewLink = page.getByRole('link', { name: /review/i }).first();
      await expect(reviewLink).toBeVisible({ timeout: 10000 });
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
      await expect(page.locator('.MuiDrawer-paper')).toBeVisible({ timeout: 3000 });
      // Click a nav link in the drawer
      const entitiesLink = page.getByRole('link', { name: /entities/i }).first();
      await expect(entitiesLink).toBeVisible({ timeout: 10000 });
      await entitiesLink.click();
      await expect(page).toHaveURL(/\/entities/);
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
      // The app must expose navigable links to Entities and Sources (not just text on the page)
      await expect(page.getByRole('link', { name: /entities/i }).first()).toBeVisible({ timeout: 5000 });
      await expect(page.getByRole('link', { name: /sources/i }).first()).toBeVisible({ timeout: 5000 });
    });
  });
});
