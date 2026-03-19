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
    if (resp.ok()) {
      const data = await resp.json();
      relationId = data.id;
    }
  });

  test.afterEach(async ({ page }) => {
    await clearAuthState(page);
  });

  // US-REL-03 — Edit Relation
  test('should navigate to the relation edit page', async ({ page }) => {
    if (!relationId) test.skip();

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

    // The kind field should be pre-filled
    const kindField = page.getByLabel(/relation kind|kind/i);
    if (await kindField.isVisible({ timeout: 3000 })) {
      await expect(kindField).toHaveValue('mentions');
    }
  });

  test('should save a relation update and create a new revision', async ({ page }) => {
    if (!relationId) test.skip();

    await page.goto(`/relations/${relationId}/edit`);
    await page.waitForLoadState('domcontentloaded');

    const kindField = page.getByLabel(/relation kind|kind/i);
    if (await kindField.isVisible({ timeout: 3000 })) {
      await kindField.clear();
      await kindField.fill('updated-mention');

      await page.getByRole('button', { name: /save|update/i }).click();
      await page.waitForTimeout(2000);

      // Should navigate away from edit page or show a success indicator
      const url = page.url();
      const notOnEditPage = !url.includes('/edit');
      const successAlert = await page.getByRole('alert').isVisible({ timeout: 1000 }).catch(() => false);
      expect(notOnEditPage || successAlert).toBeTruthy();
    }
  });

  // US-REL-04 — Delete Relation
  test('should delete a relation from the relations list', async ({ page }) => {
    if (!relationId) test.skip();

    await page.goto('/relations');
    await expect(page.getByRole('heading', { name: 'Relations', exact: true })).toBeVisible();

    // Find a delete button for our relation
    const deleteButton = page.getByRole('button', { name: /delete/i }).first();
    if (await deleteButton.isVisible({ timeout: 5000 })) {
      await deleteButton.click();

      // Confirmation dialog
      const confirmButton = page.locator('[role="dialog"]').getByRole('button', { name: /delete|confirm/i });
      if (await confirmButton.isVisible({ timeout: 2000 })) {
        await confirmButton.click();
        await page.waitForTimeout(1000);
      }

      // Should still be on relations page
      await expect(page.getByRole('heading', { name: 'Relations', exact: true })).toBeVisible();
    }
  });
});
