import { test, expect } from '../../fixtures/test-fixtures';
import { loginAsAdminViaAPI, clearAuthState } from '../../fixtures/auth-helpers';

/**
 * Smart Discovery E2E tests.
 *
 * Creates a "fibromyalgia" entity then exercises the smart discovery flow:
 *   1. Navigate to /sources/smart-discovery
 *   2. Select the entity in the autocomplete
 *   3. Launch the search
 *   4. Assert that results are displayed
 */

test.describe('Smart Discovery', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdminViaAPI(page);
  });

  test.afterEach(async ({ page }) => {
    await clearAuthState(page);
  });

  test('should create fibromyalgia entity and run smart discovery', async ({
    page,
    cleanup,
    testSlug,
  }) => {
    // ── Step 1: Create the entity ──────────────────────────────────────────
    const entitySlug = testSlug('fibromyalgia');

    await page.goto('/entities/new');
    await expect(page.getByRole('heading', { name: 'Create Entity' })).toBeVisible();

    await page.getByLabel(/slug/i).fill(entitySlug);
    await page.getByLabel(/summary.*english/i).fill(
      'Fibromyalgia is a chronic disorder characterized by widespread musculoskeletal pain.'
    );
    await page.getByRole('button', { name: /create|submit/i }).click();

    await page.waitForURL(/\/entities\/[a-f0-9-]+/, { timeout: 10_000 });
    const entityId = page.url().match(/\/entities\/([a-f0-9-]+)/)?.[1] ?? '';
    expect(entityId).toBeTruthy();
    cleanup.track('entity', entityId);

    await expect(page.locator(`text=${entitySlug}`)).toBeVisible();

    // ── Step 2: Navigate to Smart Discovery ───────────────────────────────
    await page.goto('/sources/smart-discovery');
    await expect(
      page.getByRole('heading', { name: /smart source discovery/i })
        .or(page.locator('text=/smart source discovery/i').first())
    ).toBeVisible({ timeout: 10_000 });

    // ── Step 3: Select the entity in the autocomplete ─────────────────────
    const entityInput = page.getByLabel(/select entities/i);
    await entityInput.click();
    await entityInput.fill(entitySlug);

    // Wait for the dropdown option and click it
    const option = page.getByRole('option', { name: new RegExp(entitySlug) });
    await expect(option).toBeVisible({ timeout: 8_000 });
    await option.click();

    // Confirm the chip appears (entity selected)
    await expect(page.getByRole('button', { name: new RegExp(entitySlug) })).toBeVisible();

    // ── Step 4: Confirm PubMed is selected and launch search ──────────────
    // PubMed checkbox should be checked by default
    const pubmedCheckbox = page.getByRole('checkbox', { name: /pubmed/i });
    await expect(pubmedCheckbox).toBeChecked();

    const discoverButton = page.getByRole('button', { name: /discover|search/i }).last();
    await expect(discoverButton).toBeEnabled();
    await discoverButton.click();

    // ── Step 5: Assert results appear ─────────────────────────────────────
    // Discovery hits a real external API — allow up to 45s
    await expect(
      page.locator('text=/found.*source|sources found/i').first()
        .or(page.getByRole('table').first())
    ).toBeVisible({ timeout: 45_000 });

    // Results table should have at least one row beyond the header
    const rows = page.getByRole('row');
    await expect(rows.first()).toBeVisible({ timeout: 5_000 });
    const rowCount = await rows.count();
    expect(rowCount).toBeGreaterThanOrEqual(2); // header + ≥1 data row
  });
});
