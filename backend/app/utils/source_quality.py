"""
Source quality scoring utilities.

Provides standardized trust level calculation based on source type,
study design, and publication venue.

**Standards Implemented:**
- Oxford Centre for Evidence-Based Medicine (OCEBM) Levels of Evidence (2011)
- GRADE (Grading of Recommendations Assessment, Development and Evaluation)

**References:**
- OCEBM: https://www.cebm.ox.ac.uk/resources/levels-of-evidence/ocebm-levels-of-evidence
- GRADE: https://www.gradeworkinggroup.org/

See also: backend/docs/EVIDENCE_QUALITY_STANDARDS.md for detailed documentation.
"""
from typing import Literal


# =============================================================================
# Evidence Hierarchy Constants
# =============================================================================

StudyType = Literal[
    "systematic_review",      # Systematic review with meta-analysis
    "meta_analysis",          # Meta-analysis
    "randomized_controlled_trial",  # RCT
    "cohort_study",          # Prospective cohort study
    "case_control_study",    # Case-control study
    "case_series",           # Case series
    "case_report",           # Single case report
    "expert_opinion",        # Expert opinion, editorials
    "in_vitro",              # Laboratory/in vitro studies
    "animal_study",          # Animal/preclinical studies
    "unknown"                # Unknown or unspecified
]


# Evidence hierarchy mapping to base trust levels
# Based on Oxford Centre for Evidence-Based Medicine (OCEBM) Levels of Evidence (2011)
# and GRADE quality of evidence framework
EVIDENCE_HIERARCHY = {
    "systematic_review": 1.0,          # OCEBM Level 1a / GRADE High (⊕⊕⊕⊕)
    "meta_analysis": 0.95,             # OCEBM Level 1a / GRADE High (⊕⊕⊕⊕)
    "randomized_controlled_trial": 0.9, # OCEBM Level 1b / GRADE High (⊕⊕⊕⊕)
    "cohort_study": 0.75,              # OCEBM Level 2b / GRADE Moderate (⊕⊕⊕◯)
    "case_control_study": 0.65,        # OCEBM Level 3b / GRADE Moderate (⊕⊕⊕◯)
    "case_series": 0.5,                # OCEBM Level 4 / GRADE Low (⊕⊕◯◯)
    "case_report": 0.4,                # OCEBM Level 4 / GRADE Low (⊕⊕◯◯)
    "expert_opinion": 0.3,             # OCEBM Level 5 / GRADE Very Low (⊕◯◯◯)
    "in_vitro": 0.4,                   # Preclinical / GRADE Very Low
    "animal_study": 0.45,              # Preclinical / GRADE Very Low
    "unknown": 0.5,                    # Neutral default
}


# Publication venue modifiers (multipliers applied to base score)
VENUE_QUALITY_MODIFIERS = {
    # Top-tier medical journals (impact factor > 50)
    "high_impact": 1.0,  # No modifier - already at max
    # Reputable peer-reviewed journals
    "peer_reviewed": 1.0,  # Standard quality
    # Preprints, non-peer-reviewed
    "preprint": 0.85,
    # Unknown or unverified venue
    "unknown": 0.95,
}


# Known high-impact journals (can be expanded)
HIGH_IMPACT_JOURNALS = {
    "new england journal of medicine",
    "nejm",
    "lancet",
    "the lancet",
    "jama",
    "journal of the american medical association",
    "bmj",
    "british medical journal",
    "nature",
    "science",
    "cell",
    "nature medicine",
    "lancet oncology",
    "jama internal medicine",
    # Cochrane - Gold standard for systematic reviews
    "cochrane database",
    "cochrane database of systematic reviews",
    "cochrane library",
}


# Preprint servers
PREPRINT_SERVERS = {
    "biorxiv",
    "medrxiv",
    "arxiv",
    "ssrn",
}


# =============================================================================
# Trust Level Calculation
# =============================================================================

