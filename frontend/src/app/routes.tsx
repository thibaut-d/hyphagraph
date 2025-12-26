import { createBrowserRouter } from "react-router-dom";
import { Layout } from "../components/Layout";

import { HomeView } from "../views/HomeView";
import { EntitiesView } from "../views/EntitiesView";
import { EntityDetailView } from "../views/EntityDetailView";
import { SourcesView } from "../views/SourcesView";
import { SourceDetailView } from "../views/SourceDetailView";
import { SearchView } from "../views/SearchView";
import { AccountView } from "../views/AccountView";
import { CreateRelationView } from "../views/CreateRelationView";
import RequestPasswordResetView from "../views/RequestPasswordResetView";
import ResetPasswordView from "../views/ResetPasswordView";
import VerifyEmailView from "../views/VerifyEmailView";
import ResendVerificationView from "../views/ResendVerificationView";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <Layout />,
    children: [
      { index: true, element: <HomeView /> },

      { path: "entities", element: <EntitiesView /> },
      { path: "entities/:id", element: <EntityDetailView /> },

      { path: "sources", element: <SourcesView /> },
      { path: "sources/:id", element: <SourceDetailView /> },

      { path: "search", element: <SearchView /> },

      { path: "account", element: <AccountView /> },
      { path: "forgot-password", element: <RequestPasswordResetView /> },
      { path: "reset-password", element: <ResetPasswordView /> },
      { path: "verify-email", element: <VerifyEmailView /> },
      { path: "resend-verification", element: <ResendVerificationView /> },

      { path: "relations/new", element: <CreateRelationView /> },
    ],
  },
]);