import { Container, Typography, Button, Stack, Paper, Box } from "@mui/material";
import { useNotification } from "../notifications/NotificationContext";

/**
 * Demo view to test the global toast notification system.
 * This is for development/testing purposes only.
 *
 * To access: Navigate to /notification-demo
 */
export function NotificationDemoView() {
  const { showSuccess, showError, showInfo, showWarning } = useNotification();

  return (
    <Container maxWidth="md" sx={{ py: 4 }}>
      <Typography variant="h4" gutterBottom>
        Notification System Demo
      </Typography>

      <Typography variant="body1" color="text.secondary" paragraph>
        Click the buttons below to test different notification types. Notifications will appear at the top center of the screen.
      </Typography>

      <Paper sx={{ p: 3, mt: 3 }}>
        <Typography variant="h6" gutterBottom>
          Basic Notifications
        </Typography>

        <Stack spacing={2} sx={{ mt: 2 }}>
          <Button
            variant="contained"
            color="success"
            onClick={() => showSuccess("Operation completed successfully!")}
            fullWidth
          >
            Show Success Notification
          </Button>

          <Button
            variant="contained"
            color="error"
            onClick={() => showError("An error occurred. Please try again.")}
            fullWidth
          >
            Show Error Notification
          </Button>

          <Button
            variant="contained"
            color="info"
            onClick={() => showInfo("Here is some helpful information.")}
            fullWidth
          >
            Show Info Notification
          </Button>

          <Button
            variant="contained"
            color="warning"
            onClick={() => showWarning("Warning: This action cannot be undone.")}
            fullWidth
          >
            Show Warning Notification
          </Button>
        </Stack>
      </Paper>

      <Paper sx={{ p: 3, mt: 3 }}>
        <Typography variant="h6" gutterBottom>
          i18n Translations
        </Typography>

        <Stack spacing={2} sx={{ mt: 2 }}>
          <Button
            variant="outlined"
            onClick={() => showError("notifications.network_error")}
            fullWidth
          >
            Show Network Error (Translated)
          </Button>

          <Button
            variant="outlined"
            onClick={() => showError("notifications.session_expired")}
            fullWidth
          >
            Show Session Expired (Translated)
          </Button>

          <Button
            variant="outlined"
            onClick={() => showError("notifications.server_error")}
            fullWidth
          >
            Show Server Error (Translated)
          </Button>
        </Stack>
      </Paper>

      <Paper sx={{ p: 3, mt: 3 }}>
        <Typography variant="h6" gutterBottom>
          Advanced Options
        </Typography>

        <Stack spacing={2} sx={{ mt: 2 }}>
          <Button
            variant="outlined"
            onClick={() =>
              showSuccess("Quick message", {
                duration: 2000,
                autoDismiss: true,
              })
            }
            fullWidth
          >
            Show Quick Notification (2s)
          </Button>

          <Button
            variant="outlined"
            onClick={() =>
              showError("Persistent message - click X to close", {
                autoDismiss: false,
              })
            }
            fullWidth
          >
            Show Persistent Notification (No Auto-Dismiss)
          </Button>

          <Button
            variant="outlined"
            onClick={() => {
              showSuccess("First notification");
              setTimeout(() => showInfo("Second notification"), 100);
              setTimeout(() => showWarning("Third notification"), 200);
            }}
            fullWidth
          >
            Test Notification Queue (3 messages)
          </Button>
        </Stack>
      </Paper>

      <Box sx={{ mt: 4, p: 2, bgcolor: "grey.100", borderRadius: 1 }}>
        <Typography variant="caption" color="text.secondary">
          <strong>Note:</strong> This demo page is for development purposes only.
          The notification system is now integrated into the app and can be used
          in any component by calling <code>useNotification()</code>.
        </Typography>
      </Box>
    </Container>
  );
}
