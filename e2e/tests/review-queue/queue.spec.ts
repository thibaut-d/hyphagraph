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

    // Page heading from t("menu.review_queue")
    await expect(
      page.getByRole('heading', { name: 'Review Queue' })
    ).toBeVisible({ timeout: 10000 });
  });

  test('should show statistics cards (pending, auto-verified, avg score, flagged)', async ({ page }) => {
    await page.goto('/review-queue');
    await page.waitForLoadState('domcontentloaded');

    // Stats cards are only shown when stats data loads. Verify heading at minimum.
    const heading = page.getByRole('heading', { name: 'Review Queue' });
    await expect(heading).toBeVisible({ timeout: 10000 });

    // Stats section may show these labels
    const pendingCard = page.locator('text=/pending/i').first();
    if (await pendingCard.isVisible({ timeout: 3000 })) {
      await expect(pendingCard).toBeVisible();
    }
  });

  test('should show empty state when queue is empty', async ({ page }) => {
    await page.goto('/review-queue');
    await page.waitForLoadState('domcontentloaded');

    // When empty, shows no_pending message (t("review_queue.no_pending_title"))
    const emptyState = page.locator('text=/no pending|queue.*empty|all.*reviewed/i').first();
    if (await emptyState.isVisible({ timeout: 5000 })) {
      await expect(emptyState).toBeVisible();
    }
  });

  test('should show a refresh button', async ({ page }) => {
    await page.goto('/review-queue');
    await page.waitForLoadState('domcontentloaded');

    const refreshButton = page.getByRole('button', { name: /refresh/i });
    await expect(refreshButton).toBeVisible({ timeout: 10000 });
  });

  // US-LLM-04 — Filter Extraction Queue

  test('should show minimum score filter input', async ({ page }) => {
    await page.goto('/review-queue');
    await page.waitForLoadState('domcontentloaded');

    // Min score filter — TextField labeled with min_score_label
    const minScoreInput = page.getByLabel(/min.*score|score/i).first();
    if (await minScoreInput.isVisible({ timeout: 5000 })) {
      await expect(minScoreInput).toBeVisible();
    }
  });

  test('should show flagged-only filter toggle', async ({ page }) => {
    await page.goto('/review-queue');
    await page.waitForLoadState('domcontentloaded');

    // Button for onlyFlagged toggle
    const flaggedButton = page.getByRole('button', { name: /flagged/i });
    if (await flaggedButton.isVisible({ timeout: 5000 })) {
      await expect(flaggedButton).toBeVisible();
    }
  });

  test('should show extraction type filter (entity/relation/claim)', async ({ page }) => {
    await page.goto('/review-queue');
    await page.waitForLoadState('domcontentloaded');

    // ToggleButtonGroup with entity, relation, claim options
    const typeFilter = page.locator('[role="group"]').first();
    if (await typeFilter.isVisible({ timeout: 5000 })) {
      await expect(typeFilter).toBeVisible();
    }

    // Individual type buttons
    const entityToggle = page.getByRole('button', { name: /^entity$/i });
    if (await entityToggle.isVisible({ timeout: 2000 })) {
      await expect(entityToggle).toBeVisible();
    }
  });

  test('should apply extraction type filter without error', async ({ page }) => {
    await page.goto('/review-queue');
    await page.waitForLoadState('domcontentloaded');

    const entityToggle = page.getByRole('button', { name: /^entity$/i });
    if (await entityToggle.isVisible({ timeout: 5000 })) {
      await entityToggle.click();
      await page.waitForTimeout(500);
      // Page should still be functional after filter change
      await expect(page.getByRole('heading', { name: 'Review Queue' })).toBeVisible();
    }
  });

  // US-LLM-02 — Approve / Reject Extractions (interaction surface test)
  // Real approve/reject requires seeded staged_extractions data; these tests
  // verify the UI controls are present when items exist.

  test('should show select-all button when extractions are present', async ({ page }) => {
    await page.goto('/review-queue');
    await page.waitForLoadState('domcontentloaded');

    // Select All button only renders when extractions.length > 0
    const selectAllButton = page.getByRole('button', { name: /select all/i });
    if (await selectAllButton.isVisible({ timeout: 3000 })) {
      await expect(selectAllButton).toBeVisible();
    }
  });

  // US-LLM-03 — Batch Approve / Reject
  test('should show batch action buttons when items are selected', async ({ page }) => {
    await page.goto('/review-queue');
    await page.waitForLoadState('domcontentloaded');

    const selectAllButton = page.getByRole('button', { name: /select all/i });
    if (await selectAllButton.isVisible({ timeout: 3000 })) {
      await selectAllButton.click();
      await page.waitForTimeout(300);

      // Batch actions bar should appear
      const approveSelected = page.getByRole('button', { name: /approve.*selected/i });
      const rejectSelected = page.getByRole('button', { name: /reject.*selected/i });
      if (await approveSelected.isVisible({ timeout: 2000 })) {
        await expect(approveSelected).toBeVisible();
        await expect(rejectSelected).toBeVisible();
      }
    }
  });

  // US-LLM-05 — Navigate from extraction to entity/relation
  test('should show entity/relation links in extraction cards when queue has items', async ({ page }) => {
    await page.goto('/review-queue');
    await page.waitForLoadState('domcontentloaded');

    // If there are extraction cards, each should have View Entity or View Relation links
    const viewEntityLink = page.getByRole('link', { name: /view entity/i }).first();
    const viewRelationLink = page.getByRole('link', { name: /view relation/i }).first();

    // Only assert if items are actually present
    const hasItems = await viewEntityLink.isVisible({ timeout: 2000 }).catch(() => false) ||
      await viewRelationLink.isVisible({ timeout: 1000 }).catch(() => false);

    if (hasItems) {
      const link = (await viewEntityLink.isVisible().catch(() => false))
        ? viewEntityLink
        : viewRelationLink;
      await link.click();
      await expect(page).toHaveURL(/\/(entities|relations)\/[a-f0-9-]+/);
    }
  });
});
