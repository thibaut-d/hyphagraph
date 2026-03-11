/**
 * Test setup file for Vitest.
 *
 * This file is executed before all tests to set up the testing environment.
 */
import '@testing-library/jest-dom';
import { vi } from 'vitest';

const stableTranslate = (key: string, defaultValue?: string) => defaultValue || key;

// Mock localStorage for tests
const localStorageMock = (() => {
  let store: Record<string, string> = {};

  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => {
      store[key] = value;
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    },
  };
})();

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
});

// Mock i18next to return the default value (second parameter) from t() calls
// This allows components to render with English text in tests
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: stableTranslate,
    i18n: {
      changeLanguage: () => Promise.resolve(),
      language: 'en',
    },
  }),
  initReactI18next: {
    type: '3rdParty',
    init: () => {},
  },
}));
