export const AUTH_STATE_CHANGED_EVENT = "auth-state-changed";
export const AUTH_SESSION_EXPIRED_EVENT = "auth-session-expired";

export type AuthTokens = {
  token: string | null;
};

// In-memory token storage — not accessible to XSS payloads unlike localStorage.
// The companion httpOnly refresh cookie (managed by the browser) is the persistence layer.
let _token: string | null = null;

function dispatchAuthStateChanged(): void {
  window.dispatchEvent(
    new CustomEvent<AuthTokens>(AUTH_STATE_CHANGED_EVENT, {
      detail: { token: _token },
    }),
  );
}

export function getStoredAuthTokens(): AuthTokens {
  return { token: _token };
}

export function setStoredAuthTokens(token: string): void {
  _token = token;
  dispatchAuthStateChanged();
}

export function updateStoredAccessToken(token: string): void {
  _token = token;
  dispatchAuthStateChanged();
}

export function clearStoredAuthTokens(): void {
  _token = null;
  dispatchAuthStateChanged();
}

export function dispatchAuthSessionExpired(): void {
  window.dispatchEvent(new Event(AUTH_SESSION_EXPIRED_EVENT));
}
