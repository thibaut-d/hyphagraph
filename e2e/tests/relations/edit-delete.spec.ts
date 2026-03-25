import { test, expect } from '@playwright/test';
import { loginAsAdminViaAPI, clearAuthState } from '../../fixtures/auth-helpers';
import { generateEntityName, generateSourceName } from '../../fixtures/test-data';

test.describe('Relation Edit and Delete', () => {
  let sourceId: string;
  let entity1Id: string;
  let entity2Id: string;
  let relationId: string;

  test.beforeEach(async ({ page }) => {
    await loginAsAdminViaAPI(page);

    // Create prerequisite source
    const sourceTitle = generateSourceName('rel-edit-source');
    await page.goto('/sources/new');
    await page.waitForLoadState('domcontentloaded');
    await page.getByRole('textbox', { name: 'Title' }).fill(sourceTitle);
    await page.getByRole('textbox', { name: 'URL' }).fill('https://example.com/rel-edit-source');
    await page.getByRole('button', { name: /create|submit/i }).click();
    await page.waitForURL(/\/sources\/([a-f0-9-]+)/);
    sourceId = page.url().match(/\/sources\/([a-f0-9-]+)/)?.[1] || '';

    // Create two entities
    const slug1 = generateEntityName('rel-edit-e1').toLowerCase().replace(/\s+/g, '-');
    await page.goto('/entities/new');
    await page.waitForLoadState('domcontentloaded');
    await page.getByRole('textbox', { name: 'Slug' }).fill(slug1);
    await page.getByRole('textbox', { name: /summary.*english/i }).fill('Entity 1 for relation edit');
    await page.getByRole('button', { name: /create|submit/i }).click();
    await page.waitForURL(/\/entities\/([a-f0-9-]+)/);
    entity1Id = page.url().match(/\/entities\/([a-f0-9-]+)/)?.[1] || '';

    const slug2 = generateEntityName('rel-edit-e2').toLowerCase().replace(/\s+/g, '-');
    await page.goto('/entities/new');
    await page.waitForLoadState('domcontentloaded');
    await page.getByRole('textbox', { name: 'Slug' }).fill(slug2);
    await page.getByRole('textbox', { name: /summary.*english/i }).fill('Entity 2 for relation edit');
    await page.getByRole('button', { name: /create|submit/i }).click();
    await page.waitForURL(/\/entities\/([a-f0-9-]+)/);
    entity2Id = page.url().match(/\/entities\/([a-f0-9-]+)/)?.[1] || '';

    // Create a relation via API for deterministic setup
    const API_URL = process.env.API_URL || 'http://localhost:8001';
    const token = await page.evaluate(() => localStorage.getItem('auth_token'));
    const resp = await page.request.post(`${API_URL}/api/relations/`, {
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      data: {
        source_id: sourceId,
        kind: 'mentions',
        direction: 'forward',
        confidence: 0.8,
        roles: [
          { entity_id: entity1Id, role_type: 'subject', weight: 1.0, coverage: 1.0 },
          { entity_id: entity2Id, role_type: 'object', weight: 1.0, coverage: 1.0 },
        ],
      },
    });
    if (!resp.ok()) {
      throw new Error(`beforeEach relation creation failed: ${resp.status()} ${await resp.text()}`);
    }
    const data = await resp.json();
    relationId = data.id;
  });

  test.afterEach(async ({ page }) => {
    await clearAuthState(page);
  });

  // US-REL-03 — Edit Relation
  test('should navigate to the relation edit page', async ({ page }) => {
    if (!relationId) test.skip(true, 'No relation was created in beforeEach — seed relation data to run this test');

    await page.goto(`/relations/${relationId}/edit`);
    await expect(page).toHaveURL(`/relations/${relationId}/edit`);
    // Edit form should be visible
    await expect(
      page.getByRole('heading', { name: /edit relation/i })
        .or(page.locator('text=/edit relation/i').first())
    ).toBeVisible({ timeout: 10000 });
  });

  test('should pre-fill form with current relation values', async ({ page }) => {
    if (!relationId) test.skip();

    await page.goto(`/relations/${relationId}/edit`);
    await page.waitForLoadState('domcontentloaded');

    // The kind field must be pre-filled — relation was seeded with kind='mentions'
    const kindField = page.getByLabel(/relation kind|kind/i);
    await expect(kindField).toBeVisible({ timeout: 5000 });
    await expect(kindField).toHaveValue('mentions');
  });

  test('should save a relation update and create a new revision', async ({ page }) => {
    const API_URL = process.env.API_URL || 'http://localhost:8001';
    const token = await page.evaluate(() => localStorage.getItem('auth_token'));

    // Capture the updated_at before edit
    const beforeResp = await page.request.get(`${API_URL}/api/relations/${relationId}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(beforeResp.ok()).toBe(true);
    const beforeData = await beforeResp.json();

    await page.goto(`/relations/${relationId}/edit`);
    await page.waitForLoadState('domcontentloaded');

    const kindField = page.getByLabel(/relation kind|kind/i);
    await expect(kindField).toBeVisible({ timeout: 5000 });
    await kindField.clear();
    await kindField.fill('updated-mention');

    await page.getByRole('button', { name: /save|update/i }).click();
    // EditRelationView navigates to /sources/{source_id} on save
    await page.waitForURL(/\/(relations|sources)\/[a-f0-9-]+/, { timeout: 10000 });
    await page.waitForTimeout(500);

    // Verify via API that the relation was actually updated
    const afterResp = await page.request.get(`${API_URL}/api/relations/${relationId}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(afterResp.ok()).toBe(true);
    const afterData = await afterResp.json();

    // The kind must reflect the update
    expect(afterData.kind).toBe('updated-mention');
    // updated_at must have advanced (new revision)
    expect(afterData.updated_at).not.toBe(beforeData.updated_at);
  });

  // US-REL-04 — Delete Relation
  test('should delete a relation from the source detail page', async ({ page }) => {
    if (!relationId) test.skip(true, 'No relation was created in beforeEach — seed relation data to run this test');

    // Relations are shown with delete buttons on the source detail page
    await page.goto(`/sources/${sourceId}`);
    await page.waitForLoadState('domcontentloaded');

    // A delete button must be present — relation was seeded in beforeEach
    const deleteButton = page.getByRole('button', { name: /delete.*relation|relation.*delete/i }).first()
      .or(page.locator('[data-testid*="delete-relation"]').first())
      .or(page.getByRole('button', { name: /delete/i }).nth(1)); // second delete (first may be source delete)
    await expect(deleteButton).toBeVisible({ timeout: 10000 });
    await deleteButton.click();

    // Confirmation dialog must appear
    const confirmButton = page.locator('[role="dialog"]').getByRole('button', { name: /delete|confirm/i });
    await expect(confirmButton).toBeVisible({ timeout: 3000 });
    await confirmButton.click();
    await page.waitForTimeout(500);

    // Should still be on source detail page
    await expect(page).toHaveURL(new RegExp(`/sources/${sourceId}`));
  });
});
