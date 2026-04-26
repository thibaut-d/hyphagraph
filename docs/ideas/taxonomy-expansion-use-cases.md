# Feature Draft: Taxonomy Expansion for New Hypergraph Domains

## Overview

HyphaGraph should be able to support multiple kinds of hypergraphs, not only medical or scientific knowledge graphs.

The core idea is to keep the graph engine and evidence-first architecture, while allowing different domain taxonomies to define:

- entity categories
- relation types
- source types
- extraction and normalization rules
- domain-specific UX labels

This would let the same platform support very different knowledge systems without forcing them into a medical-science schema.

## Core Concept

Instead of treating the current taxonomy as fixed, treat it as one domain profile among several possible profiles.

A domain profile could define:

- allowed entity types
- allowed relation types
- source ingestion options
- validation rules
- optional domain-specific prompts or extraction guidance

## Candidate Domains

### 1. Computer Science / AI Team Knowledge Graph

Use HyphaGraph to build a team knowledge graph for AI, ML, systems, tooling, and research operations.

Possible uses:

- track concepts, methods, models, benchmarks, and tools
- connect papers to claims and implementation notes
- organize internal research knowledge for the team
- support onboarding and shared understanding

Additional source need:

- add `arXiv` as a source

Potential source types:

- arXiv papers
- internal notes
- documentation
- benchmark reports
- copied article excerpts with provenance

Possible entity examples:

- model
- method
- dataset
- benchmark
- library
- architecture
- research claim
- failure mode

### 2. Fiction Worldbuilding and Lore Graph

Use HyphaGraph to build a hypergraph for fictional worlds, characters, places, timelines, and lore.

Possible uses:

- track characters, factions, locations, events, and artifacts
- preserve contradictions across drafts
- connect scenes, notes, and lore fragments to graph entities
- support long-form consistency during writing

Additional source needs:

- add copied and pasted text as a source
- add free-written ideas and notes as a source

Potential source types:

- pasted manuscript excerpts
- scene drafts
- character notes
- lore notes
- brainstorming text

Possible entity examples:

- character
- faction
- location
- artifact
- event
- belief system
- rule of magic
- historical period

## Impact Analysis

### Shared Architectural Impact

- Taxonomy configuration:
  The current schema likely assumes a relatively fixed set of categories and relation semantics. Supporting multiple domains would require a configurable taxonomy layer rather than hard-coded assumptions.

- Validation rules:
  Domain-specific validation would need to remain explicit and auditable. A medical relation validator should not silently govern fiction or software-knowledge relations.

- Extraction prompts and normalization:
  Extraction quality will depend on domain-specific prompts, examples, and normalization rules. Reusing one extraction strategy across all domains will likely reduce precision.

- Provenance model:
  The provenance architecture fits this direction well, because all domains still need source-backed claims, revision history, and contradiction visibility.

- UI language:
  Some current UI copy may be science-oriented. Labels and workflows may need to become domain-aware without forking the entire frontend.

### Impact Analysis: Computer Science / AI Knowledge Graph

- Strong fit with current evidence-first model:
  Papers, benchmark reports, and internal notes map well to source-backed claims and contradictory findings.

- New ingestion requirements:
  `arXiv` support would likely require source ingestion, metadata parsing, and citation/provenance handling for preprints.

- Taxonomy changes:
  The existing medical categories and relations would need alternatives for methods, tools, datasets, benchmarks, and engineering claims.

- Team value:
  This could turn HyphaGraph into an internal institutional memory system for research and engineering decisions.

- Risk:
  AI and software knowledge changes quickly, so stale claims and duplicate concepts could accumulate without strong normalization and review workflows.

### Impact Analysis: Fiction Worldbuilding and Lore Graph

- Good fit for contradiction visibility:
  Fiction drafting often contains conflicting versions of events, rules, or character histories. HyphaGraph's explicit contradiction handling is valuable here.

- Source model expansion:
  Pasted text and free-written notes would need to be first-class sources, with clear provenance so rough ideas do not become indistinguishable from finalized canon.

- Taxonomy changes:
  Entity and relation types would need to represent narrative and worldbuilding concepts rather than scientific concepts.

- UX opportunity:
  This domain pairs naturally with a lightweight writing layer, especially if blog-like notes can link automatically to entities.

- Risk:
  If canon status, draft status, and narrator perspective are not modeled clearly, the graph could mix speculative notes with authoritative lore in confusing ways.

## Design Principles

- keep the graph engine domain-agnostic
- move taxonomy assumptions into explicit configuration
- preserve provenance and contradiction visibility across all domains
- do not let free-form text become authoritative without source framing
- prefer one explainable pipeline with configurable rules over multiple hidden pipelines

## Open Questions

- How should a domain profile be represented: code configuration, database records, or both?
- Which parts of extraction are truly generic, and which must be domain-specific?
- Should a workspace belong to exactly one domain profile, or support multiple profiles?
- How should canon versus draft status be modeled for fiction use cases?
- How should imported sources like `arXiv` be normalized and deduplicated?

## Summary

By making taxonomy configurable, HyphaGraph could evolve from a medical/scientific graph into a broader hypergraph platform.

Two strong early candidates are:

- a computer science and AI team knowledge graph with `arXiv` ingestion
- a fiction worldbuilding and lore graph with pasted text and free-written idea sources

The main impact is architectural: taxonomy, validation, ingestion, and UX would need to become domain-aware while preserving the current evidence-first principles.
