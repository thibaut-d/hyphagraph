import { RouterProvider } from "react-router-dom";
import { router } from "./routes";
import { AuthProvider } from "../auth/AuthContext";


export function App() {
  return (
    <AuthProvider>
      <RouterProvider router={router} />
    </AuthProvider>
  );
}

