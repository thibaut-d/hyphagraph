/**
 * SmartSourceDiscoveryView
 *
 * Intelligent multi-source discovery based on entities.
 *
 * Features:
 * - Entity-based search (1-10 entities)
 * - Multi-database support (PubMed, arXiv, etc.)
 * - Automatic quality scoring
 * - Budget-based pre-selection
 * - Deduplication against existing sources
 * - Bulk import workflow
 */

import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  Stack,
} from "@mui/material";

import { SmartDiscoveryConfigSection } from "../components/smart-discovery/SmartDiscoveryConfigSection";
import { SmartDiscoveryEntitySelector } from "../components/smart-discovery/SmartDiscoveryEntitySelector";
import { SmartDiscoveryHeader } from "../components/smart-discovery/SmartDiscoveryHeader";
import { SmartDiscoveryResultsSection } from "../components/smart-discovery/SmartDiscoveryResultsSection";
import { useDiscoveryEntities } from "../hooks/useDiscoveryEntities";
import { useSmartDiscoveryController } from "../hooks/useSmartDiscoveryController";

export function SmartSourceDiscoveryView() {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const {
    availableEntities,
    selectedEntities,
    setSelectedEntities,
    loadingEntities,
    entityLoadError,
  } = useDiscoveryEntities();
  const {
    maxResults,
    setMaxResults,
    minQuality,
    setMinQuality,
    selectedDatabases,
    setSelectedDatabases,
    searching,
    searchError,
    results,
    queryUsed,
    totalFound,
    selectedPmids,
    importing,
    importError,
    importSuccess,
    selectedCount,
    notImportedCount,
    alreadyImportedCount,
    handleSearch,
    handleToggleSelect,
    handleSelectAll,
    handleImport,
  } = useSmartDiscoveryController();

  const getQualityLabel = (trustLevel: number): string => {
    if (trustLevel >= 0.9) return "Systematic Review / Meta-analysis";
    if (trustLevel >= 0.75) return "RCT / High Quality";
    if (trustLevel >= 0.65) return "Case-Control";
    if (trustLevel >= 0.5) return "Observational";
    return "Low Quality";
  };

  const getQualityColor = (trustLevel: number): "success" | "info" | "warning" | "error" => {
    if (trustLevel >= 0.9) return "success";
    if (trustLevel >= 0.75) return "info";
    if (trustLevel >= 0.5) return "warning";
    return "error";
  };

  return (
    <Stack spacing={3}>
      <SmartDiscoveryHeader
        title={t("smart_discovery.title", "🔍 Smart Source Discovery")}
        description={t(
          "smart_discovery.description",
          "Automatically discover high-quality scientific sources related to your entities. The system will search PubMed, arXiv, and other databases, score each source using OCEBM/GRADE standards, and pre-select the best ones for you."
        )}
        onBack={() => navigate(-1)}
      />

      <SmartDiscoveryEntitySelector
        availableEntities={availableEntities}
        selectedEntities={selectedEntities}
        loadingEntities={loadingEntities}
        entityLoadError={entityLoadError}
        onChange={setSelectedEntities}
        title={t("smart_discovery.step1", "Select Entities")}
        helpText={t(
          "smart_discovery.step1_help",
          "Choose 1-10 entities to search for. The system will find sources that mention all selected entities."
        )}
        label={t("smart_discovery.select_entities", "Select entities (1-10)")}
        placeholder={t("smart_discovery.entity_placeholder", "Start typing to search...")}
        previewLabel={t("smart_discovery.query_preview", "Query will search for:")}
      />

      <SmartDiscoveryConfigSection
        maxResults={maxResults}
        minQuality={minQuality}
        selectedDatabases={selectedDatabases}
        searching={searching}
        searchError={searchError}
        onMaxResultsChange={setMaxResults}
        onMinQualityChange={setMinQuality}
        onDatabasesChange={setSelectedDatabases}
        onSearch={() => void handleSearch(selectedEntities)}
        searchDisabled={searching || selectedEntities.length === 0 || selectedDatabases.length === 0}
        getQualityLabel={getQualityLabel}
      />

      <SmartDiscoveryResultsSection
        results={results}
        queryUsed={queryUsed}
        totalFound={totalFound}
        maxResults={maxResults}
        selectedPmids={selectedPmids}
        selectedCount={selectedCount}
        notImportedCount={notImportedCount}
        alreadyImportedCount={alreadyImportedCount}
        importing={importing}
        importError={importError}
        importSuccess={importSuccess}
        onToggleSelect={handleToggleSelect}
        onSelectAll={handleSelectAll}
        onImport={() => void handleImport()}
        getQualityLabel={getQualityLabel}
        getQualityColor={getQualityColor}
      />
    </Stack>
  );
}
