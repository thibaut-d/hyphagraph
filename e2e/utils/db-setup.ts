/**
 * Database Setup Utilities for E2E Tests
 *
 * Strategy: Fresh database per test suite using API-based seeding
 * - Realistic data flow through the application
 * - Tests actual API validation and business logic
 * - Ensures test isolation
 */

const API_URL = process.env.API_URL || 'http://localhost:8000';

async function waitForTestApi(maxAttempts: number = 30): Promise<void> {
  let lastError: unknown = null;

  for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
    try {
      const response = await fetch(`${API_URL}/api/test/health`);
      if (response.ok) {
        return;
      }

      lastError = new Error(`Test API health check returned ${response.status}`);
    } catch (error) {
      lastError = error;
    }

    await new Promise((resolve) => setTimeout(resolve, 1000));
  }

  throw lastError instanceof Error
    ? lastError
    : new Error('Timed out waiting for test API health endpoint');
}

/**
 * Reset the database to a clean state
 * This should be called before each test suite
 *
 * Uses the backend's test-only /api/test/reset-database endpoint
 * which truncates all tables (only available when TESTING=True)
 */
export async function resetDatabase(): Promise<void> {
  try {
    await waitForTestApi();

    let lastError: Error | null = null;

    for (let attempt = 1; attempt <= 5; attempt += 1) {
      try {
        const response = await fetch(`${API_URL}/api/test/reset-database`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
        });

        if (!response.ok) {
          const error = await response.text();
          throw new Error(`Failed to reset database: ${response.status} - ${error}`);
        }

        const result = await response.json();
        console.log(`Database reset: ${result.tables_truncated} tables truncated`);
        return;
      } catch (error) {
        lastError = error instanceof Error ? error : new Error(String(error));
        await new Promise((resolve) => setTimeout(resolve, 1000));
      }
    }

    throw lastError ?? new Error('Failed to reset database');
  } catch (error) {
    console.error('Database reset failed:', error);
    throw error;
  }
}

/**
 * Seed the database with initial test data
 * Creates a superuser admin account for testing
 */
export async function seedDatabase(): Promise<void> {
  // The backend already creates an admin user on startup
  // See backend/app/startup.py - create_admin_user()
  // Default credentials: admin@example.com / admin123

  console.log('Database seeded with admin user');
}

/**
 * Create a test user via the API
 */
export async function createTestUser(email: string, password: string, is_superuser: boolean = false): Promise<{ id: string; email: string; access_token: string }> {
  const response = await fetch(`${API_URL}/api/auth/register`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      email,
      password,
      is_superuser,
    }),
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Failed to create test user: ${error}`);
  }

  const user = await response.json();

  // Login to get access token
  const loginResponse = await fetch(`${API_URL}/api/auth/login`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: new URLSearchParams({
      username: email,
      password: password,
    }),
  });

  if (!loginResponse.ok) {
    throw new Error('Failed to login test user');
  }

  const { access_token } = await loginResponse.json();

  return {
    id: user.id,
    email: user.email,
    access_token,
  };
}

/**
 * Delete a user via the API
 */
export async function deleteTestUser(userId: string, accessToken: string): Promise<void> {
  const response = await fetch(`${API_URL}/api/users/${userId}`, {
    method: 'DELETE',
    headers: {
      'Authorization': `Bearer ${accessToken}`,
    },
  });

  if (!response.ok && response.status !== 404) {
    throw new Error('Failed to delete test user');
  }
}

/**
 * Clean up all test data created during a test
 * This should be called after each test
 *
 * For E2E tests, we rely on resetDatabase() between test suites
 * rather than cleaning up individual resources. This ensures:
 * - Complete isolation between test suites
 * - No leftover data from failed tests
 * - Simpler test logic (no tracking of created resources)
 *
 * Individual tests can clean up specific resources if needed,
 * but it's not required for test correctness.
 */
export async function cleanupTestData(): Promise<void> {
  // No-op: We reset the entire database between test suites
  // Individual tests can implement their own cleanup if needed
  console.log('Test data cleanup: relying on database reset between suites');
}
