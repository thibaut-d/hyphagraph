/**
 * Test Data Fixtures for E2E Tests
 *
 * Provides reusable test data for different scenarios
 */

// Default admin credentials (created by backend startup)
export const ADMIN_USER = {
  email: 'admin@example.com',
  password: 'changeme123',
};

// Test users
export const TEST_USERS = {
  regularUser: {
    email: 'testuser@example.com',
    password: 'TestPassword123!',
  },
  anotherUser: {
    email: 'another@example.com',
    password: 'AnotherPassword123!',
  },
};

// Test entities
export const TEST_ENTITIES = {
  person: {
    name: 'John Doe',
    description: 'A test person entity',
  },
  organization: {
    name: 'ACME Corporation',
    description: 'A test organization entity',
  },
  location: {
    name: 'New York City',
    description: 'A test location entity',
  },
};

// Test sources
export const TEST_SOURCES = {
  website: {
    name: 'Test Website',
    url: 'https://example.com',
    description: 'A test website source',
  },
  document: {
    name: 'Test Document',
    description: 'A test document source',
  },
};

// Test relations
export const TEST_RELATIONS = {
  employment: {
    name: 'Works For',
    description: 'Employment relationship',
    roles: [
      { name: 'Employee', entity_id: '' }, // Will be filled in tests
      { name: 'Employer', entity_id: '' },
    ],
  },
  location: {
    name: 'Located In',
    description: 'Location relationship',
    roles: [
      { name: 'Subject', entity_id: '' },
      { name: 'Location', entity_id: '' },
    ],
  },
};

/**
 * Generate a unique email for testing
 */
export function generateTestEmail(): string {
  const timestamp = Date.now();
  const random = Math.random().toString(36).substring(7);
  return `test-${timestamp}-${random}@example.com`;
}

/**
 * Generate a unique entity name for testing
 */
export function generateEntityName(prefix: string = 'Entity'): string {
  const timestamp = Date.now();
  return `${prefix} ${timestamp}`;
}

/**
 * Generate a unique source name for testing
 */
export function generateSourceName(prefix: string = 'Source'): string {
  const timestamp = Date.now();
  return `${prefix} ${timestamp}`;
}

/**
 * Generate a unique relation name for testing
 */
export function generateRelationName(prefix: string = 'Relation'): string {
  const timestamp = Date.now();
  return `${prefix} ${timestamp}`;
}
