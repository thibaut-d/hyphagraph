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
  test: {
    // Test environment (jsdom for React component testing)
    environment: 'jsdom',

    // Global test setup files
    // setupFiles: ['./src/test/setup.ts'],

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

    // Mock configuration
    mockReset: true,
    clearMocks: true,
    restoreMocks: true,
  },
});
