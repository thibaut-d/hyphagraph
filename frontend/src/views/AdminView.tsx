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
  Select,
  MenuItem,
  FormControl,
  InputLabel,
} from "@mui/material";
import EditIcon from "@mui/icons-material/Edit";
import DeleteIcon from "@mui/icons-material/Delete";
import AddIcon from "@mui/icons-material/Add";
import CallMergeIcon from "@mui/icons-material/CallMerge";
import PeopleIcon from "@mui/icons-material/People";
import VerifiedUserIcon from "@mui/icons-material/VerifiedUser";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import EmailIcon from "@mui/icons-material/Email";
import CategoryIcon from "@mui/icons-material/Category";
import BugReportIcon from "@mui/icons-material/BugReport";
import AccountTreeIcon from "@mui/icons-material/AccountTree";
import CleaningServicesIcon from "@mui/icons-material/CleaningServices";
import LockIcon from "@mui/icons-material/Lock";
import LabelIcon from "@mui/icons-material/Label";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import RadioButtonUncheckedIcon from "@mui/icons-material/RadioButtonUnchecked";
import { apiFetch } from "../api/client";
import {
  applyDuplicateRelationReview,
  applyRoleCorrection,
  critiqueGraphCleaningCandidates,
  getGraphCleaningAnalysis,
  listGraphCleaningDecisions,
  saveGraphCleaningDecision,
  type GraphCleaningAnalysis,
  type GraphCleaningCritiqueItem,
  type GraphCleaningDecision,
} from "../api/graphCleaning";
import { usePageErrorHandler } from "../hooks/usePageErrorHandler";
import { AdminEditDialog } from "../components/admin/AdminEditDialog";
import { AdminDeleteDialog } from "../components/admin/AdminDeleteDialog";
import {
  GraphCleaningPanel,
  type CleaningRecommendationFilter,
  type CleaningStatusFilter,
  type CleaningTypeFilter,
  type EntityMergeCandidate,
} from "../components/admin/GraphCleaningPanel";

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

interface EntityCategoryItem {
  category_id: string;
  label: Record<string, string>;
  description: string;
  examples: string | null;
  is_active: boolean;
  is_system: boolean;
  usage_count: number;
}

interface RelationTypeItem {
  type_id: string;
  label: Record<string, string>;
  description: string;
  examples: string | null;
  aliases: string[] | null;
  category: string | null;
  usage_count: number;
  is_system: boolean;
}

interface EntitySearchResult {
  id: string;
  slug: string;
  summary: Record<string, string> | null;
}

