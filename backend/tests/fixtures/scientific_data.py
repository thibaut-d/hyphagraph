"""
Scientific Test Data Fixtures for Fibromyalgia and Chronic Pain Research.

This module provides scientifically accurate test data based on widely accepted
medical knowledge about fibromyalgia and chronic widespread pain. All entities,
relations, and sources reflect real medical literature and clinical practice.

Design Principles:
- Use only well-established, non-controversial medical knowledge
- Maintain scientific accuracy while serving test requirements
- Avoid duplication by providing a comprehensive catalog
- Reference actual clinical guidelines and FDA approvals
"""
from typing import Dict, List


# ============================================================================
# ENTITIES: Scientifically Accurate Medical Entities
# ============================================================================

class ScientificEntities:
    """Catalog of scientifically accurate entities for testing."""

    # Primary Conditions (3)
    FIBROMYALGIA = {
        "slug": "fibromyalgia",
        "summary": {"en": "Chronic disorder characterized by widespread musculoskeletal pain, fatigue, and tenderness"},
    }

    CHRONIC_WIDESPREAD_PAIN = {
        "slug": "chronic-widespread-pain",
        "summary": {"en": "Pain affecting multiple body regions persisting for at least 3 months"},
    }

    CHRONIC_FATIGUE_SYNDROME = {
        "slug": "chronic-fatigue-syndrome",
        "summary": {"en": "Complex disorder with extreme fatigue lasting more than 6 months"},
    }

    # Symptoms/Manifestations (10)
    WIDESPREAD_MUSCULOSKELETAL_PAIN = {
        "slug": "widespread-musculoskeletal-pain",
        "summary": {"en": "Pain affecting muscles and bones across multiple body regions"},
    }

    FATIGUE = {
        "slug": "fatigue",
        "summary": {"en": "Persistent tiredness and lack of energy not relieved by rest"},
    }

    SLEEP_DISTURBANCE = {
        "slug": "sleep-disturbance",
        "summary": {"en": "Difficulty falling asleep, staying asleep, or non-restorative sleep"},
    }

    COGNITIVE_DYSFUNCTION = {
        "slug": "cognitive-dysfunction",
        "summary": {"en": "Impaired memory, concentration, and mental clarity (fibro fog)"},
    }

    MORNING_STIFFNESS = {
        "slug": "morning-stiffness",
        "summary": {"en": "Joint and muscle stiffness upon waking"},
    }

    HEADACHE = {
        "slug": "headache",
        "summary": {"en": "Recurrent head pain of varying intensity and location"},
    }

    PARESTHESIA = {
        "slug": "paresthesia",
        "summary": {"en": "Abnormal sensations such as tingling, numbness, or pins and needles"},
    }

    ALLODYNIA = {
        "slug": "allodynia",
        "summary": {"en": "Pain caused by stimuli that normally do not provoke pain"},
    }

    HYPERALGESIA = {
        "slug": "hyperalgesia",
        "summary": {"en": "Increased sensitivity to pain stimuli"},
    }

    ANXIETY = {
        "slug": "anxiety",
        "summary": {"en": "Excessive worry, nervousness, or fear affecting daily functioning"},
    }

    # FDA-Approved Medications (3)
    PREGABALIN = {
        "slug": "pregabalin",
        "summary": {"en": "FDA-approved anticonvulsant for fibromyalgia (2007), first-line treatment"},
    }

    DULOXETINE = {
        "slug": "duloxetine",
        "summary": {"en": "FDA-approved SNRI antidepressant for fibromyalgia"},
    }

    MILNACIPRAN = {
        "slug": "milnacipran",
        "summary": {"en": "FDA-approved SNRI specifically for fibromyalgia management"},
    }

    # Commonly Prescribed Medications (6)
    AMITRIPTYLINE = {
        "slug": "amitriptyline",
        "summary": {"en": "Tricyclic antidepressant commonly prescribed off-label for fibromyalgia"},
    }

    GABAPENTIN = {
        "slug": "gabapentin",
        "summary": {"en": "Anticonvulsant similar to pregabalin, used off-label"},
    }

    CYCLOBENZAPRINE = {
        "slug": "cyclobenzaprine",
        "summary": {"en": "Muscle relaxant used off-label for fibromyalgia symptoms"},
    }

    TRAMADOL = {
        "slug": "tramadol",
        "summary": {"en": "Opioid analgesic used cautiously for pain management"},
    }

    LOW_DOSE_NALTREXONE = {
        "slug": "low-dose-naltrexone",
        "summary": {"en": "Emerging treatment modulating immune system and pain response"},
    }

    ACETAMINOPHEN = {
        "slug": "acetaminophen",
        "summary": {"en": "Over-the-counter analgesic for mild pain relief"},
    }

    # Non-Pharmacological Interventions (8)
    AEROBIC_EXERCISE = {
        "slug": "aerobic-exercise",
        "summary": {"en": "Evidence-based first-line treatment involving cardiovascular exercise"},
    }

    RESISTANCE_TRAINING = {
        "slug": "resistance-training",
        "summary": {"en": "Strength-building exercises using weights or resistance"},
    }

    AQUATIC_THERAPY = {
        "slug": "aquatic-therapy",
        "summary": {"en": "Low-impact exercise performed in water"},
    }

    COGNITIVE_BEHAVIORAL_THERAPY = {
        "slug": "cognitive-behavioral-therapy",
        "summary": {"en": "Psychological intervention addressing pain perception and coping"},
    }

    MINDFULNESS_MEDITATION = {
        "slug": "mindfulness-meditation",
        "summary": {"en": "Mind-body technique focusing on present-moment awareness"},
    }

    SLEEP_HYGIENE = {
        "slug": "sleep-hygiene",
        "summary": {"en": "Practices to improve sleep quality and duration"},
    }

    TAI_CHI = {
        "slug": "tai-chi",
        "summary": {"en": "Mind-body exercise combining gentle movements with meditation"},
    }

    YOGA = {
        "slug": "yoga",
        "summary": {"en": "Mind-body practice combining postures, breathing, and meditation"},
    }

    # Pathophysiological Mechanisms (5)
    CENTRAL_SENSITIZATION = {
        "slug": "central-sensitization",
        "summary": {"en": "Amplified pain processing in the central nervous system"},
    }

    ALTERED_PAIN_PROCESSING = {
        "slug": "altered-pain-processing",
        "summary": {"en": "Abnormal neurological processing of pain signals"},
    }

    NEUROTRANSMITTER_IMBALANCE = {
        "slug": "neurotransmitter-imbalance",
        "summary": {"en": "Dysregulation of serotonin, norepinephrine, and other neurotransmitters"},
    }

    SMALL_FIBER_NEUROPATHY = {
        "slug": "small-fiber-neuropathy",
        "summary": {"en": "Damage to small nerve fibers observed in subset of fibromyalgia patients"},
    }

    HPA_AXIS_DYSFUNCTION = {
        "slug": "hpa-axis-dysfunction",
        "summary": {"en": "Abnormal hypothalamic-pituitary-adrenal stress response"},
    }

    # Patient Populations (4)
    ADULT_FEMALES = {
        "slug": "adult-females",
        "summary": {"en": "Women aged 18-65, most commonly affected demographic"},
    }

    ADULT_MALES = {
        "slug": "adult-males",
        "summary": {"en": "Men aged 18-65, less commonly affected but significant population"},
    }

    ELDERLY_POPULATION = {
        "slug": "elderly-population",
        "summary": {"en": "Adults over 65 with age-specific considerations"},
    }

    ADOLESCENTS = {
        "slug": "adolescents",
        "summary": {"en": "Teenagers with juvenile fibromyalgia syndrome"},
    }

    # Biomarkers/Diagnostic (3)
    TENDER_POINTS = {
        "slug": "tender-points",
        "summary": {"en": "Historical diagnostic criterion involving 18 specific body locations"},
    }

    WIDESPREAD_PAIN_INDEX = {
        "slug": "widespread-pain-index",
        "summary": {"en": "Current diagnostic tool measuring pain location count (0-19)"},
    }

    SYMPTOM_SEVERITY_SCALE = {
        "slug": "symptom-severity-scale",
        "summary": {"en": "Diagnostic scoring system for symptom intensity (0-12)"},
    }

    # Comorbidities (5)
    IRRITABLE_BOWEL_SYNDROME = {
        "slug": "irritable-bowel-syndrome",
        "summary": {"en": "Gastrointestinal disorder frequently comorbid with fibromyalgia"},
    }

    TEMPOROMANDIBULAR_DISORDER = {
        "slug": "temporomandibular-disorder",
        "summary": {"en": "Jaw joint and muscle disorder (TMJ)"},
    }

    MIGRAINE = {
        "slug": "migraine",
        "summary": {"en": "Severe recurrent headache disorder often comorbid with fibromyalgia"},
    }

    DEPRESSION = {
        "slug": "depression",
        "summary": {"en": "Mood disorder frequently comorbid with chronic pain conditions"},
    }

    RHEUMATOID_ARTHRITIS = {
        "slug": "rheumatoid-arthritis",
        "summary": {"en": "Autoimmune arthritis that can coexist with fibromyalgia"},
    }

    @classmethod
    def get_all(cls) -> List[Dict]:
        """Return all entities as a list of dictionaries."""
        return [
            getattr(cls, attr) for attr in dir(cls)
            if not attr.startswith('_') and isinstance(getattr(cls, attr), dict)
        ]

    @classmethod
    def get_by_slug(cls, slug: str) -> Dict:
        """Get entity by slug."""
        for entity in cls.get_all():
            if entity["slug"] == slug:
                return entity
        raise ValueError(f"Entity with slug '{slug}' not found")


