import { test, expect } from '@playwright/test';
import { loginAsAdminViaAPI, clearAuthState } from '../../fixtures/auth-helpers';
import { generateEntityName, generateSourceName } from '../../fixtures/test-data';

test.describe('Batch Relation Creation', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdminViaAPI(page);
  });

  test.afterEach(async ({ page }) => {
    await clearAuthState(page);
  });

  // US-REL-05 — Batch Create Relations

  test('should load the batch relation creation page', async ({ page }) => {
    await page.goto('/relations/batch');
    await page.waitForLoadState('domcontentloaded');
    await expect(page.getByRole('heading', { name: /batch/i })).toBeVisible({ timeout: 10000 });
  });

  test('should show a shared source selector', async ({ page }) => {
    await page.goto('/relations/batch');
    await page.waitForLoadState('domcontentloaded');

    // Source selector must be present on the batch form
    await expect(page.getByLabel(/source/i).first()).toBeVisible({ timeout: 5000 });
  });

  test('should allow adding multiple relation rows', async ({ page }) => {
    await page.goto('/relations/batch');
    await page.waitForLoadState('domcontentloaded');

    // Add row button must be present
    const addRowButton = page.getByRole('button', { name: /add relation|add row|\+/i }).first();
    await expect(addRowButton).toBeVisible({ timeout: 5000 });
    await addRowButton.click();
    await addRowButton.click();

    // Should have at least one row card visible
    const cards = page.locator('[data-testid="relation-row"], .MuiCard-root').filter({
      hasText: /kind|confidence/i,
    });
    await expect(cards.first()).toBeVisible({ timeout: 3000 });
    const count = await cards.count();
    expect(count).toBeGreaterThanOrEqual(1);
  });

  test('should show per-row result after batch submit', async ({ page }) => {
    // M9 fix: source creation uses only Title + URL (summary is in a collapsed Advanced section)
    const sourceTitle = generateSourceName('batch-rel-source');
    await page.goto('/sources/new');
    await page.waitForLoadState('domcontentloaded');
    await page.getByRole('textbox', { name: 'Title' }).fill(sourceTitle);
    await page.getByRole('textbox', { name: 'URL' }).fill('https://example.com/batch-rel');
    await page.getByRole('button', { name: /create|submit/i }).click();
    await page.waitForURL(/\/sources\/[a-f0-9-]+/);

    const slug1 = generateEntityName('batch-e1').toLowerCase().replace(/\s+/g, '-');
    await page.goto('/entities/new');
    await page.waitForLoadState('domcontentloaded');
    await page.getByRole('textbox', { name: 'Slug' }).fill(slug1);
    await page.getByRole('textbox', { name: /summary.*english/i }).fill('Entity 1 for batch');
    await page.getByRole('button', { name: /create|submit/i }).click();
    await page.waitForURL(/\/entities\/[a-f0-9-]+/);

    const slug2 = generateEntityName('batch-e2').toLowerCase().replace(/\s+/g, '-');
    await page.goto('/entities/new');
    await page.waitForLoadState('domcontentloaded');
    await page.getByRole('textbox', { name: 'Slug' }).fill(slug2);
    await page.getByRole('textbox', { name: /summary.*english/i }).fill('Entity 2 for batch');
    await page.getByRole('button', { name: /create|submit/i }).click();
    await page.waitForURL(/\/entities\/[a-f0-9-]+/);

    await page.goto('/relations/batch');
    await page.waitForLoadState('domcontentloaded');

    const sourceSelect = page.getByLabel(/source/i).first();
    await expect(sourceSelect).toBeVisible({ timeout: 5000 });
    await sourceSelect.click();

    const firstOption = page.getByRole('option').first();
    await expect(firstOption).toBeVisible({ timeout: 3000 });
    await firstOption.click();

    const kindField = page.getByLabel(/kind/i).first();
    if (await kindField.isVisible({ timeout: 2000 })) {
      await kindField.fill('test-batch-kind');
    }

    const submitButton = page.getByRole('button', { name: /submit|create all/i });
    await expect(submitButton).toBeVisible({ timeout: 3000 });
    await submitButton.click();
    await page.waitForTimeout(2000);

    // Per-row result (success chip or error) must appear
    await expect(
      page.locator('text=/success|created|error|failed/i').first()
    ).toBeVisible({ timeout: 5000 });
  });
});
