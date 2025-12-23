import { RouterProvider } from "react-router-dom";
import { router } from "./routes";
import { Layout } from "../components/Layout";
import { AuthProvider } from "../auth/AuthContext";


export function App() {
  return (
    <AuthProvider>
      <Layout>
        <RouterProvider router={router} />
      </Layout>
    </AuthProvider>
  );
}

