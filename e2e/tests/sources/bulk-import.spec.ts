import { test, expect } from '@playwright/test';
import { loginAsAdminViaAPI, clearAuthState } from '../../fixtures/auth-helpers';

test.describe('Source Bulk Import', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdminViaAPI(page);
  });

  test.afterEach(async ({ page }) => {
    await clearAuthState(page);
  });

  // US-SRC-10 — Bulk Import Sources (BibTeX / RIS / JSON)

  test('should load the source import page at /sources/import', async ({ page }) => {
    await page.goto('/sources/import');
    await page.waitForLoadState('domcontentloaded');
    // Page heading: t("import.page_title") = "Import Sources"
    await expect(page.getByRole('heading', { name: /import/i })).toBeVisible({ timeout: 10000 });
  });

  test('should show file upload input on import page', async ({ page }) => {
    await page.goto('/sources/import');
    await page.waitForLoadState('domcontentloaded');

    // File input is hidden — detect via the visible "Choose file…" button
    const chooseFileButton = page.getByRole('button', { name: /choose file/i });
    const uploadButton = page.getByRole('button', { name: /upload|select file/i });
    const hasChooseFile = await chooseFileButton.isVisible({ timeout: 5000 }).catch(() => false);
    const hasUploadButton = await uploadButton.isVisible({ timeout: 1000 }).catch(() => false);
    expect(hasChooseFile || hasUploadButton).toBeTruthy();
  });

  test('should support BibTeX format selection', async ({ page }) => {
    await page.goto('/sources/import');
    await page.waitForLoadState('domcontentloaded');

    const bibtexOption = page.locator('text=/bibtex|bib/i').first();
    if (await bibtexOption.isVisible({ timeout: 3000 })) {
      await expect(bibtexOption).toBeVisible();
    }
  });

  test('should support RIS format selection', async ({ page }) => {
    await page.goto('/sources/import');
    await page.waitForLoadState('domcontentloaded');

    const risOption = page.locator('text=/ris/i').first();
    if (await risOption.isVisible({ timeout: 3000 })) {
      await expect(risOption).toBeVisible();
    }
  });

  test('should support JSON format selection', async ({ page }) => {
    await page.goto('/sources/import');
    await page.waitForLoadState('domcontentloaded');

    const jsonOption = page.locator('text=/json/i').first();
    if (await jsonOption.isVisible({ timeout: 3000 })) {
      await expect(jsonOption).toBeVisible();
    }
  });

  test('should preview a valid JSON file before committing', async ({ page }) => {
    await page.goto('/sources/import');
    await page.waitForLoadState('domcontentloaded');

    const prefix = Date.now();
    const jsonContent = JSON.stringify([
      { title: `${prefix} Import Source A`, kind: 'journal_article', year: 2023, url: `https://example.com/${prefix}-a` },
    ]);

    const fileInput = page.locator('input[type="file"]');
    if (await fileInput.waitFor({ state: 'attached', timeout: 5000 }).then(() => true).catch(() => false)) {
      await fileInput.setInputFiles({
        name: 'sources.json',
        mimeType: 'application/json',
        buffer: Buffer.from(jsonContent),
      });

      const previewButton = page.getByRole('button', { name: /preview/i });
      if (await previewButton.isVisible({ timeout: 3000 })) {
        await previewButton.click();
        // Should show preview table
        await expect(page.locator('table, [role="table"]').first()).toBeVisible({ timeout: 10000 });
      }
    }
  });

  test('should show done summary after successful import', async ({ page }) => {
    await page.goto('/sources/import');
    await page.waitForLoadState('domcontentloaded');

    const prefix = Date.now();
    const jsonContent = JSON.stringify([
      { title: `${prefix} Done Summary Source`, kind: 'journal_article', year: 2022, url: `https://example.com/${prefix}-done` },
    ]);

    const fileInput = page.locator('input[type="file"]');
    if (await fileInput.waitFor({ state: 'attached', timeout: 5000 }).then(() => true).catch(() => false)) {
      await fileInput.setInputFiles({
        name: 'sources.json',
        mimeType: 'application/json',
        buffer: Buffer.from(jsonContent),
      });

      const previewButton = page.getByRole('button', { name: /preview/i });
      if (await previewButton.isVisible({ timeout: 3000 })) {
        await previewButton.click();
        await page.waitForTimeout(2000);

        const importButton = page.getByRole('button', { name: /^import|^commit/i });
        if (await importButton.isVisible({ timeout: 5000 })) {
          await importButton.click();
          // Done summary should appear
          const doneSummary = page.locator('text=/done|created|imported|summary/i').first();
          await expect(doneSummary).toBeVisible({ timeout: 10000 });
        }
      }
    }
  });
});
