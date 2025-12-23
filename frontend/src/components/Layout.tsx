import { AppBar, Toolbar, Typography, Container } from "@mui/material";
import { ReactNode } from "react";

export function Layout({ children }: { children: ReactNode }) {
  return (
    <>
      <AppBar position="static">
        <Toolbar>
          <Typography variant="h6">
            HyphaGraph
          </Typography>
        </Toolbar>
      </AppBar>

      <Container maxWidth="lg" sx={{ mt: 4 }}>
        {children}
      </Container>
    </>
  );
}