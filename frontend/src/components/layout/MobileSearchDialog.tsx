import { useTranslation } from "react-i18next";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  IconButton,
  Box,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import { GlobalSearch } from "../GlobalSearch";

interface MobileSearchDialogProps {
  open: boolean;
  onClose: () => void;
}

/**
 * Mobile search dialog.
 *
 * Full-screen dialog containing GlobalSearch component for mobile devices.
 */
export function MobileSearchDialog({ open, onClose }: MobileSearchDialogProps) {
  const { t } = useTranslation();

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="sm"
      fullWidth
      sx={{ display: { xs: "block", md: "none" } }}
    >
      <DialogTitle
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        {t("common.search", "Search")}
        <IconButton onClick={onClose} size="small" edge="end">
          <CloseIcon />
        </IconButton>
      </DialogTitle>
      <DialogContent>
        <Box sx={{ pt: 1 }}>
          <GlobalSearch />
        </Box>
      </DialogContent>
    </Dialog>
  );
}
