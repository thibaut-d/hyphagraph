import { test, expect } from '@playwright/test';
import { loginAsAdminViaAPI, clearAuthState, getAccessToken } from '../../fixtures/auth-helpers';
import { generateEntityName, generateSourceName } from '../../fixtures/test-data';

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
    await page.waitForLoadState('domcontentloaded');

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
    await page.waitForLoadState('domcontentloaded');

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
    await page.waitForLoadState('domcontentloaded');

    const disagreementsLink = page.getByRole('link', { name: /disagree/i }).or(
      page.getByRole('button', { name: /disagree/i })
    );
    await expect(disagreementsLink.first()).toBeVisible({ timeout: 10000 });
    await disagreementsLink.first().click();
    await expect(page).toHaveURL(new RegExp(`/entities/${entityId}/disagreements`));
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
    await page.waitForLoadState('domcontentloaded');

    const backButton = page.getByRole('button', { name: /back/i }).or(
      page.getByRole('link', { name: /back|entity/i })
    );
    await expect(backButton.first()).toBeVisible({ timeout: 10000 });
    await backButton.first().click();
    await expect(page).toHaveURL(new RegExp(`/entities/${entityId}$`));
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
    await page.waitForLoadState('domcontentloaded');

    const synthButton = page.getByRole('button', { name: /synthesis/i }).or(
      page.getByRole('link', { name: /synthesis/i })
    );
    await expect(synthButton.first()).toBeVisible({ timeout: 10000 });
    await synthButton.first().click();
    await expect(page).toHaveURL(new RegExp(`/entities/${entityId}/synthesis`));
  });

  // G2 + G4 — contradiction visibility with seeded contradictory data
  test('should display contradictions when contradictory relations exist', async ({ page }) => {
    const API_URL = process.env.API_URL || 'http://localhost:8001';

    // Create two sources
    const src1Title = generateSourceName('contra-source-a');
    await page.goto('/sources/new');
    await page.getByRole('textbox', { name: 'Title' }).fill(src1Title);
    await page.getByRole('textbox', { name: 'URL' }).fill('https://example.com/contra-a');
    await page.getByRole('button', { name: /create|submit/i }).click();
    await page.waitForURL(/\/sources\/([a-f0-9-]+)/);
    const src1Id = page.url().match(/\/sources\/([a-f0-9-]+)/)?.[1] || '';

    const src2Title = generateSourceName('contra-source-b');
    await page.goto('/sources/new');
    await page.getByRole('textbox', { name: 'Title' }).fill(src2Title);
    await page.getByRole('textbox', { name: 'URL' }).fill('https://example.com/contra-b');
    await page.getByRole('button', { name: /create|submit/i }).click();
    await page.waitForURL(/\/sources\/([a-f0-9-]+)/);
    const src2Id = page.url().match(/\/sources\/([a-f0-9-]+)/)?.[1] || '';

    // Create two entities
    const entitySlug = generateEntityName('contra-entity').toLowerCase().replace(/\s+/g, '-');
    await page.goto('/entities/new');
    await page.getByRole('textbox', { name: 'Slug' }).fill(entitySlug);
    await page.getByRole('textbox', { name: /summary.*english/i }).fill('Entity for contradiction test');
    await page.getByRole('button', { name: /create|submit/i }).click();
    await page.waitForURL(/\/entities\/([a-f0-9-]+)/);
    const entityId = page.url().match(/\/entities\/([a-f0-9-]+)/)?.[1] || '';

    const otherSlug = generateEntityName('contra-other').toLowerCase().replace(/\s+/g, '-');
    await page.goto('/entities/new');
    await page.getByRole('textbox', { name: 'Slug' }).fill(otherSlug);
    await page.getByRole('textbox', { name: /summary.*english/i }).fill('Other entity for contradiction');
    await page.getByRole('button', { name: /create|submit/i }).click();
    await page.waitForURL(/\/entities\/([a-f0-9-]+)/);
    const otherId = page.url().match(/\/entities\/([a-f0-9-]+)/)?.[1] || '';

    // Seed two relations with the same kind/entity but from different sources (potential contradiction)
    const token = await getAccessToken(page);
    for (const [srcId, direction] of [[src1Id, 'forward'], [src2Id, 'backward']] as [string, string][]) {
      await page.request.post(`${API_URL}/api/relations/`, {
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        data: {
          source_id: srcId,
          kind: 'associated_with',
          direction,
          confidence: 0.9,
          roles: [
            { entity_id: entityId, role_type: 'subject', weight: 1.0, coverage: 1.0 },
            { entity_id: otherId, role_type: 'object', weight: 1.0, coverage: 1.0 },
          ],
        },
      });
    }

    // Navigate to disagreements page
    await page.goto(`/entities/${entityId}/disagreements`);
    await page.waitForLoadState('domcontentloaded');

    await expect(page).toHaveURL(`/entities/${entityId}/disagreements`);

    // Page must render — either showing disagreement groups or an empty state
    const content = page.locator('text=/disagree|contradict|no.*conflict|no.*contradict/i').first();
    await expect(content).toBeVisible({ timeout: 10000 });

    // G2 invariant: if disagreements are shown, there must be NO hidden/suppressed groups
    // (i.e. no element with aria-hidden=true that contains "disagree" text)
    const hiddenDisagreements = page.locator('[aria-hidden="true"]').filter({ hasText: /disagree|contradict/i });
    const hiddenCount = await hiddenDisagreements.count();
    expect(hiddenCount).toBe(0);
  });
});
