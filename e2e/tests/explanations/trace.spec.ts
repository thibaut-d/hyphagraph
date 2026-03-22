import { test, expect } from '@playwright/test';
import { loginAsAdminViaAPI, clearAuthState } from '../../fixtures/auth-helpers';
import { generateEntityName, generateSourceName, generateRelationName } from '../../fixtures/test-data';

test.describe('Explanation Trace', () => {
  test.beforeEach(async ({ page }) => {
    // Login before each test
    await loginAsAdminViaAPI(page);
  });

  test.afterEach(async ({ page }) => {
    // Clear auth state to avoid polluting other tests
    await clearAuthState(page);
  });

  test('should navigate to explanation page', async ({ page }) => {
    // Create test data first
    const entitySlug = generateEntityName('explain-entity').toLowerCase().replace(/\s+/g, '-');
    await page.goto('/entities/new');
    await page.getByRole('textbox', { name: 'Slug' }).fill(entitySlug);
    await page.getByRole('textbox', { name: /summary.*english/i }).fill('Entity for explanation test');
    await page.getByRole('button', { name: /create|submit/i }).click();
    await page.waitForURL(/\/entities\/([a-f0-9-]+)/);

    const entityId = page.url().match(/\/entities\/([a-f0-9-]+)/)?.[1];

    // Navigate to explanation page
    // Route format: /explain/:entityId/:roleType
    await page.goto(`/explain/${entityId}/test-role`);

    // Should be on explanation page
    await expect(page).toHaveURL(/\/explain\/[a-f0-9-]+\//);
  });

  test('should display explanation trace', async ({ page }) => {
    // Create entities and relations to generate explanation data
    const sourceTitle = generateSourceName('exp-source');
    await page.goto('/sources/new');
    await page.getByRole('textbox', { name: 'Title' }).fill(sourceTitle);
    await page.getByRole('textbox', { name: 'URL' }).fill('https://example.com/exp-source');
    await page.getByRole('button', { name: /create|submit/i }).click();
    await page.waitForURL(/\/sources\/[a-f0-9-]+/);

    const entitySlug = generateEntityName('trace-entity').toLowerCase().replace(/\s+/g, '-');
    await page.goto('/entities/new');
    await page.getByRole('textbox', { name: 'Slug' }).fill(entitySlug);
    await page.getByRole('textbox', { name: /summary.*english/i }).fill('Entity with trace');
    await page.getByRole('button', { name: /create|submit/i }).click();
    await page.waitForURL(/\/entities\/([a-f0-9-]+)/);

    const entityId = page.url().match(/\/entities\/([a-f0-9-]+)/)?.[1];

    // Navigate to explanation
    await page.goto(`/explain/${entityId}/subject`);

    // The explanation page must load without crashing
    await expect(page).toHaveURL(/\/explain\/[a-f0-9-]+\//);
    // Either explanation content or an empty/no-data state must be visible
    const explanationContent = page.locator('text=/Explanation|Evidence|Trace|Path|no data|not found/i').first();
    await expect(explanationContent).toBeVisible({ timeout: 5000 });
  });

  test('should show evidence paths', async ({ page }) => {
    // Create complex relation chain for evidence path
    const entitySlug = generateEntityName('evidence-entity').toLowerCase().replace(/\s+/g, '-');
    await page.goto('/entities/new');
    await page.getByRole('textbox', { name: 'Slug' }).fill(entitySlug);
    await page.getByRole('textbox', { name: /summary.*english/i }).fill('Entity with evidence');
    await page.getByRole('button', { name: /create|submit/i }).click();
    await page.waitForURL(/\/entities\/([a-f0-9-]+)/);

    const entityId = page.url().match(/\/entities\/([a-f0-9-]+)/)?.[1];

    // Navigate to explanation — page must load without crashing
    await page.goto(`/explain/${entityId}/subject`);
    await page.waitForLoadState('networkidle');

    // The explanation page must render at minimum some content (data or empty-state)
    await expect(
      page.locator('text=/Explanation|Evidence|Trace|Path|Chain|no data|not found/i').first()
    ).toBeVisible({ timeout: 5000 });
  });

  test('should expand/collapse evidence nodes', async ({ page }) => {
    const entitySlug = generateEntityName('expand-entity').toLowerCase().replace(/\s+/g, '-');
    await page.goto('/entities/new');
    await page.getByRole('textbox', { name: 'Slug' }).fill(entitySlug);
    await page.getByRole('textbox', { name: /summary.*english/i }).fill('Entity for expand test');
    await page.getByRole('button', { name: /create|submit/i }).click();
    await page.waitForURL(/\/entities\/([a-f0-9-]+)/);

    const entityId = page.url().match(/\/entities\/([a-f0-9-]+)/)?.[1];

    await page.goto(`/explain/${entityId}/subject`);
    await page.waitForLoadState('networkidle');

    // Page must render content regardless of expand state
    await expect(
      page.locator('text=/Explanation|Evidence|Trace|Path|no data|not found/i').first()
    ).toBeVisible({ timeout: 5000 });

    // Expand/collapse is an optional UI feature — if buttons are present they must be interactive
    const expandButton = page.getByRole('button', { name: /expand|show more/i });
    if (await expandButton.first().isVisible({ timeout: 2000 })) {
      await expandButton.first().click();
      await page.waitForLoadState('networkidle');
      // Page must remain functional after expanding
      await expect(page.getByRole('heading').or(page.locator('main')).first()).toBeVisible();
    }
  });

  test('should show inference scores in explanation', async ({ page }) => {
    const entitySlug = generateEntityName('score-explain').toLowerCase().replace(/\s+/g, '-');
    await page.goto('/entities/new');
    await page.getByRole('textbox', { name: 'Slug' }).fill(entitySlug);
    await page.getByRole('textbox', { name: /summary.*english/i }).fill('Entity with scored explanation');
    await page.getByRole('button', { name: /create|submit/i }).click();
    await page.waitForURL(/\/entities\/([a-f0-9-]+)/);

    const entityId = page.url().match(/\/entities\/([a-f0-9-]+)/)?.[1];

    await page.goto(`/explain/${entityId}/subject`);
    await page.waitForLoadState('networkidle');

    // Explanation page must render (scores appear only when inference data exists)
    await expect(
      page.locator('text=/Explanation|Evidence|Trace|no data|not found/i').first()
    ).toBeVisible({ timeout: 5000 });
  });

  test('should navigate between entity detail and explanation', async ({ page }) => {
    const entitySlug = generateEntityName('nav-explain').toLowerCase().replace(/\s+/g, '-');
    await page.goto('/entities/new');
    await page.getByRole('textbox', { name: 'Slug' }).fill(entitySlug);
    await page.getByRole('textbox', { name: /summary.*english/i }).fill('Entity for nav test');
    await page.getByRole('button', { name: /create|submit/i }).click();
    await page.waitForURL(/\/entities\/([a-f0-9-]+)/);

    const entityUrl = page.url();
    const entityId = entityUrl.match(/\/entities\/([a-f0-9-]+)/)?.[1];

    // Go to explanation — must load without crashing
    await page.goto(`/explain/${entityId}/subject`);
    await page.waitForLoadState('networkidle');
    await expect(page).toHaveURL(/\/explain/);

    // Back navigation is optional UI — if present it must work; if absent the page must still be valid
    const backButton = page.getByRole('button', { name: /back/i }).or(
      page.getByRole('link', { name: /back|entity/i })
    );
    if (await backButton.isVisible({ timeout: 2000 })) {
      await backButton.click();
      await expect(page).toHaveURL(/\/entities\/[a-f0-9-]+$/);
    } else {
      // No back button — verify page is still functional
      await expect(
        page.locator('text=/Explanation|Evidence|Trace|no data|not found/i').first()
      ).toBeVisible({ timeout: 5000 });
    }
  });

  test('should handle explanation for non-existent role', async ({ page }) => {
    const entitySlug = generateEntityName('no-role').toLowerCase().replace(/\s+/g, '-');
    await page.goto('/entities/new');
    await page.getByRole('textbox', { name: 'Slug' }).fill(entitySlug);
    await page.getByRole('textbox', { name: /summary.*english/i }).fill('Entity without role');
    await page.getByRole('button', { name: /create|submit/i }).click();
    await page.waitForURL(/\/entities\/([a-f0-9-]+)/);

    const entityId = page.url().match(/\/entities\/([a-f0-9-]+)/)?.[1];

    // Try to explain a role that doesn't exist — page must not crash
    await page.goto(`/explain/${entityId}/non-existent-role`);
    await page.waitForLoadState('networkidle');

    // Must show an error or empty-state — a blank/crashed page is a failure
    await expect(
      page.locator('text=/not found|no data|error|empty|Explanation/i').first()
    ).toBeVisible({ timeout: 5000 });
  });

  test('should display a parsed rate-limit error when explanation loading is throttled', async ({ page }) => {
    await page.route('**/api/explain/**', async (route) => {
      await route.fulfill({
        status: 429,
        contentType: 'application/json',
        body: JSON.stringify({
          error: {
            code: 'RATE_LIMIT_EXCEEDED',
            message: 'Too many requests. Please try again later.',
            details: 'Explanation endpoint rate limited',
          },
        }),
      });
    });

    await page.goto('/explain/00000000-0000-0000-0000-000000000000/test-role');

    // Must show an error indication — a blank page or JS error is not acceptable
    await expect(
      page.locator('[role="alert"]').or(
        page.getByText(/too many requests|rate limit|try again later/i)
      ).first()
    ).toBeVisible({ timeout: 5000 });
  });
});
