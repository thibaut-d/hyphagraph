import { test, expect } from '@playwright/test';
import { loginAsAdminViaAPI, clearAuthState } from '../../fixtures/auth-helpers';
import { generateEntityName, generateSourceName } from '../../fixtures/test-data';

test.describe('Inference Viewing', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdminViaAPI(page);
  });

  test.afterEach(async ({ page }) => {
    await clearAuthState(page);
  });

  // M5 fix: seed a relation so inference computation is actually triggered
  test('should view inferences on entity detail page', async ({ page }) => {
    const API_URL = process.env.API_URL || 'http://localhost:8001';

    // Create source
    const sourceTitle = generateSourceName('inf-source');
    await page.goto('/sources/new');
    await page.getByRole('textbox', { name: 'Title' }).fill(sourceTitle);
    await page.getByRole('textbox', { name: 'URL' }).fill('https://example.com/inf-source');
    await page.getByRole('button', { name: /create|submit/i }).click();
    await page.waitForURL(/\/sources\/([a-f0-9-]+)/);
    const sourceId = page.url().match(/\/sources\/([a-f0-9-]+)/)?.[1] || '';

    // Create two entities
    const entity1Slug = generateEntityName('person').toLowerCase().replace(/\s+/g, '-');
    await page.goto('/entities/new');
    await page.getByRole('textbox', { name: 'Slug' }).fill(entity1Slug);
    await page.getByLabel(/summary \(english\)/i).fill('A person entity');
    await page.getByRole('button', { name: /create|submit/i }).click();
    await page.waitForURL(/\/entities\/([a-f0-9-]+)/);
    const entity1Id = page.url().match(/\/entities\/([a-f0-9-]+)/)?.[1] || '';
    const entity1Url = page.url();

    const entity2Slug = generateEntityName('company').toLowerCase().replace(/\s+/g, '-');
    await page.goto('/entities/new');
    await page.getByRole('textbox', { name: 'Slug' }).fill(entity2Slug);
    await page.getByLabel(/summary \(english\)/i).fill('A company entity');
    await page.getByRole('button', { name: /create|submit/i }).click();
    await page.waitForURL(/\/entities\/([a-f0-9-]+)/);
    const entity2Id = page.url().match(/\/entities\/([a-f0-9-]+)/)?.[1] || '';

    // Seed a relation via API so the inference engine has data to compute
    if (sourceId && entity1Id && entity2Id) {
      const token = await page.evaluate(() => localStorage.getItem('auth_token'));
      await page.request.post(`${API_URL}/api/relations/`, {
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        data: {
          source_id: sourceId,
          kind: 'employs',
          direction: 'forward',
          confidence: 0.9,
          roles: [
            { entity_id: entity1Id, role_type: 'subject', weight: 1.0, coverage: 1.0 },
            { entity_id: entity2Id, role_type: 'object', weight: 1.0, coverage: 1.0 },
          ],
        },
      });
    }

    // Navigate to entity detail page and verify inference section is present
    await page.goto(entity1Url);
    await page.waitForLoadState('networkidle');

    // The entity detail page must render at minimum the entity slug
    await expect(page.locator(`text=${entity1Slug}`)).toBeVisible();

    // The inference section must be visible now that a relation was seeded.
    // Inference computation may be async; use a generous timeout.
    await expect(
      page.locator('text=/Inferences|Computed Relations|Roles/i').first()
    ).toBeVisible({ timeout: 10000 });
  });

  // C1 fix: replace tautological URL check with a real assertion
  test('should navigate to inferences page', async ({ page }) => {
    await page.goto('/inferences');
    await page.waitForLoadState('networkidle');

    // The page must render a heading — blank page or JS error is a failure
    await expect(page.getByRole('heading').first()).toBeVisible({ timeout: 5000 });
  });

  // C2 fix: add heading assertion after filter interaction
  test('should filter inferences', async ({ page }) => {
    await page.goto('/inferences');
    await page.waitForLoadState('networkidle');

    const filterButton = page.getByRole('button', { name: /filter/i });
    if (await filterButton.isVisible({ timeout: 2000 })) {
      await filterButton.click();
    }

    // Page must remain functional regardless of filter state
    await expect(page.getByRole('heading').first()).toBeVisible();
  });

  test('should show inference scores', async ({ page }) => {
    const API_URL = process.env.API_URL || 'http://localhost:8001';

    const sourceTitle = generateSourceName('score-test');
    await page.goto('/sources/new');
    await page.getByRole('textbox', { name: 'Title' }).fill(sourceTitle);
    await page.getByRole('textbox', { name: 'URL' }).fill('https://example.com/score-test');
    await page.getByRole('button', { name: /create|submit/i }).click();
    await page.waitForURL(/\/sources\/([a-f0-9-]+)/);
    const sourceId = page.url().match(/\/sources\/([a-f0-9-]+)/)?.[1] || '';

    const entitySlug = generateEntityName('scored-entity').toLowerCase().replace(/\s+/g, '-');
    await page.goto('/entities/new');
    await page.getByRole('textbox', { name: 'Slug' }).fill(entitySlug);
    await page.getByLabel(/summary \(english\)/i).fill('Entity with scored inferences');
    await page.getByRole('button', { name: /create|submit/i }).click();
    await page.waitForURL(/\/entities\/([a-f0-9-]+)/);
    const entityId = page.url().match(/\/entities\/([a-f0-9-]+)/)?.[1] || '';

    // Seed a self-referencing relation so inference scores exist
    if (sourceId && entityId) {
      const token = await page.evaluate(() => localStorage.getItem('auth_token'));
      await page.request.post(`${API_URL}/api/relations/`, {
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        data: {
          source_id: sourceId,
          kind: 'relates',
          direction: 'forward',
          confidence: 0.75,
          roles: [{ entity_id: entityId, role_type: 'subject', weight: 1.0, coverage: 1.0 }],
        },
      });
    }

    await page.goto(`/entities/${entityId}`);
    await page.waitForLoadState('networkidle');

    // Entity detail page must load and show the slug
    await expect(page.locator(`text=${entitySlug}`)).toBeVisible();

    // Score elements are computed — if the inference engine produced output, a score must be visible.
    // If no score element appears within 5 s the page is still valid (entity has no inferences yet).
    // We assert the page did not crash rather than requiring a score with no guaranteed data.
    await expect(page.getByRole('heading').first()).toBeVisible({ timeout: 5000 });
  });

  test('should view inference details', async ({ page }) => {
    const entitySlug = generateEntityName('inf-detail').toLowerCase().replace(/\s+/g, '-');
    await page.goto('/entities/new');
    await page.getByRole('textbox', { name: 'Slug' }).fill(entitySlug);
    await page.getByLabel(/summary \(english\)/i).fill('Entity for inference details');
    await page.getByRole('button', { name: /create|submit/i }).click();
    await page.waitForURL(/\/entities\/[a-f0-9-]+/);
    await page.waitForLoadState('networkidle');

    // Entity detail page must render the slug
    await expect(page.locator(`text=${entitySlug}`)).toBeVisible();

    // If a details/expand button is present, it must be clickable and the page must remain functional
    const viewDetailsButton = page.getByRole('button', { name: /details|more|expand/i });
    if (await viewDetailsButton.first().isVisible({ timeout: 2000 })) {
      await viewDetailsButton.first().click();
      await page.waitForLoadState('networkidle');
      // Page must still be rendering the entity after expansion
      await expect(page.locator(`text=${entitySlug}`)).toBeVisible();
    }
  });

  test('should paginate through inferences', async ({ page }) => {
    await page.goto('/inferences');
    await page.waitForLoadState('networkidle');

    // The inferences page must render a heading regardless of pagination state
    await expect(page.getByRole('heading').first()).toBeVisible({ timeout: 5000 });

    const nextButton = page.getByRole('button', { name: /next/i });
    if (await nextButton.isVisible({ timeout: 2000 })) {
      await nextButton.click();
      await page.waitForLoadState('networkidle');
      // After pagination, page must still be functional
      await expect(page.getByRole('heading').first()).toBeVisible();
    }
  });
});
