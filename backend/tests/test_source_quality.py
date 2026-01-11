"""
Tests for source quality scoring system.

Validates trust level calculation based on evidence hierarchy.
"""
import pytest
from app.utils.source_quality import (
    calculate_trust_level,
    infer_trust_level_from_pubmed_metadata,
    detect_study_type_from_title,
    pubmed_default_trust_level,
    website_trust_level,
    preprint_trust_level,
    book_trust_level,
)


class TestCalculateTrustLevel:
    """Test trust level calculation with various parameters."""

    def test_systematic_review_nejm(self):
        """Systematic review in NEJM should get maximum score."""
        score = calculate_trust_level(
            study_type="systematic_review",
            journal="New England Journal of Medicine"
        )
        assert score == 1.0

    def test_meta_analysis_lancet(self):
        """Meta-analysis in Lancet should get near-maximum score."""
        score = calculate_trust_level(
            study_type="meta_analysis",
            journal="The Lancet"
        )
        assert score == 0.95

    def test_rct_high_impact_journal(self):
        """RCT in high-impact journal."""
        score = calculate_trust_level(
            study_type="randomized_controlled_trial",
            journal="JAMA"
        )
        assert score == 0.9

    def test_rct_with_large_sample(self):
        """RCT with large sample size gets bonus."""
        score = calculate_trust_level(
            study_type="randomized_controlled_trial",
            journal="BMJ",
            sample_size=10000
        )
        assert score > 0.9  # Base 0.9 + sample bonus

    def test_cohort_study_standard_journal(self):
        """Cohort study in standard journal."""
        score = calculate_trust_level(
            study_type="cohort_study",
            journal="Journal of Internal Medicine",
            is_peer_reviewed=True
        )
        assert score == 0.75

    def test_case_control_study(self):
        """Case-control study."""
        score = calculate_trust_level(
            study_type="case_control_study"
        )
        assert score == 0.65

    def test_case_report(self):
        """Case report has low trust."""
        score = calculate_trust_level(
            study_type="case_report"
        )
        assert score == 0.4

    def test_expert_opinion(self):
        """Expert opinion has lowest trust."""
        score = calculate_trust_level(
            study_type="expert_opinion"
        )
        assert score == 0.3

    def test_preprint_penalty(self):
        """Preprints get penalty modifier."""
        score = calculate_trust_level(
            study_type="randomized_controlled_trial",
            is_peer_reviewed=False  # Preprint
        )
        assert score == 0.9 * 0.85  # 0.765

    def test_old_study_penalty(self):
        """Very old studies get slight penalty."""
        score = calculate_trust_level(
            study_type="randomized_controlled_trial",
            publication_year=1990  # 36 years old
        )
        assert score < 0.9  # Should have age penalty

    def test_recent_study_no_penalty(self):
        """Recent studies have no age penalty."""
        score = calculate_trust_level(
            study_type="randomized_controlled_trial",
            publication_year=2024
        )
        assert score == 0.9  # No penalty

    def test_unknown_defaults_to_neutral(self):
        """Unknown study type defaults to neutral 0.5."""
        score = calculate_trust_level(
            study_type="unknown"
        )
        assert score == 0.5


class TestDetectStudyTypeFromTitle:
    """Test study type detection from article titles."""

    def test_detect_systematic_review(self):
        """Detect systematic review from title."""
        title = "Systematic review and meta-analysis of aspirin for migraine"
        result = detect_study_type_from_title(title)
        assert result == "systematic_review"

    def test_detect_meta_analysis(self):
        """Detect meta-analysis from title."""
        title = "Meta-analysis of duloxetine efficacy in fibromyalgia"
        result = detect_study_type_from_title(title)
        assert result == "meta_analysis"

    def test_detect_rct(self):
        """Detect RCT from title."""
        title = "A randomized controlled trial of ibuprofen vs placebo"
        result = detect_study_type_from_title(title)
        assert result == "randomized_controlled_trial"

    def test_detect_rct_abbreviated(self):
        """Detect RCT from abbreviation."""
        title = "An RCT comparing two treatments"
        result = detect_study_type_from_title(title)
        assert result == "randomized_controlled_trial"

    def test_detect_cohort_study(self):
        """Detect cohort study."""
        title = "A prospective cohort study of cardiovascular risk"
        result = detect_study_type_from_title(title)
        assert result == "cohort_study"

    def test_detect_case_control(self):
        """Detect case-control study."""
        title = "A case-control study of lung cancer and smoking"
        result = detect_study_type_from_title(title)
        assert result == "case_control_study"

    def test_detect_case_report(self):
        """Detect case report."""
        title = "Case report: Rare adverse reaction to penicillin"
        result = detect_study_type_from_title(title)
        assert result == "case_report"

    def test_detect_animal_study(self):
        """Detect animal study."""
        title = "Effect of drug X in mice with diabetes"
        result = detect_study_type_from_title(title)
        assert result == "animal_study"

    def test_detect_in_vitro(self):
        """Detect in vitro study."""
        title = "In vitro effects of compound Y on cell proliferation"
        result = detect_study_type_from_title(title)
        assert result == "in_vitro"

    def test_unknown_when_no_keywords(self):
        """Unknown when no study type keywords present."""
        title = "The effects of exercise on health"
        result = detect_study_type_from_title(title)
        assert result == "unknown"


