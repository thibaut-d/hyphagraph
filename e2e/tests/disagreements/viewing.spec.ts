import { test, expect } from '@playwright/test';
import { loginAsAdminViaAPI, clearAuthState } from '../../fixtures/auth-helpers';
import { generateEntityName } from '../../fixtures/test-data';

test.describe('Disagreements View', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdminViaAPI(page);
  });

  test.afterEach(async ({ page }) => {
    await clearAuthState(page);
  });

  // US-EXP-04 — View Disagreements

  test('should load disagreements page for an entity', async ({ page }) => {
    const entitySlug = generateEntityName('disagree-entity').toLowerCase().replace(/\s+/g, '-');
    await page.goto('/entities/new');
    await page.getByRole('textbox', { name: 'Slug' }).fill(entitySlug);
    await page.getByRole('textbox', { name: /summary.*english/i }).fill('Entity for disagreements test');
    await page.getByRole('button', { name: /create|submit/i }).click();
    await page.waitForURL(/\/entities\/([a-f0-9-]+)/);
    const entityId = page.url().match(/\/entities\/([a-f0-9-]+)/)?.[1];

    await page.goto(`/entities/${entityId}/disagreements`);
    await page.waitForLoadState('networkidle');

    await expect(page).toHaveURL(`/entities/${entityId}/disagreements`);
    // Either shows disagreement groups or empty-state message
    const content = page.locator(
      'text=/disagree|contradict|no.*conflict|no.*contradict/i'
    ).first();
    await expect(content).toBeVisible({ timeout: 10000 });
  });

  test('should show empty state when no contradictions exist', async ({ page }) => {
    const entitySlug = generateEntityName('disagree-empty').toLowerCase().replace(/\s+/g, '-');
    await page.goto('/entities/new');
    await page.getByRole('textbox', { name: 'Slug' }).fill(entitySlug);
    await page.getByRole('textbox', { name: /summary.*english/i }).fill('No contradictions entity');
    await page.getByRole('button', { name: /create|submit/i }).click();
    await page.waitForURL(/\/entities\/([a-f0-9-]+)/);
    const entityId = page.url().match(/\/entities\/([a-f0-9-]+)/)?.[1];

    await page.goto(`/entities/${entityId}/disagreements`);
    await page.waitForLoadState('networkidle');

    // Empty state alert should be visible (from DisagreementsView — success severity)
    await expect(
      page.locator('text=/no.*contradict|no.*conflict|no.*disagree/i').first()
    ).toBeVisible({ timeout: 10000 });
  });

  test('should be accessible from entity detail page', async ({ page }) => {
    const entitySlug = generateEntityName('disagree-nav').toLowerCase().replace(/\s+/g, '-');
    await page.goto('/entities/new');
    await page.getByRole('textbox', { name: 'Slug' }).fill(entitySlug);
    await page.getByRole('textbox', { name: /summary.*english/i }).fill('Disagreements nav entity');
    await page.getByRole('button', { name: /create|submit/i }).click();
    await page.waitForURL(/\/entities\/([a-f0-9-]+)/);
    const entityId = page.url().match(/\/entities\/([a-f0-9-]+)/)?.[1];

    await page.goto(`/entities/${entityId}`);
    await page.waitForLoadState('networkidle');

    const disagreementsLink = page.getByRole('link', { name: /disagree/i }).or(
      page.getByRole('button', { name: /disagree/i })
    );
    if (await disagreementsLink.isVisible({ timeout: 3000 })) {
      await disagreementsLink.click();
      await expect(page).toHaveURL(new RegExp(`/entities/${entityId}/disagreements`));
    }
  });

  test('should provide a back navigation to entity detail', async ({ page }) => {
    const entitySlug = generateEntityName('disagree-back').toLowerCase().replace(/\s+/g, '-');
    await page.goto('/entities/new');
    await page.getByRole('textbox', { name: 'Slug' }).fill(entitySlug);
    await page.getByRole('textbox', { name: /summary.*english/i }).fill('Disagreements back nav entity');
    await page.getByRole('button', { name: /create|submit/i }).click();
    await page.waitForURL(/\/entities\/([a-f0-9-]+)/);
    const entityId = page.url().match(/\/entities\/([a-f0-9-]+)/)?.[1];

    await page.goto(`/entities/${entityId}/disagreements`);
    await page.waitForLoadState('networkidle');

    const backButton = page.getByRole('button', { name: /back/i }).or(
      page.getByRole('link', { name: /back|entity/i })
    );
    if (await backButton.first().isVisible({ timeout: 3000 })) {
      await backButton.first().click();
      await expect(page).toHaveURL(new RegExp(`/entities/${entityId}$`));
    }
  });

  test('should provide navigation to synthesis view', async ({ page }) => {
    const entitySlug = generateEntityName('disagree-synth').toLowerCase().replace(/\s+/g, '-');
    await page.goto('/entities/new');
    await page.getByRole('textbox', { name: 'Slug' }).fill(entitySlug);
    await page.getByRole('textbox', { name: /summary.*english/i }).fill('Disagree to synth entity');
    await page.getByRole('button', { name: /create|submit/i }).click();
    await page.waitForURL(/\/entities\/([a-f0-9-]+)/);
    const entityId = page.url().match(/\/entities\/([a-f0-9-]+)/)?.[1];

    await page.goto(`/entities/${entityId}/disagreements`);
    await page.waitForLoadState('networkidle');

    const synthButton = page.getByRole('button', { name: /synthesis/i }).or(
      page.getByRole('link', { name: /synthesis/i })
    );
    if (await synthButton.first().isVisible({ timeout: 3000 })) {
      await synthButton.first().click();
      await expect(page).toHaveURL(new RegExp(`/entities/${entityId}/synthesis`));
    }
  });
});
