import { useState } from "react";
import { Link as RouterLink } from "react-router-dom";
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Link,
  Paper,
  Slider,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import AutoFixHighIcon from "@mui/icons-material/AutoFixHigh";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import RateReviewIcon from "@mui/icons-material/RateReview";

import { startBulkSourceExtractionJob } from "../api/extraction";
import { getLongRunningJob } from "../api/longRunningJobs";
import type { BulkSourceExtractionResponse } from "../types/extraction";
import { usePageErrorHandler } from "../hooks/usePageErrorHandler";

export function BulkSourceExtractionView() {
  const handlePageError = usePageErrorHandler();
  const [searchTerm, setSearchTerm] = useState("");
  const [studyBudget, setStudyBudget] = useState(10);
  const [extracting, setExtracting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<BulkSourceExtractionResponse | null>(null);

  const waitForJob = async (jobId: string): Promise<BulkSourceExtractionResponse> => {
    for (let attempt = 0; attempt < 180; attempt += 1) {
      const job = await getLongRunningJob<BulkSourceExtractionResponse>(jobId);
      if (job.status === "succeeded" && job.result_payload) {
        return job.result_payload;
      }
      if (job.status === "failed") {
        throw new Error(job.error_message || "Bulk extraction failed");
      }
      await new Promise((resolve) => setTimeout(resolve, 2000));
    }
    throw new Error("Bulk extraction is still running. Check the review queue later.");
  };

  const handleBulkExtract = async () => {
    if (!searchTerm.trim()) {
      setError("Enter words to search imported studies");
      return;
    }

    setExtracting(true);
    setError(null);
    setResult(null);

    try {
      const job = await startBulkSourceExtractionJob({
        search: searchTerm,
        study_budget: studyBudget,
      });
      setResult(await waitForJob(job.job_id));
    } catch (caught) {
      const parsedError = handlePageError(caught, "Failed to bulk extract studies");
      setError(parsedError.userMessage);
    } finally {
      setExtracting(false);
    }
  };

  return (
    <Stack spacing={3}>
      <Box>
        <Button component={RouterLink} to="/sources" startIcon={<ArrowBackIcon />} size="small">
          Back to sources
        </Button>
      </Box>

      <Paper sx={{ p: 3 }}>
        <Typography variant="h4" gutterBottom>
          Bulk Extract Imported Studies
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Search studies that are already in Sources, then run automatic entity and relation
          extraction on matching studies that have not been extracted yet.
        </Typography>
      </Paper>

      <Paper sx={{ p: 3 }}>
        <Stack spacing={2}>
          <TextField
            fullWidth
            label="Search imported studies"
            placeholder="e.g., ketamine depression"
            value={searchTerm}
            onChange={(event) => setSearchTerm(event.target.value)}
            disabled={extracting}
          />
          <Box>
            <Typography gutterBottom>Study budget: {studyBudget}</Typography>
            <Slider
              value={studyBudget}
              onChange={(_, value) => setStudyBudget(value as number)}
              min={1}
              max={50}
              step={1}
              marks={[
                { value: 1, label: "1" },
                { value: 10, label: "10" },
                { value: 25, label: "25" },
                { value: 50, label: "50" },
              ]}
              disabled={extracting}
              sx={{ maxWidth: 600 }}
            />
          </Box>
          <Box>
            <Button
              variant="contained"
              startIcon={extracting ? <CircularProgress size={16} /> : <AutoFixHighIcon />}
              onClick={handleBulkExtract}
              disabled={extracting}
            >
              {extracting ? "Extracting..." : "Start Bulk Extraction"}
            </Button>
          </Box>
        </Stack>

        {error && (
          <Alert severity="error" sx={{ mt: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}
        {result && (
          <Alert
            severity={result.failed_count > 0 ? "warning" : "success"}
            icon={<RateReviewIcon />}
            sx={{ mt: 2 }}
          >
            Matched {result.matched_count} unextracted studies. Extracted{" "}
            {result.extracted_count} of {result.selected_count} selected studies;{" "}
            {result.failed_count} failed. Review staged entities and relations in the{" "}
            <Link component={RouterLink} to="/review-queue">
              review queue
            </Link>
            .
          </Alert>
        )}
      </Paper>
    </Stack>
  );
}
