import {
  createContext,
  useContext,
  useEffect,
  useState,
  ReactNode,
} from "react";

import { getMe, logout as logoutApi } from "../api/auth";

type User = {
  id: string;
  email: string;
};

type AuthContextValue = {
  user: User | null;
  token: string | null;
  refreshToken: string | null;
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

  // Listen for storage changes (token refresh from API client)
  useEffect(() => {
    const handleStorageChange = () => {
      const newToken = localStorage.getItem("auth_token");
      const newRefreshToken = localStorage.getItem("refresh_token");

      if (newToken !== token) {
        setToken(newToken);
      }
      if (newRefreshToken !== refreshToken) {
        setRefreshToken(newRefreshToken);
      }
    };

    // Poll for changes (since localStorage events don't fire in same window)
    const interval = setInterval(handleStorageChange, 1000);

    return () => clearInterval(interval);
  }, [token, refreshToken]);

  useEffect(() => {
    if (!token) {
      setUser(null);
      return;
    }

    getMe()
      .then(setUser)
      .catch(() => logout());
  }, [token]);

  const login = (newToken: string, newRefreshToken: string) => {
    localStorage.setItem("auth_token", newToken);
    localStorage.setItem("refresh_token", newRefreshToken);
    setToken(newToken);
    setRefreshToken(newRefreshToken);
  };

  const logout = () => {
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
  };

  return (
    <AuthContext.Provider value={{ user, token, refreshToken, login, logout }}>
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