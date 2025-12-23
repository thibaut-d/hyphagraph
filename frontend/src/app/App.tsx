import { RouterProvider } from "react-router-dom";
import { router } from "./routes";
import { Layout } from "../components/Layout";

export function App() {
  return (
    <Layout>
      <RouterProvider router={router} />
    </Layout>
  );
}