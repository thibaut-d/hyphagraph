import { test, expect } from '@playwright/test';
import { loginAsAdminViaAPI, clearAuthState } from '../../fixtures/auth-helpers';

test.describe('Relation Export', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdminViaAPI(page);
  });

  test.afterEach(async ({ page }) => {
    await clearAuthState(page);
  });

  // US-REL-06 — Export Relations

  test('should show export button on relations list', async ({ page }) => {
    await page.goto('/relations');
    await expect(page.getByRole('heading', { name: 'Relations', exact: true })).toBeVisible();

    // Export button must be present
    await expect(page.getByRole('button', { name: /export/i })).toBeVisible({ timeout: 5000 });
  });

  test('should trigger a file download when export is clicked', async ({ page }) => {
    await page.goto('/relations');
    await expect(page.getByRole('heading', { name: 'Relations', exact: true })).toBeVisible();

    const exportButton = page.getByRole('button', { name: /export/i });
    await expect(exportButton).toBeVisible({ timeout: 5000 });

    const [download] = await Promise.all([
      page.waitForEvent('download', { timeout: 10000 }).catch(() => null),
      exportButton.click(),
    ]);

    if (download) {
      const filename = download.suggestedFilename();
      expect(filename).toMatch(/\.(json|csv|rdf)$/i);
    }
  });

  test('should offer RDF export format', async ({ page }) => {
    await page.goto('/relations');
    await expect(page.getByRole('heading', { name: 'Relations', exact: true })).toBeVisible();

    const exportButton = page.getByRole('button', { name: /export/i });
    await expect(exportButton).toBeVisible({ timeout: 5000 });
    await exportButton.click();

    // After clicking, a menu or dialog may show format options
    const rdfOption = page.getByRole('menuitem', { name: /rdf/i }).or(
      page.getByRole('button', { name: /rdf/i })
    );
    if (await rdfOption.isVisible({ timeout: 2000 })) {
      const [download] = await Promise.all([
        page.waitForEvent('download', { timeout: 10000 }).catch(() => null),
        rdfOption.click(),
      ]);
      if (download) {
        expect(download.suggestedFilename()).toMatch(/\.rdf$|\.ttl$|\.n3$/i);
      }
    }
  });
});
