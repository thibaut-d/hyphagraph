import {
  Alert,
  Autocomplete,
  Chip,
  Paper,
  TextField,
  Typography,
} from "@mui/material";

import type { EntityRead } from "../../types/entity";

interface SmartDiscoveryEntitySelectorProps {
  availableEntities: EntityRead[];
  selectedEntities: EntityRead[];
  loadingEntities: boolean;
  entityLoadError: string | null;
  entityListTruncated: boolean;
  entityTotal: number;
  onChange: (entities: EntityRead[]) => void;
  title: string;
  helpText: string;
  label: string;
  placeholder: string;
  previewLabel: string;
  truncatedHint: string;
}

export function SmartDiscoveryEntitySelector({
  availableEntities,
  selectedEntities,
  loadingEntities,
  entityLoadError,
  entityListTruncated,
  onChange,
  title,
  helpText,
  label,
  placeholder,
  previewLabel,
  truncatedHint,
}: SmartDiscoveryEntitySelectorProps) {
  return (
    <Paper sx={{ p: 3 }}>
      <Typography variant="h5" gutterBottom sx={{ display: "flex", alignItems: "center", gap: 1 }}>
        <span>1️⃣</span> {title}
      </Typography>

      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        {helpText}
      </Typography>

      <Autocomplete
        multiple
        options={availableEntities}
        getOptionLabel={(entity) => entity.slug}
        value={selectedEntities}
        onChange={(_, newValue) => onChange(newValue)}
        loading={loadingEntities}
        renderInput={(params) => (
          <TextField {...params} label={label} placeholder={placeholder} />
        )}
        renderTags={(value, getTagProps) =>
          value.map((entity, index) => (
            <Chip label={entity.slug} {...getTagProps({ index })} color="primary" />
          ))
        }
      />

      {entityListTruncated && (
        <Alert severity="info" sx={{ mt: 2 }}>
          {truncatedHint}
        </Alert>
      )}

      {entityLoadError && (
        <Alert severity="error" sx={{ mt: 2 }}>
          {entityLoadError}
        </Alert>
      )}

      {selectedEntities.length > 0 && (
        <Alert severity="success" sx={{ mt: 2 }}>
          {previewLabel}{" "}
          <strong>
            {selectedEntities
              .map((entity) => entity.slug.replace("-", " ").toUpperCase())
              .join(" AND ")}
          </strong>
        </Alert>
      )}
    </Paper>
  );
}
