# HyphaGraph - Le Modèle Hypergraphe Expliqué

**Date**: 2026-01-14
**Public**: Explication complète du modèle de données

---

## 🎯 Qu'est-ce qu'un Hypergraphe ?

### Graphe Classique (Binaire)

```
Nœud A ──(lien)── Nœud B

Exemple:
  Duloxetine ──(traite)── Fibromyalgie
```

**Limitation** : Un lien connecte exactement **2 nœuds**.

**Problème** : Les faits scientifiques ne sont jamais binaires !
- "Duloxetine traite la fibromyalgie... chez qui ? à quelle dose ? dans quel contexte ?"

---

### Hypergraphe (N-aire)

```
┌────────────────────────────────────┐
│        Hyper-arête (Relation)      │
│                                    │
│  ┌─ Duloxetine                     │
│  ├─ Fibromyalgie                   │
│  ├─ Adultes                        │
│  └─ 60mg/jour                      │
└────────────────────────────────────┘

Une relation peut connecter 2, 3, 4, N entités !
```

**Avantage** : Capture toute la complexité d'un fait scientifique.

---

## 🏗️ Les 4 Concepts Fondamentaux de HyphaGraph

### 1. **Entités** (Vertices/Nœuds)

**Ce sont les "choses" du domaine**.

**Types d'entités** :
- Médicaments : duloxetine, pregabalin
- Maladies : fibromyalgie, dépression
- Symptômes : douleur, fatigue
- Biomarqueurs : miRNA-223-3p, CRP
- Populations : adultes, femmes
- Mécanismes : serotonin-reuptake-inhibition

**En base** : Tables `entities` et `entity_revisions`
```
Entity:
  - id: UUID
  - slug: "fibromyalgia"
  - summary: "Chronic disorder with pain..."
```

---

### 2. **Relations** (Hyper-arêtes)

**Ce sont les "liens" entre entités - mais avec N participants**.

