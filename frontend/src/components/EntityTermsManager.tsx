/**
 * EntityTermsManager
 *
 * Component for managing entity terms (aliases/synonyms).
 * Supports adding, editing, deleting, and reordering terms.
 *
 * Features:
 * - Display terms grouped by language
 * - Inline editing with validation
 * - Drag-and-drop reordering (future enhancement)
 * - Language selection
 * - Display order management
 */

import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import {
  Box,
  Typography,
  TextField,
  Button,
  IconButton,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  Paper,
  Stack,
  Chip,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Divider,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import DeleteIcon from "@mui/icons-material/Delete";
import EditIcon from "@mui/icons-material/Edit";
import SaveIcon from "@mui/icons-material/Save";
import CancelIcon from "@mui/icons-material/Cancel";
import TranslateIcon from "@mui/icons-material/Translate";

import {
  listEntityTerms,
  createEntityTerm,
  updateEntityTerm,
  deleteEntityTerm,
  EntityTermRead,
  EntityTermWrite,
} from "../api/entityTerms";

interface EntityTermsManagerProps {
  entityId: string;
  readonly?: boolean;
}

interface TermFormData {
  term: string;
  language: string;
  display_order: number | null;
}

const LANGUAGE_OPTIONS = [
  { code: "", label: "International / No language" },
  { code: "en", label: "English" },
  { code: "fr", label: "French" },
  { code: "es", label: "Spanish" },
  { code: "de", label: "German" },
  { code: "it", label: "Italian" },
  { code: "pt", label: "Portuguese" },
  { code: "zh", label: "Chinese" },
  { code: "ja", label: "Japanese" },
];

export function EntityTermsManager({
  entityId,
  readonly = false,
}: EntityTermsManagerProps) {
  const { t } = useTranslation();

  const [terms, setTerms] = useState<EntityTermRead[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form state
  const [isAdding, setIsAdding] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [formData, setFormData] = useState<TermFormData>({
    term: "",
    language: "",
    display_order: null,
  });

  // Delete confirmation dialog
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [termToDelete, setTermToDelete] = useState<EntityTermRead | null>(null);

  // Load terms
  useEffect(() => {
    loadTerms();
  }, [entityId]);

  const loadTerms = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listEntityTerms(entityId);
      setTerms(data);
    } catch (err) {
      console.error("Failed to load terms:", err);
      setError("Failed to load terms");
    } finally {
      setLoading(false);
    }
  };

  const handleAdd = () => {
    setIsAdding(true);
    setEditingId(null);
    setFormData({
      term: "",
      language: "",
      display_order: null,
    });
  };

  const handleEdit = (term: EntityTermRead) => {
    setEditingId(term.id);
    setIsAdding(false);
    setFormData({
      term: term.term,
      language: term.language || "",
      display_order: term.display_order,
    });
  };

  const handleCancel = () => {
    setIsAdding(false);
    setEditingId(null);
    setFormData({
      term: "",
      language: "",
      display_order: null,
    });
  };

  const handleSave = async () => {
    if (!formData.term.trim()) {
      setError("Term cannot be empty");
      return;
    }

    setError(null);
    setLoading(true);

    try {
      const payload: EntityTermWrite = {
        term: formData.term.trim(),
        language: formData.language || null,
        display_order: formData.display_order,
      };

      if (isAdding) {
        await createEntityTerm(entityId, payload);
      } else if (editingId) {
        await updateEntityTerm(entityId, editingId, payload);
      }

      await loadTerms();
      handleCancel();
    } catch (err: any) {
      console.error("Failed to save term:", err);
      if (err.message && err.message.includes("already exists")) {
        setError("This term already exists for this language");
      } else {
        setError("Failed to save term");
      }
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteClick = (term: EntityTermRead) => {
    setTermToDelete(term);
    setDeleteDialogOpen(true);
  };

  const handleDeleteConfirm = async () => {
    if (!termToDelete) return;

    setLoading(true);
    setError(null);

    try {
      await deleteEntityTerm(entityId, termToDelete.id);
      await loadTerms();
      setDeleteDialogOpen(false);
      setTermToDelete(null);
    } catch (err) {
      console.error("Failed to delete term:", err);
      setError("Failed to delete term");
    } finally {
      setLoading(false);
    }
  };

  const getLanguageLabel = (code: string | null): string => {
    if (!code) return "International";
    const option = LANGUAGE_OPTIONS.find((opt) => opt.code === code);
    return option ? option.label : code;
  };

  // Group terms by language for display
  const groupedTerms = terms.reduce((acc, term) => {
    const lang = term.language || "international";
    if (!acc[lang]) acc[lang] = [];
    acc[lang].push(term);
    return acc;
  }, {} as Record<string, EntityTermRead[]>);

  return (
    <Paper sx={{ p: 2 }}>
      <Stack spacing={2}>
        {/* Header */}
        <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            <TranslateIcon color="action" />
            <Typography variant="h6">
              {t("entityTerms.title", "Alternative Names & Aliases")}
            </Typography>
          </Box>
          {!readonly && !isAdding && !editingId && (
            <Button
              startIcon={<AddIcon />}
              onClick={handleAdd}
              size="small"
              variant="outlined"
            >
              {t("entityTerms.addTerm", "Add Term")}
            </Button>
          )}
        </Box>

        <Typography variant="body2" color="text.secondary">
          {t(
            "entityTerms.description",
            "Add alternative names, synonyms, or translations to help users find this entity."
          )}
        </Typography>

        {error && (
          <Alert severity="error" onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {/* Add/Edit Form */}
        {(isAdding || editingId) && (
          <Paper variant="outlined" sx={{ p: 2, bgcolor: "action.hover" }}>
            <Stack spacing={2}>
              <Typography variant="subtitle2">
                {isAdding
                  ? t("entityTerms.addNew", "Add New Term")
                  : t("entityTerms.editTerm", "Edit Term")}
              </Typography>

              <TextField
                label={t("entityTerms.term", "Term")}
                value={formData.term}
                onChange={(e) =>
                  setFormData({ ...formData, term: e.target.value })
                }
                fullWidth
                size="small"
                required
                autoFocus
              />

              <FormControl fullWidth size="small">
                <InputLabel>{t("entityTerms.language", "Language")}</InputLabel>
                <Select
                  value={formData.language}
                  onChange={(e) =>
                    setFormData({ ...formData, language: e.target.value })
                  }
                  label={t("entityTerms.language", "Language")}
                >
                  {LANGUAGE_OPTIONS.map((opt) => (
                    <MenuItem key={opt.code} value={opt.code}>
                      {opt.label}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              <TextField
                label={t("entityTerms.displayOrder", "Display Order")}
                value={formData.display_order ?? ""}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    display_order: e.target.value
                      ? parseInt(e.target.value)
                      : null,
                  })
                }
                type="number"
                fullWidth
                size="small"
                helperText={t(
                  "entityTerms.displayOrderHelp",
                  "Lower numbers appear first (optional)"
                )}
              />

              <Box sx={{ display: "flex", gap: 1, justifyContent: "flex-end" }}>
                <Button
                  startIcon={<CancelIcon />}
                  onClick={handleCancel}
                  size="small"
                  disabled={loading}
                >
                  {t("common.cancel", "Cancel")}
                </Button>
                <Button
                  startIcon={<SaveIcon />}
                  onClick={handleSave}
                  variant="contained"
                  size="small"
                  disabled={loading || !formData.term.trim()}
                >
                  {t("common.save", "Save")}
                </Button>
              </Box>
            </Stack>
          </Paper>
        )}

        {/* Terms List */}
        {terms.length === 0 && !isAdding ? (
          <Alert severity="info">
            {t(
              "entityTerms.noTerms",
              "No alternative names defined. Add terms to improve searchability."
            )}
          </Alert>
        ) : (
          <Box>
            {Object.entries(groupedTerms).map(([lang, langTerms]) => (
              <Box key={lang} sx={{ mb: 2 }}>
                <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1 }}>
                  {getLanguageLabel(lang === "international" ? null : lang)} (
                  {langTerms.length})
                </Typography>
                <List dense>
                  {langTerms.map((term) => (
                    <ListItem
                      key={term.id}
                      sx={{
                        border: 1,
                        borderColor: "divider",
                        borderRadius: 1,
                        mb: 0.5,
                        bgcolor:
                          editingId === term.id ? "action.selected" : "background.paper",
                      }}
                    >
                      <ListItemText
                        primary={term.term}
                        secondary={
                          term.display_order !== null
                            ? `Display order: ${term.display_order}`
                            : undefined
                        }
                      />
                      {!readonly && (
                        <ListItemSecondaryAction>
                          <IconButton
                            edge="end"
                            size="small"
                            onClick={() => handleEdit(term)}
                            disabled={loading || isAdding || editingId !== null}
                            sx={{ mr: 0.5 }}
                          >
                            <EditIcon fontSize="small" />
                          </IconButton>
                          <IconButton
                            edge="end"
                            size="small"
                            onClick={() => handleDeleteClick(term)}
                            disabled={loading || isAdding || editingId !== null}
                          >
                            <DeleteIcon fontSize="small" />
                          </IconButton>
                        </ListItemSecondaryAction>
                      )}
                    </ListItem>
                  ))}
                </List>
              </Box>
            ))}
          </Box>
        )}

        {/* Summary */}
        {terms.length > 0 && (
          <Divider>
            <Chip
              label={t("entityTerms.totalTerms", "{{count}} term(s)", {
                count: terms.length,
              })}
              size="small"
            />
          </Divider>
        )}
      </Stack>

      {/* Delete Confirmation Dialog */}
      <Dialog
        open={deleteDialogOpen}
        onClose={() => !loading && setDeleteDialogOpen(false)}
      >
        <DialogTitle>
          {t("entityTerms.deleteConfirmTitle", "Delete Term?")}
        </DialogTitle>
        <DialogContent>
          <Typography>
            {t(
              "entityTerms.deleteConfirmMessage",
              'Are you sure you want to delete the term "{{term}}"?',
              { term: termToDelete?.term }
            )}
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialogOpen(false)} disabled={loading}>
            {t("common.cancel", "Cancel")}
          </Button>
          <Button
            onClick={handleDeleteConfirm}
            color="error"
            variant="contained"
            disabled={loading}
          >
            {t("common.delete", "Delete")}
          </Button>
        </DialogActions>
      </Dialog>
    </Paper>
  );
}
