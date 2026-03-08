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

type User = {
  id: string;
  email: string;
  is_active?: boolean;
  is_superuser?: boolean;
  is_verified?: boolean;
  created_at?: string;
};

type AuthContextValue = {
  user: User | null;
  token: string | null;
  refreshToken: string | null;
  loading: boolean;
  login: (token: string, refreshToken: string) => void;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(
    localStorage.getItem("auth_token"),
  );
  const [refreshToken, setRefreshToken] = useState<string | null>(
    localStorage.getItem("refresh_token"),
  );
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState<boolean>(!!localStorage.getItem("auth_token"));

  // Use refs to track current token values without causing re-renders
  const tokenRef = useRef(token);
  const refreshTokenRef = useRef(refreshToken);

  // Update refs when state changes
  useEffect(() => {
    tokenRef.current = token;
  }, [token]);

  useEffect(() => {
    refreshTokenRef.current = refreshToken;
  }, [refreshToken]);

  // Listen for storage changes (token refresh from API client)
  // Dependencies removed to prevent memory leak from multiple intervals
  useEffect(() => {
    const handleStorageChange = () => {
      const newToken = localStorage.getItem("auth_token");
      const newRefreshToken = localStorage.getItem("refresh_token");

      if (newToken !== tokenRef.current) {
        setToken(newToken);
      }
      if (newRefreshToken !== refreshTokenRef.current) {
        setRefreshToken(newRefreshToken);
      }
    };

    // Poll for changes (since localStorage events don't fire in same window)
    const interval = setInterval(handleStorageChange, 1000);

    return () => clearInterval(interval);
  }, []); // Empty dependency array - only create interval once

  // Stabilize logout with useCallback to prevent unnecessary re-renders
  const logout = useCallback(() => {
    const currentRefreshToken = localStorage.getItem("refresh_token");

    // Call logout API to revoke refresh token
    if (currentRefreshToken) {
      logoutApi(currentRefreshToken).catch(() => {
        // Ignore errors during logout
      });
    }

    localStorage.removeItem("auth_token");
    localStorage.removeItem("refresh_token");
    setToken(null);
    setRefreshToken(null);
    setUser(null);
  }, []); // No dependencies needed - uses localStorage directly

  useEffect(() => {
    if (!token) {
      setUser(null);
      setLoading(false);
      return;
    }

    setLoading(true);
    getMe()
      .then((userData: any) => {
        setUser(userData as User);
        setLoading(false);
      })
      .catch(() => {
        logout();
        setLoading(false);
      });
  }, [token, logout]); // Now includes logout in dependencies

  const login = (newToken: string, newRefreshToken: string) => {
    localStorage.setItem("auth_token", newToken);
    localStorage.setItem("refresh_token", newRefreshToken);
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
