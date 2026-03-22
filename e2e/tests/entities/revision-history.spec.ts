import { test, expect } from '@playwright/test';
import { loginAsAdminViaAPI, clearAuthState } from '../../fixtures/auth-helpers';
import { generateEntityName, generateSourceName } from '../../fixtures/test-data';

test.describe('Revision History', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdminViaAPI(page);
  });

  test.afterEach(async ({ page }) => {
    await clearAuthState(page);
  });

  // E2E-G3 — Entity and relation revision history

  test('should create a new revision when an entity is edited', async ({ page }) => {
    const API_URL = process.env.API_URL || 'http://localhost:8001';

    // Create an entity via UI
    const entitySlug = generateEntityName('rev-entity').toLowerCase().replace(/\s+/g, '-');
    await page.goto('/entities/new');
    await page.getByLabel(/slug/i).fill(entitySlug);
    await page.getByLabel(/summary.*english/i).fill('Original summary');
    await page.getByRole('button', { name: /create|submit/i }).click();
    await page.waitForURL(/\/entities\/([a-f0-9-]+)/);
    const entityId = page.url().match(/\/entities\/([a-f0-9-]+)/)?.[1] || '';

    const token = await page.evaluate(() => localStorage.getItem('auth_token'));

    // Capture updated_at before edit
    const beforeResp = await page.request.get(`${API_URL}/api/entities/${entityId}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(beforeResp.ok()).toBe(true);
    const beforeData = await beforeResp.json();

    // Navigate to edit page and update summary
    await page.goto(`/entities/${entityId}/edit`);
    await page.waitForLoadState('domcontentloaded');

    const summaryField = page.getByLabel(/summary.*english/i);
    await expect(summaryField).toBeVisible({ timeout: 5000 });
    await summaryField.clear();
    await summaryField.fill('Revised summary for revision test');

    await page.getByRole('button', { name: /save|update/i }).click();
    await page.waitForURL(/\/entities\/[a-f0-9-]+$/, { timeout: 10000 });

    // Verify via API that updated_at advanced (new revision created)
    const afterResp = await page.request.get(`${API_URL}/api/entities/${entityId}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(afterResp.ok()).toBe(true);
    const afterData = await afterResp.json();

    // updated_at must differ — a new revision row was written
    expect(afterData.updated_at).not.toBe(beforeData.updated_at);
  });

  test('should create a new revision when a relation is edited', async ({ page }) => {
    const API_URL = process.env.API_URL || 'http://localhost:8001';

    // Create prerequisite source
    const sourceTitle = generateSourceName('rev-source');
    await page.goto('/sources/new');
    await page.waitForLoadState('domcontentloaded');
    await page.getByRole('textbox', { name: 'Title' }).fill(sourceTitle);
    await page.getByRole('textbox', { name: 'URL' }).fill('https://example.com/rev-source');
    await page.getByRole('button', { name: /create|submit/i }).click();
    await page.waitForURL(/\/sources\/([a-f0-9-]+)/);
    const sourceId = page.url().match(/\/sources\/([a-f0-9-]+)/)?.[1] || '';

    // Create two entities
    const slug1 = generateEntityName('rev-e1').toLowerCase().replace(/\s+/g, '-');
    await page.goto('/entities/new');
    await page.getByRole('textbox', { name: 'Slug' }).fill(slug1);
    await page.getByRole('textbox', { name: /summary.*english/i }).fill('Entity 1 for relation revision');
    await page.getByRole('button', { name: /create|submit/i }).click();
    await page.waitForURL(/\/entities\/([a-f0-9-]+)/);
    const entity1Id = page.url().match(/\/entities\/([a-f0-9-]+)/)?.[1] || '';

    const slug2 = generateEntityName('rev-e2').toLowerCase().replace(/\s+/g, '-');
    await page.goto('/entities/new');
    await page.getByRole('textbox', { name: 'Slug' }).fill(slug2);
    await page.getByRole('textbox', { name: /summary.*english/i }).fill('Entity 2 for relation revision');
    await page.getByRole('button', { name: /create|submit/i }).click();
    await page.waitForURL(/\/entities\/([a-f0-9-]+)/);
    const entity2Id = page.url().match(/\/entities\/([a-f0-9-]+)/)?.[1] || '';

    const token = await page.evaluate(() => localStorage.getItem('auth_token'));

    // Create relation via API
    const createResp = await page.request.post(`${API_URL}/api/relations/`, {
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      data: {
        source_id: sourceId,
        kind: 'involves',
        direction: 'forward',
        confidence: 0.7,
        roles: [
          { entity_id: entity1Id, role_type: 'subject', weight: 1.0, coverage: 1.0 },
          { entity_id: entity2Id, role_type: 'object', weight: 1.0, coverage: 1.0 },
        ],
      },
    });
    if (!createResp.ok()) {
      throw new Error(`Relation creation failed: ${createResp.status()} ${await createResp.text()}`);
    }
    const { id: relationId } = await createResp.json();

    // Capture updated_at before edit
    const beforeResp = await page.request.get(`${API_URL}/api/relations/${relationId}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(beforeResp.ok()).toBe(true);
    const beforeData = await beforeResp.json();

    // Edit the relation via UI
    await page.goto(`/relations/${relationId}/edit`);
    await page.waitForLoadState('domcontentloaded');

    const kindField = page.getByLabel(/relation kind|kind/i);
    await expect(kindField).toBeVisible({ timeout: 5000 });
    await kindField.clear();
    await kindField.fill('involves-revised');

    await page.getByRole('button', { name: /save|update/i }).click();
    await page.waitForTimeout(1500);
    await expect(page).not.toHaveURL(/\/edit$/);

    // Verify via API that updated_at advanced (new revision created)
    const afterResp = await page.request.get(`${API_URL}/api/relations/${relationId}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(afterResp.ok()).toBe(true);
    const afterData = await afterResp.json();

    expect(afterData.kind).toBe('involves-revised');
    expect(afterData.updated_at).not.toBe(beforeData.updated_at);
  });
});
