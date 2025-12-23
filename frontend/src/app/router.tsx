import { createBrowserRouter, Outlet } from "react-router-dom";
import { Layout } from "../components/Layout";

import { HomeView } from "../views/HomeView";
import { EntitiesView } from "../views/EntitiesView";
import { SourcesView } from "../views/SourcesView";
import { SearchView } from "../views/SearchView";
import { AccountView } from "../views/AccountView";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <Layout><Outlet /></Layout>,
    children: [
      { index: true, element: <HomeView /> },
      { path: "entities", element: <EntitiesView /> },
      { path: "sources", element: <SourcesView /> },
      { path: "search", element: <SearchView /> },
      { path: "account", element: <AccountView /> },
    ],
  },
]);