interface BugReportItem {
  id: string;
  user_id: string | null;
  message: string;
  page_url: string | null;
  user_agent: string | null;
  created_at: string;
  resolved: boolean;
  resolved_at: string | null;
  resolved_by: string | null;
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

const emptyRelTypeForm = () => ({
  type_id: "",
  label_en: "",
  description: "",
  examples: "",
  aliases: "",
  category: "",
});

const emptyEntityCatForm = () => ({
  category_id: "",
  label_en: "",
  description: "",
  examples: "",
});

export function AdminView() {
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
  // Bug report state
  const [bugReports, setBugReports] = useState<BugReportItem[]>([]);
  const [bugLoading, setBugLoading] = useState(false);
  const [bugError, setBugError] = useState<string | null>(null);
  // Relation type state
  const [relTypes, setRelTypes] = useState<RelationTypeItem[]>([]);
  const [relTypeLoading, setRelTypeLoading] = useState(false);
  const [relTypeError, setRelTypeError] = useState<string | null>(null);
  const [relTypeDialogOpen, setRelTypeDialogOpen] = useState(false);
  const [relTypeDeleteDialogOpen, setRelTypeDeleteDialogOpen] = useState(false);
  const [selectedRelType, setSelectedRelType] = useState<RelationTypeItem | null>(null);
  const [relTypeForm, setRelTypeForm] = useState(emptyRelTypeForm());
  const [relTypeSaving, setRelTypeSaving] = useState(false);
  const [relTypeMergeDialogOpen, setRelTypeMergeDialogOpen] = useState(false);
  const [relTypeMergeSource, setRelTypeMergeSource] = useState<RelationTypeItem | null>(null);
  const [relTypeMergeTargetId, setRelTypeMergeTargetId] = useState("");
  const [relTypeMergePreview, setRelTypeMergePreview] = useState<{ pending_staged: number; relation_revisions: number } | null>(null);
  const [relTypeMergeSaving, setRelTypeMergeSaving] = useState(false);
  // Entity category state
  const [entityCats, setEntityCats] = useState<EntityCategoryItem[]>([]);
  const [entityCatLoading, setEntityCatLoading] = useState(false);
  const [entityCatError, setEntityCatError] = useState<string | null>(null);
  const [entityCatDialogOpen, setEntityCatDialogOpen] = useState(false);
  const [entityCatDeleteDialogOpen, setEntityCatDeleteDialogOpen] = useState(false);
  const [selectedEntityCat, setSelectedEntityCat] = useState<EntityCategoryItem | null>(null);
  const [entityCatForm, setEntityCatForm] = useState(emptyEntityCatForm());
  const [entityCatSaving, setEntityCatSaving] = useState(false);
  const [entityCatMergeDialogOpen, setEntityCatMergeDialogOpen] = useState(false);
  const [entityCatMergeSource, setEntityCatMergeSource] = useState<EntityCategoryItem | null>(null);
  const [entityCatMergeTargetId, setEntityCatMergeTargetId] = useState("");
  const [entityCatMergePendingStaged, setEntityCatMergePendingStaged] = useState<number | null>(null);
  const [entityCatMergeSaving, setEntityCatMergeSaving] = useState(false);
  // Entity graph merge state
  const [entityMergeSource, setEntityMergeSource] = useState<EntitySearchResult | null>(null);
  const [entityMergeTarget, setEntityMergeTarget] = useState<EntitySearchResult | null>(null);
  const [entityMergeSourceOptions, setEntityMergeSourceOptions] = useState<EntitySearchResult[]>([]);
  const [entityMergeTargetOptions, setEntityMergeTargetOptions] = useState<EntitySearchResult[]>([]);
  const [entityMergeSourceLoading, setEntityMergeSourceLoading] = useState(false);
  const [entityMergeTargetLoading, setEntityMergeTargetLoading] = useState(false);
  const [entityMergeConfirmOpen, setEntityMergeConfirmOpen] = useState(false);
  const [entityMergeSaving, setEntityMergeSaving] = useState(false);
  const [entityMergeError, setEntityMergeError] = useState<string | null>(null);
  const [entityMergeResult, setEntityMergeResult] = useState<{ source_slug: string; target_slug: string; relations_moved: number } | null>(null);
  const [mergeCandidates, setMergeCandidates] = useState<EntityMergeCandidate[]>([]);
  const [mergeCandidatesLoading, setMergeCandidatesLoading] = useState(false);
  const [mergeCandidatesScanned, setMergeCandidatesScanned] = useState(false);
  const [mergeCandidateThreshold, setMergeCandidateThreshold] = useState(0.86);
  const [cleaningAnalysis, setCleaningAnalysis] = useState<GraphCleaningAnalysis>({
    duplicate_relations: [],
    role_consistency: [],
  });
  const [cleaningDecisions, setCleaningDecisions] = useState<GraphCleaningDecision[]>([]);
  const [cleaningCritiques, setCleaningCritiques] = useState<GraphCleaningCritiqueItem[]>([]);
  const [cleaningCritiqueBatchSize, setCleaningCritiqueBatchSize] = useState(5);
  const [cleaningActionBusy, setCleaningActionBusy] = useState(false);
  const [cleaningStatusFilter, setCleaningStatusFilter] = useState<CleaningStatusFilter>("open");
  const [cleaningTypeFilter, setCleaningTypeFilter] = useState<CleaningTypeFilter>("all");
  const [cleaningRecommendationFilter, setCleaningRecommendationFilter] =
    useState<CleaningRecommendationFilter>("all");
  const [duplicateDialogOpen, setDuplicateDialogOpen] = useState(false);
  const [duplicateDialogFingerprint, setDuplicateDialogFingerprint] = useState("");
  const [duplicateDialogRelationIds, setDuplicateDialogRelationIds] = useState<string[]>([]);
  const [duplicateDialogRationale, setDuplicateDialogRationale] = useState("");
  const [roleDialogOpen, setRoleDialogOpen] = useState(false);
  const [roleDialogEntityId, setRoleDialogEntityId] = useState("");
  const [roleDialogEntityLabel, setRoleDialogEntityLabel] = useState("");
  const [roleDialogRelationKind, setRoleDialogRelationKind] = useState<string | null>(null);
  const [roleDialogRelationId, setRoleDialogRelationId] = useState("");
  const [roleDialogFromRole, setRoleDialogFromRole] = useState("");
  const [roleDialogToRole, setRoleDialogToRole] = useState("");
  const [roleDialogRationale, setRoleDialogRationale] = useState("");

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    if (activeTab === 1) loadCategories();
    if (activeTab === 2) loadBugReports();
    if (activeTab === 3) loadRelTypes();
    if (activeTab === 4) loadEntityCats();
    if (activeTab === 5) loadCleaningDecisions();
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

  const loadBugReports = async () => {
    setBugLoading(true);
    setBugError(null);
    try {
      const data = await apiFetch<BugReportItem[]>("/bug-reports");
      setBugReports(data);
    } catch (err) {
      const parsedError = handlePageError(err, "Failed to load bug reports");
      setBugError(parsedError.userMessage);
    } finally {
      setBugLoading(false);
    }
  };

  const handleToggleResolved = async (report: BugReportItem) => {
    try {
      const updated = await apiFetch<BugReportItem>(`/bug-reports/${report.id}`, {
        method: "PATCH",
        body: JSON.stringify({ resolved: !report.resolved }),
      });
      setBugReports((prev) =>
        prev.map((r) => (r.id === updated.id ? updated : r))
      );
    } catch (err) {
      const parsedError = handlePageError(err, "Failed to update bug report");
      setBugError(parsedError.userMessage);
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

  const loadRelTypes = async () => {
    setRelTypeLoading(true);
    setRelTypeError(null);
    try {
      const data = await apiFetch<RelationTypeItem[]>("/relation-types/");
      setRelTypes(data);
    } catch (err) {
      const parsedError = handlePageError(err, "Failed to load relation types");
      setRelTypeError(parsedError.userMessage);
    } finally {
      setRelTypeLoading(false);
    }
  };

  const handleRelTypeNewClick = () => {
    setSelectedRelType(null);
    setRelTypeForm(emptyRelTypeForm());
    setRelTypeDialogOpen(true);
  };

  const handleRelTypeEditClick = (rt: RelationTypeItem) => {
    setSelectedRelType(rt);
    setRelTypeForm({
      type_id: rt.type_id,
      label_en: rt.label.en ?? "",
      description: rt.description,
      examples: rt.examples ?? "",
      aliases: (rt.aliases ?? []).join(", "),
      category: rt.category ?? "",
    });
    setRelTypeDialogOpen(true);
  };

  const handleRelTypeSave = async () => {
    setRelTypeSaving(true);
    setRelTypeError(null);
    const aliases = relTypeForm.aliases
      ? relTypeForm.aliases.split(",").map((a) => a.trim()).filter(Boolean)
      : [];
    try {
      if (selectedRelType) {
        await apiFetch(`/relation-types/${selectedRelType.type_id}`, {
          method: "PATCH",
          body: JSON.stringify({
            label: relTypeForm.label_en ? { en: relTypeForm.label_en } : undefined,
            description: relTypeForm.description || undefined,
            examples: relTypeForm.examples || null,
            aliases: aliases.length > 0 ? aliases : null,
            category: relTypeForm.category || null,
          }),
        });
      } else {
        await apiFetch("/relation-types/", {
          method: "POST",
          body: JSON.stringify({
            type_id: relTypeForm.type_id,
            label: { en: relTypeForm.label_en },
            description: relTypeForm.description,
            examples: relTypeForm.examples || null,
            aliases: aliases.length > 0 ? aliases : null,
            category: relTypeForm.category || null,
          }),
        });
      }
      setRelTypeDialogOpen(false);
      await loadRelTypes();
    } catch (err) {
      const parsedError = handlePageError(err, "Failed to save relation type");
      setRelTypeError(parsedError.userMessage);
    } finally {
      setRelTypeSaving(false);
    }
  };

  const handleRelTypeDeleteClick = (rt: RelationTypeItem) => {
    setSelectedRelType(rt);
    setRelTypeDeleteDialogOpen(true);
  };

  const handleRelTypeConfirmDelete = async () => {
    if (!selectedRelType) return;
    setRelTypeError(null);
    try {
      await apiFetch(`/relation-types/${selectedRelType.type_id}`, {
        method: "DELETE",
      });
      setRelTypeDeleteDialogOpen(false);
      await loadRelTypes();
    } catch (err) {
      const parsedError = handlePageError(err, "Failed to delete relation type");
      setRelTypeError(parsedError.userMessage);
    }
  };

  const handleRelTypeMergeClick = async (rt: RelationTypeItem) => {
    setRelTypeMergeSource(rt);
    setRelTypeMergeTargetId("");
    setRelTypeMergePreview(null);
    setRelTypeMergeDialogOpen(true);
    try {
      const preview = await apiFetch<{ pending_staged: number; relation_revisions: number }>(
        `/relation-types/${rt.type_id}/merge-preview`
      );
      setRelTypeMergePreview(preview);
    } catch {
      setRelTypeMergePreview({ pending_staged: 0, relation_revisions: 0 });
    }
  };

  const handleRelTypeMergeConfirm = async () => {
    if (!relTypeMergeSource || !relTypeMergeTargetId) return;
    setRelTypeMergeSaving(true);
    setRelTypeError(null);
    try {
      await apiFetch(
        `/relation-types/${relTypeMergeSource.type_id}/merge-into/${relTypeMergeTargetId}`,
        { method: "POST" }
      );
      setRelTypeMergeDialogOpen(false);
      await loadRelTypes();
    } catch (err) {
      const parsedError = handlePageError(err, "Failed to merge relation types");
      setRelTypeError(parsedError.userMessage);
    } finally {
      setRelTypeMergeSaving(false);
    }
  };

  const loadEntityCats = async () => {
    setEntityCatLoading(true);
    setEntityCatError(null);
    try {
      const data = await apiFetch<EntityCategoryItem[]>("/entity-categories/all");
      setEntityCats(data);
    } catch (err) {
      const parsedError = handlePageError(err, "Failed to load entity categories");
      setEntityCatError(parsedError.userMessage);
    } finally {
      setEntityCatLoading(false);
    }
  };

  const handleEntityCatNewClick = () => {
    setSelectedEntityCat(null);
    setEntityCatForm(emptyEntityCatForm());
    setEntityCatDialogOpen(true);
  };

  const handleEntityCatEditClick = (cat: EntityCategoryItem) => {
    setSelectedEntityCat(cat);
    setEntityCatForm({
      category_id: cat.category_id,
      label_en: cat.label.en ?? "",
      description: cat.description,
      examples: cat.examples ?? "",
    });
    setEntityCatDialogOpen(true);
  };

  const handleEntityCatSave = async () => {
    setEntityCatSaving(true);
    setEntityCatError(null);
    try {
      if (selectedEntityCat) {
        await apiFetch(`/entity-categories/${selectedEntityCat.category_id}`, {
          method: "PATCH",
          body: JSON.stringify({
            label: entityCatForm.label_en ? { en: entityCatForm.label_en } : undefined,
            description: entityCatForm.description || undefined,
            examples: entityCatForm.examples || null,
          }),
        });
      } else {
        await apiFetch("/entity-categories/", {
          method: "POST",
          body: JSON.stringify({
            category_id: entityCatForm.category_id,
            label: { en: entityCatForm.label_en },
            description: entityCatForm.description,
            examples: entityCatForm.examples || null,
          }),
        });
      }
      setEntityCatDialogOpen(false);
      await loadEntityCats();
    } catch (err) {
      const parsedError = handlePageError(err, "Failed to save entity category");
      setEntityCatError(parsedError.userMessage);
    } finally {
      setEntityCatSaving(false);
    }
  };

  const handleEntityCatDeleteClick = (cat: EntityCategoryItem) => {
    setSelectedEntityCat(cat);
    setEntityCatDeleteDialogOpen(true);
  };

  const handleEntityCatConfirmDelete = async () => {
    if (!selectedEntityCat) return;
    setEntityCatError(null);
    try {
      await apiFetch(`/entity-categories/${selectedEntityCat.category_id}`, {
        method: "DELETE",
      });
      setEntityCatDeleteDialogOpen(false);
      await loadEntityCats();
    } catch (err) {
      const parsedError = handlePageError(err, "Failed to delete entity category");
      setEntityCatError(parsedError.userMessage);
    }
  };

  const handleEntityCatMergeClick = async (cat: EntityCategoryItem) => {
    setEntityCatMergeSource(cat);
    setEntityCatMergeTargetId("");
    setEntityCatMergePendingStaged(null);
    setEntityCatMergeDialogOpen(true);
    try {
      const preview = await apiFetch<{ pending_staged: number }>(
        `/entity-categories/${cat.category_id}/merge-preview`
      );
      setEntityCatMergePendingStaged(preview.pending_staged);
    } catch {
      setEntityCatMergePendingStaged(0);
    }
  };

  const handleEntityCatMergeConfirm = async () => {
    if (!entityCatMergeSource || !entityCatMergeTargetId) return;
    setEntityCatMergeSaving(true);
    setEntityCatError(null);
    try {
      await apiFetch(
        `/entity-categories/${entityCatMergeSource.category_id}/merge-into/${entityCatMergeTargetId}`,
        { method: "POST" }
      );
      setEntityCatMergeDialogOpen(false);
      await loadEntityCats();
    } catch (err) {
      const parsedError = handlePageError(err, "Failed to merge entity categories");
      setEntityCatError(parsedError.userMessage);
    } finally {
      setEntityCatMergeSaving(false);
    }
  };

  const searchEntities = async (
    query: string,
    setOptions: (opts: EntitySearchResult[]) => void,
    setSearchLoading: (v: boolean) => void,
  ) => {
    if (!query || query.length < 2) {
      setOptions([]);
      return;
    }
    setSearchLoading(true);
    try {
      const data = await apiFetch<{ items: EntitySearchResult[]; total: number }>(
        `/entities/?search=${encodeURIComponent(query)}&limit=10`
      );
      setOptions(data.items);
    } catch {
      setOptions([]);
    } finally {
      setSearchLoading(false);
    }
  };

  const handleEntityMergeConfirm = async () => {
    if (!entityMergeSource || !entityMergeTarget) return;
    setEntityMergeSaving(true);
    setEntityMergeError(null);
    setEntityMergeResult(null);
    try {
      const result = await apiFetch<{ source_slug: string; target_slug: string; relations_moved: number }>(
        `/entities/${entityMergeSource.id}/merge-into/${entityMergeTarget.id}`,
        { method: "POST" }
      );
      setEntityMergeResult(result);
      setEntityMergeConfirmOpen(false);
      setEntityMergeSource(null);
      setEntityMergeTarget(null);
      setEntityMergeSourceOptions([]);
      setEntityMergeTargetOptions([]);
    } catch (err) {
      const parsedError = handlePageError(err, "Failed to merge entities");
      setEntityMergeError(parsedError.userMessage);
      setEntityMergeConfirmOpen(false);
    } finally {
      setEntityMergeSaving(false);
    }
  };

  const loadMergeCandidates = async () => {
    setMergeCandidatesLoading(true);
    setEntityMergeError(null);
    try {
      const [entityCandidates, analysis, decisions] = await Promise.all([
        apiFetch<EntityMergeCandidate[]>(
          `/entities/merge-candidates?similarity_threshold=${mergeCandidateThreshold}&limit=50`
        ),
        getGraphCleaningAnalysis(50),
        listGraphCleaningDecisions(),
      ]);
      setMergeCandidates(entityCandidates);
      setCleaningAnalysis(analysis);
      setCleaningDecisions(decisions);
      setMergeCandidatesScanned(true);
    } catch (err) {
      const parsedError = handlePageError(err, "Failed to load graph cleaning candidates");
      setEntityMergeError(parsedError.userMessage);
    } finally {
      setMergeCandidatesLoading(false);
    }
  };

  const loadCleaningDecisions = async () => {
    setEntityMergeError(null);
    try {
      setCleaningDecisions(await listGraphCleaningDecisions());
    } catch (err) {
      const parsedError = handlePageError(err, "Failed to load graph cleaning decisions");
      setEntityMergeError(parsedError.userMessage);
    }
  };

  const reviewMergeCandidate = (candidate: EntityMergeCandidate) => {
    setEntityMergeSource(candidate.source);
    setEntityMergeTarget(candidate.target);
    setEntityMergeConfirmOpen(true);
  };

  const getCleaningDecision = (candidateType: GraphCleaningDecision["candidate_type"], fingerprint: string) =>
    cleaningDecisions.find(
      (decision) =>
        decision.candidate_type === candidateType &&
        decision.candidate_fingerprint === fingerprint,
    );

  const getCleaningCritique = (fingerprint: string) =>
    cleaningCritiques.find((critique) => critique.candidate_fingerprint === fingerprint);

  const shouldShowCleaningCandidate = (
    candidateType: GraphCleaningDecision["candidate_type"],
    fingerprint: string,
  ) => {
    if (cleaningTypeFilter !== "all" && cleaningTypeFilter !== candidateType) return false;
    const decision = getCleaningDecision(candidateType, fingerprint);
    if (cleaningStatusFilter !== "all" && (decision?.status ?? "open") !== cleaningStatusFilter) {
      return false;
    }
    const critique = getCleaningCritique(fingerprint);
    if (cleaningRecommendationFilter === "no_critique") return !critique;
    if (cleaningRecommendationFilter !== "all") {
      return critique?.recommendation === cleaningRecommendationFilter;
    }
    return true;
  };

  const saveCleaningDecision = async (
    candidateType: GraphCleaningDecision["candidate_type"],
    fingerprint: string,
    status: GraphCleaningDecision["status"],
    notes: string,
    decisionPayload?: Record<string, unknown>,
  ) => {
    setCleaningActionBusy(true);
    setEntityMergeError(null);
    try {
      await saveGraphCleaningDecision({
        candidate_type: candidateType,
        candidate_fingerprint: fingerprint,
        status,
        notes,
        decision_payload: decisionPayload ?? null,
      });
      await loadCleaningDecisions();
    } catch (err) {
      const parsedError = handlePageError(err, "Failed to save graph cleaning decision");
      setEntityMergeError(parsedError.userMessage);
    } finally {
      setCleaningActionBusy(false);
    }
  };

  const allCleaningCritiqueCandidates = () => [
    ...mergeCandidates.map((candidate) => ({
      candidate_fingerprint: `${candidate.source.id}:${candidate.target.id}`,
      candidate_type: "entity_merge",
      source_slug: candidate.source.slug,
      target_slug: candidate.target.slug,
      reason: candidate.reason,
      similarity: candidate.similarity,
    })),
    ...cleaningAnalysis.duplicate_relations.map((candidate) => ({
      ...candidate,
      candidate_type: "duplicate_relation",
      candidate_fingerprint: candidate.fingerprint,
    })),
    ...cleaningAnalysis.role_consistency.map((candidate) => ({
      ...candidate,
      candidate_type: "role_consistency",
      candidate_fingerprint: `${candidate.entity_id}:${candidate.relation_kind ?? "unknown"}`,
    })),
  ];

  const totalCleaningCritiqueCandidates = allCleaningCritiqueCandidates().length;
  const remainingCleaningCritiqueCandidates = allCleaningCritiqueCandidates().filter(
    (candidate) => !getCleaningCritique(String(candidate.candidate_fingerprint)),
  ).length;

  const runCleaningCritique = async () => {
    setCleaningActionBusy(true);
    setEntityMergeError(null);
    try {
      const candidates = allCleaningCritiqueCandidates()
        .filter((candidate) => !getCleaningCritique(String(candidate.candidate_fingerprint)))
        .slice(0, cleaningCritiqueBatchSize);
      if (candidates.length === 0) {
        return;
      }
      const critique = await critiqueGraphCleaningCandidates(candidates);
      setCleaningCritiques((current) => {
        const merged = new Map(current.map((item) => [item.candidate_fingerprint, item]));
        critique.items.forEach((item) => merged.set(item.candidate_fingerprint, item));
        return Array.from(merged.values());
      });
    } catch (err) {
      const parsedError = handlePageError(err, "Failed to run LLM critique");
      setEntityMergeError(parsedError.userMessage);
    } finally {
      setCleaningActionBusy(false);
    }
  };

  const runSingleCleaningCritique = async (candidate: Record<string, unknown>) => {
    setCleaningActionBusy(true);
    setEntityMergeError(null);
    try {
      const critique = await critiqueGraphCleaningCandidates([candidate]);
      setCleaningCritiques((current) => {
        const merged = new Map(current.map((item) => [item.candidate_fingerprint, item]));
        critique.items.forEach((item) => merged.set(item.candidate_fingerprint, item));
        return Array.from(merged.values());
      });
    } catch (err) {
      const parsedError = handlePageError(err, "Failed to run LLM critique");
      setEntityMergeError(parsedError.userMessage);
    } finally {
      setCleaningActionBusy(false);
    }
  };

  const openDuplicateDialog = (fingerprint: string, relationIds: string[]) => {
    setDuplicateDialogFingerprint(fingerprint);
    setDuplicateDialogRelationIds(relationIds);
    setDuplicateDialogRationale("");
    setDuplicateDialogOpen(true);
  };

  const applyDuplicateCandidate = async () => {
    const duplicateIds = duplicateDialogRelationIds.slice(1);
    if (duplicateIds.length === 0 || !duplicateDialogRationale.trim()) return;
    setCleaningActionBusy(true);
    setEntityMergeError(null);
    try {
      await applyDuplicateRelationReview({
        duplicate_relation_ids: duplicateIds,
        rationale: duplicateDialogRationale.trim(),
        candidate_fingerprint: duplicateDialogFingerprint,
      });
      setDuplicateDialogOpen(false);
      await loadMergeCandidates();
    } catch (err) {
      const parsedError = handlePageError(err, "Failed to apply duplicate relation review");
      setEntityMergeError(parsedError.userMessage);
    } finally {
      setCleaningActionBusy(false);
    }
  };

  const applyRoleCandidate = async (candidate: {
    entity_id: string;
    entity_slug?: string | null;
    relation_kind: string | null;
    usages: Array<{ role_type: string; relation_ids: string[] }>;
  }) => {
    const fromUsage = candidate.usages[0];
    const relationId = fromUsage?.relation_ids[0];
    if (!relationId || !fromUsage) return;
    setRoleDialogEntityId(candidate.entity_id);
    setRoleDialogEntityLabel(candidate.entity_slug ?? candidate.entity_id);
    setRoleDialogRelationKind(candidate.relation_kind);
    setRoleDialogRelationId(relationId);
    setRoleDialogFromRole(fromUsage.role_type);
    setRoleDialogToRole("");
    setRoleDialogRationale("");
    setRoleDialogOpen(true);
  };

  const confirmRoleCorrection = async () => {
    if (!roleDialogRelationId || !roleDialogToRole.trim() || !roleDialogRationale.trim()) return;
    setCleaningActionBusy(true);
    setEntityMergeError(null);
    try {
      await applyRoleCorrection(roleDialogRelationId, {
        corrections: [{
          entity_id: roleDialogEntityId,
          from_role_type: roleDialogFromRole,
          to_role_type: roleDialogToRole.trim(),
        }],
        rationale: roleDialogRationale.trim(),
        candidate_fingerprint: `${roleDialogEntityId}:${roleDialogRelationKind ?? "unknown"}`,
      });
      setRoleDialogOpen(false);
      await loadMergeCandidates();
    } catch (err) {
      const parsedError = handlePageError(err, "Failed to apply role correction");
      setEntityMergeError(parsedError.userMessage);
    } finally {
      setCleaningActionBusy(false);
    }
  };

  const visibleMergeCandidates = mergeCandidates.filter((candidate) =>
    shouldShowCleaningCandidate(
      "entity_merge",
      `${candidate.source.id}:${candidate.target.id}`,
    )
  );
  const visibleDuplicateRelationCandidates = cleaningAnalysis.duplicate_relations.filter((candidate) =>
    shouldShowCleaningCandidate("duplicate_relation", candidate.fingerprint)
  );
  const visibleRoleConsistencyCandidates = cleaningAnalysis.role_consistency.filter((candidate) =>
    shouldShowCleaningCandidate(
      "role_consistency",
      `${candidate.entity_id}:${candidate.relation_kind ?? "unknown"}`,
    )
  );

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
          variant="scrollable"
          scrollButtons="auto"
          allowScrollButtonsMobile
          sx={{ mt: 2 }}
        >
          <Tab icon={<PeopleIcon />} iconPosition="start" label="Users" />
          <Tab icon={<CategoryIcon />} iconPosition="start" label="UI Categories" />
          <Tab icon={<BugReportIcon />} iconPosition="start" label="Bug Reports" />
          <Tab icon={<AccountTreeIcon />} iconPosition="start" label="Relation Types" />
          <Tab icon={<LabelIcon />} iconPosition="start" label="Entity Categories" />
          <Tab icon={<CleaningServicesIcon />} iconPosition="start" label="Graph Cleaning" />
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

      {/* ── Bug Reports tab ── */}
      {activeTab === 2 && (
        <Paper sx={{ p: 3 }}>
          <Typography variant="h5" gutterBottom>Bug Reports</Typography>

          {bugError && <Alert severity="error" sx={{ mb: 2 }}>{bugError}</Alert>}

          {/* Summary chips */}
          {!bugLoading && (
            <Box sx={{ display: "flex", gap: 1, mb: 2 }}>
              <Chip label={`Total: ${bugReports.length}`} size="small" />
              <Chip
                label={`Open: ${bugReports.filter((r) => !r.resolved).length}`}
                color="warning"
                size="small"
              />
              <Chip
                label={`Resolved: ${bugReports.filter((r) => r.resolved).length}`}
                color="success"
                size="small"
              />
            </Box>
          )}

          {bugLoading ? (
            <Typography>Loading…</Typography>
          ) : (
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>User</TableCell>
                    <TableCell>Message</TableCell>
                    <TableCell>Page</TableCell>
                    <TableCell>Submitted</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Action</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {bugReports.map((report) => (
                    <TableRow key={report.id}>
                      <TableCell>
                        <Typography variant="body2" noWrap sx={{ maxWidth: 160 }}>
                          {report.user_id ?? "Anonymous"}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" sx={{ maxWidth: 320, whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
                          {report.message.length > 200
                            ? report.message.slice(0, 200) + "…"
                            : report.message}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        {report.page_url ? (
                          <Typography variant="body2" noWrap sx={{ maxWidth: 200 }} title={report.page_url}>
                            {report.page_url}
                          </Typography>
                        ) : (
                          <Typography variant="body2" color="text.secondary">—</Typography>
                        )}
                      </TableCell>
                      <TableCell>
                        {new Date(report.created_at).toLocaleDateString()}
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={report.resolved ? "Resolved" : "Open"}
                          color={report.resolved ? "success" : "warning"}
                          size="small"
                        />
                      </TableCell>
                      <TableCell>
                        <IconButton
                          size="small"
                          onClick={() => handleToggleResolved(report)}
                          title={report.resolved ? "Mark as open" : "Mark as resolved"}
                          color={report.resolved ? "default" : "success"}
                        >
                          {report.resolved ? (
                            <RadioButtonUncheckedIcon fontSize="small" />
                          ) : (
                            <CheckCircleOutlineIcon fontSize="small" />
                          )}
                        </IconButton>
                      </TableCell>
                    </TableRow>
                  ))}
                  {bugReports.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={6} align="center">
                        <Typography color="text.secondary">No bug reports yet</Typography>
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </Paper>
      )}

      {/* ── Relation Types tab ── */}
      {activeTab === 3 && (
        <Paper sx={{ p: 3 }}>
          <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
            <Typography variant="h5">Relation Types</Typography>
            <Button
              variant="contained"
              startIcon={<AddIcon />}
              onClick={handleRelTypeNewClick}
            >
              New Type
            </Button>
          </Box>

          {relTypeError && <Alert severity="error" sx={{ mb: 2 }}>{relTypeError}</Alert>}

          {relTypeLoading ? (
            <Typography>Loading…</Typography>
          ) : (
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>ID</TableCell>
                    <TableCell>Label</TableCell>
                    <TableCell>Category</TableCell>
                    <TableCell>Description</TableCell>
                    <TableCell align="right">Usage</TableCell>
                    <TableCell>Flags</TableCell>
                    <TableCell>Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {relTypes.map((rt) => (
                    <TableRow key={rt.type_id}>
                      <TableCell><code>{rt.type_id}</code></TableCell>
                      <TableCell>{rt.label.en ?? "—"}</TableCell>
                      <TableCell>{rt.category ?? "—"}</TableCell>
                      <TableCell>
                        <Typography variant="body2" sx={{ maxWidth: 300, whiteSpace: "normal" }}>
                          {rt.description.length > 120 ? rt.description.slice(0, 120) + "…" : rt.description}
                        </Typography>
                      </TableCell>
                      <TableCell align="right">{rt.usage_count}</TableCell>
                      <TableCell>
                        {rt.is_system && (
                          <Chip
                            icon={<LockIcon />}
                            label="system"
                            size="small"
                            variant="outlined"
                            color="default"
                            title="Built-in type — deletion will deactivate it rather than remove it"
                          />
                        )}
                      </TableCell>
                      <TableCell>
                        <IconButton
                          size="small"
                          onClick={() => handleRelTypeEditClick(rt)}
                          title="Edit"
                        >
                          <EditIcon fontSize="small" />
                        </IconButton>
                        <IconButton
                          size="small"
                          onClick={() => handleRelTypeMergeClick(rt)}
                          title="Merge into another type"
                        >
                          <CallMergeIcon fontSize="small" />
                        </IconButton>
                        <IconButton
                          size="small"
                          color="error"
                          onClick={() => handleRelTypeDeleteClick(rt)}
                          title={rt.is_system ? "Deactivate (system type)" : "Delete"}
                        >
                          <DeleteIcon fontSize="small" />
                        </IconButton>
                      </TableCell>
                    </TableRow>
                  ))}
                  {relTypes.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={7} align="center">
                        <Typography color="text.secondary">No relation types found</Typography>
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </Paper>
      )}

      {/* Relation type create/edit dialog */}
      <Dialog open={relTypeDialogOpen} onClose={() => setRelTypeDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{selectedRelType ? `Edit: ${selectedRelType.type_id}` : "New Relation Type"}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            {!selectedRelType && (
              <TextField
                label="Type ID"
                value={relTypeForm.type_id}
                onChange={(e) => setRelTypeForm((f) => ({ ...f, type_id: e.target.value }))}
                fullWidth
                required
                helperText="Snake_case identifier, e.g. inhibits_growth. Cannot be changed after creation."
                inputProps={{ pattern: "[a-z][a-z0-9_]*" }}
              />
            )}
            <TextField
              label="Label (EN)"
              value={relTypeForm.label_en}
              onChange={(e) => setRelTypeForm((f) => ({ ...f, label_en: e.target.value }))}
              fullWidth
              required
            />
            <TextField
              label="Description"
              value={relTypeForm.description}
              onChange={(e) => setRelTypeForm((f) => ({ ...f, description: e.target.value }))}
              fullWidth
              required
              multiline
              rows={3}
              helperText="At least 10 characters. Used in LLM prompts."
            />
            <TextField
              label="Examples"
              value={relTypeForm.examples}
              onChange={(e) => setRelTypeForm((f) => ({ ...f, examples: e.target.value }))}
              fullWidth
              multiline
              rows={2}
              helperText="Optional. Free-text examples for the LLM."
            />
            <TextField
              label="Aliases"
              value={relTypeForm.aliases}
              onChange={(e) => setRelTypeForm((f) => ({ ...f, aliases: e.target.value }))}
              fullWidth
              helperText="Comma-separated synonyms, e.g. treats, cures"
            />
            <TextField
              label="Category"
              value={relTypeForm.category}
              onChange={(e) => setRelTypeForm((f) => ({ ...f, category: e.target.value }))}
              fullWidth
              helperText="Optional grouping, e.g. therapeutic, causal, diagnostic"
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRelTypeDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={handleRelTypeSave}
            variant="contained"
            disabled={
              relTypeSaving ||
              (!selectedRelType && !relTypeForm.type_id) ||
              !relTypeForm.label_en ||
              relTypeForm.description.length < 10
            }
          >
            {relTypeSaving ? "Saving…" : "Save"}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Relation type delete confirmation dialog */}
      <Dialog open={relTypeDeleteDialogOpen} onClose={() => setRelTypeDeleteDialogOpen(false)}>
        <DialogTitle>
          {selectedRelType?.is_system ? "Deactivate System Type" : "Delete Relation Type"}
        </DialogTitle>
        <DialogContent>
          <Typography>
            {selectedRelType?.is_system
              ? <>
                  <strong>{selectedRelType?.type_id}</strong> is a built-in system type. It will be{" "}
                  <strong>deactivated</strong> (hidden from prompts and UI) rather than permanently deleted.
                </>
              : <>
                  Permanently delete <strong>{selectedRelType?.type_id}</strong>? This cannot be undone.
                  {(selectedRelType?.usage_count ?? 0) > 0 && (
                    <> It has been used <strong>{selectedRelType?.usage_count}</strong> time(s) in the graph.</>
                  )}
                </>}
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRelTypeDeleteDialogOpen(false)}>Cancel</Button>
          <Button color="error" variant="contained" onClick={handleRelTypeConfirmDelete}>
            {selectedRelType?.is_system ? "Deactivate" : "Delete"}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Relation type merge dialog */}
      <Dialog
        open={relTypeMergeDialogOpen}
        onClose={() => setRelTypeMergeDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Merge Relation Type</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <Typography>
              Merge <strong>{relTypeMergeSource?.type_id}</strong> into another type.
              All relation revisions and <em>pending</em> staged extractions using this type will be re-labelled.
              The source type will then be deactivated.
            </Typography>

            {relTypeMergePreview !== null && (
              <Alert severity={
                relTypeMergePreview.relation_revisions + relTypeMergePreview.pending_staged > 0
                  ? "warning"
                  : "info"
              }>
                {relTypeMergePreview.relation_revisions > 0 && (
                  <>{relTypeMergePreview.relation_revisions} relation revision(s) in the graph will be re-labelled. </>
                )}
                {relTypeMergePreview.pending_staged > 0 && (
                  <>{relTypeMergePreview.pending_staged} pending staged extraction(s) will be re-labelled.</>
                )}
                {relTypeMergePreview.relation_revisions + relTypeMergePreview.pending_staged === 0 && (
                  <>No live data uses this type.</>
                )}
              </Alert>
            )}

            <FormControl fullWidth required>
              <InputLabel id="rel-merge-target-label">Merge into</InputLabel>
              <Select
                labelId="rel-merge-target-label"
                label="Merge into"
                value={relTypeMergeTargetId}
                onChange={(e) => setRelTypeMergeTargetId(e.target.value)}
              >
                {relTypes
                  .filter((r) => r.type_id !== relTypeMergeSource?.type_id)
                  .map((r) => (
                    <MenuItem key={r.type_id} value={r.type_id}>
                      {r.label.en ?? r.type_id} ({r.type_id})
                    </MenuItem>
                  ))}
              </Select>
            </FormControl>
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRelTypeMergeDialogOpen(false)}>Cancel</Button>
          <Button
            variant="contained"
            color="warning"
            disabled={!relTypeMergeTargetId || relTypeMergeSaving}
            onClick={handleRelTypeMergeConfirm}
          >
            {relTypeMergeSaving ? "Merging…" : "Merge"}
          </Button>
        </DialogActions>
      </Dialog>

      {/* ── Entity Categories tab ── */}
      {activeTab === 4 && (
        <Paper sx={{ p: 3 }}>
          <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
            <Typography variant="h5">Entity Categories</Typography>
            <Button
              variant="contained"
              startIcon={<AddIcon />}
              onClick={handleEntityCatNewClick}
            >
              New Category
            </Button>
          </Box>

          {entityCatError && <Alert severity="error" sx={{ mb: 2 }}>{entityCatError}</Alert>}

          {entityCatLoading ? (
            <Typography>Loading…</Typography>
          ) : (
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>ID</TableCell>
                    <TableCell>Label</TableCell>
                    <TableCell>Description</TableCell>
                    <TableCell>Examples</TableCell>
                    <TableCell align="right">Usage</TableCell>
                    <TableCell>Flags</TableCell>
                    <TableCell>Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {entityCats.map((cat) => (
                    <TableRow key={cat.category_id}>
                      <TableCell><code>{cat.category_id}</code></TableCell>
                      <TableCell>{cat.label.en ?? "—"}</TableCell>
                      <TableCell>
                        <Typography variant="body2" sx={{ maxWidth: 280, whiteSpace: "normal" }}>
                          {cat.description.length > 100 ? cat.description.slice(0, 100) + "…" : cat.description}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" color="text.secondary" sx={{ maxWidth: 200 }}>
                          {cat.examples ?? "—"}
                        </Typography>
                      </TableCell>
                      <TableCell align="right">{cat.usage_count}</TableCell>
                      <TableCell>
                        {!cat.is_active && (
                          <Chip label="inactive" size="small" variant="outlined" color="default" />
                        )}
                        {cat.is_system && (
                          <Chip
                            icon={<LockIcon />}
                            label="system"
                            size="small"
                            variant="outlined"
                            color="default"
                            title="Built-in category — deletion will deactivate it"
                          />
                        )}
                      </TableCell>
                      <TableCell>
                        <IconButton size="small" onClick={() => handleEntityCatEditClick(cat)} title="Edit">
                          <EditIcon fontSize="small" />
                        </IconButton>
                        <IconButton
                          size="small"
                          onClick={() => handleEntityCatMergeClick(cat)}
                          title="Merge into another category"
                        >
                          <CallMergeIcon fontSize="small" />
                        </IconButton>
                        <IconButton
                          size="small"
                          color="error"
                          onClick={() => handleEntityCatDeleteClick(cat)}
                          title={cat.is_system ? "Deactivate (system category)" : "Delete"}
                        >
                          <DeleteIcon fontSize="small" />
                        </IconButton>
                      </TableCell>
                    </TableRow>
                  ))}
                  {entityCats.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={7} align="center">
                        <Typography color="text.secondary">No entity categories found</Typography>
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </Paper>
      )}

      {/* Entity category create/edit dialog */}
      <Dialog open={entityCatDialogOpen} onClose={() => setEntityCatDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{selectedEntityCat ? `Edit: ${selectedEntityCat.category_id}` : "New Entity Category"}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            {!selectedEntityCat && (
              <TextField
                label="Category ID"
                value={entityCatForm.category_id}
                onChange={(e) => setEntityCatForm((f) => ({ ...f, category_id: e.target.value }))}
                fullWidth
                required
                helperText="Snake_case identifier, e.g. genetic_variant. Cannot be changed after creation."
                inputProps={{ pattern: "[a-z][a-z0-9_]*" }}
              />
            )}
            <TextField
              label="Label (EN)"
              value={entityCatForm.label_en}
              onChange={(e) => setEntityCatForm((f) => ({ ...f, label_en: e.target.value }))}
              fullWidth
              required
            />
            <TextField
              label="Description"
              value={entityCatForm.description}
              onChange={(e) => setEntityCatForm((f) => ({ ...f, description: e.target.value }))}
              fullWidth
              required
              multiline
              rows={3}
              helperText="At least 10 characters. Shown to the LLM to guide category assignment."
            />
            <TextField
              label="Examples"
              value={entityCatForm.examples}
              onChange={(e) => setEntityCatForm((f) => ({ ...f, examples: e.target.value }))}
              fullWidth
              multiline
              rows={2}
              helperText="Optional. Comma-separated examples for the LLM."
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEntityCatDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={handleEntityCatSave}
            variant="contained"
            disabled={
              entityCatSaving ||
              (!selectedEntityCat && !entityCatForm.category_id) ||
              !entityCatForm.label_en ||
              entityCatForm.description.length < 10
            }
          >
            {entityCatSaving ? "Saving…" : "Save"}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Entity category delete confirmation dialog */}
      <Dialog open={entityCatDeleteDialogOpen} onClose={() => setEntityCatDeleteDialogOpen(false)}>
        <DialogTitle>
          {selectedEntityCat?.is_system ? "Deactivate System Category" : "Delete Entity Category"}
        </DialogTitle>
        <DialogContent>
          <Typography>
            {selectedEntityCat?.is_system
              ? <>
                  <strong>{selectedEntityCat?.category_id}</strong> is a built-in system category.
                  It will be <strong>deactivated</strong> rather than permanently deleted.
                </>
              : <>
                  Permanently delete <strong>{selectedEntityCat?.category_id}</strong>? This cannot be undone.
                  {(selectedEntityCat?.usage_count ?? 0) > 0 && (
                    <> It has been used <strong>{selectedEntityCat?.usage_count}</strong> time(s).</>
                  )}
                </>}
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEntityCatDeleteDialogOpen(false)}>Cancel</Button>
          <Button color="error" variant="contained" onClick={handleEntityCatConfirmDelete}>
            {selectedEntityCat?.is_system ? "Deactivate" : "Delete"}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Entity category merge dialog */}
      <Dialog
        open={entityCatMergeDialogOpen}
        onClose={() => setEntityCatMergeDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Merge Entity Category</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <Typography>
              Merge <strong>{entityCatMergeSource?.category_id}</strong> into another category.
              All <em>pending</em> staged extractions using this category will be re-labelled.
              The source category will then be deactivated.
            </Typography>

            {entityCatMergePendingStaged !== null && (
              <Alert severity={entityCatMergePendingStaged > 0 ? "warning" : "info"}>
                {entityCatMergePendingStaged > 0
                  ? `${entityCatMergePendingStaged} pending staged extraction(s) will be re-labelled.`
                  : "No pending staged extractions use this category."}
              </Alert>
            )}

            <FormControl fullWidth required>
              <InputLabel id="merge-target-label">Merge into</InputLabel>
              <Select
                labelId="merge-target-label"
                label="Merge into"
                value={entityCatMergeTargetId}
                onChange={(e) => setEntityCatMergeTargetId(e.target.value)}
              >
                {entityCats
                  .filter((c) => c.category_id !== entityCatMergeSource?.category_id && c.is_active)
                  .map((c) => (
                    <MenuItem key={c.category_id} value={c.category_id}>
                      {c.label.en ?? c.category_id} ({c.category_id})
                    </MenuItem>
                  ))}
              </Select>
            </FormControl>
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEntityCatMergeDialogOpen(false)}>Cancel</Button>
          <Button
            variant="contained"
            color="warning"
            disabled={!entityCatMergeTargetId || entityCatMergeSaving}
            onClick={handleEntityCatMergeConfirm}
          >
            {entityCatMergeSaving ? "Merging…" : "Merge"}
          </Button>
        </DialogActions>
      </Dialog>

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

      {/* ── Graph Cleaning tab ── */}
      {activeTab === 5 && (
        <GraphCleaningPanel
          entityMergeError={entityMergeError}
          entityMergeResult={entityMergeResult}
          mergeCandidates={mergeCandidates}
          visibleMergeCandidates={visibleMergeCandidates}
          visibleDuplicateRelationCandidates={visibleDuplicateRelationCandidates}
          visibleRoleConsistencyCandidates={visibleRoleConsistencyCandidates}
          cleaningAnalysis={cleaningAnalysis}
          cleaningDecisions={cleaningDecisions}
          cleaningCritiques={cleaningCritiques}
          cleaningCritiqueBatchSize={cleaningCritiqueBatchSize}
          totalCleaningCritiqueCandidates={totalCleaningCritiqueCandidates}
          remainingCleaningCritiqueCandidates={remainingCleaningCritiqueCandidates}
          cleaningActionBusy={cleaningActionBusy}
          mergeCandidatesLoading={mergeCandidatesLoading}
          mergeCandidatesScanned={mergeCandidatesScanned}
          mergeCandidateThreshold={mergeCandidateThreshold}
          cleaningStatusFilter={cleaningStatusFilter}
          cleaningTypeFilter={cleaningTypeFilter}
          cleaningRecommendationFilter={cleaningRecommendationFilter}
          entityMergeSourceOptions={entityMergeSourceOptions}
          entityMergeTargetOptions={entityMergeTargetOptions}
          entityMergeSourceLoading={entityMergeSourceLoading}
          entityMergeTargetLoading={entityMergeTargetLoading}
          entityMergeSource={entityMergeSource}
          entityMergeTarget={entityMergeTarget}
          setMergeCandidateThreshold={setMergeCandidateThreshold}
          setCleaningStatusFilter={setCleaningStatusFilter}
          setCleaningTypeFilter={setCleaningTypeFilter}
          setCleaningRecommendationFilter={setCleaningRecommendationFilter}
          setCleaningCritiqueBatchSize={setCleaningCritiqueBatchSize}
          runCleaningCritique={runCleaningCritique}
          runSingleCleaningCritique={runSingleCleaningCritique}
          loadMergeCandidates={loadMergeCandidates}
          getCleaningDecision={getCleaningDecision}
          getCleaningCritique={getCleaningCritique}
          reviewMergeCandidate={reviewMergeCandidate}
          saveCleaningDecision={saveCleaningDecision}
          openDuplicateDialog={openDuplicateDialog}
          applyRoleCandidate={applyRoleCandidate}
          searchEntities={searchEntities}
          setEntityMergeSourceOptions={setEntityMergeSourceOptions}
          setEntityMergeTargetOptions={setEntityMergeTargetOptions}
          setEntityMergeSourceLoading={setEntityMergeSourceLoading}
          setEntityMergeTargetLoading={setEntityMergeTargetLoading}
          setEntityMergeSource={setEntityMergeSource}
          setEntityMergeTarget={setEntityMergeTarget}
          openEntityMergeConfirm={() => setEntityMergeConfirmOpen(true)}
        />
      )}
      {/* Entity merge confirmation dialog */}
      <Dialog open={entityMergeConfirmOpen} onClose={() => setEntityMergeConfirmOpen(false)}>
        <DialogTitle>Confirm Entity Merge</DialogTitle>
        <DialogContent>
          <Typography>
            Merge <strong>{entityMergeSource?.slug}</strong> into{" "}
            <strong>{entityMergeTarget?.slug}</strong>?
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            All current-revision relations from <em>{entityMergeSource?.slug}</em> will be
            re-attributed to <em>{entityMergeTarget?.slug}</em>. The source slug will be added as
            a term on the target. This action cannot be undone.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEntityMergeConfirmOpen(false)}>Cancel</Button>
          <Button
            variant="contained"
            color="warning"
            disabled={entityMergeSaving}
            onClick={handleEntityMergeConfirm}
          >
            {entityMergeSaving ? "Merging…" : "Merge"}
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={duplicateDialogOpen} onClose={() => setDuplicateDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Mark Duplicate Relations</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <Alert severity="warning">
              This hides reviewed duplicate relations from normal listings but preserves their audit trail.
              The first relation in the group is kept; the remaining {Math.max(duplicateDialogRelationIds.length - 1, 0)} relation(s) are marked duplicate/rejected.
            </Alert>
            <TextField
              label="Rationale"
              value={duplicateDialogRationale}
              onChange={(event) => setDuplicateDialogRationale(event.target.value)}
              multiline
              rows={3}
              required
              helperText="Explain why these are duplicate extractions from the same evidence context."
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDuplicateDialogOpen(false)}>Cancel</Button>
          <Button
            variant="contained"
            color="warning"
            disabled={cleaningActionBusy || duplicateDialogRationale.trim().length < 3}
            onClick={applyDuplicateCandidate}
          >
            Mark duplicates
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={roleDialogOpen} onClose={() => setRoleDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Correct Relation Role</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <Alert severity="info">
              This creates a new relation revision. Historical role rows are not edited.
            </Alert>
            <Typography variant="body2">
              Entity <strong>{roleDialogEntityLabel}</strong> currently appears as{" "}
              <code>{roleDialogFromRole}</code> in relation{" "}
              <code>{roleDialogRelationId}</code>.
            </Typography>
            <TextField
              label="Correct role type"
              value={roleDialogToRole}
              onChange={(event) => setRoleDialogToRole(event.target.value)}
              required
              helperText="Example: target, condition, agent, outcome"
            />
            <TextField
              label="Rationale"
              value={roleDialogRationale}
              onChange={(event) => setRoleDialogRationale(event.target.value)}
              multiline
              rows={3}
              required
              helperText="Explain why this role correction is warranted."
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRoleDialogOpen(false)}>Cancel</Button>
          <Button
            variant="contained"
            color="warning"
            disabled={
              cleaningActionBusy ||
              roleDialogToRole.trim().length < 1 ||
              roleDialogRationale.trim().length < 3
            }
            onClick={confirmRoleCorrection}
          >
            Create revision
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
