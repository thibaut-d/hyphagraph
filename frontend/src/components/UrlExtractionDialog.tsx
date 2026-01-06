/**
 * Dialog for URL-based document extraction.
 *
 * Allows users to input a URL (PubMed article, web page, etc.) and fetch
 * content for knowledge extraction.
 */
import React, { useState } from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Button,
  Alert,
  Box,
  Typography,
  CircularProgress,
} from "@mui/material";
import { Link as LinkIcon } from "@mui/icons-material";

interface UrlExtractionDialogProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (url: string) => Promise<void>;
  loading?: boolean;
}

/**
 * URL extraction dialog component.
 *
 * Features:
 * - URL input with validation
 * - PubMed URL detection
 * - Loading state
 * - Error handling
 */
export function UrlExtractionDialog({
  open,
  onClose,
  onSubmit,
  loading = false,
}: UrlExtractionDialogProps) {
  const [url, setUrl] = useState("");
  const [error, setError] = useState<string | null>(null);

  const isPubMedUrl = (urlString: string): boolean => {
    try {
      const urlObj = new URL(urlString);
      return (
        urlObj.hostname.includes("pubmed.ncbi.nlm.nih.gov") ||
        urlObj.hostname.includes("ncbi.nlm.nih.gov")
      );
    } catch {
      return false;
    }
  };

  const validateUrl = (urlString: string): boolean => {
    try {
      new URL(urlString);
      return true;
    } catch {
      return false;
    }
  };

  const handleSubmit = async () => {
    setError(null);

    if (!url.trim()) {
      setError("Please enter a URL");
      return;
    }

    if (!validateUrl(url)) {
      setError("Please enter a valid URL (e.g., https://pubmed.ncbi.nlm.nih.gov/...)");
      return;
    }

    try {
      await onSubmit(url);
      setUrl("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to extract from URL");
    }
  };

  const handleClose = () => {
    if (!loading) {
      setUrl("");
      setError(null);
      onClose();
    }
  };

  const urlType = isPubMedUrl(url)
    ? "PubMed article (uses official NCBI API)"
    : url && validateUrl(url)
    ? "Web page (limited support)"
    : "";

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <DialogTitle>
        <Box display="flex" alignItems="center" gap={1}>
          <LinkIcon />
          <span>Extract from URL</span>
        </Box>
      </DialogTitle>

      <DialogContent>
        <Box sx={{ pt: 1, display: "flex", flexDirection: "column", gap: 2 }}>
          <Typography variant="body2" color="text.secondary">
            Enter a URL to fetch content and extract knowledge. Supports PubMed
            articles and general web pages.
          </Typography>

          <TextField
            autoFocus
            fullWidth
            label="URL"
            placeholder="https://pubmed.ncbi.nlm.nih.gov/12345678/"
            value={url}
            onChange={(e) => {
              setUrl(e.target.value);
              setError(null);
            }}
            disabled={loading}
            error={Boolean(error)}
            helperText={error || urlType}
            onKeyPress={(e) => {
              if (e.key === "Enter" && !loading) {
                handleSubmit();
              }
            }}
          />

          {loading && (
            <Alert severity="info" sx={{ alignItems: "center" }}>
              <Box display="flex" alignItems="center" gap={2}>
                <CircularProgress size={20} />
                <span>Fetching URL and extracting knowledge...</span>
              </Box>
            </Alert>
          )}

          <Alert severity="info">
            <Typography variant="body2" fontWeight="bold">
              Supported URLs:
            </Typography>
            <Typography variant="body2" component="div">
              • <strong>PubMed articles</strong> - Full support with metadata
              (PMID, DOI, authors, journal)
              <br />• <strong>General web pages</strong> - Limited support (many
              sites block automated access)
            </Typography>
          </Alert>
        </Box>
      </DialogContent>

      <DialogActions>
        <Button onClick={handleClose} disabled={loading}>
          Cancel
        </Button>
        <Button
          onClick={handleSubmit}
          variant="contained"
          disabled={loading || !url.trim()}
          startIcon={loading ? <CircularProgress size={16} /> : <LinkIcon />}
        >
          {loading ? "Extracting..." : "Extract"}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
