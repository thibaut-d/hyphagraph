import { test, expect } from '../../fixtures/test-fixtures';
import { loginAsAdminViaAPI, clearAuthState } from '../../fixtures/auth-helpers';

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
    const searchInput = page.getByRole('searchbox').or(page.getByPlaceholder(/search/i)).first();
    await expect(searchInput).toBeVisible({ timeout: 10000 });
  });

  test('should be accessible from the main navigation', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    const searchNavLink = page.getByRole('link', { name: /search/i }).first();
    await expect(searchNavLink).toBeVisible({ timeout: 5000 });
    await searchNavLink.click();
    await expect(page).toHaveURL(/\/search/);
  });

  test('should return entity results matching a query', async ({ page, cleanup, testSlug }) => {
    const entitySlug = testSlug('searchable-entity');
    await page.goto('/entities/new');
    await page.getByRole('textbox', { name: 'Slug' }).fill(entitySlug);
    await page.getByRole('textbox', { name: /summary.*english/i }).fill('Searchable entity for global search');
    await page.getByRole('button', { name: /create|submit/i }).click();
    await page.waitForURL(/\/entities\/[a-f0-9-]+/);
    const entityId = page.url().match(/\/entities\/([a-f0-9-]+)/)?.[1] ?? '';
    cleanup.track('entity', entityId);

    await page.goto('/search');
    await page.waitForLoadState('networkidle');

    const searchInput = page.getByRole('searchbox').or(page.getByPlaceholder(/search/i)).first();
    await expect(searchInput).toBeVisible({ timeout: 5000 });
    await searchInput.fill(entitySlug);

    await expect(page.locator(`text=${entitySlug}`).first()).toBeVisible({ timeout: 10000 });
  });

  test('should navigate to entity detail when result is clicked', async ({ page, cleanup, testSlug }) => {
    const entitySlug = testSlug('search-nav-entity');
    await page.goto('/entities/new');
    await page.getByRole('textbox', { name: 'Slug' }).fill(entitySlug);
    await page.getByRole('textbox', { name: /summary.*english/i }).fill('Search nav entity');
    await page.getByRole('button', { name: /create|submit/i }).click();
    await page.waitForURL(/\/entities\/[a-f0-9-]+/);
    const entityId = page.url().match(/\/entities\/([a-f0-9-]+)/)?.[1] ?? '';
    cleanup.track('entity', entityId);

    await page.goto('/search');
    await page.waitForLoadState('networkidle');

    const searchInput = page.getByRole('searchbox').or(page.getByPlaceholder(/search/i)).first();
    await expect(searchInput).toBeVisible({ timeout: 5000 });
    await searchInput.fill(entitySlug);

    const result = page.locator(`text=${entitySlug}`).first();
    await expect(result).toBeVisible({ timeout: 10000 });
    await result.click();
    await expect(page).toHaveURL(/\/entities\/[a-f0-9-]+/);
  });

  test('should return source results matching a query', async ({ page, cleanup, testLabel, testSlug }) => {
    const sourceTitle = testLabel('searchable-source');
    await page.goto('/sources/new');
    await page.waitForLoadState('domcontentloaded');
    await page.getByRole('textbox', { name: 'Title' }).fill(sourceTitle);
    await page.getByRole('textbox', { name: 'URL' }).fill(`https://example.com/${testSlug('url')}`);
    await page.getByRole('button', { name: /create|submit/i }).click();
    await page.waitForURL(/\/sources\/[a-f0-9-]+/);
    const sourceId = page.url().match(/\/sources\/([a-f0-9-]+)/)?.[1] ?? '';
    cleanup.track('source', sourceId);

    await page.goto('/search');
    await page.waitForLoadState('networkidle');

    // Target the main page search input (not the navbar autocomplete)
    const searchInput = page.getByLabel(/search entities|search.*sources|search.*relations/i);
    await expect(searchInput).toBeVisible({ timeout: 5000 });
    // Use the plain label suffix (no special chars) as the search query
    const searchQuery = 'searchable-source';
    await searchInput.fill(searchQuery);

    await expect(page.getByText(searchQuery).first()).toBeVisible({ timeout: 10000 });
  });

  test('should show autocomplete results from the nav search bar', async ({ page }) => {
    await page.goto('/entities');
    await expect(page.getByRole('heading', { name: 'Entities' })).toBeVisible();

    const searchInput = page.getByPlaceholder(/search/i).first();
    await expect(searchInput).toBeVisible({ timeout: 5000 });
    // Use 'hypha' to match the always-present 'HyphaGraph Inference Engine' system source
    await searchInput.fill('hypha');

    await expect(page.getByRole('listbox')).toBeVisible({ timeout: 5000 });
  });
});
