# 📘 Design Brief — HyphaGraph (MVP)

## 0. Content overview

```
HyphaGraph — Page Tree (MVP)
===========================

/
├── Home
│
├── Entities
│   └── /entities
│       ├── Entity List
│       │
│       └── Entity Detail
│           └── /entities/:entityId
│               ├── Summary
│               ├── External References
│               ├── Derived Properties
│               │   └── Property Detail (drawer / dialog)
│               │       └── /entities/:entityId/properties/:propertyId
│               │           └── Evidence (Hyperedges)
│               │               └── /properties/:propertyId/hyperedges
│               │                   └── Source Detail
│               │                       └── /sources/:sourceId
│               │
│               └── Ranked Sources
│                   └── Source Detail
│                       └── /sources/:sourceId
│
├── Sources
│   └── /sources
│       ├── Source List
│       │
│       └── Source Detail
│           └── /sources/:sourceId
│               ├── Metadata
│               ├── Abstract / Summary
│               ├── Related Entities
│               │   └── Entity Detail
│               │       └── /entities/:entityId
│               │
│               └── Related Evidence (Hyperedges)
│
└── Account
    └── /account
        ├── Profile
        ├── Preferences
        └── (Future: Contributions / Roles)
```

## 1. Context and Product Vision

### 1.1 Context
HyphaGraph is a web application dedicated to **evidence-based knowledge synthesis** in domains where information is:

- heterogeneous  
- sometimes contradictory  
- incomplete or evolving  
- supported by sources of unequal quality  

Typical domains include medicine, science, public policy, or any field requiring **auditable reasoning**.

The primary users are **experts** (physicians, researchers, analysts), but the interface must remain **usable without prior knowledge of graphs, databases, or formal logic**.

---

### 1.2 UX Vision

> **Enable users to quickly understand what is known,  
> clearly see what this knowledge is based on,  
> and immediately identify where consensus is weak or disputed.**

Core UX principles:
- scientific honesty (no oversimplification)
- systematic traceability
- progressive disclosure of complexity
- clear separation between navigation, exploration, and evidence

---

## 2. General Design Principles

### 2.1 Fundamental Rules

- The interface must **never hide contradictions**
- Syntheses must **never appear as absolute truth**
- Every conclusion must be **traceable to its sources**
- Complexity should be **revealed progressively**, never imposed upfront

---

### 2.2 Clear UI Responsibilities

| UI Element | Responsibility |
|----------|----------------|
| Main menu | Global navigation |
| Pages | Context changes |
| Drawer | Filters / point of view |
| Cards / tables | Reading & decision |
| Detail views | Evidence & audit |

---

## 3. Page Architecture

### 3.1 Root Pages (Main Menu)

Accessible only from the main navigation:

- **Home** → `/`
- **Entities** → `/entities`
- **Sources** → `/sources`
- **Account** → `/account`

---

### 3.2 Contextual Pages (Secondary Navigation)

Accessible only through interactions within pages:

- Entity detail → `/entities/:entityId`
- Property detail → `/entities/:entityId/properties/:propertyId`
- Evidence / hyperedges → `/properties/:propertyId/hyperedges`
- Source detail → `/sources/:sourceId`

---

## 4. Main Navigation (Top Navigation)

### 4.1 Objective
Allow users to **switch global context at any time**.

### 4.2 Expected Content
- Product name / logo (returns to Home)
- Navigation links:
  - Home
  - Entities
  - Sources
  - Account
- Global search entry
- User / language access

### 4.3 Constraints
- Always visible
- No filters
- No domain-specific logic
- No hidden access to main pages

> The designer is free to choose the visual form (tabs, buttons, typography), as long as these rules are respected.

---

## 5. Drawer (Side Panel)

### 5.1 General Role
The drawer is **strictly reserved for filters**.  
It must **never be used for main navigation**.

---

### 5.2 Drawer — Entities List (`/entities`)

#### Objective
Help physicians or experts **narrow down relevant entities** using clinical or scientific criteria.

#### Expected Filter Types
- Entity type (drug, disease, symptom, etc.)
- Clinical effects / derived properties
- Level of consensus
- Overall evidence quality
- Time relevance

#### Constraints
- Filters must use **domain language**
- Based on **derived properties**, not free text
- Filters affect displayed results, **not underlying calculations**

---

### 5.3 Drawer — Entity Detail (`/entities/:id`)

#### Objective
Allow users to **change their analytical point of view** on a single entity.

#### Expected Filter Types
- Evidence direction (supports / contradicts / heterogeneous)
- Study type
- Publication year
- Minimum source authority

#### Constraints
- Filters must never change:
  - consensus status
  - computed scores
- A clear indication must appear when evidence is hidden by filters

---

### 5.4 Drawer — Sources List (`/sources`)

#### Objective
Support **critical reading of the literature**.

#### Expected Filter Types
- Study type
- Publication year
- Authority score
- Domain / topic
- Role in the graph (pillar, supporting, contradictory)

---

## 6. Pages — Expected Content

### 6.1 Home

#### Objective
Quick orientation.

#### Expected Content
- Entry points to Entities
- Entry points to Sources
- (Optional) recent or highlighted items

---

### 6.2 Entities — List

#### Objective
Help users **identify relevant entities** efficiently.

#### Expected Content
- List of entity cards or rows
- For each entity:
  - name
  - type
  - 2–3 key clinical properties
  - consensus level
  - global evidence quality indicator
- Primary action: *View entity*

---

### 6.3 Entity — Detail

#### Objective
Answer the question:  
**“What do we actually know about this entity?”**

#### Required Sections
- Header (name, type)
- Short summary (human or LLM, clearly labeled)
- External references (Wikipedia, Vidal, etc.)
- Derived properties with consensus status
- Ranked key sources

#### Constraints
- Clear visual distinction between:
  - narrative summary
  - computed conclusions
- Every property must link to its evidence

---

### 6.4 Property — Detail (Drawer or Dialog)

#### Objective
Explain **how a conclusion is established**.

#### Expected Content
- Consensus status
- Score (if shown)
- Known limitations
- Access to evidence

---

### 6.5 Evidence / Hyperedges

#### Objective
Enable **scientific audit**.

#### Expected Content
- Table or list of evidence items
- Readable claim
- Direction (support / contradict)
- Conditions
- Associated source

---

### 6.6 Sources — List

#### Objective
Explore **literature independently from entities**.

#### Expected Content
- Source cards with:
  - title
  - study type
  - year
  - authority
  - usage in the graph
- Action: *View source*

---

### 6.7 Source — Detail

#### Objective
Support in-depth critical reading.

#### Expected Content
- Full metadata
- Abstract or summary
- External links
- Related hyperedges
- Linked entities

---

## 7. Freedom Given to the Designer

The designer has **full freedom** regarding:
- visual style
- typography
- component choice
- layout details
- micro-interactions

As long as:
- page roles are respected
- navigation and filters remain clearly separated
- traceability is always visible
- contradictions are never hidden

---

## 8. UX Success Criteria

The design is considered successful if:

- A physician understands within **30 seconds**:
  - what an entity is
  - whether consensus is strong or weak
- Any claim’s source can be reached in **two clicks or fewer**
- Narrative summaries cannot be confused with scientific conclusions
- Knowledge limitations are clearly perceived

---

### ✅ Conclusion

This design brief defines the **conceptual and functional framework** of the HyphaGraph interface.  
It ensures a UX that is:

- rigorous  
- honest  
- expert-friendly  

while deliberately leaving designers free to **translate these principles into an elegant, efficient, and distinctive interface**.