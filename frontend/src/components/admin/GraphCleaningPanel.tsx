import {
  Alert,
  Autocomplete,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  FormControl,
  Grid,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import MergeTypeIcon from "@mui/icons-material/MergeType";

import type {
  DuplicateRelationCandidate,
  GraphCleaningAnalysis,
  GraphCleaningCritiqueItem,
  GraphCleaningDecision,
  RoleConsistencyCandidate,
} from "../../api/graphCleaning";

interface EntitySearchResult {
  id: string;
  slug: string;
  summary: Record<string, string> | null;
}

export interface EntityMergeCandidate {
  source: EntitySearchResult;
  target: EntitySearchResult;
  similarity: number;
  reason: string;
  score_factors?: Record<string, string | number | boolean>;
  proposed_action: "merge";
}

export type CleaningStatusFilter = GraphCleaningDecision["status"] | "all";
export type CleaningTypeFilter =
  | GraphCleaningDecision["candidate_type"]
  | "all";
export type CleaningRecommendationFilter =
  | GraphCleaningCritiqueItem["recommendation"]
  | "all"
  | "no_critique";

interface GraphCleaningPanelProps {
  entityMergeError: string | null;
  entityMergeResult: { source_slug: string; target_slug: string; relations_moved: number } | null;
  mergeCandidates: EntityMergeCandidate[];
  visibleMergeCandidates: EntityMergeCandidate[];
  visibleDuplicateRelationCandidates: DuplicateRelationCandidate[];
  visibleRoleConsistencyCandidates: RoleConsistencyCandidate[];
  cleaningAnalysis: GraphCleaningAnalysis;
  cleaningDecisions: GraphCleaningDecision[];
  cleaningCritiques: GraphCleaningCritiqueItem[];
  cleaningCritiqueBatchSize: number;
  totalCleaningCritiqueCandidates: number;
  remainingCleaningCritiqueCandidates: number;
  cleaningActionBusy: boolean;
  mergeCandidatesLoading: boolean;
  mergeCandidatesScanned: boolean;
  mergeCandidateThreshold: number;
  cleaningStatusFilter: CleaningStatusFilter;
  cleaningTypeFilter: CleaningTypeFilter;
  cleaningRecommendationFilter: CleaningRecommendationFilter;
  entityMergeSourceOptions: EntitySearchResult[];
  entityMergeTargetOptions: EntitySearchResult[];
  entityMergeSourceLoading: boolean;
  entityMergeTargetLoading: boolean;
  entityMergeSource: EntitySearchResult | null;
  entityMergeTarget: EntitySearchResult | null;
  setMergeCandidateThreshold: (value: number) => void;
  setCleaningStatusFilter: (value: CleaningStatusFilter) => void;
  setCleaningTypeFilter: (value: CleaningTypeFilter) => void;
  setCleaningRecommendationFilter: (value: CleaningRecommendationFilter) => void;
  setCleaningCritiqueBatchSize: (value: number) => void;
  runCleaningCritique: () => void;
  runSingleCleaningCritique: (candidate: Record<string, unknown>) => void;
  loadMergeCandidates: () => void;
  getCleaningDecision: (
    candidateType: GraphCleaningDecision["candidate_type"],
    fingerprint: string,
  ) => GraphCleaningDecision | undefined;
  getCleaningCritique: (fingerprint: string) => GraphCleaningCritiqueItem | undefined;
  reviewMergeCandidate: (candidate: EntityMergeCandidate) => void;
  saveCleaningDecision: (
    candidateType: GraphCleaningDecision["candidate_type"],
    fingerprint: string,
    status: GraphCleaningDecision["status"],
    notes: string,
    decisionPayload?: Record<string, unknown>,
  ) => void;
  openDuplicateDialog: (fingerprint: string, relationIds: string[]) => void;
  applyRoleCandidate: (candidate: RoleConsistencyCandidate) => void;
  searchEntities: (
    query: string,
    setOptions: (opts: EntitySearchResult[]) => void,
    setSearchLoading: (value: boolean) => void,
  ) => void;
  setEntityMergeSourceOptions: (options: EntitySearchResult[]) => void;
  setEntityMergeTargetOptions: (options: EntitySearchResult[]) => void;
  setEntityMergeSourceLoading: (value: boolean) => void;
  setEntityMergeTargetLoading: (value: boolean) => void;
  setEntityMergeSource: (value: EntitySearchResult | null) => void;
  setEntityMergeTarget: (value: EntitySearchResult | null) => void;
  openEntityMergeConfirm: () => void;
}

export function GraphCleaningPanel({
  entityMergeError,
  entityMergeResult,
  mergeCandidates,
  visibleMergeCandidates,
  visibleDuplicateRelationCandidates,
  visibleRoleConsistencyCandidates,
  cleaningAnalysis,
  cleaningDecisions,
  cleaningCritiques,
  cleaningCritiqueBatchSize,
  totalCleaningCritiqueCandidates,
  remainingCleaningCritiqueCandidates,
  cleaningActionBusy,
  mergeCandidatesLoading,
  mergeCandidatesScanned,
  mergeCandidateThreshold,
  cleaningStatusFilter,
  cleaningTypeFilter,
  cleaningRecommendationFilter,
  entityMergeSourceOptions = [],
  entityMergeTargetOptions = [],
  entityMergeSourceLoading,
  entityMergeTargetLoading,
  entityMergeSource,
  entityMergeTarget,
  setMergeCandidateThreshold,
  setCleaningStatusFilter,
  setCleaningTypeFilter,
  setCleaningRecommendationFilter,
  setCleaningCritiqueBatchSize,
  runCleaningCritique,
  runSingleCleaningCritique,
  loadMergeCandidates,
  getCleaningDecision,
  getCleaningCritique,
  reviewMergeCandidate,
  saveCleaningDecision,
  openDuplicateDialog,
  applyRoleCandidate,
  searchEntities,
  setEntityMergeSourceOptions,
  setEntityMergeTargetOptions,
  setEntityMergeSourceLoading,
  setEntityMergeTargetLoading,
  setEntityMergeSource,
  setEntityMergeTarget,
  openEntityMergeConfirm,
}: GraphCleaningPanelProps) {
  const renderCritiqueReport = (critique: GraphCleaningCritiqueItem | undefined) => {
    if (!critique) return null;

    return (
      <Alert severity="warning" sx={{ mt: 1 }}>
        <Typography variant="subtitle2">LLM critique: {critique.recommendation}</Typography>
        <Typography variant="body2">{critique.rationale}</Typography>
        {critique.risks.length > 0 && (
          <Typography variant="caption" display="block">
            Risks: {critique.risks.join("; ")}
          </Typography>
        )}
        {critique.evidence_gaps.length > 0 && (
          <Typography variant="caption" display="block">
            Evidence gaps: {critique.evidence_gaps.join("; ")}
          </Typography>
        )}
      </Alert>
    );
  };

  return (
    <Stack spacing={3}>
      <Paper sx={{ p: 3 }}>
        <Typography variant="h5" sx={{ mb: 1 }}>Graph Cleaning</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Review automatic and semi-automatic cleaning actions before mutating the graph.
          Suggestions are advisory: LLM or heuristic analysis is never authoritative, and every
          merge still requires explicit admin confirmation.
        </Typography>

        {entityMergeError && <Alert severity="error" sx={{ mb: 2 }}>{entityMergeError}</Alert>}
        {entityMergeResult && (
          <Alert severity="success" sx={{ mb: 2 }}>
            Merged <strong>{entityMergeResult.source_slug}</strong> →{" "}
            <strong>{entityMergeResult.target_slug}</strong>:{" "}
            {entityMergeResult.relations_moved} relation(s) moved.
          </Alert>
        )}

      </Paper>

      <Paper sx={{ p: 3 }}>
        <Box sx={{ display: "flex", justifyContent: "space-between", gap: 2, alignItems: "center", mb: 2, flexWrap: "wrap" }}>
          <Box>
            <Typography variant="h6">Automatic Candidate Scan</Typography>
            <Typography variant="body2" color="text.secondary">
              Deterministic dry-run scan. Use this list as input for human or LLM critical review.
            </Typography>
          </Box>
          <Stack direction="row" spacing={1} alignItems="center">
            <TextField
              label="Threshold"
              type="number"
              size="small"
              value={mergeCandidateThreshold}
              onChange={(e) => setMergeCandidateThreshold(Number(e.target.value))}
              inputProps={{ min: 0, max: 1, step: 0.01 }}
              sx={{ width: 120 }}
            />
            <Button
              variant="outlined"
              disabled={mergeCandidatesLoading}
              onClick={loadMergeCandidates}
            >
              {mergeCandidatesLoading ? "Scanning..." : "Scan"}
            </Button>
          </Stack>
        </Box>

        <Alert severity="info" sx={{ mb: 2 }}>
          LLM critical analysis should challenge these candidates and propose actions, but the
          graph is changed only by confirmed operations below.
        </Alert>

        {!mergeCandidatesScanned && !mergeCandidatesLoading ? (
          <Alert severity="info">
            No candidate scan has been run for this session. Press Scan when you want to
            compute the deterministic graph-cleaning candidates.
          </Alert>
        ) : mergeCandidatesLoading ? (
          <Typography>Scanning candidates...</Typography>
        ) : (
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Source removed</TableCell>
                  <TableCell>Target kept</TableCell>
                  <TableCell>Reason</TableCell>
                  <TableCell align="right">Similarity</TableCell>
                  <TableCell>Action</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {visibleMergeCandidates.map((candidate) => {
                  const fingerprint = `${candidate.source.id}:${candidate.target.id}`;
                  const decision = getCleaningDecision("entity_merge", fingerprint);
                  const critique = getCleaningCritique(fingerprint);
                  const critiquePayload = {
                    candidate_fingerprint: fingerprint,
                    candidate_type: "entity_merge",
                    source_slug: candidate.source.slug,
                    target_slug: candidate.target.slug,
                    reason: candidate.reason,
                    similarity: candidate.similarity,
                  };
                  return (
                    <TableRow key={`${candidate.source.id}-${candidate.target.id}`}>
                      <TableCell><code>{candidate.source.slug}</code></TableCell>
                      <TableCell><code>{candidate.target.slug}</code></TableCell>
                      <TableCell>
                        {candidate.reason}
                        {candidate.score_factors && (
                          <Typography variant="caption" color="text.secondary" display="block">
                            Factors: {Object.entries(candidate.score_factors)
                              .map(([key, value]) => `${key}=${String(value)}`)
                              .join(", ")}
                          </Typography>
                        )}
                        {decision && <Chip label={decision.status} size="small" sx={{ ml: 1 }} />}
                        {critique && <Chip label={`LLM: ${critique.recommendation}`} size="small" sx={{ ml: 1 }} />}
                        {renderCritiqueReport(critique)}
                      </TableCell>
                      <TableCell align="right">{Math.round(candidate.similarity * 100)}%</TableCell>
                      <TableCell>
                        <Stack direction="row" spacing={1}>
                          <Button
                            size="small"
                            color="warning"
                            startIcon={<MergeTypeIcon />}
                            onClick={() => reviewMergeCandidate(candidate)}
                          >
                            Review merge
                          </Button>
                          <Button
                            size="small"
                            disabled={cleaningActionBusy}
                            onClick={() => runSingleCleaningCritique(critiquePayload)}
                          >
                            LLM review
                          </Button>
                          <Button
                            size="small"
                            disabled={cleaningActionBusy}
                            onClick={() =>
                              saveCleaningDecision(
                                "entity_merge",
                                fingerprint,
                                "dismissed",
                                "Dismissed from graph-cleaning UI.",
                                candidate as unknown as Record<string, unknown>,
                              )
                            }
                          >
                            Dismiss
                          </Button>
                        </Stack>
                      </TableCell>
                    </TableRow>
                  );
                })}
                {visibleMergeCandidates.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={5} align="center">
                      <Typography color="text.secondary">No candidates found for the active filters.</Typography>
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </Paper>

      <Paper sx={{ p: 3 }}>
        <Typography variant="h6" sx={{ mb: 2 }}>Review Workspace</Typography>
        <Grid container spacing={2}>
          <Grid size={{ xs: 12, md: 4 }}>
            <Card variant="outlined">
              <CardContent>
                <Typography variant="h6">Entity deduplication</Typography>
                <Typography variant="h4">{mergeCandidates.length}</Typography>
                <Typography variant="body2" color="text.secondary">
                  Find likely duplicate nodes such as fibromyalgia and fibromyalgia syndrome.
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid size={{ xs: 12, md: 4 }}>
            <Card variant="outlined">
              <CardContent>
                <Typography variant="h6">Relation cleanup</Typography>
                <Typography variant="h4">{cleaningAnalysis.duplicate_relations.length}</Typography>
                <Typography variant="body2" color="text.secondary">
                  Detect duplicate relations from the same source story without hiding
                  contradictions or evidence.
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid size={{ xs: 12, md: 4 }}>
            <Card variant="outlined">
              <CardContent>
                <Typography variant="h6">Role consistency</Typography>
                <Typography variant="h4">{cleaningAnalysis.role_consistency.length}</Typography>
                <Typography variant="body2" color="text.secondary">
                  Flag inconsistent role usage for the same entity and relation type.
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
        <Stack direction="row" spacing={1} sx={{ mt: 2, flexWrap: "wrap" }}>
          <TextField
            label="LLM batch"
            type="number"
            size="small"
            value={cleaningCritiqueBatchSize}
            onChange={(event) =>
              setCleaningCritiqueBatchSize(
                Math.max(1, Math.min(10, Number(event.target.value) || 1)),
              )
            }
            inputProps={{ min: 1, max: 10, step: 1 }}
            sx={{ width: 120 }}
          />
          <Button
            variant="outlined"
            disabled={
              cleaningActionBusy ||
              mergeCandidatesLoading ||
              !mergeCandidatesScanned ||
              remainingCleaningCritiqueCandidates === 0
            }
            onClick={runCleaningCritique}
          >
            {cleaningActionBusy ? "Working..." : "Critique next batch"}
          </Button>
          <Chip label={`Decisions: ${cleaningDecisions.length}`} />
          <Chip label={`LLM critiques: ${cleaningCritiques.length}/${totalCleaningCritiqueCandidates}`} />
          <Chip label={`Remaining: ${remainingCleaningCritiqueCandidates}`} />
          <FormControl size="small" sx={{ minWidth: 170 }}>
            <InputLabel id="cleaning-status-filter-label">Status</InputLabel>
            <Select
              labelId="cleaning-status-filter-label"
              label="Status"
              value={cleaningStatusFilter}
              onChange={(event) =>
                setCleaningStatusFilter(event.target.value as CleaningStatusFilter)
              }
            >
              <MenuItem value="all">All statuses</MenuItem>
              <MenuItem value="open">Open</MenuItem>
              <MenuItem value="needs_review">Needs review</MenuItem>
              <MenuItem value="dismissed">Dismissed</MenuItem>
              <MenuItem value="approved">Approved</MenuItem>
              <MenuItem value="applied">Applied</MenuItem>
            </Select>
          </FormControl>
          <FormControl size="small" sx={{ minWidth: 170 }}>
            <InputLabel id="cleaning-type-filter-label">Type</InputLabel>
            <Select
              labelId="cleaning-type-filter-label"
              label="Type"
              value={cleaningTypeFilter}
              onChange={(event) =>
                setCleaningTypeFilter(event.target.value as CleaningTypeFilter)
              }
            >
              <MenuItem value="all">All types</MenuItem>
              <MenuItem value="entity_merge">Entity merges</MenuItem>
              <MenuItem value="duplicate_relation">Duplicate relations</MenuItem>
              <MenuItem value="role_consistency">Role consistency</MenuItem>
            </Select>
          </FormControl>
          <FormControl size="small" sx={{ minWidth: 190 }}>
            <InputLabel id="cleaning-recommendation-filter-label">LLM recommendation</InputLabel>
            <Select
              labelId="cleaning-recommendation-filter-label"
              label="LLM recommendation"
              value={cleaningRecommendationFilter}
              onChange={(event) =>
                setCleaningRecommendationFilter(event.target.value as CleaningRecommendationFilter)
              }
            >
              <MenuItem value="all">All recommendations</MenuItem>
              <MenuItem value="recommend">Recommend</MenuItem>
              <MenuItem value="reject">Reject</MenuItem>
              <MenuItem value="needs_human_review">Needs human review</MenuItem>
              <MenuItem value="no_critique">No critique</MenuItem>
            </Select>
          </FormControl>
        </Stack>
        {cleaningCritiques.length > 0 && (
          <Alert severity="warning" sx={{ mt: 2 }}>
            LLM critique is advisory only. Latest recommendation:{" "}
            <strong>{cleaningCritiques[0].recommendation}</strong> - {cleaningCritiques[0].rationale}
          </Alert>
        )}
      </Paper>

      <Paper sx={{ p: 3 }}>
        <Typography variant="h6">Duplicate Relation Review</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Read-only analysis. These groups may represent duplicate extractions, but separate
          relations can be valid when evidence context differs.
        </Typography>

        {!mergeCandidatesScanned && !mergeCandidatesLoading ? (
          <Alert severity="info">
            Relation analysis is computed only when you run a candidate scan.
          </Alert>
        ) : mergeCandidatesLoading ? (
          <Typography>Loading relation analysis...</Typography>
        ) : (
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Source</TableCell>
                  <TableCell>Signature</TableCell>
                  <TableCell align="right">Relations</TableCell>
                  <TableCell>Participants</TableCell>
                  <TableCell>Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {visibleDuplicateRelationCandidates.map((candidate) => {
                  const firstRelation = candidate.relations[0];
                  const critique = getCleaningCritique(candidate.fingerprint);
                  const critiquePayload = {
                    ...candidate,
                    candidate_type: "duplicate_relation",
                    candidate_fingerprint: candidate.fingerprint,
                  };
                  return (
                    <TableRow key={candidate.fingerprint}>
                      <TableCell>{candidate.source_title ?? firstRelation?.source_title ?? "Untitled source"}</TableCell>
                      <TableCell>
                        <Typography variant="body2">
                          {firstRelation?.kind ?? "unknown"} / {firstRelation?.direction ?? "no direction"}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {candidate.reason}
                        </Typography>
                        {critique && <Chip label={`LLM: ${critique.recommendation}`} size="small" sx={{ ml: 1 }} />}
                        {renderCritiqueReport(critique)}
                      </TableCell>
                      <TableCell align="right">{candidate.relation_count}</TableCell>
                      <TableCell>
                        {(firstRelation?.roles ?? []).map((role) => (
                          <Chip
                            key={`${role.role_type}-${role.entity_id}`}
                            label={`${role.role_type}: ${role.entity_slug ?? role.entity_id}`}
                            size="small"
                            sx={{ mr: 0.5, mb: 0.5 }}
                          />
                        ))}
                      </TableCell>
                      <TableCell>
                        <Stack direction="row" spacing={1}>
                          <Button
                            size="small"
                            color="warning"
                            disabled={cleaningActionBusy || candidate.relations.length < 2}
                            onClick={() =>
                              openDuplicateDialog(
                                candidate.fingerprint,
                                candidate.relations.map((relation) => relation.relation_id),
                              )
                            }
                          >
                            Mark duplicates
                          </Button>
                          <Button
                            size="small"
                            disabled={cleaningActionBusy}
                            onClick={() => runSingleCleaningCritique(critiquePayload)}
                          >
                            LLM review
                          </Button>
                          <Button
                            size="small"
                            disabled={cleaningActionBusy}
                            onClick={() =>
                              saveCleaningDecision(
                                "duplicate_relation",
                                candidate.fingerprint,
                                "dismissed",
                                "Dismissed from graph-cleaning UI.",
                                candidate as unknown as Record<string, unknown>,
                              )
                            }
                          >
                            Dismiss
                          </Button>
                        </Stack>
                      </TableCell>
                    </TableRow>
                  );
                })}
                {visibleDuplicateRelationCandidates.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={5} align="center">
                      <Typography color="text.secondary">No duplicate relation groups found for the active filters.</Typography>
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </Paper>

      <Paper sx={{ p: 3 }}>
        <Typography variant="h6">Role Consistency Review</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Read-only warnings for entities used with multiple role types in the same relation kind.
          Review source context before changing any relation.
        </Typography>

        {!mergeCandidatesScanned && !mergeCandidatesLoading ? (
          <Alert severity="info">
            Role consistency analysis is computed only when you run a candidate scan.
          </Alert>
        ) : mergeCandidatesLoading ? (
          <Typography>Loading role analysis...</Typography>
        ) : (
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Entity</TableCell>
                  <TableCell>Relation kind</TableCell>
                  <TableCell>Role usage</TableCell>
                  <TableCell>Reason</TableCell>
                  <TableCell>Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {visibleRoleConsistencyCandidates.map((candidate) => {
                  const fingerprint = `${candidate.entity_id}:${candidate.relation_kind ?? "unknown"}`;
                  const critique = getCleaningCritique(fingerprint);
                  const critiquePayload = {
                    ...candidate,
                    candidate_type: "role_consistency",
                    candidate_fingerprint: fingerprint,
                  };
                  return (
                    <TableRow key={fingerprint}>
                      <TableCell><code>{candidate.entity_slug ?? candidate.entity_id}</code></TableCell>
                      <TableCell>{candidate.relation_kind ?? "unknown"}</TableCell>
                      <TableCell>
                        {candidate.usages.map((usage) => (
                          <Chip
                            key={usage.role_type}
                            label={`${usage.role_type}: ${usage.count}`}
                            size="small"
                            sx={{ mr: 0.5, mb: 0.5 }}
                          />
                        ))}
                      </TableCell>
                      <TableCell>
                        {candidate.reason}
                        {critique && <Chip label={`LLM: ${critique.recommendation}`} size="small" sx={{ ml: 1 }} />}
                        {renderCritiqueReport(critique)}
                      </TableCell>
                      <TableCell>
                        <Stack direction="row" spacing={1}>
                          <Button
                            size="small"
                            color="warning"
                            disabled={cleaningActionBusy}
                            onClick={() => applyRoleCandidate(candidate)}
                          >
                            Correct role
                          </Button>
                          <Button
                            size="small"
                            disabled={cleaningActionBusy}
                            onClick={() => runSingleCleaningCritique(critiquePayload)}
                          >
                            LLM review
                          </Button>
                          <Button
                            size="small"
                            disabled={cleaningActionBusy}
                            onClick={() =>
                              saveCleaningDecision(
                                "role_consistency",
                                fingerprint,
                                "dismissed",
                                "Dismissed from graph-cleaning UI.",
                                candidate as unknown as Record<string, unknown>,
                              )
                            }
                          >
                            Dismiss
                          </Button>
                        </Stack>
                      </TableCell>
                    </TableRow>
                  );
                })}
                {visibleRoleConsistencyCandidates.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={5} align="center">
                      <Typography color="text.secondary">No role consistency warnings found for the active filters.</Typography>
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </Paper>

      <Paper sx={{ p: 3 }}>
        <Typography variant="h6" sx={{ mb: 1 }}>Semi-automatic Manual Merge</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
          Merge two knowledge-graph entity nodes into one. All current-revision relations from the
          source will be re-attributed to the target. The source slug is preserved as a term on the
          target. The source entity is then marked as merged and hidden from listings.
        </Typography>

        <Stack spacing={3} sx={{ maxWidth: 600 }}>
          <Autocomplete
            options={entityMergeSourceOptions}
            getOptionLabel={(o) => `${o.slug}${o.summary?.en ? " - " + o.summary.en.slice(0, 60) : ""}`}
            isOptionEqualToValue={(a, b) => a.id === b.id}
            loading={entityMergeSourceLoading}
            value={entityMergeSource}
            onChange={(_, value) => {
              setEntityMergeSource(value);
              if (value?.id === entityMergeTarget?.id) setEntityMergeTarget(null);
            }}
            onInputChange={(_, value) =>
              searchEntities(value, setEntityMergeSourceOptions, setEntityMergeSourceLoading)
            }
            renderInput={(params) => (
              <TextField
                {...params}
                label="Source entity (will be merged away)"
                helperText="Type at least 2 characters to search"
                InputProps={{
                  ...params.InputProps,
                  endAdornment: (
                    <>
                      {entityMergeSourceLoading ? <CircularProgress size={16} /> : null}
                      {params.InputProps.endAdornment}
                    </>
                  ),
                }}
              />
            )}
          />

          <Autocomplete
            options={entityMergeTargetOptions}
            getOptionLabel={(o) => `${o.slug}${o.summary?.en ? " - " + o.summary.en.slice(0, 60) : ""}`}
            isOptionEqualToValue={(a, b) => a.id === b.id}
            loading={entityMergeTargetLoading}
            value={entityMergeTarget}
            onChange={(_, value) => setEntityMergeTarget(value)}
            onInputChange={(_, value) =>
              searchEntities(value, setEntityMergeTargetOptions, setEntityMergeTargetLoading)
            }
            renderInput={(params) => (
              <TextField
                {...params}
                label="Target entity (will be kept)"
                helperText="Type at least 2 characters to search"
                InputProps={{
                  ...params.InputProps,
                  endAdornment: (
                    <>
                      {entityMergeTargetLoading ? <CircularProgress size={16} /> : null}
                      {params.InputProps.endAdornment}
                    </>
                  ),
                }}
              />
            )}
          />

          <Box>
            <Button
              variant="contained"
              color="warning"
              startIcon={<MergeTypeIcon />}
              disabled={!entityMergeSource || !entityMergeTarget || entityMergeSource.id === entityMergeTarget.id}
              onClick={openEntityMergeConfirm}
            >
              Merge
            </Button>
          </Box>
        </Stack>
      </Paper>
    </Stack>
  );
}
