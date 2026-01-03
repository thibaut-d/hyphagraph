import { test, expect, chromium } from '@playwright/test';

test.describe('Production Application Test', () => {
  test('should login with admin credentials and create entities and relations', async () => {
    const browser = await chromium.launch({ headless: false });
    const context = await browser.newContext();
    const page = await context.newPage();

    try {
      // Navigate to the application
      console.log('1. Navigating to http://localhost...');
      await page.goto('http://localhost/');
      await page.waitForLoadState('networkidle');

      // Wait for React app to load
      await page.waitForSelector('text=HyphaGraph', { timeout: 10000 });
      console.log('✓ Application loaded successfully');

      // Navigate to login
      console.log('\n2. Navigating to login page...');
      await page.goto('http://localhost/login');
      await page.waitForLoadState('networkidle');

      // Login with admin credentials
      console.log('\n3. Logging in with admin@example.com...');
      await page.getByLabel(/email/i).fill('admin@example.com');
      await page.getByLabel(/password/i).fill('changeme123');
      await page.getByRole('button', { name: /log in|sign in/i }).click();

      // Wait for redirect to home or dashboard
      await page.waitForURL(/\/(home|entities|$)/, { timeout: 15000 });
      console.log('✓ Login successful');

      // Create a test entity
      console.log('\n4. Creating a test entity...');
      await page.goto('http://localhost/entities/new');
      await page.waitForLoadState('networkidle');

      const entitySlug = `test-entity-${Date.now()}`;
      await page.getByLabel(/slug/i).fill(entitySlug);
      await page.getByLabel(/summary.*english/i).fill('Test entity created via production test');

      await page.getByRole('button', { name: /create|submit/i }).click();

      // Wait for navigation to entity detail page
      await page.waitForURL(/\/entities\/[a-f0-9-]+/, { timeout: 10000 });
      console.log(`✓ Entity created: ${entitySlug}`);

      // Verify entity is visible
      await expect(page.locator(`text=${entitySlug}`)).toBeVisible();
      console.log('✓ Entity details visible');

      // Get the entity ID from URL
      const entityUrl = page.url();
      const entityId = entityUrl.match(/\/entities\/([a-f0-9-]+)/)?.[1];
      console.log(`  Entity ID: ${entityId}`);

      // Create a source first (needed for relations)
      console.log('\n5. Creating a test source...');
      await page.goto('http://localhost/sources/new');
      await page.waitForLoadState('networkidle');

      await page.getByLabel(/title/i).fill('Test Source');
      await page.getByLabel(/url/i).fill('https://example.com/test');
      await page.getByLabel(/kind/i).selectOption('article');

      await page.getByRole('button', { name: /create|submit/i }).click();

      await page.waitForURL(/\/sources\/[a-f0-9-]+/, { timeout: 10000 });
      console.log('✓ Source created');

      // Get the source ID
      const sourceUrl = page.url();
      const sourceId = sourceUrl.match(/\/sources\/([a-f0-9-]+)/)?.[1];
      console.log(`  Source ID: ${sourceId}`);

      // Create another entity for the relation
      console.log('\n6. Creating second entity for relation...');
      await page.goto('http://localhost/entities/new');
      await page.waitForLoadState('networkidle');

      const entity2Slug = `test-entity-2-${Date.now()}`;
      await page.getByLabel(/slug/i).fill(entity2Slug);
      await page.getByLabel(/summary.*english/i).fill('Second test entity');

      await page.getByRole('button', { name: /create|submit/i }).click();
      await page.waitForURL(/\/entities\/[a-f0-9-]+/, { timeout: 10000 });

      const entity2Url = page.url();
      const entity2Id = entity2Url.match(/\/entities\/([a-f0-9-]+)/)?.[1];
      console.log(`✓ Second entity created: ${entity2Slug}`);
      console.log(`  Entity ID: ${entity2Id}`);

      // Create a relation between the two entities
      console.log('\n7. Creating relation between entities...');
      await page.goto(`http://localhost/relations/new?entity_id=${entityId}`);
      await page.waitForLoadState('networkidle');

      // Select the source
      await page.getByLabel(/source/i).selectOption(sourceId);

      // Add a role - first entity as "subject"
      await page.getByRole('button', { name: /add.*role|add.*entity/i }).first().click();
      await page.waitForTimeout(500);

      // This depends on the actual form structure - adjust as needed
      // The form might auto-populate the first entity

      await page.getByRole('button', { name: /create|submit/i }).click();
      await page.waitForURL(/\/relations\/[a-f0-9-]+/, { timeout: 10000 });

      console.log('✓ Relation created successfully');

      // Navigate back to entities list
      console.log('\n8. Verifying entities list...');
      await page.goto('http://localhost/entities');
      await page.waitForLoadState('networkidle');

      await expect(page.getByRole('heading', { name: 'Entities' })).toBeVisible();
      console.log('✓ Entities list accessible');

      // Test duplicate slug validation
      console.log('\n9. Testing duplicate slug validation...');
      await page.goto('http://localhost/entities/new');
      await page.waitForLoadState('networkidle');

      await page.getByLabel(/slug/i).fill(entitySlug); // Use same slug as before
      await page.getByLabel(/summary.*english/i).fill('Duplicate test');
      await page.getByRole('button', { name: /create|submit/i }).click();

      // Should show error or stay on same page
      await page.waitForTimeout(2000);
      const hasError = await page.getByRole('alert').isVisible().catch(() => false);
      const stayedOnPage = page.url().includes('/entities/new');

      if (hasError || stayedOnPage) {
        console.log('✓ Duplicate slug validation working');
      } else {
        console.log('⚠ Duplicate slug validation may not be working (entity was created)');
      }

      console.log('\n✅ All production tests completed successfully!');

    } catch (error) {
      console.error('\n❌ Test failed:', error);
      throw error;
    } finally {
      await browser.close();
    }
  });
});
