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

// Test entities - Scientifically accurate fibromyalgia/chronic pain entities
export const TEST_ENTITIES = {
  medication1: {
    name: 'Pregabalin',
    description: 'FDA-approved anticonvulsant for fibromyalgia (2007), first-line treatment',
  },
  medication2: {
    name: 'Duloxetine',
    description: 'FDA-approved SNRI antidepressant for fibromyalgia',
  },
  condition: {
    name: 'Fibromyalgia',
    description: 'Chronic disorder characterized by widespread musculoskeletal pain, fatigue, and tenderness',
  },
  symptom: {
    name: 'Widespread Musculoskeletal Pain',
    description: 'Pain affecting muscles and bones across multiple body regions',
  },
  therapy: {
    name: 'Cognitive Behavioral Therapy',
    description: 'Psychological intervention addressing pain perception and coping',
  },
};

// Test sources - Clinical studies and guidelines
export const TEST_SOURCES = {
  guideline: {
    name: 'ACR 2016 Fibromyalgia Diagnostic Criteria',
    url: 'https://doi.org/10.1016/j.semarthrit.2016.08.012',
    description: 'American College of Rheumatology revised diagnostic criteria for fibromyalgia',
  },
  study: {
    name: 'Pregabalin FDA Approval Study',
    url: 'https://doi.org/10.1002/art.23968',
    description: 'Clinical trial supporting FDA approval of pregabalin for fibromyalgia treatment',
  },
  review: {
    name: 'Cochrane Review: Exercise for Fibromyalgia',
    url: 'https://doi.org/10.1002/14651858.CD003786.pub3',
    description: 'Systematic review of exercise interventions for fibromyalgia management',
  },
};

// Test relations - Medical relationships
export const TEST_RELATIONS = {
  treats: {
    name: 'Treats',
    description: 'Therapeutic intervention treats condition',
    roles: [
      { name: 'Intervention', entity_id: '' }, // Will be filled in tests
      { name: 'Condition', entity_id: '' },
    ],
  },
  causes: {
    name: 'Causes',
    description: 'Mechanism causes symptom',
    roles: [
      { name: 'Mechanism', entity_id: '' },
      { name: 'Symptom', entity_id: '' },
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
