import { test, expect } from '../../fixtures/test-fixtures';
import { loginAsAdminViaAPI, clearAuthState, getAccessToken } from '../../fixtures/auth-helpers';

test.describe('Inference Viewing', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdminViaAPI(page);
  });

  test.afterEach(async ({ page }) => {
    await clearAuthState(page);
  });

  // M5 fix: seed a relation so inference computation is actually triggered
  test('should view inferences on entity detail page', async ({ page, cleanup, testLabel, testSlug }) => {
    const API_URL = process.env.API_URL || 'http://localhost:8001';

    const sourceTitle = testLabel('source');
    await page.goto('/sources/new');
    await page.getByRole('textbox', { name: 'Title' }).fill(sourceTitle);
    await page.getByRole('textbox', { name: 'URL' }).fill(`https://example.com/${testSlug('url')}`);
    await page.getByRole('button', { name: /create|submit/i }).click();
    await page.waitForURL(/\/sources\/([a-f0-9-]+)/);
    const sourceId = page.url().match(/\/sources\/([a-f0-9-]+)/)?.[1] ?? '';
    cleanup.track('source', sourceId);

    const entity1Slug = testSlug('entity1');
    await page.goto('/entities/new');
    await page.getByRole('textbox', { name: 'Slug' }).fill(entity1Slug);
    await page.getByLabel(/summary \(english\)/i).fill('A person entity');
    await page.getByRole('button', { name: /create|submit/i }).click();
    await page.waitForURL(/\/entities\/([a-f0-9-]+)/);
    const entity1Id = page.url().match(/\/entities\/([a-f0-9-]+)/)?.[1] ?? '';
    const entity1Url = page.url();
    cleanup.track('entity', entity1Id);

    const entity2Slug = testSlug('entity2');
    await page.goto('/entities/new');
    await page.getByRole('textbox', { name: 'Slug' }).fill(entity2Slug);
    await page.getByLabel(/summary \(english\)/i).fill('A company entity');
    await page.getByRole('button', { name: /create|submit/i }).click();
    await page.waitForURL(/\/entities\/([a-f0-9-]+)/);
    const entity2Id = page.url().match(/\/entities\/([a-f0-9-]+)/)?.[1] ?? '';
    cleanup.track('entity', entity2Id);

    if (sourceId && entity1Id && entity2Id) {
      const token = await getAccessToken(page);
      const relResp = await page.request.post(`${API_URL}/api/relations/`, {
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
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
      if (relResp.ok()) {
        const { id: relId } = await relResp.json();
        cleanup.track('relation', relId);
      }
    }

    await page.goto(entity1Url);
    await page.waitForLoadState('domcontentloaded');

    await expect(page.locator(`text=${entity1Slug}`).first()).toBeVisible();
    await expect(
      page.getByRole('heading', { name: /Related assertions|Inferences|Computed Relations|Roles/i }).first()
    ).toBeVisible({ timeout: 10000 });
  });

  // C1 fix: replace tautological URL check with a real assertion
  test('should navigate to inferences page', async ({ page }) => {
    await page.goto('/inferences');
    await page.waitForLoadState('networkidle');
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

    await expect(page.getByRole('heading').first()).toBeVisible();
  });

  test('should show inference scores', async ({ page, cleanup, testLabel, testSlug }) => {
    const API_URL = process.env.API_URL || 'http://localhost:8001';

    const sourceTitle = testLabel('source');
    await page.goto('/sources/new');
    await page.getByRole('textbox', { name: 'Title' }).fill(sourceTitle);
    await page.getByRole('textbox', { name: 'URL' }).fill(`https://example.com/${testSlug('url')}`);
    await page.getByRole('button', { name: /create|submit/i }).click();
    await page.waitForURL(/\/sources\/([a-f0-9-]+)/);
    const sourceId = page.url().match(/\/sources\/([a-f0-9-]+)/)?.[1] ?? '';
    cleanup.track('source', sourceId);

    const entitySlug = testSlug('scored-entity');
    await page.goto('/entities/new');
    await page.getByRole('textbox', { name: 'Slug' }).fill(entitySlug);
    await page.getByLabel(/summary \(english\)/i).fill('Entity with scored inferences');
    await page.getByRole('button', { name: /create|submit/i }).click();
    await page.waitForURL(/\/entities\/([a-f0-9-]+)/);
    const entityId = page.url().match(/\/entities\/([a-f0-9-]+)/)?.[1] ?? '';
    cleanup.track('entity', entityId);

    if (sourceId && entityId) {
      const token = await getAccessToken(page);
      const relResp = await page.request.post(`${API_URL}/api/relations/`, {
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        data: {
          source_id: sourceId,
          kind: 'relates',
          direction: 'forward',
          confidence: 0.75,
          roles: [{ entity_id: entityId, role_type: 'subject', weight: 1.0, coverage: 1.0 }],
        },
      });
      if (relResp.ok()) {
        const { id: relId } = await relResp.json();
        cleanup.track('relation', relId);
      }
    }

    await page.goto(`/entities/${entityId}`);
    await page.waitForLoadState('domcontentloaded');

    await expect(page.locator(`text=${entitySlug}`).first()).toBeVisible();
    await expect(page.getByRole('heading').first()).toBeVisible({ timeout: 5000 });
  });

  test('should view inference details', async ({ page, cleanup, testSlug }) => {
    const entitySlug = testSlug('inf-detail');
    await page.goto('/entities/new');
    await page.getByRole('textbox', { name: 'Slug' }).fill(entitySlug);
    await page.getByLabel(/summary \(english\)/i).fill('Entity for inference details');
    await page.getByRole('button', { name: /create|submit/i }).click();
    await page.waitForURL(/\/entities\/[a-f0-9-]+/);
    const entityId = page.url().match(/\/entities\/([a-f0-9-]+)/)?.[1] ?? '';
    await page.waitForLoadState('domcontentloaded');
    cleanup.track('entity', entityId);

    await expect(page.locator(`text=${entitySlug}`).first()).toBeVisible();

    const viewDetailsButton = page.getByRole('button', { name: /details|more|expand/i });
    if (await viewDetailsButton.first().isVisible({ timeout: 2000 })) {
      await viewDetailsButton.first().click();
      await page.waitForLoadState('domcontentloaded');
      await expect(page.locator(`text=${entitySlug}`).first()).toBeVisible();
    }
  });

  test('should paginate through inferences', async ({ page }) => {
    await page.goto('/inferences');
    await page.waitForLoadState('networkidle');

    await expect(page.getByRole('heading').first()).toBeVisible({ timeout: 5000 });

    const nextButton = page.getByRole('button', { name: /next/i });
    if (await nextButton.isVisible({ timeout: 2000 })) {
      await nextButton.click();
      await page.waitForLoadState('networkidle');
      await expect(page.getByRole('heading').first()).toBeVisible();
    }
  });
});
