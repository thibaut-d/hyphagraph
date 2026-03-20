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
  Alert,
  Tabs,
  Tab,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
} from "@mui/material";
import EditIcon from "@mui/icons-material/Edit";
import DeleteIcon from "@mui/icons-material/Delete";
import AddIcon from "@mui/icons-material/Add";
import PeopleIcon from "@mui/icons-material/People";
import VerifiedUserIcon from "@mui/icons-material/VerifiedUser";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import EmailIcon from "@mui/icons-material/Email";
import CategoryIcon from "@mui/icons-material/Category";
import { apiFetch } from "../api/client";
import { usePageErrorHandler } from "../hooks/usePageErrorHandler";
import { AdminEditDialog } from "../components/admin/AdminEditDialog";
import { AdminDeleteDialog } from "../components/admin/AdminDeleteDialog";

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

interface UICategoryItem {
  id: string;
  slug: string;
  labels: Record<string, string>;
  description?: Record<string, string> | null;
  order: number;
}

const emptyCatForm = () => ({
  slug: "",
  label_en: "",
  label_fr: "",
  desc_en: "",
  desc_fr: "",
  order: 0,
});

export function AdminView() {
  const { t } = useTranslation();
  const handlePageError = usePageErrorHandler();
  const [activeTab, setActiveTab] = useState(0);
  const [stats, setStats] = useState<UserStats | null>(null);
  const [users, setUsers] = useState<UserListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState<UserListItem | null>(null);
  // User edit form state
  const [editIsActive, setEditIsActive] = useState(false);
  const [editIsSuperuser, setEditIsSuperuser] = useState(false);
  const [editIsVerified, setEditIsVerified] = useState(false);
  // Category state
  const [categories, setCategories] = useState<UICategoryItem[]>([]);
  const [catLoading, setCatLoading] = useState(false);
  const [catError, setCatError] = useState<string | null>(null);
  const [catDialogOpen, setCatDialogOpen] = useState(false);
  const [catDeleteDialogOpen, setCatDeleteDialogOpen] = useState(false);
  const [selectedCat, setSelectedCat] = useState<UICategoryItem | null>(null);
  const [catForm, setCatForm] = useState(emptyCatForm());
  const [catSaving, setCatSaving] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    if (activeTab === 1) loadCategories();
  }, [activeTab]);

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

  const loadCategories = async () => {
    setCatLoading(true);
    setCatError(null);
    try {
      const data = await apiFetch<UICategoryItem[]>("/admin/categories");
      setCategories(data);
    } catch (err) {
      const parsedError = handlePageError(err, "Failed to load categories");
      setCatError(parsedError.userMessage);
    } finally {
      setCatLoading(false);
    }
  };

  const handleCatNewClick = () => {
    setSelectedCat(null);
    setCatForm(emptyCatForm());
    setCatDialogOpen(true);
  };

  const handleCatEditClick = (cat: UICategoryItem) => {
    setSelectedCat(cat);
    setCatForm({
      slug: cat.slug,
      label_en: cat.labels.en ?? "",
      label_fr: cat.labels.fr ?? "",
      desc_en: cat.description?.en ?? "",
      desc_fr: cat.description?.fr ?? "",
      order: cat.order,
    });
    setCatDialogOpen(true);
  };

  const handleCatSave = async () => {
    setCatSaving(true);
    setCatError(null);
    const payload = {
      slug: catForm.slug,
      labels: { en: catForm.label_en, fr: catForm.label_fr },
      description:
        catForm.desc_en || catForm.desc_fr
          ? { en: catForm.desc_en, fr: catForm.desc_fr }
          : null,
      order: catForm.order,
    };
    try {
      if (selectedCat) {
        await apiFetch(`/admin/categories/${selectedCat.id}`, {
          method: "PUT",
          body: JSON.stringify(payload),
        });
      } else {
        await apiFetch("/admin/categories", {
          method: "POST",
          body: JSON.stringify(payload),
        });
      }
      setCatDialogOpen(false);
      await loadCategories();
    } catch (err) {
      const parsedError = handlePageError(err, "Failed to save category");
      setCatError(parsedError.userMessage);
    } finally {
      setCatSaving(false);
    }
  };

  const handleCatDeleteClick = (cat: UICategoryItem) => {
    setSelectedCat(cat);
    setCatDeleteDialogOpen(true);
  };

  const handleCatConfirmDelete = async () => {
    if (!selectedCat) return;
    setCatError(null);
    try {
      await apiFetch(`/admin/categories/${selectedCat.id}`, {
        method: "DELETE",
      });
      setCatDeleteDialogOpen(false);
      await loadCategories();
    } catch (err) {
      const parsedError = handlePageError(err, "Failed to delete category");
      setCatError(parsedError.userMessage);
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
        <Tabs
          value={activeTab}
          onChange={(_, v) => setActiveTab(v)}
          sx={{ mt: 2 }}
        >
          <Tab icon={<PeopleIcon />} iconPosition="start" label="Users" />
          <Tab icon={<CategoryIcon />} iconPosition="start" label="UI Categories" />
        </Tabs>
      </Paper>

      {/* ── Users tab ── */}
      {activeTab === 0 && <>

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

      </>}

      {/* ── UI Categories tab ── */}
      {activeTab === 1 && (
        <Paper sx={{ p: 3 }}>
          <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
            <Typography variant="h5">UI Categories</Typography>
            <Button
              variant="contained"
              startIcon={<AddIcon />}
              onClick={handleCatNewClick}
            >
              New Category
            </Button>
          </Box>

          {catError && <Alert severity="error" sx={{ mb: 2 }}>{catError}</Alert>}

          {catLoading ? (
            <Typography>Loading...</Typography>
          ) : (
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Slug</TableCell>
                    <TableCell>Label (EN)</TableCell>
                    <TableCell>Label (FR)</TableCell>
                    <TableCell>Order</TableCell>
                    <TableCell>Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {categories.map((cat) => (
                    <TableRow key={cat.id}>
                      <TableCell><code>{cat.slug}</code></TableCell>
                      <TableCell>{cat.labels.en ?? "—"}</TableCell>
                      <TableCell>{cat.labels.fr ?? "—"}</TableCell>
                      <TableCell>{cat.order}</TableCell>
                      <TableCell>
                        <IconButton
                          size="small"
                          onClick={() => handleCatEditClick(cat)}
                          title="Edit category"
                        >
                          <EditIcon fontSize="small" />
                        </IconButton>
                        <IconButton
                          size="small"
                          color="error"
                          onClick={() => handleCatDeleteClick(cat)}
                          title="Delete category"
                        >
                          <DeleteIcon fontSize="small" />
                        </IconButton>
                      </TableCell>
                    </TableRow>
                  ))}
                  {categories.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={5} align="center">
                        <Typography color="text.secondary">No categories yet</Typography>
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </Paper>
      )}

      {/* Category create/edit dialog */}
      <Dialog open={catDialogOpen} onClose={() => setCatDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{selectedCat ? "Edit Category" : "New Category"}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField
              label="Slug"
              value={catForm.slug}
              onChange={(e) => setCatForm((f) => ({ ...f, slug: e.target.value }))}
              fullWidth
              required
              helperText="Unique identifier, e.g. drugs"
            />
            <TextField
              label="Label (EN)"
              value={catForm.label_en}
              onChange={(e) => setCatForm((f) => ({ ...f, label_en: e.target.value }))}
              fullWidth
              required
            />
            <TextField
              label="Label (FR)"
              value={catForm.label_fr}
              onChange={(e) => setCatForm((f) => ({ ...f, label_fr: e.target.value }))}
              fullWidth
            />
            <TextField
              label="Description (EN)"
              value={catForm.desc_en}
              onChange={(e) => setCatForm((f) => ({ ...f, desc_en: e.target.value }))}
              fullWidth
              multiline
              rows={2}
            />
            <TextField
              label="Description (FR)"
              value={catForm.desc_fr}
              onChange={(e) => setCatForm((f) => ({ ...f, desc_fr: e.target.value }))}
              fullWidth
              multiline
              rows={2}
            />
            <TextField
              label="Display Order"
              type="number"
              value={catForm.order}
              onChange={(e) => setCatForm((f) => ({ ...f, order: parseInt(e.target.value) || 0 }))}
              fullWidth
              inputProps={{ min: 0 }}
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCatDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={handleCatSave}
            variant="contained"
            disabled={catSaving || !catForm.slug || !catForm.label_en}
          >
            {catSaving ? "Saving…" : "Save"}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Category delete confirmation dialog */}
      <Dialog open={catDeleteDialogOpen} onClose={() => setCatDeleteDialogOpen(false)}>
        <DialogTitle>Delete Category</DialogTitle>
        <DialogContent>
          <Typography>
            Delete category <strong>{selectedCat?.slug}</strong>? This cannot be undone.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCatDeleteDialogOpen(false)}>Cancel</Button>
          <Button color="error" variant="contained" onClick={handleCatConfirmDelete}>
            Delete
          </Button>
        </DialogActions>
      </Dialog>

      <AdminEditDialog
        open={editDialogOpen}
        user={selectedUser}
        isActive={editIsActive}
        isSuperuser={editIsSuperuser}
        isVerified={editIsVerified}
        onIsActiveChange={setEditIsActive}
        onIsSuperuserChange={setEditIsSuperuser}
        onIsVerifiedChange={setEditIsVerified}
        onSave={handleSaveEdit}
        onClose={() => setEditDialogOpen(false)}
      />

      <AdminDeleteDialog
        open={deleteDialogOpen}
        user={selectedUser}
        onConfirm={handleConfirmDelete}
        onClose={() => setDeleteDialogOpen(false)}
      />
    </Stack>
  );
}
