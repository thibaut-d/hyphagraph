import { RouterProvider } from "react-router-dom";
import { router } from "./routes";
import { AuthProvider } from "../auth/AuthContext";
import { NotificationProvider } from "../notifications/NotificationContext";


export function App() {
  return (
    <AuthProvider>
      <NotificationProvider>
        <RouterProvider router={router} />
      </NotificationProvider>
    </AuthProvider>
  );
}

