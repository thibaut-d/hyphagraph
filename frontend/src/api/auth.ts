import { apiFetch } from "./client";
import type { UserRead } from "../types/auth";

export type LoginPayload = {
  username: string;
  password: string;
};

export type RegisterPayload = {
  email: string;
  password: string;
};

export type TokenPairResponse = {
  access_token: string;
  refresh_token: string;
  token_type: string;
};

export type TokenResponse = {
  access_token: string;
  token_type: string;
};

export function login(payload: LoginPayload): Promise<TokenPairResponse> {
  const body = new URLSearchParams({
    username: payload.username,
    password: payload.password,
  });

  return apiFetch("/auth/login", {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body,
  });
}

export function register(payload: RegisterPayload): Promise<UserRead> {
  return apiFetch<UserRead>("/auth/register", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getMe(): Promise<UserRead> {
  return apiFetch<UserRead>("/auth/me");
}

export function refreshAccessToken(refreshToken: string): Promise<TokenResponse> {
  return apiFetch("/auth/refresh", {
    method: "POST",
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
}

export function logout(refreshToken: string): Promise<void> {
  return apiFetch("/auth/logout", {
    method: "POST",
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
}

export function requestPasswordReset(email: string): Promise<void> {
  return apiFetch("/auth/request-password-reset", {
    method: "POST",
    body: JSON.stringify({ email }),
  });
}

export function resetPassword(token: string, newPassword: string): Promise<UserRead> {
  return apiFetch<UserRead>("/auth/reset-password", {
    method: "POST",
    body: JSON.stringify({ token, new_password: newPassword }),
  });
}

export function verifyEmail(token: string): Promise<UserRead> {
  return apiFetch<UserRead>("/auth/verify-email", {
    method: "POST",
    body: JSON.stringify({ token }),
  });
}

export function resendVerificationEmail(email: string): Promise<void> {
  return apiFetch("/auth/resend-verification", {
    method: "POST",
    body: JSON.stringify({ email }),
  });
}

export type ChangePasswordPayload = {
  current_password: string;
  new_password: string;
};

export function changePassword(payload: ChangePasswordPayload): Promise<void> {
  return apiFetch("/auth/change-password", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export type UpdateProfilePayload = {
  email?: string;
};

export function updateProfile(payload: UpdateProfilePayload): Promise<UserRead> {
  return apiFetch<UserRead>("/auth/me", {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function deactivateAccount(): Promise<void> {
  return apiFetch("/auth/deactivate", {
    method: "POST",
  });
}

export function deleteAccount(): Promise<void> {
  return apiFetch("/auth/me", {
    method: "DELETE",
  });
}
