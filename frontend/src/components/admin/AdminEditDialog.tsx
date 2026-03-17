import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  Stack,
  Switch,
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

interface AdminEditDialogProps {
  open: boolean;
  user: UserListItem | null;
  isActive: boolean;
  isSuperuser: boolean;
  isVerified: boolean;
  onIsActiveChange: (value: boolean) => void;
  onIsSuperuserChange: (value: boolean) => void;
  onIsVerifiedChange: (value: boolean) => void;
  onSave: () => void;
  onClose: () => void;
}

export function AdminEditDialog({
  open,
  user,
  isActive,
  isSuperuser,
  isVerified,
  onIsActiveChange,
  onIsSuperuserChange,
  onIsVerifiedChange,
  onSave,
  onClose,
}: AdminEditDialogProps) {
  return (
    <Dialog open={open} onClose={onClose}>
      <DialogTitle>Edit User</DialogTitle>
      <DialogContent>
        {user && (
          <Stack spacing={2} sx={{ mt: 1 }}>
            <Typography variant="body2" color="text.secondary">
              {user.email}
            </Typography>
            <FormControlLabel
              control={
                <Switch checked={isActive} onChange={(e) => onIsActiveChange(e.target.checked)} />
              }
              label="Active"
            />
            <FormControlLabel
              control={
                <Switch
                  checked={isSuperuser}
                  onChange={(e) => onIsSuperuserChange(e.target.checked)}
                />
              }
              label="Superuser"
            />
            <FormControlLabel
              control={
                <Switch
                  checked={isVerified}
                  onChange={(e) => onIsVerifiedChange(e.target.checked)}
                />
              }
              label="Email Verified"
            />
          </Stack>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button onClick={onSave} variant="contained">
          Save Changes
        </Button>
      </DialogActions>
    </Dialog>
  );
}
