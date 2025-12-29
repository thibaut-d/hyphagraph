import { useEffect, useState } from "react";
import { Box } from "@mui/material";
import { useTranslation } from "react-i18next";

import { FilterSection } from "./FilterSection";
import { CheckboxFilter } from "./CheckboxFilter";
import { RangeFilter } from "./RangeFilter";
import { SourceRead } from "../../types/source";

export interface EntityDetailFilterValues {
  directions?: string[];
  kinds?: string[];
  yearRange?: [number, number];
  minTrustLevel?: number;
}

interface EntityDetailFiltersProps {
  filters: EntityDetailFilterValues;
  onFilterChange: (key: string, value: any) => void;
  sources: SourceRead[];
}

/**
 * Filter controls for EntityDetailView.
 *
 * Allows filtering relations by:
 * - Evidence direction (supports/contradicts/heterogeneous)
 * - Study type (source kind)
 * - Publication year range
 * - Minimum source authority (trust level)
 *
 * Per UX.md Section 5.3: "Allow users to change their analytical point of view"
 * These filters affect displayed evidence but never change consensus status or computed scores.
 */
export function EntityDetailFilters({
  filters,
  onFilterChange,
  sources,
}: EntityDetailFiltersProps) {
  const { t } = useTranslation();

  // Extract unique directions from sources
  const [directionOptions, setDirectionOptions] = useState<{ value: string; label: string }[]>([]);

  // Extract unique kinds from sources
  const [kindOptions, setKindOptions] = useState<{ value: string; label: string }[]>([]);

  // Extract year range from sources
  const [yearRange, setYearRange] = useState<[number, number] | null>(null);

  useEffect(() => {
    // Note: Direction comes from relations, not sources
    // We'll provide common direction options statically
    const commonDirections = [
      { value: "positive", label: t("relation.direction.positive", "Supports") },
      { value: "negative", label: t("relation.direction.negative", "Contradicts") },
      { value: "neutral", label: t("relation.direction.neutral", "Neutral") },
      { value: "mixed", label: t("relation.direction.mixed", "Mixed") },
    ];
    setDirectionOptions(commonDirections);

    // Extract unique source kinds
    const uniqueKinds = Array.from(new Set(sources.map((s) => s.kind)))
      .filter(Boolean)
      .sort()
      .map((kind) => ({ value: kind, label: kind }));
    setKindOptions(uniqueKinds);

    // Calculate year range from sources
    if (sources.length > 0) {
      const years = sources.map((s) => s.year).filter((y) => y != null);
      if (years.length > 0) {
        const min = Math.min(...years);
        const max = Math.max(...years);
        setYearRange([min, max]);
      }
    }
  }, [sources, t]);

  return (
    <Box>
      {directionOptions.length > 0 && (
        <FilterSection title={t("filters.evidence_direction", "Evidence Direction")}>
          <CheckboxFilter
            options={directionOptions}
            value={filters.directions || []}
            onChange={(value) => onFilterChange("directions", value)}
          />
        </FilterSection>
      )}

      {kindOptions.length > 0 && (
        <FilterSection title={t("filters.study_type", "Study Type")}>
          <CheckboxFilter
            options={kindOptions}
            value={filters.kinds || []}
            onChange={(value) => onFilterChange("kinds", value)}
          />
        </FilterSection>
      )}

      {yearRange && (
        <FilterSection title={t("filters.publication_year", "Publication Year")}>
          <RangeFilter
            min={yearRange[0]}
            max={yearRange[1]}
            step={1}
            value={filters.yearRange || yearRange}
            onChange={(value) => onFilterChange("yearRange", value)}
            formatValue={(v) => v.toString()}
          />
        </FilterSection>
      )}

      <FilterSection title={t("filters.minimum_authority", "Minimum Authority Score")}>
        <RangeFilter
          min={0}
          max={1}
          step={0.1}
          value={[filters.minTrustLevel ?? 0, 1]}
          onChange={(value) => onFilterChange("minTrustLevel", value[0])}
          formatValue={(v) => v.toFixed(1)}
        />
      </FilterSection>
    </Box>
  );
}
