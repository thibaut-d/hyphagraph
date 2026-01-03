const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: false, slowMo: 500 });
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

    // Navigate to account page (where login form is)
    console.log('\n2. Navigating to account page...');
    await page.goto('http://localhost/account');
    await page.waitForLoadState('networkidle');

    // Login with admin credentials
    console.log('\n3. Logging in with admin@example.com...');
    const emailField = page.getByRole('textbox', { name: /email/i });
    const passwordField = page.getByLabel(/password/i);
    const loginButton = page.getByRole('button', { name: /login/i });

    await emailField.waitFor({ state: 'visible', timeout: 10000 });
    await passwordField.waitFor({ state: 'visible', timeout: 10000 });

    await emailField.fill('admin@example.com');
    await passwordField.fill('changeme123');
    await page.waitForTimeout(500);
    await loginButton.click();

    // Wait for successful login - check for auth token in localStorage
    await page.waitForFunction(
      () => !!localStorage.getItem('auth_token'),
      { timeout: 20000 }
    );
    console.log('✓ Login successful');
    console.log(`  Current URL after login: ${page.url()}`);

    // Wait a moment for any redirects to complete
    await page.waitForTimeout(2000);

    // Create a test entity
    console.log('\n4. Creating a test entity...');
    await page.goto('http://localhost/entities/new');
    await page.waitForLoadState('networkidle');

    // Wait for form to load and debug what's on the page
    console.log(`  Current URL: ${page.url()}`);

    try {
      await page.getByRole('heading', { name: /create entity/i }).waitFor({ state: 'visible', timeout: 10000 });
    } catch (e) {
      console.log('  Failed to find "Create Entity" heading, checking what headings exist...');
      const headings = await page.locator('h1, h2, h3, h4, h5, h6').allTextContents();
      console.log(`  Found headings: ${JSON.stringify(headings)}`);
      throw e;
    }

    const entitySlug = `test-entity-${Date.now()}`;
    await page.getByLabel(/slug/i).fill(entitySlug);
    await page.getByLabel(/summary.*english/i).fill('Test entity created via production test');

    await page.getByRole('button', { name: /create|submit/i }).click();

    // Wait for navigation to entity detail page
    await page.waitForURL(/\/entities\/[a-f0-9-]+/, { timeout: 10000 });
    console.log(`✓ Entity created: ${entitySlug}`);

    // Verify entity is visible
    const entityVisible = await page.locator(`text=${entitySlug}`).isVisible();
    if (entityVisible) {
      console.log('✓ Entity details visible');
    }

    // Get the entity ID from URL
    const entityUrl = page.url();
    const entityId = entityUrl.match(/\/entities\/([a-f0-9-]+)/)?.[1];
    console.log(`  Entity ID: ${entityId}`);

    // Create a source first (needed for relations)
    console.log('\n5. Creating a test source...');
    await page.goto('http://localhost/sources/new');
    await page.waitForLoadState('networkidle');

    // Wait for form to load
    await page.getByRole('heading', { name: /create source/i }).waitFor({ state: 'visible', timeout: 10000 });

    await page.getByLabel(/title/i).fill('Test Source');
    await page.getByLabel(/url/i).fill('https://example.com/test');

    // Try to select kind if available
    try {
      await page.getByLabel(/kind/i).selectOption('article');
    } catch (e) {
      console.log('  Kind field not found or already set');
    }

    await page.getByRole('button', { name: /create|submit/i }).click();

    await page.waitForURL(/\/sources\/[a-f0-9-]+/, { timeout: 10000 });
    console.log('✓ Source created');

    // Get the source ID
    const sourceUrl = page.url();
    const sourceId = sourceUrl.match(/\/sources\/([a-f0-9-]+)/)?.[1];
    console.log(`  Source ID: ${sourceId}`);

    // Navigate back to entities list
    console.log('\n6. Verifying entities list...');
    await page.goto('http://localhost/entities');
    await page.waitForLoadState('networkidle');

    const entitiesHeading = await page.getByRole('heading', { name: 'Entities' }).isVisible();
    if (entitiesHeading) {
      console.log('✓ Entities list accessible');
    }

    // Test duplicate slug validation
    console.log('\n7. Testing duplicate slug validation...');
    await page.goto('http://localhost/entities/new');
    await page.waitForLoadState('networkidle');

    await page.getByLabel(/slug/i).fill(entitySlug); // Use same slug as before
    await page.getByLabel(/summary.*english/i).fill('Duplicate test');
    await page.getByRole('button', { name: /create|submit/i }).click();

    // Wait a moment for response
    await page.waitForTimeout(3000);

    const hasError = await page.getByRole('alert').isVisible().catch(() => false);
    const stayedOnPage = page.url().includes('/entities/new');

    if (hasError) {
      console.log('✓ Duplicate slug validation working - error shown');
      const errorText = await page.getByRole('alert').textContent();
      console.log(`  Error message: ${errorText}`);
    } else if (stayedOnPage) {
      console.log('✓ Duplicate slug validation working - stayed on form');
    } else {
      console.log('⚠ Duplicate slug validation may not be working (entity was created)');
      console.log(`  Current URL: ${page.url()}`);
    }

    console.log('\n✅ All production tests completed successfully!');
    console.log('\nPress Ctrl+C to close the browser...');

    // Keep browser open for inspection
    await page.waitForTimeout(30000);

  } catch (error) {
    console.error('\n❌ Test failed:', error.message);
    console.error('Stack:', error.stack);
    throw error;
  } finally {
    await browser.close();
  }
})();
