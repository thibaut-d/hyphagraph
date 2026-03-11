export const AUTH_STATE_CHANGED_EVENT = "auth-state-changed";

export type AuthTokens = {
  token: string | null;
  refreshToken: string | null;
};

function readAuthTokens(): AuthTokens {
  return {
    token: localStorage.getItem("auth_token"),
    refreshToken: localStorage.getItem("refresh_token"),
  };
}

function dispatchAuthStateChanged(): void {
  window.dispatchEvent(
    new CustomEvent<AuthTokens>(AUTH_STATE_CHANGED_EVENT, {
      detail: readAuthTokens(),
    }),
  );
}

export function getStoredAuthTokens(): AuthTokens {
  return readAuthTokens();
}

export function setStoredAuthTokens(token: string, refreshToken: string): void {
  localStorage.setItem("auth_token", token);
  localStorage.setItem("refresh_token", refreshToken);
  dispatchAuthStateChanged();
}

export function updateStoredAccessToken(token: string): void {
  localStorage.setItem("auth_token", token);
  dispatchAuthStateChanged();
}

export function clearStoredAuthTokens(): void {
  localStorage.removeItem("auth_token");
  localStorage.removeItem("refresh_token");
  dispatchAuthStateChanged();
}
