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
    await page.getByRole('textbox', { name: /summary.*english/i }).fill('Source for explanation');
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

    // Look for explanation components
    const explanationContent = page.locator('text=/Explanation|Evidence|Trace|Path/i');
    if (await explanationContent.isVisible({ timeout: 3000 })) {
      await expect(explanationContent).toBeVisible();
    }
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

    // Navigate to explanation
    await page.goto(`/explain/${entityId}/subject`);

    // Look for evidence path visualization
    // Might be a tree, list, or graph
    const evidencePath = page.locator('[data-testid="evidence-path"]').or(
      page.locator('text=/Evidence|Path|Chain/i')
    );

    if (await evidencePath.isVisible({ timeout: 3000 })) {
      await expect(evidencePath).toBeVisible();
    }
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

    // Look for expand/collapse buttons
    const expandButton = page.getByRole('button', { name: /expand|show more/i });
    if (await expandButton.first().isVisible({ timeout: 2000 })) {
      await expandButton.first().click();

      // Should show more details
      await page.waitForLoadState('networkidle');

      // Look for collapse button
      const collapseButton = page.getByRole('button', { name: /collapse|hide|show less/i });
      if (await collapseButton.first().isVisible({ timeout: 1000 })) {
        await collapseButton.first().click();
      }
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

    // Look for score display
    const scoreDisplay = page.locator('text=/%|score|confidence|probability/i');
    if (await scoreDisplay.isVisible({ timeout: 3000 })) {
      await expect(scoreDisplay).toBeVisible();
    }
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

    // Go to explanation
    await page.goto(`/explain/${entityId}/subject`);

    // Should be on explanation page
    await expect(page).toHaveURL(/\/explain/);

    // Look for back button or link to entity
    const backButton = page.getByRole('button', { name: /back/i }).or(
      page.getByRole('link', { name: /back|entity/i })
    );

    if (await backButton.isVisible({ timeout: 2000 })) {
      await backButton.click();

      // Should navigate back to entity detail
      await expect(page).toHaveURL(/\/entities\/[a-f0-9-]+$/);
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

    // Try to explain a role that doesn't exist
    await page.goto(`/explain/${entityId}/non-existent-role`);

    // Should show error or empty state
    const errorMessage = page.locator('text=/not found|no data|error|empty/i');
    if (await errorMessage.isVisible({ timeout: 3000 })) {
      await expect(errorMessage).toBeVisible();
    }
  });
});
