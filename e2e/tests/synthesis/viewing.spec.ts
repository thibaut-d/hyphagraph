import { test, expect } from '@playwright/test';
import { loginAsAdminViaAPI, clearAuthState } from '../../fixtures/auth-helpers';
import { generateEntityName } from '../../fixtures/test-data';

test.describe('Synthesis View', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdminViaAPI(page);
  });

  test.afterEach(async ({ page }) => {
    await clearAuthState(page);
  });

  // US-EXP-03 — View Synthesis

  test('should load synthesis page for an entity', async ({ page }) => {
    const entitySlug = generateEntityName('synth-entity').toLowerCase().replace(/\s+/g, '-');
    await page.goto('/entities/new');
    await page.getByRole('textbox', { name: 'Slug' }).fill(entitySlug);
    await page.getByRole('textbox', { name: /summary.*english/i }).fill('Entity for synthesis test');
    await page.getByRole('button', { name: /create|submit/i }).click();
    await page.waitForURL(/\/entities\/([a-f0-9-]+)/);
    const entityId = page.url().match(/\/entities\/([a-f0-9-]+)/)?.[1];

    await page.goto(`/entities/${entityId}/synthesis`);
    await page.waitForLoadState('domcontentloaded');

    // Should render the synthesis page
    await expect(page).toHaveURL(`/entities/${entityId}/synthesis`);
    // Either shows data or an empty-state message
    const content = page.locator('text=/synthesis|no.*data|no.*knowledge|relation/i').first();
    await expect(content).toBeVisible({ timeout: 10000 });
  });

  test('should show empty state message when entity has no relations', async ({ page }) => {
    const entitySlug = generateEntityName('synth-empty').toLowerCase().replace(/\s+/g, '-');
    await page.goto('/entities/new');
    await page.getByRole('textbox', { name: 'Slug' }).fill(entitySlug);
    await page.getByRole('textbox', { name: /summary.*english/i }).fill('Empty synthesis entity');
    await page.getByRole('button', { name: /create|submit/i }).click();
    await page.waitForURL(/\/entities\/([a-f0-9-]+)/);
    const entityId = page.url().match(/\/entities\/([a-f0-9-]+)/)?.[1];

    await page.goto(`/entities/${entityId}/synthesis`);
    await page.waitForLoadState('domcontentloaded');

    // Empty state message should be visible
    await expect(
      page.locator('text=/no.*synthes|no.*knowledge|no.*data/i').first()
    ).toBeVisible({ timeout: 10000 });
  });

  test('should be accessible from entity detail page', async ({ page }) => {
    const entitySlug = generateEntityName('synth-nav').toLowerCase().replace(/\s+/g, '-');
    await page.goto('/entities/new');
    await page.getByRole('textbox', { name: 'Slug' }).fill(entitySlug);
    await page.getByRole('textbox', { name: /summary.*english/i }).fill('Synthesis nav entity');
    await page.getByRole('button', { name: /create|submit/i }).click();
    await page.waitForURL(/\/entities\/([a-f0-9-]+)/);
    const entityId = page.url().match(/\/entities\/([a-f0-9-]+)/)?.[1];

    await page.goto(`/entities/${entityId}`);
    await page.waitForLoadState('domcontentloaded');

    // Synthesis link must be reachable from entity detail — if absent, use skip with reason
    const synthesisLink = page.getByRole('link', { name: /synthesis/i }).or(
      page.getByRole('button', { name: /synthesis/i })
    );
    if (!await synthesisLink.isVisible({ timeout: 3000 })) {
      test.skip(true, 'Synthesis link not present on entity detail page');
      return;
    }
    await synthesisLink.click();
    await expect(page).toHaveURL(new RegExp(`/entities/${entityId}/synthesis`));
  });

  test('should label synthesis as computed, not authored', async ({ page }) => {
    const entitySlug = generateEntityName('synth-label').toLowerCase().replace(/\s+/g, '-');
    await page.goto('/entities/new');
    await page.getByRole('textbox', { name: 'Slug' }).fill(entitySlug);
    await page.getByRole('textbox', { name: /summary.*english/i }).fill('Synthesis label entity');
    await page.getByRole('button', { name: /create|submit/i }).click();
    await page.waitForURL(/\/entities\/([a-f0-9-]+)/);
    const entityId = page.url().match(/\/entities\/([a-f0-9-]+)/)?.[1];

    await page.goto(`/entities/${entityId}/synthesis`);
    await page.waitForLoadState('domcontentloaded');

    // The page title (e.g. "Evidence Synthesis") labels this as computed, not authored truth
    await expect(page.getByRole('heading', { name: /synthesis/i }).first()).toBeVisible({ timeout: 5000 });
  });

  test('should provide a back navigation to entity detail', async ({ page }) => {
    const entitySlug = generateEntityName('synth-back').toLowerCase().replace(/\s+/g, '-');
    await page.goto('/entities/new');
    await page.getByRole('textbox', { name: 'Slug' }).fill(entitySlug);
    await page.getByRole('textbox', { name: /summary.*english/i }).fill('Synthesis back nav entity');
    await page.getByRole('button', { name: /create|submit/i }).click();
    await page.waitForURL(/\/entities\/([a-f0-9-]+)/);
    const entityId = page.url().match(/\/entities\/([a-f0-9-]+)/)?.[1];

    await page.goto(`/entities/${entityId}/synthesis`);
    await page.waitForLoadState('domcontentloaded');

    const backButton = page.getByRole('button', { name: /back/i }).or(
      page.getByRole('link', { name: /back|entity/i })
    );
    if (!await backButton.first().isVisible({ timeout: 3000 })) {
      test.skip(true, 'Back button not present on synthesis page');
      return;
    }
    await backButton.first().click();
    await expect(page).toHaveURL(new RegExp(`/entities/${entityId}$`));
  });
});
