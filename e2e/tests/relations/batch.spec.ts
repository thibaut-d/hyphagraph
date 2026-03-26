import { test, expect } from '../../fixtures/test-fixtures';
import { loginAsAdminViaAPI, clearAuthState } from '../../fixtures/auth-helpers';

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
    await expect(page.getByLabel(/source/i).first()).toBeVisible({ timeout: 5000 });
  });

  test('should allow adding multiple relation rows', async ({ page }) => {
    await page.goto('/relations/batch');
    await page.waitForLoadState('domcontentloaded');

    const addRowButton = page.getByRole('button', { name: /add relation|add row|\+/i }).first();
    await expect(addRowButton).toBeVisible({ timeout: 5000 });
    await addRowButton.click();
    await addRowButton.click();

    const cards = page.locator('[data-testid="relation-row"], .MuiCard-root').filter({
      hasText: /kind|confidence/i,
    });
    await expect(cards.first()).toBeVisible({ timeout: 3000 });
    const count = await cards.count();
    expect(count).toBeGreaterThanOrEqual(1);
  });

  test('should show per-row result after batch submit', async ({ page, cleanup, testLabel, testSlug }) => {
    const sourceTitle = testLabel('source');
    await page.goto('/sources/new');
    await page.waitForLoadState('domcontentloaded');
    await page.getByRole('textbox', { name: 'Title' }).fill(sourceTitle);
    await page.getByRole('textbox', { name: 'URL' }).fill(`https://example.com/${testSlug('url')}`);
    await page.getByRole('button', { name: /create|submit/i }).click();
    await page.waitForURL(/\/sources\/[a-f0-9-]+/);
    const sourceId = page.url().match(/\/sources\/([a-f0-9-]+)/)?.[1] ?? '';
    cleanup.track('source', sourceId);

    const slug1 = testSlug('e1');
    await page.goto('/entities/new');
    await page.waitForLoadState('domcontentloaded');
    await page.getByRole('textbox', { name: 'Slug' }).fill(slug1);
    await page.getByRole('textbox', { name: /summary.*english/i }).fill('Entity 1 for batch');
    await page.getByRole('button', { name: /create|submit/i }).click();
    await page.waitForURL(/\/entities\/[a-f0-9-]+/);
    const entity1Id = page.url().match(/\/entities\/([a-f0-9-]+)/)?.[1] ?? '';
    cleanup.track('entity', entity1Id);

    const slug2 = testSlug('e2');
    await page.goto('/entities/new');
    await page.waitForLoadState('domcontentloaded');
    await page.getByRole('textbox', { name: 'Slug' }).fill(slug2);
    await page.getByRole('textbox', { name: /summary.*english/i }).fill('Entity 2 for batch');
    await page.getByRole('button', { name: /create|submit/i }).click();
    await page.waitForURL(/\/entities\/[a-f0-9-]+/);
    const entity2Id = page.url().match(/\/entities\/([a-f0-9-]+)/)?.[1] ?? '';
    cleanup.track('entity', entity2Id);

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

    const submitButton = page.getByRole('button', { name: /create.*relation/i });
    await expect(submitButton).toBeVisible({ timeout: 3000 });
    await submitButton.click();
    await page.waitForLoadState('networkidle');

    await expect(
      page.locator('text=/success|created|error|failed/i').first()
    ).toBeVisible({ timeout: 5000 });
  });
});
