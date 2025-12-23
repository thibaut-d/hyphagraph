import { ReactNode } from "react";
import { Link as RouterLink, useLocation } from "react-router-dom";

import {
  AppBar,
  Toolbar,
  Typography,
  Box,
  Button,
  Container,
} from "@mui/material";

const menuItems = [
  { label: "Accueil", path: "/" },
  { label: "Entities", path: "/entities" },
  { label: "Sources", path: "/sources" },
  { label: "Search", path: "/search" },
  { label: "Mon compte", path: "/account" },
];

export function Layout({ children }: { children: ReactNode }) {
  const location = useLocation();

  return (
    <>
      <AppBar position="static">
        <Toolbar>
          <Typography variant="h6" sx={{ mr: 4 }}>
            HyphaGraph
          </Typography>

          <Box sx={{ flexGrow: 1 }}>
            {menuItems.map((item) => {
              const isActive = location.pathname === item.path;

              return (
                <Button
                  key={item.path}
                  component={RouterLink}
                  to={item.path}
                  color="inherit"
                  sx={{
                    fontWeight: isActive ? "bold" : "normal",
                    textDecoration: isActive ? "underline" : "none",
                  }}
                >
                  {item.label}
                </Button>
              );
            })}
          </Box>
        </Toolbar>
      </AppBar>

      <Container maxWidth="lg" sx={{ mt: 4 }}>
        {children}
      </Container>
    </>
  );
}