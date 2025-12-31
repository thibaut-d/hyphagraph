import { defineConfig, devices } from '@playwright/test';
import * as dotenv from 'dotenv';
import * as path from 'path';

// Load environment variables from .env file
dotenv.config({ path: path.resolve(__dirname, '.env') });

/**
 * Playwright E2E Test Configuration for Hyphagraph
 *
 * Strategy:
 * - Fresh database per test suite for isolation
 * - API-based seeding for realistic data
 * - On-demand execution (not CI/CD yet)
 * - Parallel execution enabled
 * - Screenshots/videos on failure
 * - English only (no i18n testing)
 */
export default defineConfig({
  // Test directory
  testDir: './tests',

  // Timeout settings
  timeout: 30 * 1000, // 30 seconds per test
  expect: {
    timeout: 5 * 1000, // 5 seconds for assertions
  },

  // Test execution
  fullyParallel: true, // Run tests in parallel
  forbidOnly: !!process.env.CI, // Prevent .only in CI
  retries: process.env.CI ? 2 : 0, // Retry on CI only
  workers: process.env.CI ? 1 : undefined, // Parallel workers (auto-detect locally)

  // Reporter configuration
  reporter: [
    ['html', { outputFolder: 'playwright-report' }],
    ['list'], // Console output
    ['json', { outputFile: 'test-results.json' }]
  ],

  // Shared settings for all tests
  use: {
    // Base URL for the application (Caddy proxy on port 80)
    baseURL: process.env.BASE_URL || 'http://localhost',

    // API endpoint
    extraHTTPHeaders: {
      'Accept': 'application/json',
    },

    // Screenshots and videos
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    trace: 'retain-on-failure',

    // Timeouts
    actionTimeout: 10 * 1000, // 10 seconds for actions
    navigationTimeout: 30 * 1000, // 30 seconds for navigation
  },

  // Test output
  outputDir: 'test-results/',

  // Projects for different browsers
  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        viewport: { width: 1920, height: 1080 },
      },
    },
    // Uncomment for cross-browser testing
    // {
    //   name: 'firefox',
    //   use: { ...devices['Desktop Firefox'] },
    // },
    // {
    //   name: 'webkit',
    //   use: { ...devices['Desktop Safari'] },
    // },
  ],

  // Web server configuration (optional - start services automatically)
  // webServer: {
  //   command: 'docker-compose up',
  //   url: 'http://localhost:3000',
  //   timeout: 120 * 1000,
  //   reuseExistingServer: !process.env.CI,
  // },
});
