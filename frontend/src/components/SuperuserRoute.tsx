import type { ReactNode } from "react";

import { Navigate } from "react-router-dom";

import { ProtectedRoute } from "./ProtectedRoute";
import { useAuth } from "../auth/useAuth";

interface SuperuserRouteProps {
  children: ReactNode;
}

export function SuperuserRoute({ children }: SuperuserRouteProps) {
  const { user } = useAuth();

  return (
    <ProtectedRoute>
      {user?.is_superuser ? children : <Navigate to="/" replace />}
    </ProtectedRoute>
  );
}
