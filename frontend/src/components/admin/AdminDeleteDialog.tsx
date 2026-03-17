import {
  Alert,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Typography,
} from "@mui/material";

interface UserListItem {
  id: string;
  email: string;
  is_active: boolean;
  is_superuser: boolean;
  is_verified: boolean;
  created_at: string;
}

interface AdminDeleteDialogProps {
  open: boolean;
  user: UserListItem | null;
  onConfirm: () => void;
  onClose: () => void;
}

export function AdminDeleteDialog({ open, user, onConfirm, onClose }: AdminDeleteDialogProps) {
  return (
    <Dialog open={open} onClose={onClose}>
      <DialogTitle>Delete User</DialogTitle>
      <DialogContent>
        {user && (
          <>
            <Typography>Are you sure you want to delete this user?</Typography>
            <Typography variant="body2" sx={{ mt: 2, fontWeight: 600 }}>
              {user.email}
            </Typography>
            <Alert severity="warning" sx={{ mt: 2 }}>
              This action cannot be undone. All user data will be permanently deleted.
            </Alert>
          </>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button onClick={onConfirm} color="error" variant="contained">
          Delete User
        </Button>
      </DialogActions>
    </Dialog>
  );
}