# ============================================================================
# SOURCES: Scientific Studies and Clinical Guidelines
# ============================================================================

class ScientificSources:
    """Catalog of scientifically accurate sources for testing."""

    ACR_2010_DIAGNOSTIC = {
        "kind": "guideline",
        "title": "ACR 2010 Fibromyalgia Diagnostic Criteria",
        "url": "https://doi.org/10.1002/art.27339",
        "year": 2010,
        "origin": "pubmed",
        "trust_level": 0.95,
    }

    ACR_2016_REVISED = {
        "kind": "guideline",
        "title": "ACR 2016 Revised Fibromyalgia Diagnostic Criteria",
        "url": "https://doi.org/10.1016/j.semarthrit.2016.08.012",
        "year": 2016,
        "origin": "pubmed",
        "trust_level": 0.95,
    }

    EULAR_2017_GUIDELINES = {
        "kind": "guideline",
        "title": "EULAR 2017 Fibromyalgia Management Guidelines",
        "url": "https://doi.org/10.1136/annrheumdis-2016-209724",
        "year": 2017,
        "origin": "pubmed",
        "trust_level": 0.95,
    }

    PREGABALIN_FDA_APPROVAL = {
        "kind": "study",
        "title": "Pregabalin FDA Approval Study for Fibromyalgia",
        "url": "https://doi.org/10.1002/art.23968",
        "year": 2007,
        "origin": "pubmed",
        "trust_level": 0.90,
    }

    DULOXETINE_FDA_APPROVAL = {
        "kind": "study",
        "title": "Duloxetine FDA Approval Study for Fibromyalgia",
        "url": "https://doi.org/10.1002/art.23889",
        "year": 2008,
        "origin": "pubmed",
        "trust_level": 0.90,
    }

    MILNACIPRAN_FDA_APPROVAL = {
        "kind": "study",
        "title": "Milnacipran FDA Approval Study for Fibromyalgia",
        "url": "https://doi.org/10.1016/j.jpain.2008.09.013",
        "year": 2009,
        "origin": "pubmed",
        "trust_level": 0.90,
    }

    COCHRANE_EXERCISE_REVIEW = {
        "kind": "systematic_review",
        "title": "Cochrane Review: Exercise for Fibromyalgia",
        "url": "https://doi.org/10.1002/14651858.CD003786.pub3",
        "year": 2017,
        "origin": "pubmed",
        "trust_level": 0.95,
    }

    COCHRANE_AMITRIPTYLINE_REVIEW = {
        "kind": "systematic_review",
        "title": "Cochrane Review: Amitriptyline for Fibromyalgia",
        "url": "https://doi.org/10.1002/14651858.CD011824.pub2",
        "year": 2015,
        "origin": "pubmed",
        "trust_level": 0.95,
    }

    NIH_CHRONIC_PAIN_RESEARCH = {
        "kind": "guideline",
        "title": "NIH Chronic Pain Research Initiative",
        "url": "https://heal.nih.gov/research/clinical-research/chronic-pain",
        "year": 2018,
        "origin": "nih",
        "trust_level": 0.90,
    }

    CDC_CHRONIC_PAIN_GUIDELINES = {
        "kind": "guideline",
        "title": "CDC Guideline for Prescribing Opioids for Chronic Pain",
        "url": "https://doi.org/10.15585/mmwr.rr6501e1",
        "year": 2016,
        "origin": "cdc",
        "trust_level": 0.90,
    }

    CENTRAL_SENSITIZATION_STUDY = {
        "kind": "study",
        "title": "Central Sensitization in Fibromyalgia Patients",
        "url": "https://doi.org/10.1016/j.pain.2005.08.036",
        "year": 2006,
        "origin": "pubmed",
        "trust_level": 0.85,
    }

    CBT_FIBROMYALGIA_RCT = {
        "kind": "study",
        "title": "Cognitive Behavioral Therapy for Fibromyalgia RCT",
        "url": "https://doi.org/10.1002/art.27481",
        "year": 2010,
        "origin": "pubmed",
        "trust_level": 0.85,
    }

    @classmethod
    def get_all(cls) -> List[Dict]:
        """Return all sources as a list of dictionaries."""
        return [
            getattr(cls, attr) for attr in dir(cls)
            if not attr.startswith('_') and isinstance(getattr(cls, attr), dict)
        ]


