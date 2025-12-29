import { useState, useCallback, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  TextField,
  Autocomplete,
  Box,
  Typography,
  Chip,
  InputAdornment,
  CircularProgress,
  Paper,
} from "@mui/material";
import SearchIcon from "@mui/icons-material/Search";
import { getSuggestions, SearchSuggestion } from "../api/search";
import { useDebounce } from "../hooks/useDebounce";

/**
 * GlobalSearch component for the main navigation header.
 *
 * Provides autocomplete search with suggestions from entities and sources.
 * Uses debounced input to avoid excessive API calls.
 */
export function GlobalSearch() {
  const navigate = useNavigate();
  const [inputValue, setInputValue] = useState("");
  const [suggestions, setSuggestions] = useState<SearchSuggestion[]>([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);

  // Debounce input to reduce API calls
  const debouncedQuery = useDebounce(inputValue, 300);

  // Fetch suggestions when debounced query changes
  useEffect(() => {
    if (!debouncedQuery || debouncedQuery.length < 2) {
      setSuggestions([]);
      return;
    }

    const fetchSuggestions = async () => {
      setLoading(true);
      try {
        const response = await getSuggestions(debouncedQuery, undefined, 10);
        setSuggestions(response.suggestions);
      } catch (error) {
        console.error("Failed to fetch suggestions:", error);
        setSuggestions([]);
      } finally {
        setLoading(false);
      }
    };

    fetchSuggestions();
  }, [debouncedQuery]);

  const handleSelect = useCallback(
    (_event: any, value: SearchSuggestion | null) => {
      if (value) {
        // Navigate to detail page based on type
        if (value.type === "entity") {
          navigate(`/entities/${value.id}`);
        } else if (value.type === "source") {
          navigate(`/sources/${value.id}`);
        }
        // Clear input after selection
        setInputValue("");
        setOpen(false);
      }
    },
    [navigate]
  );

  const handleInputChange = useCallback(
    (_event: any, newValue: string, reason: string) => {
      if (reason === "input") {
        setInputValue(newValue);
        setOpen(true);
      } else if (reason === "clear") {
        setInputValue("");
        setSuggestions([]);
        setOpen(false);
      }
    },
    []
  );

  const handleKeyDown = useCallback(
    (event: React.KeyboardEvent) => {
      // If user presses Enter without selecting a suggestion, go to search page
      if (event.key === "Enter" && inputValue.trim()) {
        const searchQuery = inputValue.trim();
        setInputValue("");
        setOpen(false);
        navigate(`/search?q=${encodeURIComponent(searchQuery)}`);
      }
    },
    [inputValue, navigate]
  );

  return (
    <Autocomplete
      freeSolo
      open={open && suggestions.length > 0}
      onOpen={() => setOpen(true)}
      onClose={() => setOpen(false)}
      options={suggestions}
      inputValue={inputValue}
      onInputChange={handleInputChange}
      onChange={handleSelect}
      getOptionLabel={(option) =>
        typeof option === "string" ? option : option.label
      }
      filterOptions={(x) => x} // Don't filter - backend does that
      loading={loading}
      renderInput={(params) => (
        <TextField
          {...params}
          placeholder="Search entities, sources..."
          size="small"
          onKeyDown={handleKeyDown}
          InputProps={{
            ...params.InputProps,
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon fontSize="small" />
              </InputAdornment>
            ),
            endAdornment: (
              <>
                {loading ? (
                  <CircularProgress color="inherit" size={20} />
                ) : null}
                {params.InputProps.endAdornment}
              </>
            ),
          }}
          sx={{
            minWidth: { xs: 200, sm: 300, md: 400 },
            backgroundColor: "background.paper",
            borderRadius: 1,
            "& .MuiOutlinedInput-root": {
              "& fieldset": {
                borderColor: "divider",
              },
              "&:hover fieldset": {
                borderColor: "primary.main",
              },
            },
          }}
        />
      )}
      renderOption={(props, option) => (
        <Box component="li" {...props} key={option.id}>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1, flex: 1 }}>
            <Chip
              label={option.type}
              size="small"
              color={option.type === "entity" ? "primary" : "secondary"}
              sx={{ minWidth: 60 }}
            />
            <Box sx={{ flex: 1, minWidth: 0 }}>
              <Typography variant="body2" noWrap>
                {option.label}
              </Typography>
              {option.secondary && (
                <Typography variant="caption" color="text.secondary" noWrap>
                  {option.secondary}
                </Typography>
              )}
            </Box>
          </Box>
        </Box>
      )}
      PaperComponent={(props) => (
        <Paper {...props} elevation={8} sx={{ mt: 1 }} />
      )}
    />
  );
}
