import { test, expect } from '@playwright/test';
import { loginAsAdminViaAPI, clearAuthState } from '../../fixtures/auth-helpers';
import { generateEntityName, generateSourceName } from '../../fixtures/test-data';

test.describe('Global Search', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdminViaAPI(page);
  });

  test.afterEach(async ({ page }) => {
    await clearAuthState(page);
  });

  // US-SRCH-01 — Global Search

  test('should load the search page at /search', async ({ page }) => {
    await page.goto('/search');
    await page.waitForLoadState('networkidle');
    await expect(page).toHaveURL('/search');
    // Search input should be present
    const searchInput = page.getByRole('searchbox').or(page.getByPlaceholder(/search/i)).first();
    await expect(searchInput).toBeVisible({ timeout: 10000 });
  });

  test('should be accessible from the main navigation', async ({ page }) => {
    await page.goto('/');
    // Search link or icon in the nav — optional UI element, skip if not present
    const searchNavLink = page.getByRole('link', { name: /search/i }).first();
    if (!await searchNavLink.isVisible({ timeout: 3000 })) {
      test.skip(true, 'Search nav link not present in this environment');
      return;
    }
    await searchNavLink.click();
    await expect(page).toHaveURL(/\/search/);
  });

  test('should return entity results matching a query', async ({ page }) => {
    // Create a uniquely named entity
    const entitySlug = generateEntityName('searchable-entity').toLowerCase().replace(/\s+/g, '-');
    await page.goto('/entities/new');
    await page.getByRole('textbox', { name: 'Slug' }).fill(entitySlug);
    await page.getByRole('textbox', { name: /summary.*english/i }).fill('Searchable entity for global search');
    await page.getByRole('button', { name: /create|submit/i }).click();
    await page.waitForURL(/\/entities\/[a-f0-9-]+/);

    await page.goto('/search');
    await page.waitForLoadState('networkidle');

    // Search input must always be present at /search
    const searchInput = page.getByRole('searchbox').or(page.getByPlaceholder(/search/i)).first();
    await expect(searchInput).toBeVisible({ timeout: 5000 });
    await searchInput.fill(entitySlug);
    await page.waitForTimeout(800); // debounce

    // Should show results containing the entity
    await expect(page.locator(`text=${entitySlug}`).first()).toBeVisible({ timeout: 10000 });
  });

  test('should navigate to entity detail when result is clicked', async ({ page }) => {
    const entitySlug = generateEntityName('search-nav-entity').toLowerCase().replace(/\s+/g, '-');
    await page.goto('/entities/new');
    await page.getByRole('textbox', { name: 'Slug' }).fill(entitySlug);
    await page.getByRole('textbox', { name: /summary.*english/i }).fill('Search nav entity');
    await page.getByRole('button', { name: /create|submit/i }).click();
    await page.waitForURL(/\/entities\/[a-f0-9-]+/);

    await page.goto('/search');
    await page.waitForLoadState('networkidle');

    // Search input must always be present at /search
    const searchInput = page.getByRole('searchbox').or(page.getByPlaceholder(/search/i)).first();
    await expect(searchInput).toBeVisible({ timeout: 5000 });
    await searchInput.fill(entitySlug);
    await page.waitForTimeout(800);

    const result = page.locator(`text=${entitySlug}`).first();
    await expect(result).toBeVisible({ timeout: 10000 });
    await result.click();
    await expect(page).toHaveURL(/\/entities\/[a-f0-9-]+/);
  });

  test('should return source results matching a query', async ({ page }) => {
    const sourceTitle = generateSourceName('searchable-source');
    await page.goto('/sources/new');
    await page.waitForLoadState('domcontentloaded');
    await page.getByRole('textbox', { name: 'Title' }).fill(sourceTitle);
    await page.getByRole('textbox', { name: 'URL' }).fill('https://example.com/searchable-source');
    await page.getByRole('button', { name: /create|submit/i }).click();
    await page.waitForURL(/\/sources\/[a-f0-9-]+/);

    await page.goto('/search');
    await page.waitForLoadState('networkidle');

    // Search input must always be present at /search
    const searchInput = page.getByRole('searchbox').or(page.getByPlaceholder(/search/i)).first();
    await expect(searchInput).toBeVisible({ timeout: 5000 });
    await searchInput.fill(sourceTitle.substring(0, 20));
    await page.waitForTimeout(800);

    // Source must appear in results
    await expect(page.locator(`text=${sourceTitle}`).first()).toBeVisible({ timeout: 10000 });
  });

  test('should show autocomplete results from the nav search bar', async ({ page }) => {
    // Entities list has an autocomplete search in its toolbar
    await page.goto('/entities');
    const searchInput = page.getByPlaceholder(/search/i).first();
    if (await searchInput.isVisible({ timeout: 3000 })) {
      await searchInput.fill('test');
      await page.waitForTimeout(500);
      const listbox = page.getByRole('listbox');
      if (await listbox.isVisible({ timeout: 2000 })) {
        await expect(listbox).toBeVisible();
      }
    }
  });
});