# ============================================================================
# RELATION TEMPLATES: Common Relationship Patterns
# ============================================================================

class RelationTemplates:
    """Templates for common relation types in fibromyalgia research."""

    @staticmethod
    def treats(intervention_slug: str, condition_slug: str, confidence: float = 0.85) -> Dict:
        """Treatment relationship template."""
        return {
            "kind": "treats",
            "confidence": confidence,
            "direction": "positive",
            "intervention": intervention_slug,
            "condition": condition_slug,
        }

    @staticmethod
    def causes(mechanism_slug: str, symptom_slug: str, confidence: float = 0.80) -> Dict:
        """Causal mechanism template."""
        return {
            "kind": "causes",
            "confidence": confidence,
            "direction": "positive",
            "mechanism": mechanism_slug,
            "symptom": symptom_slug,
        }

    @staticmethod
    def comorbid_with(condition1_slug: str, condition2_slug: str, confidence: float = 0.75) -> Dict:
        """Comorbidity template."""
        return {
            "kind": "comorbid-with",
            "confidence": confidence,
            "direction": "neutral",
            "condition1": condition1_slug,
            "condition2": condition2_slug,
        }

    @staticmethod
    def diagnostic_for(test_slug: str, condition_slug: str, confidence: float = 0.90) -> Dict:
        """Diagnostic relationship template."""
        return {
            "kind": "diagnostic-for",
            "confidence": confidence,
            "direction": "positive",
            "test": test_slug,
            "condition": condition_slug,
        }

    @staticmethod
    def effect(drug_slug: str, confidence: float = 0.80, direction: str = "positive") -> Dict:
        """Generic effect template for testing."""
        return {
            "kind": "effect",
            "confidence": confidence,
            "direction": direction,
            "drug": drug_slug,
        }


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def get_entity_for_test(test_purpose: str) -> Dict:
    """
    Get appropriate entity based on test purpose.

    Args:
        test_purpose: One of: "simple", "orphan", "create", "update", "delete",
                      "list", "duplicate", "revision"

    Returns:
        Entity dictionary suitable for the test scenario
    """
    purpose_map = {
        "simple": ScientificEntities.PREGABALIN,
        "orphan": ScientificEntities.LOW_DOSE_NALTREXONE,
        "create": ScientificEntities.DULOXETINE,
        "update": ScientificEntities.GABAPENTIN,
        "delete": ScientificEntities.ACETAMINOPHEN,
        "list1": ScientificEntities.AMITRIPTYLINE,
        "list2": ScientificEntities.CYCLOBENZAPRINE,
        "list3": ScientificEntities.FIBROMYALGIA,
        "duplicate": ScientificEntities.TRAMADOL,
        "revision": ScientificEntities.MILNACIPRAN,
    }
    return purpose_map.get(test_purpose, ScientificEntities.PREGABALIN)


def get_source_for_test(test_purpose: str = "default") -> Dict:
    """
    Get appropriate source based on test purpose.

    Returns:
        Source dictionary suitable for the test scenario
    """
    purpose_map = {
        "default": ScientificSources.EULAR_2017_GUIDELINES,
        "high_trust": ScientificSources.ACR_2016_REVISED,
        "study": ScientificSources.PREGABALIN_FDA_APPROVAL,
        "review": ScientificSources.COCHRANE_EXERCISE_REVIEW,
    }
    return purpose_map.get(test_purpose, ScientificSources.EULAR_2017_GUIDELINES)
