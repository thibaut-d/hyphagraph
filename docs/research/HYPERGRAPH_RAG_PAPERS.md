# Hypergraph RAG and Adjacent Evidence-Centric Systems

Curated starting point for papers and projects related to:

- hypergraph-based retrieval-augmented generation
- claim-centric and evidence-centric scientific knowledge representations
- contradiction handling, truth discovery, and argument structure

Last verified: `2026-04-17`

## Scope

This is not a comprehensive survey. It is a HyphaGraph-oriented comparison note.

Implementation status is intentionally conservative:

- `official code` means the paper or official project page links to a public repository
- `dataset/code` means the main public artifact is a dataset, benchmark, or research codebase
- `paper only` means a paper was verified but no official public implementation was confirmed
- `mature OSS` means an actively maintained open-source project exists, even if it is not an exact
  research artifact match for HyphaGraph

## HyphaGraph Lenses

The comparison below is biased toward the properties HyphaGraph cares about most:

- `base unit`: what the system actually stores or reasons over
- `n-ary support`: whether it directly models more-than-binary relations
- `provenance`: whether evidence is traceable back to source text or source records
- `contradiction`: whether support, refutation, disagreement, or conflict is modeled explicitly
- `quality/confidence`: whether source trust, evidence quality, or claim status is first-class
- `text extraction`: whether there is a real text-to-structure pipeline
- `generation`: whether the project generates answers, reports, or synthesized outputs

Legend used in the comparison table:

- `yes`: directly supported and verified in the paper or official docs
- `partial`: adjacent support, but not a core or fully verified capability
- `no`: not a core feature
- `?`: I could not verify from the primary or official sources I checked

## Direct Hypergraph-RAG Papers