**Chaque relation a** :
- Un **type** (treats, causes, biomarker_for)
- Des **participants** (2, 3, 4, N entités)
- Une **source** (article qui l'affirme)
- Une **confiance** (0.6, 0.8, 1.0)

**En base** : Tables `relations` et `relation_revisions`

```
Relation:
  - id: UUID
  - source_id: UUID (article PubMed)
  - kind: "treats" (type de relation)
  - confidence: 0.8
```

---

### 3. **Rôles Sémantiques** (Participation Types)

**C'est la FONCTION de chaque entité dans la relation**.

**Pour une relation "treats"** :
- `agent` : QUI traite (le médicament)
- `target` : QUI est traité (la maladie)
- `population` : POUR qui (les patients)
- `dosage` : À quelle dose
- `duration` : Pendant combien de temps

**En base** : Table `relation_role_revisions`
```
RoleRevision:
  - relation_id: UUID
  - entity_id: UUID (quelle entité)
  - role_type: "agent" (quelle fonction)
  - weight: 1.0
```

**Les 16 rôles sémantiques** :
```
Core:
  - agent, target, outcome, mechanism, population, condition

Measurement:
  - measured_by, biomarker, control_group, study_group

Contextual:
  - location, dosage, duration, frequency, severity, effect_size
```

---

### 4. **Types de Relations** (Relation Vocabulary)

**C'est le VOCABULAIRE des relations possibles**.

**Les 16 types de relations** :
```
Therapeutic:
  - treats, prevents, decreases_risk, contraindicated

Causal:
  - causes, increases_risk

Mechanistic:
  - mechanism, metabolized_by

Diagnostic:
  - biomarker_for, measures

Methodological:
  - compared_to, studied_in

Statistical:
  - correlated_with

Population:
  - affects_population

Interaction:
  - interacts_with

General:
  - other
```

**En base** : Table `relation_types` (évolutive)

---

## 🔗 Comment Ça S'Assemble

### Exemple 1 : Relation Simple

```
┌─────────────────────────────────────────────┐
│ Relation: "duloxetine treats fibromyalgia" │
│                                             │
│ Type de Relation: treats                    │ ← QUE fait-on
│                                             │
│ Participants (2):                           │
│   ┌─ Duloxetine                             │
│   │  └─ Rôle: agent (qui traite)           │ ← QUI fait
│   │                                         │
│   └─ Fibromyalgie                           │
│      └─ Rôle: target (qui est traité)      │ ← QUI subit
│                                             │
│ Source: "Pharmacologic treatment..." PMID  │ ← D'OÙ vient l'info
│ Confidence: 0.8                             │ ← Avec quelle confiance
└─────────────────────────────────────────────┘
```

### Exemple 2 : Hypergraphe Complexe (4 entités)

```
┌──────────────────────────────────────────────────────────────┐
│ Relation: "duloxetine treats fibromyalgia in adults at 60mg" │
│                                                              │
│ Type de Relation: treats                                     │
│                                                              │
│ Participants (4):                                            │
│   ┌─ Duloxetine                                              │
│   │  └─ Rôle: agent (qui traite)                            │
│   │                                                          │
│   ├─ Fibromyalgie                                            │
│   │  └─ Rôle: target (qui est traité)                       │
│   │                                                          │
│   ├─ Adultes                                                 │
│   │  └─ Rôle: population (pour qui)                         │
│   │                                                          │
│   └─ 60mg-daily                                              │
│      └─ Rôle: dosage (à quelle dose)                        │
│                                                              │
│ Source: Article Systematic Review                           │
│ Confidence: 0.9 (haute qualité)                             │
└──────────────────────────────────────────────────────────────┘
```

**C'est ça un hypergraphe** : Une relation qui connecte N entités avec des rôles explicites.

---

## 💡 Pourquoi C'est Important

### Graphe Binaire (Ancien)
```
Duloxetine → Fibromyalgie

Problèmes:
  - Pour qui ? (manquant)
  - À quelle dose ? (manquant)
  - Dans quel contexte ? (manquant)
```

### Hypergraphe (HyphaGraph)
```
┌─ Relation treats ─────────────────┐
│  - duloxetine (agent)             │
│  - fibromyalgia (target)          │
│  - adults (population)            │
│  - 60mg-daily (dosage)            │
│  - 12-weeks (duration)            │
└───────────────────────────────────┘

Avantages:
  ✅ Contexte complet
  ✅ Rôles explicites
  ✅ Reproductible
  ✅ Pas d'ambiguïté
```

---

## 🎯 Dans la Page Fibromyalgia

### Ce Que Vous Voyez

**Computed Inference** :

```
┌─ treats (agents) ─────────────────────────┐
│ 10 entities                               │
│                                           │
│ • aerobic-exercise                        │
│   Score: 1.00, 5 sources, 99% confidence  │
│                                           │
│ • duloxetine                              │
│   Score: 1.00, 2 sources, 86% confidence  │
│                                           │
│ ... (8 autres)                            │
└───────────────────────────────────────────┘
```

**Décodage** :
- **treats** = Type de Relation (traitement)
- **(agents)** = Rôle Sémantique (ceux qui traitent)
- **aerobic-exercise, duloxetine** = Entités participantes
- Chaque entité a son propre score basé sur le nombre de sources

---

## 📐 Modèle Complet en Base de Données

```
┌─────────────────┐
│ Relation Types  │ ← QUOI (16 types)
│ - treats        │
│ - causes        │
│ - biomarker_for │
└─────────────────┘
         │
         │ Utilise
         ↓
┌─────────────────────────────────┐
│ Relation (instance)             │ ← Une relation concrète
│ - type: treats                  │
│ - source: PMID 12345           │
│ - confidence: 0.8               │
└─────────────────────────────────┘
         │
         │ Contient
         ↓
┌────────────────────────────────────────┐
│ Roles (participants)                   │ ← QUI avec QUEL RÔLE
│ - Entity: duloxetine, Role: agent     │
│ - Entity: fibromyalgia, Role: target  │
│ - Entity: adults, Role: population    │
└────────────────────────────────────────┘
         │
         │ Utilise
         ↓
┌─────────────────┐
│Semantic Roles   │ ← Vocabulaire des RÔLES (16 types)
│ - agent         │
│ - target        │
│ - population    │
│ - dosage        │
└─────────────────┘
```

---

## ✅ Résumé Simple

**Relation Type** = Le verbe (treats, causes, measures)
**Rôle Sémantique** = La fonction de chaque participant (agent, target, population)

**Exemple en français** :
```
"Duloxetine TRAITE la fibromyalgie CHEZ les adultes"
         ↑                         ↑
    Relation Type             Rôles Sémantiques:
    (treats)                  - duloxetine (agent)
                              - fibromyalgie (target)
                              - adultes (population)
```

**Les deux sont en base de données et évolutifs** ✅

C'est plus clair maintenant ?