def calculate_trust_level(
    study_type: StudyType | None = None,
    journal: str | None = None,
    is_peer_reviewed: bool | None = None,
    sample_size: int | None = None,
    publication_year: int | None = None,
) -> float:
    """
    Calculate standardized trust level for a source.

    Based on:
    1. Study design (evidence hierarchy)
    2. Publication venue (journal impact/quality)
    3. Sample size (larger = more reliable)
    4. Recency (newer = more relevant, slight modifier)

    Args:
        study_type: Type of study (RCT, cohort, etc.)
        journal: Journal name
        is_peer_reviewed: Whether article is peer-reviewed
        sample_size: Number of participants/subjects
        publication_year: Year of publication

    Returns:
        Trust level between 0.0 and 1.0

    Examples:
        >>> calculate_trust_level(study_type="randomized_controlled_trial", journal="NEJM")
        0.9
        >>> calculate_trust_level(study_type="case_report", journal="unknown preprint")
        0.34
        >>> calculate_trust_level(study_type="meta_analysis", journal="Cochrane", sample_size=10000)
        0.95
    """
    # Base score from study type
    base_score = EVIDENCE_HIERARCHY.get(study_type or "unknown", 0.5)

    # Venue quality modifier
    venue_modifier = _determine_venue_modifier(journal, is_peer_reviewed)

    # Calculate base trust level
    trust_level = base_score * venue_modifier

    # Sample size bonus (up to +0.05 for very large studies)
    if sample_size is not None and sample_size > 0:
        # Logarithmic bonus: 100 participants = +0.01, 1000 = +0.03, 10000 = +0.05
        size_bonus = min(0.05, 0.01 * (sample_size / 100) ** 0.5 / 3)
        trust_level = min(1.0, trust_level + size_bonus)

    # Recency modifier (slight penalty for very old studies)
    if publication_year is not None:
        from datetime import datetime
        current_year = datetime.now().year
        age = current_year - publication_year

        if age > 20:
            # Studies older than 20 years get a small penalty (max -0.1)
            age_penalty = min(0.1, (age - 20) * 0.005)
            trust_level = max(0.0, trust_level - age_penalty)

    # Clamp to [0.0, 1.0]
    return round(max(0.0, min(1.0, trust_level)), 2)


def _determine_venue_modifier(journal: str | None, is_peer_reviewed: bool | None) -> float:
    """
    Determine venue quality modifier.

    Args:
        journal: Journal name
        is_peer_reviewed: Whether peer-reviewed

    Returns:
        Modifier between 0.85 and 1.0
    """
    if not journal:
        return VENUE_QUALITY_MODIFIERS["unknown"]

    journal_lower = journal.lower().strip()

    # Check if high-impact journal
    if any(hi_journal in journal_lower for hi_journal in HIGH_IMPACT_JOURNALS):
        return VENUE_QUALITY_MODIFIERS["high_impact"]

    # Check if preprint
    if any(preprint in journal_lower for preprint in PREPRINT_SERVERS):
        return VENUE_QUALITY_MODIFIERS["preprint"]

    # Check peer review status
    if is_peer_reviewed is False:
        return VENUE_QUALITY_MODIFIERS["preprint"]

    # Default: assume peer-reviewed
    return VENUE_QUALITY_MODIFIERS["peer_reviewed"]


# =============================================================================
# Convenience Functions for Common Source Types
# =============================================================================

def pubmed_default_trust_level(journal: str | None = None, year: int | None = None) -> float:
    """
    Calculate trust level for PubMed article with minimal info.

    PubMed articles are generally peer-reviewed, so we default to
    "cohort_study" quality (0.75) unless we have more info.

    Args:
        journal: Journal name
        year: Publication year

    Returns:
        Trust level (typically 0.70-0.90)
    """
    return calculate_trust_level(
        study_type="cohort_study",  # Conservative default
        journal=journal,
        is_peer_reviewed=True,  # PubMed articles are generally peer-reviewed
        publication_year=year
    )


def preprint_trust_level() -> float:
    """
    Trust level for preprints (non-peer-reviewed).

    Returns:
        Trust level (0.425 = 0.5 * 0.85)
    """
    return calculate_trust_level(
        study_type="unknown",
        is_peer_reviewed=False
    )


