import { Alert, Box, IconButton, Paper, Typography } from "@mui/material";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import AutoFixHighIcon from "@mui/icons-material/AutoFixHigh";

interface SmartDiscoveryHeaderProps {
  title: string;
  description: string;
  onBack: () => void;
}

export function SmartDiscoveryHeader({
  title,
  description,
  onBack,
}: SmartDiscoveryHeaderProps) {
  return (
    <Paper sx={{ p: 3 }}>
      <Box sx={{ display: "flex", alignItems: "center", gap: 2, mb: 2 }}>
        <IconButton onClick={onBack} size="small">
          <ArrowBackIcon />
        </IconButton>
        <Typography variant="h4">{title}</Typography>
      </Box>

      <Alert severity="info" icon={<AutoFixHighIcon />}>
        {description}
      </Alert>
    </Paper>
  );
}
