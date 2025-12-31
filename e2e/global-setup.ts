/**
 * Global Setup for E2E Tests
 *
 * Runs once before all tests
 */

import { chromium, FullConfig } from '@playwright/test';
import { loginAsAdminViaAPI } from './fixtures/auth-helpers';
import { cleanupAllTestData } from './fixtures/cleanup-helpers';

async function globalSetup(config: FullConfig) {
  console.log('🧹 Running global setup: cleaning test database...');

  const browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    // Login as admin
    await loginAsAdminViaAPI(page);

    // Clean up any leftover data from previous test runs
    await cleanupAllTestData(page);

    console.log('✅ Global setup complete: database is clean');
  } catch (error) {
    console.error('❌ Global setup failed:', error);
    throw error;
  } finally {
    await browser.close();
  }
}

export default globalSetup;