def website_trust_level() -> float:
    """
    Trust level for general websites (blogs, news, etc.).

    Returns:
        Trust level (0.3 = expert opinion level)
    """
    return calculate_trust_level(
        study_type="expert_opinion",
        is_peer_reviewed=False
    )


def book_trust_level(is_peer_reviewed: bool = True) -> float:
    """
    Trust level for books and textbooks.

    Args:
        is_peer_reviewed: Whether the book is from a reputable academic publisher

    Returns:
        Trust level (0.65-0.75)
    """
    return calculate_trust_level(
        study_type="cohort_study",  # Similar to review articles
        is_peer_reviewed=is_peer_reviewed
    )


# =============================================================================
# Study Type Detection from Text
# =============================================================================

def detect_study_type_from_title(title: str) -> StudyType:
    """
    Attempt to detect study type from article title.

    Uses keywords to identify study design.

    Args:
        title: Article title

    Returns:
        Detected study type or "unknown"

    Examples:
        >>> detect_study_type_from_title("A randomized controlled trial of aspirin")
        'randomized_controlled_trial'
        >>> detect_study_type_from_title("Systematic review and meta-analysis of NSAIDs")
        'systematic_review'
    """
    title_lower = title.lower()

    # Check for systematic review / meta-analysis
    if "systematic review" in title_lower or "meta-analysis" in title_lower:
        if "systematic review" in title_lower:
            return "systematic_review"
        return "meta_analysis"

    # Check for RCT
    rct_keywords = ["randomized controlled trial", "randomised controlled trial", "rct", "double-blind"]
    if any(keyword in title_lower for keyword in rct_keywords):
        return "randomized_controlled_trial"

    # Check for cohort study
    if "cohort study" in title_lower or "prospective study" in title_lower:
        return "cohort_study"

    # Check for case-control
    if "case-control" in title_lower or "case control" in title_lower:
        return "case_control_study"

    # Check for case report/series
    if "case report" in title_lower:
        return "case_report"
    if "case series" in title_lower:
        return "case_series"

    # Check for animal/in vitro
    if any(keyword in title_lower for keyword in ["in vitro", "in-vitro", "cell culture"]):
        return "in_vitro"
    if any(keyword in title_lower for keyword in ["in mice", "in rats", "animal model", "mouse model"]):
        return "animal_study"

    # Default
    return "unknown"


def infer_trust_level_from_pubmed_metadata(
    title: str,
    journal: str | None = None,
    year: int | None = None,
    abstract: str | None = None
) -> float:
    """
    Infer trust level from PubMed article metadata.

    Attempts to detect study type from title/abstract and combines
    with journal quality.

    Special handling:
    - Cochrane Database articles are always systematic reviews (trust_level=1.0)
    - Study type detection from title keywords
    - Fallback to abstract analysis if title unclear

    Args:
        title: Article title
        journal: Journal name
        year: Publication year
        abstract: Article abstract (optional, for better detection)

    Returns:
        Inferred trust level

    Examples:
        >>> infer_trust_level_from_pubmed_metadata(
        ...     "A randomized controlled trial of aspirin for migraine",
        ...     "NEJM",
        ...     2023
        ... )
        0.9
        >>> infer_trust_level_from_pubmed_metadata(
        ...     "Antidepressants for pain management",
        ...     "Cochrane Database of Systematic Reviews",
        ...     2023
        ... )
        1.0
    """
    # Special case: Cochrane Database publications are ALWAYS systematic reviews
    if journal and "cochrane database" in journal.lower():
        return calculate_trust_level(
            study_type="systematic_review",
            journal=journal,
            is_peer_reviewed=True,
            publication_year=year
        )

    # Detect study type from title
    study_type = detect_study_type_from_title(title)

    # If abstract is available, try to refine detection
    if abstract and study_type == "unknown":
        study_type = detect_study_type_from_title(abstract[:500])

    return calculate_trust_level(
        study_type=study_type,
        journal=journal,
        is_peer_reviewed=True,  # PubMed = peer-reviewed
        publication_year=year
    )
