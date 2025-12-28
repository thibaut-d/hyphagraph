/**
 * Database Setup Utilities for E2E Tests
 *
 * Strategy: Fresh database per test suite using API-based seeding
 * - Realistic data flow through the application
 * - Tests actual API validation and business logic
 * - Ensures test isolation
 */

const API_URL = process.env.API_URL || 'http://localhost:8000';

/**
 * Reset the database to a clean state
 * This should be called before each test suite
 */
export async function resetDatabase(): Promise<void> {
  // TODO: Implement database reset logic
  // Options:
  // 1. Call a test-only endpoint that truncates all tables
  // 2. Use direct PostgreSQL connection to drop/recreate tables
  // 3. Use Docker Compose to recreate the database container

  console.log('Database reset - to be implemented');
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
 */
export async function cleanupTestData(): Promise<void> {
  // TODO: Implement cleanup logic
  // Could track created resources and delete them
  // Or rely on database reset between test suites

  console.log('Test data cleanup - to be implemented');
}
