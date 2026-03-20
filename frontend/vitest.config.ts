/**
 * Vitest configuration for frontend tests.
 *
 * To run tests:
 *   npm install -D vitest @vitest/ui jsdom
 *   npm run test
 *
 * To run tests with UI:
 *   npm run test:ui
 */
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      'react-router-dom': 'react-router'
    }
  },
  test: {
    // Test environment (jsdom for React component testing)
    environment: 'jsdom',

    // Global test setup files
    setupFiles: ['./src/test/setup.ts'],

    // Test file patterns
    include: ['**/*.{test,spec}.{ts,tsx}'],
    exclude: ['node_modules', 'dist', 'build', '.idea', '.git', '.cache'],

    // Coverage configuration
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      include: ['src/**/*.{ts,tsx}'],
      exclude: [
        'src/**/*.test.{ts,tsx}',
        'src/**/*.spec.{ts,tsx}',
        'src/main.tsx',
        'src/vite-env.d.ts',
      ],
    },

    // Globals (makes describe, it, expect available without imports)
    globals: true,

    // Output options
    reporters: ['verbose'],

    // Test timeout — increased for MUI-heavy component tests under full-suite load
    testTimeout: 15000,

    // Mock configuration
    mockReset: true,
    clearMocks: true,
    restoreMocks: true,

    // Limit worker parallelism to prevent runaway memory usage.
    // forks pool is required for jsdom; cap to 2 workers max.
    // Vitest 4: poolOptions removed — pool config is now top-level.
    pool: 'forks',
    maxWorkers: 2,
    // Cap each worker's V8 heap to 1 GB
    execArgv: ['--max-old-space-size=1024'],
  },
});
