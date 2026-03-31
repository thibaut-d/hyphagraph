import {
  createContext,
  useContext,
  useEffect,
  useState,
  ReactNode,
  useCallback,
  useRef,
} from "react";

import { getMe, logout as logoutApi, refreshAccessToken } from "../api/auth";
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
  loading: boolean;
  login: (token: string) => void;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  // Token lives in memory only — never in localStorage or sessionStorage.
  // The httpOnly refresh cookie (managed by the browser) is the persistence layer.
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<UserRead | null>(null);
  // Start loading=true so consumers don't flash unauthenticated state while we
  // attempt to restore the session from the httpOnly refresh cookie.
  const [loading, setLoading] = useState<boolean>(true);

  const tokenRef = useRef(token);
  const requestVersionRef = useRef(0);
  // Prevents the getMe() effect from treating the initial null token as a
  // logout before the session-restore attempt has finished.
  const sessionRestoreAttemptedRef = useRef(false);
  const sessionRestoreStartedRef = useRef(false);
  // Incremented by logout to cancel any in-flight session restore.
  const sessionRestoreVersionRef = useRef(0);

  useEffect(() => {
    tokenRef.current = token;
  }, [token]);

  // Sync in-tab token changes dispatched by the API client (e.g., after a
  // transparent 401->refresh cycle in client.tsx).
  useEffect(() => {
    const syncAuthState = () => {
      const nextAuth = getStoredAuthTokens();
      if (nextAuth.token !== tokenRef.current) {
        setToken(nextAuth.token);
      }
    };

    window.addEventListener(AUTH_STATE_CHANGED_EVENT, syncAuthState);
    return () => {
      window.removeEventListener(AUTH_STATE_CHANGED_EVENT, syncAuthState);
    };
  }, []);

  const logout = useCallback(() => {
    sessionRestoreVersionRef.current += 1; // Cancel any in-flight session restore
    requestVersionRef.current += 1;

    logoutApi().catch((err) => {
      // Logout should clear client state even if token revocation fails.
      console.warn("[auth] Token revocation failed (session cleared anyway):", err);
    });

    clearStoredAuthTokens();
    setToken(null);
    setUser(null);
    setLoading(false);
  }, []);

  // On mount: attempt to restore an existing session from the httpOnly refresh
  // cookie. If the cookie is present the refresh endpoint returns a new access
  // token; if not, we fall through to the unauthenticated state.
  useEffect(() => {
    if (sessionRestoreStartedRef.current) {
      return;
    }
    sessionRestoreStartedRef.current = true;

    const restoreVersion = ++sessionRestoreVersionRef.current;
    refreshAccessToken()
      .then(({ access_token }) => {
        // Abort if logout was called while the refresh was in-flight.
        if (restoreVersion !== sessionRestoreVersionRef.current) return;
        setStoredAuthTokens(access_token);
        setToken(access_token);
        // loading is cleared by the getMe() effect once user data arrives.
      })
      .catch(() => {
        if (restoreVersion !== sessionRestoreVersionRef.current) return;
        // No valid refresh cookie — user must log in.
        setLoading(false);
      })
      .finally(() => {
        sessionRestoreAttemptedRef.current = true;
      });
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Whenever token changes (login, logout, post-restore), fetch the user profile.
  useEffect(() => {
    // Skip until the session-restore attempt has completed so we don't
    // immediately flash the logged-out state on page load.
    if (!sessionRestoreAttemptedRef.current) return;

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
      .catch(() => {
        if (
          cancelled ||
          requestVersion !== requestVersionRef.current ||
          tokenRef.current !== requestedToken
        ) {
          return;
        }

        // Any failure to load user data leaves token+user in inconsistent
        // state. Clear the session so consumers never see a non-null token
        // with a null user.
        logout();
      });

    return () => {
      cancelled = true;
    };
  }, [token, logout]);

  const login = (newToken: string) => {
    setStoredAuthTokens(newToken);
    setToken(newToken);
  };

  return (
    <AuthContext.Provider value={{ user, token, loading, login, logout }}>
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
