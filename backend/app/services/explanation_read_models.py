from typing import Iterable, Optional

from app.schemas.explanation import ContradictionDetail, SourceContribution
from app.services.inference.evidence_views import RoleEvidenceRead


def build_contradiction_detail(
    role_evidence: Iterable[RoleEvidenceRead],
    disagreement: float,
) -> Optional[ContradictionDetail]:
    if disagreement < 0.1:
        return None

    supporting_sources = []
    contradicting_sources = []

    for evidence in role_evidence:
        if evidence.contribution_direction == "supports":
            supporting_sources.append(evidence)
        elif evidence.contribution_direction == "contradicts":
            contradicting_sources.append(evidence)

    return ContradictionDetail(
        supporting_sources=[],
        contradicting_sources=[],
        disagreement_score=disagreement,
    )


def attach_contradiction_sources(
    contradiction_detail: Optional[ContradictionDetail],
    source_chain: list[SourceContribution],
) -> Optional[ContradictionDetail]:
    if contradiction_detail is None:
        return None

    supporting_sources = []
    contradicting_sources = []
    for source in source_chain:
        if source.relation_direction == "supports":
            supporting_sources.append(source)
        elif source.relation_direction == "contradicts":
            contradicting_sources.append(source)

    contradiction_detail.supporting_sources = supporting_sources
    contradiction_detail.contradicting_sources = contradicting_sources
    return contradiction_detail
