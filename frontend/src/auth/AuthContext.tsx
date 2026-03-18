import {
  createContext,
  useContext,
  useEffect,
  useState,
  ReactNode,
  useCallback,
  useRef,
} from "react";

import { getMe, logout as logoutApi } from "../api/auth";
import {
  AUTH_STATE_CHANGED_EVENT,
  clearStoredAuthTokens,
  getStoredAuthTokens,
  setStoredAuthTokens,
} from "./authStorage";
import type { UserRead } from "../types/auth";

type AuthContextValue = {
  user: UserRead | null;
  token: string | null;
  refreshToken: string | null;
  loading: boolean;
  login: (token: string, refreshToken: string) => void;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const initialAuth = getStoredAuthTokens();
  const [token, setToken] = useState<string | null>(initialAuth.token);
  const [refreshToken, setRefreshToken] = useState<string | null>(initialAuth.refreshToken);
  const [user, setUser] = useState<UserRead | null>(null);
  const [loading, setLoading] = useState<boolean>(!!initialAuth.token);

  // Use refs to track current token values without causing re-renders
  const tokenRef = useRef(token);
  const refreshTokenRef = useRef(refreshToken);
  const requestVersionRef = useRef(0);

  // Update refs when state changes
  useEffect(() => {
    tokenRef.current = token;
  }, [token]);

  useEffect(() => {
    refreshTokenRef.current = refreshToken;
  }, [refreshToken]);

  useEffect(() => {
    const syncAuthState = () => {
      const nextAuth = getStoredAuthTokens();

      if (nextAuth.token !== tokenRef.current) {
        setToken(nextAuth.token);
      }
      if (nextAuth.refreshToken !== refreshTokenRef.current) {
        setRefreshToken(nextAuth.refreshToken);
      }
    };

    const handleStorageEvent = (event: StorageEvent) => {
      if (event.key === null || event.key === "auth_token" || event.key === "refresh_token") {
        syncAuthState();
      }
    };

    window.addEventListener("storage", handleStorageEvent);
    window.addEventListener(AUTH_STATE_CHANGED_EVENT, syncAuthState);

    return () => {
      window.removeEventListener("storage", handleStorageEvent);
      window.removeEventListener(AUTH_STATE_CHANGED_EVENT, syncAuthState);
    };
  }, []);

  const logout = useCallback(() => {
    requestVersionRef.current += 1;
    const currentRefreshToken = refreshTokenRef.current;

    if (currentRefreshToken) {
      logoutApi(currentRefreshToken).catch((err) => {
        // Logout should clear client state even if token revocation fails.
        console.warn("[auth] Token revocation failed (session cleared anyway):", err);
      });
    }

    clearStoredAuthTokens();
    setToken(null);
    setRefreshToken(null);
    setUser(null);
    setLoading(false);
  }, []);

  useEffect(() => {
    if (!token) {
      setUser(null);
      setLoading(false);
      return;
    }

    const requestVersion = ++requestVersionRef.current;
    const requestedToken = token;
    let cancelled = false;

    setLoading(true);
    getMe()
      .then((userData) => {
        if (
          cancelled ||
          requestVersion !== requestVersionRef.current ||
          tokenRef.current !== requestedToken
        ) {
          return;
        }

        setUser(userData);
        setLoading(false);
      })
      .catch((error) => {
        if (
          cancelled ||
          requestVersion !== requestVersionRef.current ||
          tokenRef.current !== requestedToken
        ) {
          return;
        }

        const errorMessage = error?.message || String(error);
        const isAuthError =
          errorMessage.includes("Session expired") ||
          errorMessage.includes("Authentication failed") ||
          errorMessage.includes("Unauthorized") ||
          errorMessage.includes("401");

        if (isAuthError) {
          logout();
        } else {
          console.warn("Failed to fetch user data, but keeping session:", error);
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [token, logout]);

  const login = (newToken: string, newRefreshToken: string) => {
    setStoredAuthTokens(newToken, newRefreshToken);
    setToken(newToken);
    setRefreshToken(newRefreshToken);
  };

  return (
    <AuthContext.Provider value={{ user, token, refreshToken, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuthContext() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("AuthContext not available");
  }
  return ctx;
}
