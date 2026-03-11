/**
 * Global Setup for E2E Tests
 *
 * Runs once before all tests
 */

import { FullConfig } from '@playwright/test';
import { resetDatabase } from './utils/db-setup';
import { ADMIN_USER } from './fixtures/test-data';

const API_URL = process.env.API_URL || 'http://localhost:8001';

async function globalSetup(config: FullConfig) {
  console.log('🧹 Running global setup: cleaning test database...');

  try {
    // Reset to a known baseline and re-run startup bootstrap.
    await resetDatabase();

    // Verify the admin bootstrap is available after reset.
    const response = await fetch(`${API_URL}/api/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: new URLSearchParams({
        username: ADMIN_USER.email,
        password: ADMIN_USER.password,
      }),
    });

    if (!response.ok) {
      throw new Error(`Admin bootstrap login failed: ${response.status}`);
    }

    console.log('✅ Global setup complete: database is clean');
  } catch (error) {
    console.error('❌ Global setup failed:', error);
    throw error;
  }
}

export default globalSetup;
