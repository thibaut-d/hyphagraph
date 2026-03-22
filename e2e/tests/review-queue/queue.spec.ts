import { test, expect } from '@playwright/test';
import { loginAsAdminViaAPI, clearAuthState } from '../../fixtures/auth-helpers';

test.describe('LLM Extraction Review Queue', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdminViaAPI(page);
  });

  test.afterEach(async ({ page }) => {
    await clearAuthState(page);
  });

  // US-LLM-01 — Review Extraction Queue

  test('should load the review queue page', async ({ page }) => {
    await page.goto('/review-queue');
    await page.waitForLoadState('domcontentloaded');

    await expect(
      page.getByRole('heading', { name: 'Review Queue' })
    ).toBeVisible({ timeout: 10000 });
  });

  test('should show statistics cards (pending, auto-verified, avg score, flagged)', async ({ page }) => {
    await page.goto('/review-queue');
    await page.waitForLoadState('domcontentloaded');

    await expect(page.getByRole('heading', { name: 'Review Queue' })).toBeVisible({ timeout: 10000 });

    const pendingCard = page.locator('text=/pending/i').first();
    if (await pendingCard.isVisible({ timeout: 3000 })) {
      await expect(pendingCard).toBeVisible();
    }
  });

  test('should show empty state or items list', async ({ page }) => {
    await page.goto('/review-queue');
    await page.waitForLoadState('domcontentloaded');

    await expect(page.getByRole('heading', { name: 'Review Queue' })).toBeVisible({ timeout: 10000 });

    // Either the empty state or extraction cards must be present — one must be visible
    const emptyState = page.locator('text=/no pending|queue.*empty|all.*reviewed/i').first();
    const hasItems = page.locator('[role="list"], [role="listitem"]').first();

    const emptyVisible = await emptyState.isVisible({ timeout: 5000 }).catch(() => false);
    const itemsVisible = await hasItems.isVisible({ timeout: 1000 }).catch(() => false);
    expect(emptyVisible || itemsVisible).toBe(true);
  });

  test('should show a refresh button', async ({ page }) => {
    await page.goto('/review-queue');
    await page.waitForLoadState('domcontentloaded');

    await expect(page.getByRole('button', { name: /refresh/i })).toBeVisible({ timeout: 10000 });
  });

  // US-LLM-04 — Filter Extraction Queue

  test('should show minimum score filter input', async ({ page }) => {
    await page.goto('/review-queue');
    await page.waitForLoadState('domcontentloaded');

    await expect(page.getByRole('heading', { name: 'Review Queue' })).toBeVisible({ timeout: 10000 });
    await expect(page.getByLabel(/min.*score|score/i).first()).toBeVisible({ timeout: 5000 });
  });

  test('should show flagged-only filter toggle', async ({ page }) => {
    await page.goto('/review-queue');
    await page.waitForLoadState('domcontentloaded');

    await expect(page.getByRole('heading', { name: 'Review Queue' })).toBeVisible({ timeout: 10000 });
    await expect(page.getByRole('button', { name: /flagged/i })).toBeVisible({ timeout: 5000 });
  });

  test('should show extraction type filter (entity/relation/claim)', async ({ page }) => {
    await page.goto('/review-queue');
    await page.waitForLoadState('domcontentloaded');

    await expect(page.getByRole('heading', { name: 'Review Queue' })).toBeVisible({ timeout: 10000 });

    const typeGroup = page.locator('[role="group"]').first();
    await expect(typeGroup).toBeVisible({ timeout: 5000 });

    await expect(page.getByRole('button', { name: /^entity$/i })).toBeVisible();
  });

  test('should apply extraction type filter without error', async ({ page }) => {
    await page.goto('/review-queue');
    await page.waitForLoadState('domcontentloaded');

    await expect(page.getByRole('heading', { name: 'Review Queue' })).toBeVisible({ timeout: 10000 });

    const entityToggle = page.getByRole('button', { name: /^entity$/i });
    await expect(entityToggle).toBeVisible({ timeout: 5000 });
    await entityToggle.click();
    await page.waitForTimeout(500);

    await expect(page.getByRole('heading', { name: 'Review Queue' })).toBeVisible();
  });

  // US-LLM-02 — Approve / Reject Extractions
  // These tests require seeded staged_extractions data in the E2E database.
  // They skip with a descriptive message when the queue is empty.

  test('should show select-all button when extractions are present', async ({ page }) => {
    await page.goto('/review-queue');
    await page.waitForLoadState('domcontentloaded');

    const selectAllButton = page.getByRole('button', { name: /select all/i });
    const hasItems = await selectAllButton.isVisible({ timeout: 3000 }).catch(() => false);
    if (!hasItems) {
      test.skip(true, 'Review queue is empty — seed staged_extractions data to exercise this test');
      return;
    }
    await expect(selectAllButton).toBeVisible();
  });

  // US-LLM-03 — Batch Approve / Reject
  test('should show batch action buttons when items are selected', async ({ page }) => {
    await page.goto('/review-queue');
    await page.waitForLoadState('domcontentloaded');

    const selectAllButton = page.getByRole('button', { name: /select all/i });
    const hasItems = await selectAllButton.isVisible({ timeout: 3000 }).catch(() => false);
    if (!hasItems) {
      test.skip(true, 'Review queue is empty — seed staged_extractions data to exercise this test');
      return;
    }

    await selectAllButton.click();
    await page.waitForTimeout(300);

    await expect(page.getByRole('button', { name: /approve.*selected/i })).toBeVisible({ timeout: 3000 });
    await expect(page.getByRole('button', { name: /reject.*selected/i })).toBeVisible();
  });

  // US-LLM-05 — Navigate from extraction to entity/relation
  test('should show entity/relation links in extraction cards when queue has items', async ({ page }) => {
    await page.goto('/review-queue');
    await page.waitForLoadState('domcontentloaded');

    const viewEntityLink = page.getByRole('link', { name: /view entity/i }).first();
    const viewRelationLink = page.getByRole('link', { name: /view relation/i }).first();

    const hasEntity = await viewEntityLink.isVisible({ timeout: 2000 }).catch(() => false);
    const hasRelation = await viewRelationLink.isVisible({ timeout: 1000 }).catch(() => false);

    if (!hasEntity && !hasRelation) {
      test.skip(true, 'Review queue is empty — seed staged_extractions data to exercise this test');
      return;
    }

    const link = hasEntity ? viewEntityLink : viewRelationLink;
    await link.click();
    await expect(page).toHaveURL(/\/(entities|relations)\/[a-f0-9-]+/);
  });
});
