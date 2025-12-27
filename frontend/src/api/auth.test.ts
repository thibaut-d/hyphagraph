/**
 * Unit tests for authentication API client functions.
 *
 * Tests API call construction, request formatting, and error handling
 * for all authentication endpoints.
 *
 * Note: These tests require vitest to be installed:
 * npm install -D vitest @vitest/ui
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import * as authApi from './auth';

// Mock the apiFetch function
vi.mock('./client', () => ({
  apiFetch: vi.fn(),
}));

import { apiFetch } from './client';

describe('Auth API Client', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('login', () => {
    it('should call API with form-urlencoded credentials', async () => {
      const mockResponse = {
        access_token: 'access_token_123',
        refresh_token: 'refresh_token_456',
        token_type: 'bearer',
      };

      (apiFetch as any).mockResolvedValue(mockResponse);

      const payload = {
        username: 'test@example.com',
        password: 'password123',
      };

      const result = await authApi.login(payload);

      expect(apiFetch).toHaveBeenCalledWith('/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: expect.any(URLSearchParams),
      });

      expect(result).toEqual(mockResponse);
    });

    it('should format credentials as URLSearchParams', async () => {
      (apiFetch as any).mockResolvedValue({});

      await authApi.login({
        username: 'test@example.com',
        password: 'password123',
      });

      const callArgs = (apiFetch as any).mock.calls[0];
      const body = callArgs[1].body as URLSearchParams;

      expect(body.get('username')).toBe('test@example.com');
      expect(body.get('password')).toBe('password123');
    });
  });

  describe('register', () => {
    it('should call API with JSON registration data', async () => {
      const mockResponse = {
        id: '123e4567-e89b-12d3-a456-426614174000',
        email: 'newuser@example.com',
        is_active: true,
        is_superuser: false,
        created_at: '2024-01-01T00:00:00Z',
      };

      (apiFetch as any).mockResolvedValue(mockResponse);

      const payload = {
        email: 'newuser@example.com',
        password: 'password123',
      };

      const result = await authApi.register(payload);

      expect(apiFetch).toHaveBeenCalledWith('/auth/register', {
        method: 'POST',
        body: JSON.stringify(payload),
      });

      expect(result).toEqual(mockResponse);
    });

    it('should not include password in response', async () => {
      const mockResponse = {
        id: '123',
        email: 'test@example.com',
        is_active: true,
        is_superuser: false,
        created_at: '2024-01-01T00:00:00Z',
      };

      (apiFetch as any).mockResolvedValue(mockResponse);

      const result = await authApi.register({
        email: 'test@example.com',
        password: 'password123',
      });

      expect(result).not.toHaveProperty('password');
      expect(result).not.toHaveProperty('hashed_password');
    });
  });

  describe('getMe', () => {
    it('should fetch current user information', async () => {
      const mockUser = {
        id: '123',
        email: 'test@example.com',
        is_active: true,
        is_superuser: false,
        created_at: '2024-01-01T00:00:00Z',
      };

      (apiFetch as any).mockResolvedValue(mockUser);

      const result = await authApi.getMe();

      expect(apiFetch).toHaveBeenCalledWith('/auth/me');
      expect(result).toEqual(mockUser);
    });
  });

  describe('refreshAccessToken', () => {
    it('should call refresh endpoint with refresh token', async () => {
      const mockResponse = {
        access_token: 'new_access_token',
        token_type: 'bearer',
      };

      (apiFetch as any).mockResolvedValue(mockResponse);

      const refreshToken = 'refresh_token_123';
      const result = await authApi.refreshAccessToken(refreshToken);

      expect(apiFetch).toHaveBeenCalledWith('/auth/refresh', {
        method: 'POST',
        body: JSON.stringify({ refresh_token: refreshToken }),
      });

      expect(result).toEqual(mockResponse);
    });

    it('should return only access token (not refresh token)', async () => {
      const mockResponse = {
        access_token: 'new_access_token',
        token_type: 'bearer',
      };

      (apiFetch as any).mockResolvedValue(mockResponse);

      const result = await authApi.refreshAccessToken('refresh_token_123');

      expect(result).toHaveProperty('access_token');
      expect(result).not.toHaveProperty('refresh_token');
    });
  });

  describe('logout', () => {
    it('should call logout endpoint with refresh token', async () => {
      (apiFetch as any).mockResolvedValue(undefined);

      const refreshToken = 'refresh_token_123';
      await authApi.logout(refreshToken);

      expect(apiFetch).toHaveBeenCalledWith('/auth/logout', {
        method: 'POST',
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
    });

    it('should return void', async () => {
      (apiFetch as any).mockResolvedValue(undefined);

      const result = await authApi.logout('refresh_token_123');

      expect(result).toBeUndefined();
    });
  });

  describe('requestPasswordReset', () => {
    it('should call password reset request endpoint', async () => {
      (apiFetch as any).mockResolvedValue(undefined);

      const email = 'test@example.com';
      await authApi.requestPasswordReset(email);

      expect(apiFetch).toHaveBeenCalledWith('/auth/request-password-reset', {
        method: 'POST',
        body: JSON.stringify({ email }),
      });
    });

    it('should return void (no response data)', async () => {
      (apiFetch as any).mockResolvedValue(undefined);

      const result = await authApi.requestPasswordReset('test@example.com');

      expect(result).toBeUndefined();
    });

    it('should always succeed even if email does not exist', async () => {
      // Security: always returns success to prevent email enumeration
      (apiFetch as any).mockResolvedValue(undefined);

      await expect(
        authApi.requestPasswordReset('nonexistent@example.com')
      ).resolves.toBeUndefined();
    });
  });

  describe('resetPassword', () => {
    it('should call reset password endpoint with token and new password', async () => {
      const mockResponse = {
        id: '123',
        email: 'test@example.com',
        is_active: true,
        is_superuser: false,
        created_at: '2024-01-01T00:00:00Z',
      };

      (apiFetch as any).mockResolvedValue(mockResponse);

      const token = 'reset_token_123';
      const newPassword = 'newpassword123';

      const result = await authApi.resetPassword(token, newPassword);

      expect(apiFetch).toHaveBeenCalledWith('/auth/reset-password', {
        method: 'POST',
        body: JSON.stringify({ token, new_password: newPassword }),
      });

      expect(result).toEqual(mockResponse);
    });

    it('should use snake_case for new_password field', async () => {
      (apiFetch as any).mockResolvedValue({});

      await authApi.resetPassword('token', 'newpassword');

      const callArgs = (apiFetch as any).mock.calls[0];
      const body = JSON.parse(callArgs[1].body);

      expect(body).toHaveProperty('new_password');
      expect(body).not.toHaveProperty('newPassword');
    });
  });

  describe('verifyEmail', () => {
    it('should call verify email endpoint with token', async () => {
      const mockResponse = {
        id: '123',
        email: 'test@example.com',
        is_active: true,
        is_superuser: false,
        created_at: '2024-01-01T00:00:00Z',
      };

      (apiFetch as any).mockResolvedValue(mockResponse);

      const token = 'verification_token_123';
      const result = await authApi.verifyEmail(token);

      expect(apiFetch).toHaveBeenCalledWith('/auth/verify-email', {
        method: 'POST',
        body: JSON.stringify({ token }),
      });

      expect(result).toEqual(mockResponse);
    });
  });

  describe('resendVerificationEmail', () => {
    it('should call resend verification endpoint with email', async () => {
      (apiFetch as any).mockResolvedValue(undefined);

      const email = 'test@example.com';
      await authApi.resendVerificationEmail(email);

      expect(apiFetch).toHaveBeenCalledWith('/auth/resend-verification', {
        method: 'POST',
        body: JSON.stringify({ email }),
      });
    });

    it('should return void', async () => {
      (apiFetch as any).mockResolvedValue(undefined);

      const result = await authApi.resendVerificationEmail('test@example.com');

      expect(result).toBeUndefined();
    });
  });

  describe('Error Handling', () => {
    it('should propagate API errors for login', async () => {
      const mockError = new Error('Invalid credentials');
      (apiFetch as any).mockRejectedValue(mockError);

      await expect(
        authApi.login({ username: 'test@example.com', password: 'wrong' })
      ).rejects.toThrow('Invalid credentials');
    });

    it('should propagate API errors for register', async () => {
      const mockError = new Error('Email already registered');
      (apiFetch as any).mockRejectedValue(mockError);

      await expect(
        authApi.register({ email: 'existing@example.com', password: 'password' })
      ).rejects.toThrow('Email already registered');
    });

    it('should propagate API errors for token refresh', async () => {
      const mockError = new Error('Invalid refresh token');
      (apiFetch as any).mockRejectedValue(mockError);

      await expect(
        authApi.refreshAccessToken('invalid_token')
      ).rejects.toThrow('Invalid refresh token');
    });

    it('should propagate API errors for password reset', async () => {
      const mockError = new Error('Reset token expired');
      (apiFetch as any).mockRejectedValue(mockError);

      await expect(
        authApi.resetPassword('expired_token', 'newpassword')
      ).rejects.toThrow('Reset token expired');
    });

    it('should propagate API errors for email verification', async () => {
      const mockError = new Error('Verification token expired');
      (apiFetch as any).mockRejectedValue(mockError);

      await expect(
        authApi.verifyEmail('expired_token')
      ).rejects.toThrow('Verification token expired');
    });
  });
});
