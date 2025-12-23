import { createBrowserRouter } from "react-router-dom";
import Layout from "../components/Layout";

import HomeView from "../views/HomeView";
import SourcesView from "../views/SourcesView";
import EntitiesView from "../views/EntitiesView";
import RelationsView from "../views/RelationsView";
import InferencesView from "../views/InferencesView";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <Layout />,
    children: [
      { index: true, element: <HomeView /> },
      { path: "sources", element: <SourcesView /> },
      { path: "entities", element: <EntitiesView /> },
      { path: "relations", element: <RelationsView /> },
      { path: "inferences", element: <InferencesView /> }
    ]
  }
]);