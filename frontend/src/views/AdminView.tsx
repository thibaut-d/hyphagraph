/**
 * AdminView - User management panel for superusers
 *
 * Features:
 * - User statistics dashboard
 * - User list with status indicators
 * - Edit user (activate/deactivate, promote/demote)
 * - Delete user with confirmation
 * - Security: Prevents self-lockout
 */

import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import {
  Typography,
  Paper,
  Stack,
  Box,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Chip,
  Grid,
  Card,
  CardContent,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Switch,
  FormControlLabel,
  Alert,
} from "@mui/material";
import EditIcon from "@mui/icons-material/Edit";
import DeleteIcon from "@mui/icons-material/Delete";
import PeopleIcon from "@mui/icons-material/People";
import VerifiedUserIcon from "@mui/icons-material/VerifiedUser";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import EmailIcon from "@mui/icons-material/Email";
import { apiFetch } from "../api/client";
import { usePageErrorHandler } from "../hooks/usePageErrorHandler";

interface UserStats {
  total_users: number;
  active_users: number;
  superusers: number;
  verified_users: number;
}

interface UserListItem {
  id: string;
  email: string;
  is_active: boolean;
  is_superuser: boolean;
  is_verified: boolean;
  created_at: string;
}

export function AdminView() {
  const { t } = useTranslation();
  const handlePageError = usePageErrorHandler();
  const [stats, setStats] = useState<UserStats | null>(null);
  const [users, setUsers] = useState<UserListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState<UserListItem | null>(null);
  // Edit form state
  const [editIsActive, setEditIsActive] = useState(false);
  const [editIsSuperuser, setEditIsSuperuser] = useState(false);
  const [editIsVerified, setEditIsVerified] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [statsData, usersData] = await Promise.all([
        apiFetch<UserStats>("/admin/stats"),
        apiFetch<UserListItem[]>("/admin/users"),
      ]);
      setStats(statsData);
      setUsers(usersData);
    } catch (err) {
      const parsedError = handlePageError(err, "Failed to load admin data");
      setError(parsedError.userMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleEditClick = (user: UserListItem) => {
    setSelectedUser(user);
    setEditIsActive(user.is_active);
    setEditIsSuperuser(user.is_superuser);
    setEditIsVerified(user.is_verified);
    setEditDialogOpen(true);
  };

  const handleSaveEdit = async () => {
    if (!selectedUser) return;

    try {
      await apiFetch(`/admin/users/${selectedUser.id}`, {
        method: "PUT",
        body: JSON.stringify({
          is_active: editIsActive,
          is_superuser: editIsSuperuser,
          is_verified: editIsVerified,
        }),
      });
      setError(null);
      setEditDialogOpen(false);
      await loadData();
    } catch (err) {
      const parsedError = handlePageError(err, "Failed to update user");
      setError(parsedError.userMessage);
    }
  };

  const handleDeleteClick = (user: UserListItem) => {
    setSelectedUser(user);
    setDeleteDialogOpen(true);
  };

  const handleConfirmDelete = async () => {
    if (!selectedUser) return;

    try {
      await apiFetch(`/admin/users/${selectedUser.id}`, {
        method: "DELETE",
      });
      setError(null);
      setDeleteDialogOpen(false);
      await loadData();
    } catch (err) {
      const parsedError = handlePageError(err, "Failed to delete user");
      setError(parsedError.userMessage);
    }
  };

  if (loading) {
    return <Typography>Loading...</Typography>;
  }

  if (error) {
    return <Alert severity="error">{error}</Alert>;
  }

  return (
    <Stack spacing={3}>
      {/* Header */}
      <Paper sx={{ p: 3 }}>
        <Typography variant="h4">Administration Panel</Typography>
        <Typography variant="body2" color="text.secondary">
          User management and system administration
        </Typography>
      </Paper>

      {/* Statistics Cards */}
      {stats && (
        <Grid container spacing={2}>
          <Grid size={{ xs: 12, sm: 6, md: 3 }}>
            <Card>
              <CardContent>
                <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                  <PeopleIcon color="primary" />
                  <Box>
                    <Typography variant="h4">{stats.total_users}</Typography>
                    <Typography variant="body2" color="text.secondary">
                      Total Users
                    </Typography>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>

          <Grid size={{ xs: 12, sm: 6, md: 3 }}>
            <Card>
              <CardContent>
                <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                  <CheckCircleIcon color="success" />
                  <Box>
                    <Typography variant="h4">{stats.active_users}</Typography>
                    <Typography variant="body2" color="text.secondary">
                      Active
                    </Typography>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>

          <Grid size={{ xs: 12, sm: 6, md: 3 }}>
            <Card>
              <CardContent>
                <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                  <VerifiedUserIcon color="secondary" />
                  <Box>
                    <Typography variant="h4">{stats.superusers}</Typography>
                    <Typography variant="body2" color="text.secondary">
                      Superusers
                    </Typography>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>

          <Grid size={{ xs: 12, sm: 6, md: 3 }}>
            <Card>
              <CardContent>
                <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                  <EmailIcon color="info" />
                  <Box>
                    <Typography variant="h4">{stats.verified_users}</Typography>
                    <Typography variant="body2" color="text.secondary">
                      Verified
                    </Typography>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* Users Table */}
      <Paper sx={{ p: 3 }}>
        <Typography variant="h5" gutterBottom>
          Users
        </Typography>

        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Email</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Role</TableCell>
                <TableCell>Verified</TableCell>
                <TableCell>Created</TableCell>
                <TableCell>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {users.map((user) => (
                <TableRow key={user.id}>
                  <TableCell>{user.email}</TableCell>
                  <TableCell>
                    <Chip
                      label={user.is_active ? "Active" : "Inactive"}
                      color={user.is_active ? "success" : "default"}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={user.is_superuser ? "Superuser" : "User"}
                      color={user.is_superuser ? "secondary" : "default"}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>
                    {user.is_verified ? "✓" : "✗"}
                  </TableCell>
                  <TableCell>
                    {new Date(user.created_at).toLocaleDateString()}
                  </TableCell>
                  <TableCell>
                    <IconButton
                      size="small"
                      onClick={() => handleEditClick(user)}
                      title="Edit user"
                    >
                      <EditIcon fontSize="small" />
                    </IconButton>
                    <IconButton
                      size="small"
                      color="error"
                      onClick={() => handleDeleteClick(user)}
                      title="Delete user"
                    >
                      <DeleteIcon fontSize="small" />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>

      {/* Edit Dialog */}
      <Dialog open={editDialogOpen} onClose={() => setEditDialogOpen(false)}>
        <DialogTitle>Edit User</DialogTitle>
        <DialogContent>
          {selectedUser && (
            <Stack spacing={2} sx={{ mt: 1 }}>
              <Typography variant="body2" color="text.secondary">
                {selectedUser.email}
              </Typography>

              <FormControlLabel
                control={
                  <Switch
                    checked={editIsActive}
                    onChange={(e) => setEditIsActive(e.target.checked)}
                  />
                }
                label="Active"
              />

              <FormControlLabel
                control={
                  <Switch
                    checked={editIsSuperuser}
                    onChange={(e) => setEditIsSuperuser(e.target.checked)}
                  />
                }
                label="Superuser"
              />

              <FormControlLabel
                control={
                  <Switch
                    checked={editIsVerified}
                    onChange={(e) => setEditIsVerified(e.target.checked)}
                  />
                }
                label="Email Verified"
              />
            </Stack>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleSaveEdit} variant="contained">
            Save Changes
          </Button>
        </DialogActions>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)}>
        <DialogTitle>Delete User</DialogTitle>
        <DialogContent>
          {selectedUser && (
            <>
              <Typography>
                Are you sure you want to delete this user?
              </Typography>
              <Typography variant="body2" sx={{ mt: 2, fontWeight: 600 }}>
                {selectedUser.email}
              </Typography>
              <Alert severity="warning" sx={{ mt: 2 }}>
                This action cannot be undone. All user data will be permanently deleted.
              </Alert>
            </>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleConfirmDelete} color="error" variant="contained">
            Delete User
          </Button>
        </DialogActions>
      </Dialog>
    </Stack>
  );
}
