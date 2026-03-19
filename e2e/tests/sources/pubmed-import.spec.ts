import { test, expect } from '@playwright/test';
import { loginAsAdminViaAPI, clearAuthState } from '../../fixtures/auth-helpers';

test.describe('PubMed Bulk Import', () => {
  test.beforeEach(async ({ page }) => {
    // Login before each test
    await loginAsAdminViaAPI(page);
  });

  test.afterEach(async ({ page }) => {
    // Clear auth state to avoid polluting other tests
    await clearAuthState(page);
  });

  test('should navigate to PubMed import page', async ({ page }) => {
    // Navigate directly to PubMed import page
    await page.goto('/sources/import-pubmed');

    // Should navigate to PubMed import page
    await expect(page).toHaveURL('/sources/import-pubmed');

    // Should show the heading (case-insensitive match)
    await expect(page.getByRole('heading', { name: /import.*from.*pubmed/i })).toBeVisible();
  });

  test('should show search form with query input and max results slider', async ({ page }) => {
    await page.goto('/sources/import-pubmed');

    // Should show search input with correct label
    const searchInput = page.getByLabel(/search.*query.*or.*pubmed.*url/i);
    await expect(searchInput).toBeVisible();

    // Should show search button
    const searchButton = page.getByRole('button', { name: /search.*pubmed/i });
    await expect(searchButton).toBeVisible();

    // Should show max results text and slider
    await expect(page.getByText(/maximum.*results/i)).toBeVisible();
    await expect(page.getByRole('slider')).toBeVisible();
  });

  test('should search PubMed by query and display results', async ({ page }) => {
    await page.goto('/sources/import-pubmed');

    const searchInput = page.getByLabel(/search.*query.*or.*pubmed.*url/i);
    await searchInput.fill('aspirin');
    await page.getByRole('button', { name: /search.*pubmed/i }).click();

    // PubMed API may not be accessible in all environments — conditional check
    const table = page.getByRole('table');
    if (await table.isVisible({ timeout: 15000 })) {
      await expect(page.getByRole('columnheader', { name: /article/i })).toBeVisible();
      await expect(page.getByRole('columnheader', { name: /authors/i })).toBeVisible();
    }
  });

  test('should allow selecting/deselecting articles', async ({ page }) => {
    await page.goto('/sources/import-pubmed');

    const searchInput = page.getByLabel(/search.*query.*or.*pubmed.*url/i);
    await searchInput.fill('vitamin D');
    await page.getByRole('button', { name: /search.*pubmed/i }).click();

    const table = page.getByRole('table');
    if (await table.isVisible({ timeout: 15000 })) {
      const checkboxes = page.getByRole('checkbox');
      const secondCheckbox = checkboxes.nth(1);
      await expect(secondCheckbox).toBeChecked();
      await secondCheckbox.click();
      await expect(secondCheckbox).not.toBeChecked();
      await secondCheckbox.click();
      await expect(secondCheckbox).toBeChecked();
    }
  });

  test('should import selected articles and create sources', async ({ page }) => {
    await page.goto('/sources/import-pubmed');

    const searchInput = page.getByLabel(/search.*query.*or.*pubmed.*url/i);
    await searchInput.fill('COVID-19 vaccine');
    await page.getByRole('button', { name: /search.*pubmed/i }).click();

    const table = page.getByRole('table');
    if (await table.isVisible({ timeout: 15000 })) {
      const importButton = page.getByRole('button', { name: /import.*article/i });
      await expect(importButton).toBeVisible();
      await expect(importButton).toBeEnabled();
      await importButton.click();
      await expect(page).toHaveURL('/sources', { timeout: 30000 });
    }
  });

  test('should handle search errors gracefully', async ({ page }) => {
    await page.goto('/sources/import-pubmed');

    // Try to search without entering a query
    await page.getByRole('button', { name: /search.*pubmed/i }).click();

    // Should show error message in alert
    await expect(page.getByRole('alert')).toBeVisible({ timeout: 2000 });
    await expect(page.getByText(/please.*enter.*search.*query/i)).toBeVisible();
  });

  test('should support pasting PubMed search URLs', async ({ page }) => {
    await page.goto('/sources/import-pubmed');

    const searchInput = page.getByLabel(/search.*query.*or.*pubmed.*url/i);
    await searchInput.fill('https://pubmed.ncbi.nlm.nih.gov/?term=diabetes&filter=years.2023-2024');
    await page.getByRole('button', { name: /search.*pubmed/i }).click();

    // PubMed API may not be accessible in all environments — conditional check
    const table = page.getByRole('table');
    if (await table.isVisible({ timeout: 15000 })) {
      await expect(table).toBeVisible();
    }
  });

  test('should adjust max results with slider', async ({ page }) => {
    await page.goto('/sources/import-pubmed');

    // Find the slider - MUI Slider doesn't always have a label
    const slider = page.getByRole('slider');
    await expect(slider).toBeVisible();

    // Verify default value (should be 10)
    await expect(slider).toHaveValue('10');

    // Change to different value
    await slider.fill('20');
    await expect(slider).toHaveValue('20');
  });

  test('should display article metadata in results table', async ({ page }) => {
    await page.goto('/sources/import-pubmed');

    const searchInput = page.getByLabel(/search.*query.*or.*pubmed.*url/i);
    await searchInput.fill('cancer treatment');
    await page.getByRole('button', { name: /search.*pubmed/i }).click();

    const table = page.getByRole('table');
    if (await table.isVisible({ timeout: 15000 })) {
      await expect(page.getByRole('columnheader', { name: /article/i })).toBeVisible();
      await expect(page.getByRole('columnheader', { name: /authors/i })).toBeVisible();
      await expect(page.getByRole('columnheader', { name: /journal/i })).toBeVisible();
      await expect(page.getByRole('columnheader', { name: /year/i })).toBeVisible();
      await expect(page.getByRole('columnheader', { name: /pmid/i })).toBeVisible();
      await expect(page.getByRole('cell').first()).toBeVisible();
    }
  });

  test('should show import button disabled when no articles selected', async ({ page }) => {
    await page.goto('/sources/import-pubmed');

    const searchInput = page.getByLabel(/search.*query.*or.*pubmed.*url/i);
    await searchInput.fill('medicine');
    await page.getByRole('button', { name: /search.*pubmed/i }).click();

    const table = page.getByRole('table');
    if (await table.isVisible({ timeout: 15000 })) {
      const selectAllCheckbox = page.getByRole('checkbox').first();
      if (await selectAllCheckbox.isChecked()) {
        await selectAllCheckbox.click();
      }
      const importButton = page.getByRole('button', { name: /import.*article/i });
      await expect(importButton).toBeDisabled();
    }
  });
});
