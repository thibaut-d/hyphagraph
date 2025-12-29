import { createBrowserRouter } from "react-router-dom";
import { Layout } from "../components/Layout";
import { ProtectedRoute } from "../components/ProtectedRoute";

import { HomeView } from "../views/HomeView";
import { EntitiesView } from "../views/EntitiesView";
import { EntityDetailView } from "../views/EntityDetailView";
import { CreateEntityView } from "../views/CreateEntityView";
import { EditEntityView } from "../views/EditEntityView";
import { SourcesView } from "../views/SourcesView";
import { SourceDetailView } from "../views/SourceDetailView";
import { CreateSourceView } from "../views/CreateSourceView";
import { EditSourceView } from "../views/EditSourceView";
import { SearchView } from "../views/SearchView";
import { AccountView } from "../views/AccountView";
import { ProfileView } from "../views/ProfileView";
import { ChangePasswordView } from "../views/ChangePasswordView";
import { SettingsView } from "../views/SettingsView";
import { CreateRelationView } from "../views/CreateRelationView";
import { EditRelationView } from "../views/EditRelationView";
import RelationsView from "../views/RelationsView";
import RequestPasswordResetView from "../views/RequestPasswordResetView";
import ResetPasswordView from "../views/ResetPasswordView";
import VerifyEmailView from "../views/VerifyEmailView";
import ResendVerificationView from "../views/ResendVerificationView";
import { ExplanationView } from "../views/ExplanationView";
import { PropertyDetailView } from "../views/PropertyDetailView";
import { SynthesisView } from "../views/SynthesisView";
import { DisagreementsView } from "../views/DisagreementsView";
import { EvidenceView } from "../views/EvidenceView";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <Layout />,
    children: [
      { index: true, element: <HomeView /> },

      { path: "entities", element: <EntitiesView /> },
      { path: "entities/new", element: <ProtectedRoute><CreateEntityView /></ProtectedRoute> },
      { path: "entities/:id", element: <EntityDetailView /> },
      { path: "entities/:id/edit", element: <ProtectedRoute><EditEntityView /></ProtectedRoute> },
      { path: "entities/:id/synthesis", element: <SynthesisView /> },
      { path: "entities/:id/disagreements", element: <DisagreementsView /> },
      { path: "entities/:id/evidence", element: <EvidenceView /> },
      { path: "entities/:id/properties/:roleType", element: <PropertyDetailView /> },
      { path: "entities/:id/properties/:roleType/evidence", element: <EvidenceView /> },
      { path: "explain/:entityId/:roleType", element: <ExplanationView /> },

      { path: "sources", element: <SourcesView /> },
      { path: "sources/new", element: <ProtectedRoute><CreateSourceView /></ProtectedRoute> },
      { path: "sources/:id", element: <SourceDetailView /> },
      { path: "sources/:id/edit", element: <ProtectedRoute><EditSourceView /></ProtectedRoute> },

      { path: "search", element: <SearchView /> },

      { path: "account", element: <AccountView /> },
      { path: "profile", element: <ProfileView /> },
      { path: "change-password", element: <ChangePasswordView /> },
      { path: "settings", element: <SettingsView /> },
      { path: "forgot-password", element: <RequestPasswordResetView /> },
      { path: "reset-password", element: <ResetPasswordView /> },
      { path: "verify-email", element: <VerifyEmailView /> },
      { path: "resend-verification", element: <ResendVerificationView /> },

      { path: "relations", element: <RelationsView /> },
      { path: "relations/new", element: <ProtectedRoute><CreateRelationView /></ProtectedRoute> },
      { path: "relations/:id/edit", element: <ProtectedRoute><EditRelationView /></ProtectedRoute> },
    ],
  },
]);