class TestInferTrustLevelFromPubMed:
    """Test trust level inference for PubMed articles."""

    def test_rct_in_nejm(self):
        """RCT in NEJM gets high score."""
        score = infer_trust_level_from_pubmed_metadata(
            title="A randomized controlled trial of aspirin for migraine prevention",
            journal="New England Journal of Medicine",
            year=2024
        )
        assert score == 0.9

    def test_systematic_review_cochrane(self):
        """Systematic review in Cochrane gets maximum score."""
        score = infer_trust_level_from_pubmed_metadata(
            title="Systematic review of antidepressants for chronic pain",
            journal="Cochrane Database of Systematic Reviews",
            year=2023
        )
        assert score == 1.0

    def test_case_report_low_score(self):
        """Case report gets low score."""
        score = infer_trust_level_from_pubmed_metadata(
            title="Case report: Unusual side effect of drug X",
            journal="Journal of Medical Case Reports",
            year=2024
        )
        assert score == 0.4

    def test_title_detection_with_abstract(self):
        """Use abstract when title unclear."""
        score = infer_trust_level_from_pubmed_metadata(
            title="Drug X for condition Y",  # Unclear
            journal="JAMA",
            year=2024,
            abstract="We performed a randomized controlled trial comparing drug X to placebo..."
        )
        assert score == 0.9  # Should detect RCT from abstract

    def test_cochrane_automatic_systematic_review(self):
        """Cochrane Database articles always treated as systematic reviews."""
        score = infer_trust_level_from_pubmed_metadata(
            title="Antidepressants for pain management",  # No 'systematic review' in title
            journal="Cochrane Database of Systematic Reviews",
            year=2023
        )
        assert score == 1.0  # Should be maximum score

    def test_cochrane_abbreviated_journal(self):
        """Cochrane Database Syst Rev (PubMed abbreviation) recognized."""
        score = infer_trust_level_from_pubmed_metadata(
            title="Duloxetine for painful neuropathy",
            journal="Cochrane Database Syst Rev",
            year=2015
        )
        assert score == 1.0

    def test_cochrane_with_systematic_review_in_title(self):
        """Cochrane with explicit 'systematic review' in title."""
        score = infer_trust_level_from_pubmed_metadata(
            title="Systematic review of NSAIDs for osteoarthritis",
            journal="Cochrane Database of Systematic Reviews",
            year=2024
        )
        assert score == 1.0

    def test_old_study_gets_penalty(self):
        """Very old study gets age penalty."""
        score = infer_trust_level_from_pubmed_metadata(
            title="A randomized controlled trial of aspirin",
            journal="NEJM",
            year=1985  # 41 years old
        )
        assert score < 0.9  # Should have age penalty


class TestConvenienceFunctions:
    """Test convenience functions for common source types."""

    def test_pubmed_default_trust_level(self):
        """PubMed default trust level."""
        score = pubmed_default_trust_level()
        assert 0.7 <= score <= 0.8  # Should be cohort study level

    def test_pubmed_with_high_impact_journal(self):
        """PubMed with high-impact journal."""
        score = pubmed_default_trust_level(journal="Nature", year=2024)
        assert score == 0.75  # Cohort study in high-impact journal

    def test_website_trust_level(self):
        """Website trust level is low."""
        score = website_trust_level()
        assert score == 0.3  # Expert opinion level

    def test_preprint_trust_level(self):
        """Preprint trust level."""
        score = preprint_trust_level()
        assert score < 0.5  # Lower than neutral

    def test_book_peer_reviewed(self):
        """Peer-reviewed book."""
        score = book_trust_level(is_peer_reviewed=True)
        assert score == 0.75

    def test_book_not_peer_reviewed(self):
        """Non-peer-reviewed book."""
        score = book_trust_level(is_peer_reviewed=False)
        assert score < 0.75


class TestBoundaryConditions:
    """Test edge cases and boundary conditions."""

    def test_score_never_below_zero(self):
        """Score should never go below 0.0."""
        score = calculate_trust_level(
            study_type="case_report",
            is_peer_reviewed=False,
            publication_year=1900  # Very old
        )
        assert score >= 0.0

    def test_score_never_above_one(self):
        """Score should never go above 1.0."""
        score = calculate_trust_level(
            study_type="systematic_review",
            journal="Nature",
            sample_size=100000,  # Huge sample
            publication_year=2024
        )
        assert score <= 1.0

    def test_handles_none_values(self):
        """Should handle None values gracefully."""
        score = calculate_trust_level(
            study_type=None,
            journal=None,
            is_peer_reviewed=None,
            sample_size=None,
            publication_year=None
        )
        assert score == 0.5  # Default to neutral

    def test_negative_sample_size_ignored(self):
        """Negative sample size should be ignored."""
        score = calculate_trust_level(
            study_type="randomized_controlled_trial",
            sample_size=-100
        )
        assert score == 0.9  # No sample bonus, no penalty

    def test_future_year_handled(self):
        """Future publication year handled gracefully."""
        score = calculate_trust_level(
            study_type="randomized_controlled_trial",
            publication_year=2030
        )
        assert score == 0.9  # No penalty for future years
