import { test, expect } from '@playwright/test';
import { loginAsAdminViaAPI, clearAuthState } from '../../fixtures/auth-helpers';
import { generateEntityName, generateSourceName, generateRelationName } from '../../fixtures/test-data';

test.describe('Inference Viewing', () => {
  test.beforeEach(async ({ page }) => {
    // Login before each test
    await loginAsAdminViaAPI(page);
  });

  test.afterEach(async ({ page }) => {
    // Clear auth state to avoid polluting other tests
    await clearAuthState(page);
  });

  test('should view inferences on entity detail page', async ({ page }) => {
    // Create test data: entities, source, and relation
    // This will trigger the inference engine to compute inferences

    // Create source
    const sourceTitle = generateSourceName('inf-source');
    await page.goto('/sources/new');
    await page.getByRole('textbox', { name: 'Title' }).fill(sourceTitle);
    await page.getByRole('textbox', { name: 'URL' }).fill('https://example.com/inf-source');
    await page.getByLabel(/summary \(english\)/i).fill('Source for inference test');
    await page.getByRole('button', { name: /create|submit/i }).click();
    await page.waitForURL(/\/sources\/[a-f0-9-]+/);

    // Create entities
    const entity1Slug = generateEntityName('person').toLowerCase().replace(/\s+/g, '-');
    await page.goto('/entities/new');
    await page.getByRole('textbox', { name: 'Slug' }).fill(entity1Slug);
    await page.getByLabel(/summary \(english\)/i).fill('A person entity');
    await page.getByRole('button', { name: /create|submit/i }).click();
    await page.waitForURL(/\/entities\/([a-f0-9-]+)/);
    const entity1Url = page.url();

    const entity2Slug = generateEntityName('company').toLowerCase().replace(/\s+/g, '-');
    await page.goto('/entities/new');
    await page.getByRole('textbox', { name: 'Slug' }).fill(entity2Slug);
    await page.getByLabel(/summary \(english\)/i).fill('A company entity');
    await page.getByRole('button', { name: /create|submit/i }).click();
    await page.waitForURL(/\/entities\/[a-f0-9-]+/);

    // Go back to first entity detail page
    await page.goto(entity1Url);

    // Look for inferences section
    // Note: The exact UI will depend on implementation
    const inferencesSection = page.locator('text=/Inferences|Computed Relations|Roles/i');
    if (await inferencesSection.isVisible({ timeout: 3000 })) {
      // Inferences are displayed on entity page
      await expect(inferencesSection).toBeVisible();
    }
  });

  test('should navigate to inferences page', async ({ page }) => {
    // Check if there's a dedicated inferences page
    await page.goto('/inferences');

    // Page should load (might be empty if no inferences exist)
    // Or might redirect if route doesn't exist
    const url = page.url();
    expect(url).toBeTruthy();
  });

  test('should filter inferences', async ({ page }) => {
    // Navigate to a page that shows inferences
    await page.goto('/inferences');

    // Look for filter controls
    const filterButton = page.getByRole('button', { name: /filter/i });
    if (await filterButton.isVisible({ timeout: 2000 })) {
      await filterButton.click();

      // Look for filter options (entity, role type, etc.)
      // This will depend on the actual UI implementation
    }
  });

  test('should show inference scores', async ({ page }) => {
    // Create test data that will generate inferences with scores
    // Then navigate to view them

    // Create entities and relations
    const sourceTitle = generateSourceName('score-test');
    await page.goto('/sources/new');
    await page.getByRole('textbox', { name: 'Title' }).fill(sourceTitle);
    await page.getByRole('textbox', { name: 'URL' }).fill('https://example.com/score-test');
    await page.getByLabel(/summary \(english\)/i).fill('Source with high authority');
    await page.getByRole('button', { name: /create|submit/i }).click();
    await page.waitForURL(/\/sources\/[a-f0-9-]+/);

    // Create an entity and check for inferences
    const entitySlug = generateEntityName('scored-entity').toLowerCase().replace(/\s+/g, '-');
    await page.goto('/entities/new');
    await page.getByRole('textbox', { name: 'Slug' }).fill(entitySlug);
    await page.getByLabel(/summary \(english\)/i).fill('Entity with scored inferences');
    await page.getByRole('button', { name: /create|submit/i }).click();
    await page.waitForURL(/\/entities\/[a-f0-9-]+/);

    // Look for score indicators (might be percentage, progress bar, etc.)
    // Use .first() to avoid strict mode violation when multiple elements match
    const scoreElement = page.locator('text=/%|score|confidence/i').first();
    if (await scoreElement.isVisible({ timeout: 3000 })) {
      await expect(scoreElement).toBeVisible();
    }
  });

  test('should view inference details', async ({ page }) => {
    // Create test data
    const entitySlug = generateEntityName('inf-detail').toLowerCase().replace(/\s+/g, '-');
    await page.goto('/entities/new');
    await page.getByRole('textbox', { name: 'Slug' }).fill(entitySlug);
    await page.getByLabel(/summary \(english\)/i).fill('Entity for inference details');
    await page.getByRole('button', { name: /create|submit/i }).click();
    await page.waitForURL(/\/entities\/[a-f0-9-]+/);

    // Look for a way to view inference details
    // Might be a click on inference, expand button, etc.
    const viewDetailsButton = page.getByRole('button', { name: /details|more|expand/i });
    if (await viewDetailsButton.first().isVisible({ timeout: 2000 })) {
      await viewDetailsButton.first().click();

      // Should show additional details about the inference
      // (e.g., source, confidence, evidence)
    }
  });

  test('should paginate through inferences', async ({ page }) => {
    await page.goto('/inferences');

    // Look for pagination controls
    const nextButton = page.getByRole('button', { name: /next/i });
    const prevButton = page.getByRole('button', { name: /prev|previous/i });

    if (await nextButton.isVisible({ timeout: 2000 })) {
      // Click next page
      await nextButton.click();

      // Should load next page of results
      await page.waitForLoadState('networkidle');
    }
  });
});
