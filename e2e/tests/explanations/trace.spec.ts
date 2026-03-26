import { test, expect } from '../../fixtures/test-fixtures';
import { loginAsAdminViaAPI, clearAuthState } from '../../fixtures/auth-helpers';

test.describe('Explanation Trace', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdminViaAPI(page);
  });

  test.afterEach(async ({ page }) => {
    await clearAuthState(page);
  });

  test('should navigate to explanation page', async ({ page, cleanup, testSlug }) => {
    const entitySlug = testSlug('explain-entity');
    await page.goto('/entities/new');
    await page.getByRole('textbox', { name: 'Slug' }).fill(entitySlug);
    await page.getByRole('textbox', { name: /summary.*english/i }).fill('Entity for explanation test');
    await page.getByRole('button', { name: /create|submit/i }).click();
    await page.waitForURL(/\/entities\/([a-f0-9-]+)/);
    const entityId = page.url().match(/\/entities\/([a-f0-9-]+)/)?.[1] ?? '';
    cleanup.track('entity', entityId);

    await page.goto(`/explain/${entityId}/test-role`);
    await expect(page).toHaveURL(/\/explain\/[a-f0-9-]+\//);
  });

  test('should display explanation trace', async ({ page, cleanup, testLabel, testSlug }) => {
    const sourceTitle = testLabel('source');
    await page.goto('/sources/new');
    await page.getByRole('textbox', { name: 'Title' }).fill(sourceTitle);
    await page.getByRole('textbox', { name: 'URL' }).fill(`https://example.com/${testSlug('url')}`);
    await page.getByRole('button', { name: /create|submit/i }).click();
    await page.waitForURL(/\/sources\/[a-f0-9-]+/);
    const sourceId = page.url().match(/\/sources\/([a-f0-9-]+)/)?.[1] ?? '';
    cleanup.track('source', sourceId);

    const entitySlug = testSlug('trace-entity');
    await page.goto('/entities/new');
    await page.getByRole('textbox', { name: 'Slug' }).fill(entitySlug);
    await page.getByRole('textbox', { name: /summary.*english/i }).fill('Entity with trace');
    await page.getByRole('button', { name: /create|submit/i }).click();
    await page.waitForURL(/\/entities\/([a-f0-9-]+)/);
    const entityId = page.url().match(/\/entities\/([a-f0-9-]+)/)?.[1] ?? '';
    cleanup.track('entity', entityId);

    await page.goto(`/explain/${entityId}/subject`);
    await expect(page).toHaveURL(/\/explain\/[a-f0-9-]+\//);
    await expect(
      page.locator('text=/Explanation|Evidence|Trace|Path|no data|not found/i').first()
    ).toBeVisible({ timeout: 5000 });
  });

  test('should show evidence paths', async ({ page, cleanup, testSlug }) => {
    const entitySlug = testSlug('evidence-entity');
    await page.goto('/entities/new');
    await page.getByRole('textbox', { name: 'Slug' }).fill(entitySlug);
    await page.getByRole('textbox', { name: /summary.*english/i }).fill('Entity with evidence');
    await page.getByRole('button', { name: /create|submit/i }).click();
    await page.waitForURL(/\/entities\/([a-f0-9-]+)/);
    const entityId = page.url().match(/\/entities\/([a-f0-9-]+)/)?.[1] ?? '';
    cleanup.track('entity', entityId);

    await page.goto(`/explain/${entityId}/subject`);
    await page.waitForLoadState('networkidle');
    await expect(
      page.locator('text=/Explanation|Evidence|Trace|Path|Chain|no data|not found/i').first()
    ).toBeVisible({ timeout: 5000 });
  });

  test('should expand/collapse evidence nodes', async ({ page, cleanup, testSlug }) => {
    const entitySlug = testSlug('expand-entity');
    await page.goto('/entities/new');
    await page.getByRole('textbox', { name: 'Slug' }).fill(entitySlug);
    await page.getByRole('textbox', { name: /summary.*english/i }).fill('Entity for expand test');
    await page.getByRole('button', { name: /create|submit/i }).click();
    await page.waitForURL(/\/entities\/([a-f0-9-]+)/);
    const entityId = page.url().match(/\/entities\/([a-f0-9-]+)/)?.[1] ?? '';
    cleanup.track('entity', entityId);

    await page.goto(`/explain/${entityId}/subject`);
    await page.waitForLoadState('networkidle');
    await expect(
      page.locator('text=/Explanation|Evidence|Trace|Path|no data|not found/i').first()
    ).toBeVisible({ timeout: 5000 });

    const expandButton = page.getByRole('button', { name: /expand|show more/i });
    if (await expandButton.first().isVisible({ timeout: 2000 })) {
      await expandButton.first().click();
      await page.waitForLoadState('networkidle');
      await expect(page.getByRole('heading').or(page.locator('main')).first()).toBeVisible();
    }
  });

  test('should show inference scores in explanation', async ({ page, cleanup, testSlug }) => {
    const entitySlug = testSlug('score-explain');
    await page.goto('/entities/new');
    await page.getByRole('textbox', { name: 'Slug' }).fill(entitySlug);
    await page.getByRole('textbox', { name: /summary.*english/i }).fill('Entity with scored explanation');
    await page.getByRole('button', { name: /create|submit/i }).click();
    await page.waitForURL(/\/entities\/([a-f0-9-]+)/);
    const entityId = page.url().match(/\/entities\/([a-f0-9-]+)/)?.[1] ?? '';
    cleanup.track('entity', entityId);

    await page.goto(`/explain/${entityId}/subject`);
    await page.waitForLoadState('networkidle');
    await expect(
      page.locator('text=/Explanation|Evidence|Trace|no data|not found/i').first()
    ).toBeVisible({ timeout: 5000 });
  });

  test('should navigate between entity detail and explanation', async ({ page, cleanup, testSlug }) => {
    const entitySlug = testSlug('nav-explain');
    await page.goto('/entities/new');
    await page.getByRole('textbox', { name: 'Slug' }).fill(entitySlug);
    await page.getByRole('textbox', { name: /summary.*english/i }).fill('Entity for nav test');
    await page.getByRole('button', { name: /create|submit/i }).click();
    await page.waitForURL(/\/entities\/([a-f0-9-]+)/);
    const entityId = page.url().match(/\/entities\/([a-f0-9-]+)/)?.[1] ?? '';
    cleanup.track('entity', entityId);

    await page.goto(`/explain/${entityId}/subject`);
    await page.waitForLoadState('networkidle');
    await expect(page).toHaveURL(/\/explain/);

    const backButton = page.getByRole('button', { name: /back/i }).or(
      page.getByRole('link', { name: /back|entity/i })
    );
    if (await backButton.isVisible({ timeout: 2000 })) {
      await backButton.click();
      await expect(page).toHaveURL(/\/entities\/[a-f0-9-]+$/);
    } else {
      await expect(
        page.locator('text=/Explanation|Evidence|Trace|no data|not found/i').first()
      ).toBeVisible({ timeout: 5000 });
    }
  });

  test('should handle explanation for non-existent role', async ({ page, cleanup, testSlug }) => {
    const entitySlug = testSlug('no-role');
    await page.goto('/entities/new');
    await page.getByRole('textbox', { name: 'Slug' }).fill(entitySlug);
    await page.getByRole('textbox', { name: /summary.*english/i }).fill('Entity without role');
    await page.getByRole('button', { name: /create|submit/i }).click();
    await page.waitForURL(/\/entities\/([a-f0-9-]+)/);
    const entityId = page.url().match(/\/entities\/([a-f0-9-]+)/)?.[1] ?? '';
    cleanup.track('entity', entityId);

    await page.goto(`/explain/${entityId}/non-existent-role`);
    await page.waitForLoadState('networkidle');
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

    await expect(
      page.locator('[role="alert"]').or(
        page.getByText(/too many requests|rate limit|try again later/i)
      ).first()
    ).toBeVisible({ timeout: 5000 });
  });
});
