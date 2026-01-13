/**
 * ExportMenu Component
 *
 * Dropdown menu for exporting data in multiple formats.
 * Supports JSON, CSV, and RDF exports with authentication.
 */
import { useState } from "react";
import {
  Button,
  Menu,
  MenuItem,
  ListItemIcon,
  ListItemText,
  CircularProgress,
} from "@mui/material";
import DownloadIcon from "@mui/icons-material/Download";
import DataObjectIcon from "@mui/icons-material/DataObject";
import TableChartIcon from "@mui/icons-material/TableChart";
import AccountTreeIcon from "@mui/icons-material/AccountTree";

interface ExportMenuProps {
  exportType: "entities" | "relations" | "full-graph";
  onExport?: (format: string) => void;
  disabled?: boolean;
  buttonText?: string;
  size?: "small" | "medium" | "large";
}

export function ExportMenu({
  exportType,
  onExport,
  disabled = false,
  buttonText = "Export",
  size = "small",
}: ExportMenuProps) {
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [exporting, setExporting] = useState(false);
  const open = Boolean(anchorEl);

  const handleClick = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const handleExport = async (format: string) => {
    setExporting(true);
    handleClose();

    try {
      // Get authentication token
      const token = localStorage.getItem("auth_token");

      if (!token) {
        alert("Please login to export data");
        return;
      }

      // Build export URL
      const baseUrl = `/api/export/${exportType}`;
      const url = exportType === "full-graph"
        ? baseUrl
        : `${baseUrl}?format=${format}`;

      // Fetch export
      const response = await fetch(url, {
        headers: {
          "Authorization": `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error(`Export failed: ${response.statusText}`);
      }

      // Get filename from Content-Disposition header
      const disposition = response.headers.get("Content-Disposition");
      const filenameMatch = disposition?.match(/filename="(.+)"/);
      const filename = filenameMatch?.[1] || `${exportType}-export.${format}`;

      // Download file
      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = downloadUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(downloadUrl);

      if (onExport) {
        onExport(format);
      }
    } catch (error) {
      console.error("Export failed:", error);
      alert(`Export failed: ${error instanceof Error ? error.message : "Unknown error"}`);
    } finally {
      setExporting(false);
    }
  };

  return (
    <>
      <Button
        variant="outlined"
        startIcon={exporting ? <CircularProgress size={16} /> : <DownloadIcon />}
        onClick={handleClick}
        disabled={disabled || exporting}
        size={size}
      >
        {exporting ? "Exporting..." : buttonText}
      </Button>

      <Menu
        anchorEl={anchorEl}
        open={open}
        onClose={handleClose}
      >
        {exportType !== "full-graph" && (
          <>
            <MenuItem onClick={() => handleExport("json")}>
              <ListItemIcon>
                <DataObjectIcon fontSize="small" />
              </ListItemIcon>
              <ListItemText>Export as JSON</ListItemText>
            </MenuItem>

            <MenuItem onClick={() => handleExport("csv")}>
              <ListItemIcon>
                <TableChartIcon fontSize="small" />
              </ListItemIcon>
              <ListItemText>Export as CSV</ListItemText>
            </MenuItem>

            <MenuItem onClick={() => handleExport("rdf")}>
              <ListItemIcon>
                <AccountTreeIcon fontSize="small" />
              </ListItemIcon>
              <ListItemText>Export as RDF/Turtle</ListItemText>
            </MenuItem>
          </>
        )}

        {exportType === "full-graph" && (
          <MenuItem onClick={() => handleExport("json")}>
            <ListItemIcon>
              <DataObjectIcon fontSize="small" />
            </ListItemIcon>
            <ListItemText>Export Complete Graph (JSON)</ListItemText>
          </MenuItem>
        )}
      </Menu>
    </>
  );
}
