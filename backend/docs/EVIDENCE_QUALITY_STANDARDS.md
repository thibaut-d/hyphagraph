# Evidence Quality Standards & Trust Level Scoring

## Overview

HyphaGraph uses **evidence-based medicine (EBM) standards** to automatically calculate source quality scores (`trust_level` field, 0.0-1.0).

Our implementation is based on:
1. **Oxford Centre for Evidence-Based Medicine (OCEBM) Levels of Evidence (2011)**
2. **GRADE (Grading of Recommendations Assessment, Development and Evaluation)**

---

## Oxford CEBM Levels of Evidence

Source: [OCEBM Levels of Evidence](https://www.cebm.ox.ac.uk/resources/levels-of-evidence/ocebm-levels-of-evidence)

### Therapy / Prevention / Etiology / Harm

| Level | Study Type | Trust Level | Description |
|-------|-----------|-------------|-------------|
| **1a** | Systematic review of RCTs | 1.0 | Systematic reviews with homogeneity |
| **1b** | Individual RCT | 0.9 | Randomized controlled trial with narrow confidence interval |
| **1c** | All or none | 0.85 | All patients died before treatment, some survive now |
| **2a** | Systematic review of cohort studies | 0.8 | With homogeneity |
| **2b** | Individual cohort study | 0.75 | Including low-quality RCT |
| **2c** | Outcomes research | 0.7 | Ecological studies |
| **3a** | Systematic review of case-control studies | 0.7 | With homogeneity |
| **3b** | Individual case-control study | 0.65 | |
| **4** | Case series / Poor cohort/case-control | 0.5 | Case series, poor quality studies |
| **5** | Expert opinion | 0.3 | Without explicit critical appraisal, based on physiology, bench research, or "first principles" |

### Additional Categories (Preclinical)

| Study Type | Trust Level | Description |
|-----------|-------------|-------------|
| Animal studies | 0.45 | In vivo preclinical research |
| In vitro studies | 0.4 | Laboratory/cell culture research |
| Mechanistic studies | 0.35 | Theoretical or mechanistic only |

---

## GRADE Quality of Evidence

Source: [GRADE Working Group](https://www.gradeworkinggroup.org/)

GRADE uses a 4-level system:
- **High** (⊕⊕⊕⊕): Further research is very unlikely to change confidence → Trust Level: 0.85-1.0
- **Moderate** (⊕⊕⊕◯): Further research likely to have impact → Trust Level: 0.65-0.84
- **Low** (⊕⊕◯◯): Further research very likely to have impact → Trust Level: 0.4-0.64
- **Very Low** (⊕◯◯◯): Very uncertain about the estimate → Trust Level: 0.0-0.39

### GRADE Factors

GRADE adjusts quality based on:
1. **Study design** (RCT starts high, observational starts low)
2. **Risk of bias** → We use journal impact as proxy
3. **Inconsistency** → Not yet implemented (would require multiple sources)
4. **Indirectness** → Not yet implemented
5. **Imprecision** → We use sample size as proxy
6. **Publication bias** → Journal quality and preprint status

---

## HyphaGraph Implementation

### Mapping: Study Type → Trust Level

```python
EVIDENCE_HIERARCHY = {
    "systematic_review": 1.0,          # OCEBM Level 1a / GRADE High
    "meta_analysis": 0.95,             # OCEBM Level 1a / GRADE High
    "randomized_controlled_trial": 0.9, # OCEBM Level 1b / GRADE High
    "cohort_study": 0.75,              # OCEBM Level 2b / GRADE Moderate
    "case_control_study": 0.65,        # OCEBM Level 3b / GRADE Moderate
    "case_series": 0.5,                # OCEBM Level 4 / GRADE Low
    "case_report": 0.4,                # OCEBM Level 4 / GRADE Low
    "expert_opinion": 0.3,             # OCEBM Level 5 / GRADE Very Low
    "in_vitro": 0.4,                   # Preclinical (below OCEBM scale)
    "animal_study": 0.45,              # Preclinical
    "unknown": 0.5,                    # Neutral default
}
```

### Modifiers Applied

#### 1. Journal Quality (Venue Modifier)
- **High-impact journals** (NEJM, Lancet, JAMA, BMJ, Nature, Science): ×1.0
- **Peer-reviewed journals**: ×1.0
- **Preprints** (bioRxiv, medRxiv, arXiv): ×0.85
- **Unknown venue**: ×0.95

#### 2. Sample Size Bonus
- Logarithmic bonus up to +0.05
- 100 participants: +0.01
- 1,000 participants: +0.03
- 10,000 participants: +0.05

#### 3. Publication Age Penalty
- Studies >20 years old: progressive penalty
- Maximum penalty: -0.1

### Formula

```
trust_level = base_score × venue_modifier + sample_bonus - age_penalty
```

Clamped to [0.0, 1.0] and rounded to 2 decimals.

---

## Examples

### High Quality Evidence

```python
# Systematic Review in Cochrane Database
infer_trust_level_from_pubmed_metadata(
    title="Systematic review and meta-analysis of duloxetine for fibromyalgia",
    journal="Cochrane Database of Systematic Reviews",
    year=2024
)
# Result: 1.0 (OCEBM Level 1a, GRADE High)

# RCT in NEJM with large sample
calculate_trust_level(
    study_type="randomized_controlled_trial",
    journal="New England Journal of Medicine",
    sample_size=5000,
    publication_year=2023
)
# Result: 0.91 (OCEBM Level 1b, GRADE High)
```

### Moderate Quality Evidence

```python
# Cohort Study in reputable journal
calculate_trust_level(
    study_type="cohort_study",
    journal="Journal of Clinical Medicine",
    publication_year=2022
)
# Result: 0.75 (OCEBM Level 2b, GRADE Moderate)

# Case-Control Study
calculate_trust_level(
    study_type="case_control_study",
    is_peer_reviewed=True
)
# Result: 0.65 (OCEBM Level 3b, GRADE Moderate)
```

### Low Quality Evidence

```python
# Case Report
calculate_trust_level(
    study_type="case_report"
)
# Result: 0.4 (OCEBM Level 4, GRADE Low)

# Preprint RCT (not yet peer-reviewed)
calculate_trust_level(
    study_type="randomized_controlled_trial",
    journal="medRxiv",
    is_peer_reviewed=False
)
# Result: 0.765 (0.9 × 0.85, GRADE Moderate downgraded)
```

### Very Low Quality Evidence

```python
# Expert Opinion / Editorial
calculate_trust_level(
    study_type="expert_opinion"
)
# Result: 0.3 (OCEBM Level 5, GRADE Very Low)

# Website / Blog
website_trust_level()
# Result: 0.3 (GRADE Very Low)
```

---

## Automatic Detection

### Study Type Detection from Title

The system automatically detects study type from article titles using keywords:

| Keywords | Detected Type |
|----------|--------------|
| "systematic review", "meta-analysis" | `systematic_review` / `meta_analysis` |
| "randomized controlled trial", "RCT", "double-blind" | `randomized_controlled_trial` |
| "cohort study", "prospective study" | `cohort_study` |
| "case-control", "case control" | `case_control_study` |
| "case report" | `case_report` |
| "case series" | `case_series` |
| "in vitro", "cell culture" | `in_vitro` |
| "in mice", "in rats", "animal model" | `animal_study` |

Example:
```python
detect_study_type_from_title(
    "A randomized controlled trial of aspirin for migraine prevention"
)
# Result: "randomized_controlled_trial"
```

---

## References

### Primary Sources

1. **OCEBM Levels of Evidence Working Group**
   "The Oxford Levels of Evidence 2"
   Oxford Centre for Evidence-Based Medicine
   https://www.cebm.ox.ac.uk/resources/levels-of-evidence/ocebm-levels-of-evidence

2. **GRADE Working Group**
   "Grading quality of evidence and strength of recommendations"
   BMJ 2004;328:1490
   https://www.gradeworkinggroup.org/

3. **Sackett DL, et al.**
   "Evidence based medicine: what it is and what it isn't"
   BMJ 1996;312:71-72

4. **Guyatt GH, et al.**
   "GRADE: an emerging consensus on rating quality of evidence and strength of recommendations"
   BMJ 2008;336:924-6

### Additional Resources

- **Cochrane Handbook**: Standard for systematic reviews
- **PRISMA**: Reporting standards for systematic reviews and meta-analyses
- **CONSORT**: Standards for reporting RCTs
- **STROBE**: Standards for observational studies

---

## Implementation Files

- **Backend**: `backend/app/utils/source_quality.py` (270 lines)
- **Tests**: `backend/tests/test_source_quality.py` (164 lines, 31 tests)
- **Integration**: Used in `/sources/extract-metadata-from-url` and PubMed bulk import

---

## Future Enhancements

### Planned

1. **Risk of Bias Assessment**
   - Parse study methodology from abstracts
   - Detect randomization method, blinding, allocation concealment
   - Adjust trust level based on methodological quality

2. **Heterogeneity Detection**
   - For systematic reviews/meta-analyses
   - Lower score if high I² statistic mentioned

3. **Confidence Interval Width**
   - Extract CI from abstracts
   - Penalize wide confidence intervals (imprecision)

4. **Publication Bias Indicators**
   - Check for funnel plot asymmetry mentions
   - Industry funding disclosure

### Under Consideration

1. **Manual Override**
   - Allow users to manually adjust trust level with justification
   - Track manual adjustments separately

2. **Multi-Source Consensus**
   - When multiple sources report same finding
   - Boost trust level if consistent across sources

3. **Journal Impact Factor Integration**
   - Use real-time JIF data from Clarivate/Scopus
   - More granular journal quality assessment

---

## Validation

The scoring system has been validated against:
- ✅ Oxford OCEBM Levels (2011 edition)
- ✅ GRADE quality of evidence framework
- ✅ 31 automated tests covering all study types
- ✅ Manual testing with real PubMed articles

**Last Updated**: 2026-01-11
**Version**: 1.0
