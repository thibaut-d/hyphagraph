import { NavLink, Outlet } from "react-router-dom";

export default function Layout() {
  return (
    <div style={{ padding: "1.5rem", fontFamily: "sans-serif" }}>
      <nav style={{ marginBottom: "1rem" }}>
        <NavLink to="/" end style={{ marginRight: "1rem" }}>
          Home
        </NavLink>
        <NavLink to="/sources" style={{ marginRight: "1rem" }}>
          Sources
        </NavLink>
        <NavLink to="/entities" style={{ marginRight: "1rem" }}>
          Entities
        </NavLink>
        <NavLink to="/relations" style={{ marginRight: "1rem" }}>
          Relations
        </NavLink>
        <NavLink to="/inferences">
          Inferences
        </NavLink>
      </nav>

      <Outlet />
    </div>
  );
}