| Work | First verified public date | Focus | Implementation status | Links |
|------|-----------------------------|-------|-----------------------|-------|
| `HyperGraphRAG: Retrieval-Augmented Generation via Hypergraph-Structured Knowledge Representation` | 2025-03-27 | End-to-end hypergraph-based RAG with hypergraph construction, retrieval, and generation | `official code` | [Paper](https://arxiv.org/abs/2503.21322), [Code](https://github.com/LHRLAB/HyperGraphRAG) |
| `Hyper-RAG: Combating LLM Hallucinations using Hypergraph-Driven Retrieval-Augmented Generation` | 2025-03-30 | Domain-focused hypergraph RAG for hallucination reduction, especially medical use cases | `official code` | [Paper](https://arxiv.org/abs/2504.08758), [Code](https://github.com/iMoonLab/Hyper-RAG) |
| `Cross-Granularity Hypergraph Retrieval-Augmented Generation for Multi-hop Question Answering` | 2025-08-15 | Multi-hop QA with an entity-passage hypergraph and diffusion-style retrieval | `paper only` | [Paper](https://arxiv.org/abs/2508.11247) |
| `Improving Multi-step RAG with Hypergraph-based Memory for Long-Context Complex Relational Modeling` | 2025-12-30 | Multi-step RAG with dynamic hypergraph memory instead of only passive text memory | `paper only` | [Paper](https://arxiv.org/abs/2512.23959) |

## Adjacent Hypergraph-for-Evidence Work

These are not exact matches for the retrieval pattern above, but they are close to HyphaGraph's
evidence-organization problem.

| Work | First verified public date | Focus | Implementation status | Links |
|------|-----------------------------|-------|-----------------------|-------|
| `Enhancing LLM Generation with Knowledge Hypergraph for Evidence-Based Medicine` | 2025-03-18 | Uses LLM-assisted evidence gathering plus a knowledge hypergraph and evidence prioritization for EBM queries | `paper only` | [Paper](https://arxiv.org/abs/2503.16530) |

## Adjacent Claim, Evidence, and Contradiction Work

These are not hypergraph-RAG systems, but several are highly relevant to HyphaGraph's design.

| Work | First verified public date | Focus | Implementation status | Links |
|------|-----------------------------|-------|-----------------------|-------|
| `Extracting Fine-Grained Knowledge Graphs of Scientific Claims: Dataset and Transformer-Based Results` (`SciClaim`) | 2021-11 | Fine-grained claim graphs with qualifiers, subtypes, and evidence over scientific claims | `dataset/code` | [Paper](https://aclanthology.org/2021.emnlp-main.381/), [Dataset](https://github.com/siftech/SciClaim) |
| `Building evidence-based knowledge bases from full-text literature for disease-specific biomedical reasoning` (`EvidenceNet`) | 2026-03-30 | LLM-assisted evidence records, entity normalization, evidence quality scoring, and typed relations from full-text biomedical papers | `paper only` | [Paper](https://arxiv.org/abs/2603.28325) |
| `Fact or Fiction: Verifying Scientific Claims` (`SciFact`) | 2020-11 | Scientific claim verification against abstracts with SUPPORTS / REFUTES labels and rationales | `dataset/code` | [Paper](https://www.aclweb.org/anthology/2020.emnlp-main.609.pdf), [Code](https://github.com/allenai/scifact) |
| `GraphRAG` (Microsoft) | verified docs and repo current as of 2026-04-17 | Graph-based RAG pipeline with entity, relationship, optional claim extraction, and community reporting | `mature OSS` | [Repo](https://github.com/microsoft/graphrag), [Docs](https://microsoft.github.io/graphrag/) |
| `Truth Discovery with Multiple Conflicting Information Providers on the Web` (`TruthFinder`) | 2007-08 | Source-reliability and fact-credibility estimation from conflicting providers | `paper only` | [Paper PDF mirror](https://web.cs.ucla.edu/~yzsun/classes/2014Spring_CS7280/Papers/Trust/kdd07_xyin.pdf) |
| `Resolving Conflicts in Heterogeneous Data by Truth Discovery and Source Reliability Estimation` (`CRH`) | 2014 | General optimization framework for truth discovery across heterogeneous data types | `paper only` | [Paper PDF](https://cse.buffalo.edu/~jing/doc/sigmod14_crh.pdf) |
| `Evidence graphs for parsing argumentation structure` (`evidencegraph`) | repo verified current as of 2026-04-17 | Argumentation structure parsing with support/attack-style graph structure over text segments | `dataset/code` | [Repo](https://github.com/peldszus/evidencegraph) |
| `Beyond Graphs: Can Large Language Models Comprehend Hypergraphs?` (`LLM4Hypergraph`) | 2024-10-14 | Benchmark and prompting framework for LLM reasoning over hypergraph structure | `dataset/code` | [Paper](https://arxiv.org/abs/2410.10083), [Code](https://github.com/iMoonLab/LLM4Hypergraph) |
| `Modeling Hypergraph Using Large Language Models` | 2025-10-09 | HyperLLM: LLM-driven generation of synthetic hypergraphs via multi-agent collaboration | `paper only` | [Paper](https://arxiv.org/abs/2510.11728) |

## HyphaGraph-Oriented Comparison

| Work | Base unit | N-ary support | Provenance | Contradiction | Quality / confidence | Text extraction | Generation / synthesis | Reuse fit for HyphaGraph |
|------|-----------|---------------|------------|---------------|----------------------|-----------------|------------------------|--------------------------|
| `HyperGraphRAG` | hyperedge / relational fact | `yes` | `partial` | `no` | `partial` | `yes` | `yes` | Strong reference for n-ary retrieval and hypergraph construction |
| `Hyper-RAG` | hypergraph knowledge base | `yes` | `partial` | `no` | `partial` | `yes` | `yes` | Useful for domain RAG architecture and hypergraph retrieval patterns |
| `HGRAG` | entity-passage hypergraph | `yes` | `partial` | `no` | `no` | `yes` | `yes` | Useful for multi-hop retrieval design, less so for provenance-rich curation |
| `HGMem` | memory hypergraph | `yes` | `partial` | `no` | `no` | `partial` | `yes` | Useful for agent memory or long-context reasoning ideas |
| `EBM Knowledge Hypergraph` | evidence item plus hypergraph ranking features | `yes` | `partial` | `no` | `yes` | `yes` | `yes` | Useful for evidence prioritization in medical or scientific settings |
| `SciClaim` | claim graph with entity, relation, and attribute labels | `partial` | `yes` | `no` | `no` | `yes` | `no` | Strong schema inspiration for fine-grained scientific assertions |
| `EvidenceNet` | evidence record / evidence node | `partial` | `yes` | `partial` | `yes` | `yes` | `partial` | One of the strongest references for evidence-first KG design |
| `SciFact` | claim-abstract pair plus rationale | `no` | `yes` | `yes` | `no` | `partial` | `no` | Best fit for support/refute and rationale supervision, not for KG structure |
| `GraphRAG` | entities, relationships, optional claims, community reports | `no` | `partial` | `partial` | `partial` | `yes` | `yes` | Strong pipeline reference, but binary graph and summary-oriented |
| `TruthFinder` / `CRH` | conflicting values or observations across sources | `no` | `partial` | `yes` | `yes` | `no` | `no` | Best algorithmic starting point for source weighting and conflict fusion |
| `evidencegraph` | argumentative segments and typed links | `no` | `partial` | `yes` | `no` | `yes` | `no` | Useful for support/attack modeling, not scientific evidence synthesis by itself |
| `LLM4Hypergraph` | hypergraph task instance | `yes` | `no` | `no` | `no` | `no` | `no` | Useful for evaluation and prompting of hypergraph reasoning, not storage design |

## Practical Reading Order

If the goal is to sharpen HyphaGraph specifically, this is the most useful order:

1. `SciClaim`
   Fine-grained scientific assertion structure. Best reference for "claims richer than triples".
2. `EvidenceNet`
   Strongest verified evidence-centric design match so far, especially on provenance and quality.
3. `HyperGraphRAG`
   Strongest direct reference for why hyperedges matter in RAG and how to operationalize them.
4. `GraphRAG`
   Best reference for a real open-source indexing and query pipeline over text corpora.
5. `SciFact`
   Best reference for support / refute labels plus rationales.
6. `TruthFinder` and `CRH`
   Best references for conflict-aware source weighting and truth-discovery algorithms.

## Practical Code Shortlist

These are the repositories most worth cloning first:

- [microsoft/graphrag](https://github.com/microsoft/graphrag)
- [LHRLAB/HyperGraphRAG](https://github.com/LHRLAB/HyperGraphRAG)
- [iMoonLab/Hyper-RAG](https://github.com/iMoonLab/Hyper-RAG)
- [allenai/scifact](https://github.com/allenai/scifact)
- [siftech/SciClaim](https://github.com/siftech/SciClaim)
- [peldszus/evidencegraph](https://github.com/peldszus/evidencegraph)

## Cautions and Unverified Claims

- I did **not** verify a public official repository for `EvidenceNet` as of `2026-04-17`.
- I did **not** verify the specific `Spectrum` truth-discovery implementation named in the earlier
  ChatGPT response. Do not rely on that repo reference without a fresh check.
- `TruthFinder` and `CRH` are important algorithmic references, but I did not find a canonical,
  widely-used official repository for those original papers during this pass.
- `GraphRAG` does extract claims, but in the official docs claim extraction is optional and turned
  off by default because it typically needs prompt tuning.

## Current Inference

Inference from the verified papers and official repositories above, not a claim of exhaustive
coverage:

HyphaGraph still appears to occupy a real gap. I did not find a mature open-source system that
combines all of the following in one coherent stack:

- n-ary or hypergraph-native scientific assertions
- fine-grained provenance
- explicit contradiction visibility
- source or evidence quality handling
- auditable, explorable synthesis

What exists today is closer to a set of complementary families:

- hypergraph-RAG systems
- claim and rationale datasets
- evidence-centric biomedical KGs
- truth-discovery algorithms
- argument-structure parsers

That makes HyphaGraph look less like a clone of an existing project and more like a synthesis of
several partially overlapping research directions.

## Existing General Collections

These are useful monitoring feeds, but they are broader than this niche:

- [Tongji-KGLLM/RAG-Survey](https://github.com/Tongji-KGLLM/RAG-Survey)
  General RAG knowledge base and survey project. Useful for filtering papers by code and topic,
  but not dedicated to hypergraph RAG.
- [hymie122/RAG-Survey](https://github.com/hymie122/RAG-Survey)
  Broad markdown list of RAG papers and subtopics. Useful as a general paper index.
- [HKUDS/Awesome-LLM4Graph-Papers](https://github.com/HKUDS/Awesome-LLM4Graph-Papers)
  Broad LLM-plus-graph literature tracker. Useful for adjacent graph and knowledge-structure work.
