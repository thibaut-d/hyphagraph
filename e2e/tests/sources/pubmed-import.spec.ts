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
    // Log network requests to debug
    page.on('request', request => {
      if (request.url().includes('pubmed')) {
        console.log('>>>', request.method(), request.url());
      }
    });
    page.on('response', response => {
      if (response.url().includes('pubmed')) {
        console.log('<<<', response.status(), response.url());
      }
    });

    await page.goto('/sources/import-pubmed');

    // Enter a simple query
    const searchInput = page.getByLabel(/search.*query.*or.*pubmed.*url/i);
    await searchInput.fill('aspirin');

    // Click search button
    await page.getByRole('button', { name: /search.*pubmed/i }).click();

    // Wait for results table to appear (may take a few seconds due to API)
    await expect(page.getByRole('heading', { name: /search.*results/i })).toBeVisible({ timeout: 15000 });
    await expect(page.getByRole('table')).toBeVisible();

    // Should show result metadata (authors, journal columns)
    await expect(page.getByRole('columnheader', { name: /article/i })).toBeVisible();
    await expect(page.getByRole('columnheader', { name: /authors/i })).toBeVisible();
  });

  test('should allow selecting/deselecting articles', async ({ page }) => {
    await page.goto('/sources/import-pubmed');

    // Search for articles
    const searchInput = page.getByLabel(/search.*query.*or.*pubmed.*url/i);
    await searchInput.fill('vitamin D');
    await page.getByRole('button', { name: /search.*pubmed/i }).click();

    // Wait for results
    await expect(page.getByRole('table')).toBeVisible({ timeout: 15000 });

    // Get checkboxes in table body (skip header checkbox)
    const checkboxes = page.getByRole('checkbox');
    const secondCheckbox = checkboxes.nth(1); // First checkbox after "select all"

    // Should be checked by default (auto-select all)
    await expect(secondCheckbox).toBeChecked();

    // Uncheck it
    await secondCheckbox.click();
    await expect(secondCheckbox).not.toBeChecked();

    // Check it again
    await secondCheckbox.click();
    await expect(secondCheckbox).toBeChecked();
  });

  test('should import selected articles and create sources', async ({ page }) => {
    await page.goto('/sources/import-pubmed');

    // Search for a specific query with limited results
    const searchInput = page.getByLabel(/search.*query.*or.*pubmed.*url/i);
    await searchInput.fill('COVID-19 vaccine');
    await page.getByRole('button', { name: /search.*pubmed/i }).click();

    // Wait for results
    await expect(page.getByRole('table')).toBeVisible({ timeout: 15000 });

    // Should have at least one result selected and import button visible
    const importButton = page.getByRole('button', { name: /import.*article/i });
    await expect(importButton).toBeVisible();
    await expect(importButton).toBeEnabled();

    // Click import button
    await importButton.click();

    // Should navigate back to sources list after successful import
    await expect(page).toHaveURL('/sources', { timeout: 30000 });
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

    // Paste a PubMed search URL
    const searchInput = page.getByLabel(/search.*query.*or.*pubmed.*url/i);
    await searchInput.fill('https://pubmed.ncbi.nlm.nih.gov/?term=diabetes&filter=years.2023-2024');

    // Click search button
    await page.getByRole('button', { name: /search.*pubmed/i }).click();

    // Should extract query from URL and show results
    await expect(page.getByRole('table')).toBeVisible({ timeout: 15000 });
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

    // Search for articles
    const searchInput = page.getByLabel(/search.*query.*or.*pubmed.*url/i);
    await searchInput.fill('cancer treatment');
    await page.getByRole('button', { name: /search.*pubmed/i }).click();

    // Wait for results table
    await expect(page.getByRole('table')).toBeVisible({ timeout: 15000 });

    // Check table headers - the first column is checkbox, second is "Article"
    await expect(page.getByRole('columnheader', { name: /article/i })).toBeVisible();
    await expect(page.getByRole('columnheader', { name: /authors/i })).toBeVisible();
    await expect(page.getByRole('columnheader', { name: /journal/i })).toBeVisible();
    await expect(page.getByRole('columnheader', { name: /year/i })).toBeVisible();
    await expect(page.getByRole('columnheader', { name: /pmid/i })).toBeVisible();

    // Should show actual data in cells
    const cells = page.getByRole('cell');
    await expect(cells.first()).toBeVisible();
  });

  test('should show import button disabled when no articles selected', async ({ page }) => {
    await page.goto('/sources/import-pubmed');

    // Search for articles
    const searchInput = page.getByLabel(/search.*query.*or.*pubmed.*url/i);
    await searchInput.fill('medicine');
    await page.getByRole('button', { name: /search.*pubmed/i }).click();

    // Wait for results
    await expect(page.getByRole('table')).toBeVisible({ timeout: 15000 });

    // Click the "select all" checkbox to uncheck all
    const selectAllCheckbox = page.getByRole('checkbox').first();
    if (await selectAllCheckbox.isChecked()) {
      await selectAllCheckbox.click();
    }

    // Import button should be disabled
    const importButton = page.getByRole('button', { name: /import.*article/i });
    await expect(importButton).toBeDisabled();
  });
});
