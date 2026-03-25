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
    await expect(page.getByRole('heading', { name: /import/i })).toBeVisible({ timeout: 10000 });
  });

  test('should show file upload input on import page', async ({ page }) => {
    await page.goto('/sources/import');
    await page.waitForLoadState('domcontentloaded');

    // File input is visually hidden — detect via the visible "Choose file…" button
    const chooseFileButton = page.getByRole('button', { name: /choose file/i });
    await expect(chooseFileButton).toBeVisible({ timeout: 5000 });
  });

  test('should support BibTeX format selection', async ({ page }) => {
    await page.goto('/sources/import');
    await page.waitForLoadState('domcontentloaded');

    await expect(page.locator('text=/bibtex|bib/i').first()).toBeVisible({ timeout: 5000 });
  });

  test('should support RIS format selection', async ({ page }) => {
    await page.goto('/sources/import');
    await page.waitForLoadState('domcontentloaded');

    await expect(page.locator('text=/ris/i').first()).toBeVisible({ timeout: 5000 });
  });

  test('should support JSON format selection', async ({ page }) => {
    await page.goto('/sources/import');
    await page.waitForLoadState('domcontentloaded');

    await expect(page.locator('text=/json/i').first()).toBeVisible({ timeout: 5000 });
  });

  test('should preview a valid JSON file before committing', async ({ page }) => {
    await page.goto('/sources/import');
    await page.waitForLoadState('domcontentloaded');

    // Switch to JSON format
    await page.getByRole('button', { name: /json/i }).click();

    const prefix = Date.now();
    const jsonContent = JSON.stringify([
      { title: `${prefix} Import Source A`, kind: 'journal_article', year: 2023, url: `https://example.com/${prefix}-a` },
    ]);

    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles({
      name: 'sources.json',
      mimeType: 'application/json',
      buffer: Buffer.from(jsonContent),
    });

    const previewButton = page.getByRole('button', { name: /preview/i });
    await expect(previewButton).toBeEnabled({ timeout: 5000 });
    await previewButton.click();

    // Should show preview table
    await expect(page.locator('table, [role="table"]').first()).toBeVisible({ timeout: 10000 });
  });

  test('should show done summary after successful import', async ({ page }) => {
    await page.goto('/sources/import');
    await page.waitForLoadState('domcontentloaded');

    // Switch to JSON format
    await page.getByRole('button', { name: /json/i }).click();

    const prefix = Date.now();
    const jsonContent = JSON.stringify([
      { title: `${prefix} Done Summary Source`, kind: 'journal_article', year: 2022, url: `https://example.com/${prefix}-done` },
    ]);

    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles({
      name: 'sources.json',
      mimeType: 'application/json',
      buffer: Buffer.from(jsonContent),
    });

    const previewButton = page.getByRole('button', { name: /preview/i });
    await expect(previewButton).toBeEnabled({ timeout: 5000 });
    await previewButton.click();

    const importButton = page.getByRole('button', { name: /^import|^commit/i });
    await expect(importButton).toBeVisible({ timeout: 10000 });
    await importButton.click();

    // Done summary should appear
    await expect(page.locator('text=/done|created|imported|summary/i').first()).toBeVisible({ timeout: 10000 });
  });
});
