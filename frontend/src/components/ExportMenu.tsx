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
import { useNotification } from "../notifications/NotificationContext";
import { downloadExportFile } from "../api/export";

interface ExportMenuProps {
  exportType: "entities" | "relations" | "sources" | "full-graph";
  onExport?: (format: string) => void;
  disabled?: boolean;
  buttonText?: string;
  size?: "small" | "medium" | "large";
  /** Optional filter params forwarded to the export endpoint (exports only visible/filtered data). */
  filterParams?: Record<string, string | number | string[] | undefined | null>;
}

export function ExportMenu({
  exportType,
  onExport,
  disabled = false,
  buttonText = "Export",
  size = "small",
  filterParams,
}: ExportMenuProps) {
  const { showError } = useNotification();
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
      await downloadExportFile(exportType, format, filterParams);

      if (onExport) {
        onExport(format);
      }
    } catch (error) {
      console.error("Export failed:", error);
      showError(new Error(`Export failed: ${error instanceof Error ? error.message : "Unknown error"}`));
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
        {(exportType === "entities" || exportType === "relations" || exportType === "sources") && (
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

            {exportType !== "sources" && (
              <MenuItem onClick={() => handleExport("rdf")}>
                <ListItemIcon>
                  <AccountTreeIcon fontSize="small" />
                </ListItemIcon>
                <ListItemText>Export as RDF/Turtle</ListItemText>
              </MenuItem>
            )}
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
