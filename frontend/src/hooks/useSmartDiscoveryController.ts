import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import {
  bulkImportFromDiscovery,
  startSmartDiscoveryJob,
  type SmartDiscoveryResponse,
  type SmartDiscoveryResult,
} from "../api/smart-discovery";
import { getLongRunningJob } from "../api/longRunningJobs";
import type { EntityRead } from "../types/entity";
import { useNotification } from "../notifications/NotificationContext";
import { usePageErrorHandler } from "./usePageErrorHandler";

interface ImportSuccess {
  created: number;
  failed: number;
}

interface SmartDiscoveryController {
  maxResults: number;
  setMaxResults: React.Dispatch<React.SetStateAction<number>>;
  minQuality: number;
  setMinQuality: React.Dispatch<React.SetStateAction<number>>;
  selectedDatabases: string[];
  setSelectedDatabases: React.Dispatch<React.SetStateAction<string[]>>;
  searching: boolean;
  searchError: string | null;
  results: SmartDiscoveryResult[];
  queryUsed: string;
  totalFound: number;
  selectedPmids: Set<string>;
  importing: boolean;
  importError: string | null;
  importSuccess: ImportSuccess | null;
  selectedCount: number;
  notImportedCount: number;
  alreadyImportedCount: number;
  handleSearch: (selectedEntities: EntityRead[]) => Promise<void>;
  handleToggleSelect: (pmid: string) => void;
  handleSelectAll: () => void;
  handleImport: () => Promise<void>;
}

const SMART_DISCOVERY_JOB_STORAGE_KEY = "hyphagraph.smartDiscoveryJobId";
const POLL_INTERVAL_MS = 2000;

export function useSmartDiscoveryController(): SmartDiscoveryController {
  const navigate = useNavigate();
  const { showError } = useNotification();
  const handlePageError = usePageErrorHandler();

  const [maxResults, setMaxResults] = useState(20);
  const [minQuality, setMinQuality] = useState(0.75);
  const [selectedDatabases, setSelectedDatabases] = useState<string[]>(["pubmed"]);

  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [results, setResults] = useState<SmartDiscoveryResult[]>([]);
  const [queryUsed, setQueryUsed] = useState("");
  const [totalFound, setTotalFound] = useState(0);
  const [selectedPmids, setSelectedPmids] = useState<Set<string>>(new Set());

  const [importing, setImporting] = useState(false);
  const [importError, setImportError] = useState<string | null>(null);
  const [importSuccess, setImportSuccess] = useState<ImportSuccess | null>(null);

  const applyDiscoveryResponse = useCallback((response: SmartDiscoveryResponse) => {
    setResults(response.results);
    setQueryUsed(response.query_used);
    setTotalFound(response.total_found);

    const autoSelectedPmids = response.results
      .filter((result) => !result.already_imported)
      .slice(0, maxResults)
      .map((result) => result.pmid)
      .filter((pmid): pmid is string => Boolean(pmid));

    setSelectedPmids(new Set(autoSelectedPmids));
  }, [maxResults]);

  const pollDiscoveryJob = useCallback(async (jobId: string) => {
    const job = await getLongRunningJob<SmartDiscoveryResponse>(jobId);

    if (job.status === "succeeded" && job.result_payload) {
      applyDiscoveryResponse(job.result_payload);
      localStorage.removeItem(SMART_DISCOVERY_JOB_STORAGE_KEY);
      setSearching(false);
      return true;
    }

    if (job.status === "failed") {
      localStorage.removeItem(SMART_DISCOVERY_JOB_STORAGE_KEY);
      setSearchError(job.error_message || "Smart discovery failed");
      setSearching(false);
      return true;
    }

    setSearching(true);
    return false;
  }, [applyDiscoveryResponse]);

  const pollDiscoveryJobUntilDone = useCallback((jobId: string) => {
    let cancelled = false;
    let timeoutId: number | undefined;

    const poll = async () => {
      try {
        const done = await pollDiscoveryJob(jobId);
        if (!done && !cancelled) {
          timeoutId = window.setTimeout(poll, POLL_INTERVAL_MS);
        }
      } catch (error) {
        if (!cancelled) {
          localStorage.removeItem(SMART_DISCOVERY_JOB_STORAGE_KEY);
          setSearchError(handlePageError(error, "Failed to resume smart discovery").userMessage);
          setSearching(false);
        }
      }
    };

    void poll();

    return () => {
      cancelled = true;
      if (timeoutId !== undefined) {
        window.clearTimeout(timeoutId);
      }
    };
  }, [handlePageError, pollDiscoveryJob]);

  useEffect(() => {
    const jobId = localStorage.getItem(SMART_DISCOVERY_JOB_STORAGE_KEY);
    if (!jobId) {
      return;
    }

    return pollDiscoveryJobUntilDone(jobId);
  }, [pollDiscoveryJobUntilDone]);

  const handleSearch = async (selectedEntities: EntityRead[]) => {
    if (selectedEntities.length === 0) {
      showError("Please select at least one entity");
      return;
    }

    if (selectedDatabases.length === 0) {
      showError("Please select at least one database");
      return;
    }

    setSearching(true);
    setSearchError(null);
    setResults([]);
    setSelectedPmids(new Set());
    setImportSuccess(null);
    setImportError(null);

    try {
      const job = await startSmartDiscoveryJob({
        entity_slugs: selectedEntities.map((entity) => entity.slug),
        max_results: maxResults,
        min_quality: minQuality,
        databases: selectedDatabases,
      });
      localStorage.setItem(SMART_DISCOVERY_JOB_STORAGE_KEY, job.job_id);
      pollDiscoveryJobUntilDone(job.job_id);
    } catch (error) {
      setSearchError(handlePageError(error, "Failed to run smart discovery").userMessage);
      setSearching(false);
    }
  };

  const handleToggleSelect = (pmid: string) => {
    setSelectedPmids((currentSelection) => {
      const nextSelection = new Set(currentSelection);
      if (nextSelection.has(pmid)) {
        nextSelection.delete(pmid);
      } else {
        nextSelection.add(pmid);
      }
      return nextSelection;
    });
  };

  const notImportedResults = useMemo(
    () => results.filter((result) => result.pmid && !result.already_imported),
    [results]
  );

  const handleSelectAll = () => {
    const budgetedResults = notImportedResults.slice(0, maxResults);
    if (selectedPmids.size === budgetedResults.length) {
      setSelectedPmids(new Set());
      return;
    }

    setSelectedPmids(
      new Set(
        budgetedResults
          .map((result) => result.pmid)
          .filter((pmid): pmid is string => Boolean(pmid))
      )
    );
  };

  const handleImport = async () => {
    if (selectedPmids.size === 0) {
      showError("Please select at least one article to import");
      return;
    }

    setImporting(true);
    setImportError(null);

    try {
      const response = await bulkImportFromDiscovery(Array.from(selectedPmids));
      setImportSuccess({
        created: response.sources_created,
        failed: response.failed_pmids.length,
      });

      setTimeout(() => {
        navigate("/sources");
      }, 2000);
    } catch (error) {
      setImportError(handlePageError(error, "Failed to import articles").userMessage);
    } finally {
      setImporting(false);
    }
  };

  return {
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
    selectedCount: selectedPmids.size,
    notImportedCount: notImportedResults.length,
    alreadyImportedCount: results.filter((result) => result.already_imported).length,
    handleSearch,
    handleToggleSelect,
    handleSelectAll,
    handleImport,
  };
}
