# Entity Detail Page - Redesign Analysis & Proposal

**Date**: 2026-01-14
**Status**: Analysis & Design Phase

---

## 1. Analyse du Modèle Hypergraphe

### Comment HyphaGraph Modélise les Hypergraphes

**Hypergraphe** : Une relation peut connecter N entités (pas seulement 2)

**Modèle de Données** :
```
Relation (hyper-edge)
  ├─ kind: "biomarker_for" (type de relation)
  ├─ direction: supports/contradicts (polarité)
  ├─ confidence: 0.6 (force de l'assertion)
  └─ Roles (participants):
      ├─ Entity 1 (role: "subject") → mirna-223-3p
      └─ Entity 2 (role: "object") → fibromyalgia

Source: "The Association Between miRNA-223-3p..."
```

**Contrairement aux graphes binaires** :
- Un hyper-edge peut avoir 2, 3, 4+ entités
- Les rôles explicites évitent l'ambiguïté
- Exemple complexe : "duloxetine treats fibromyalgia in adults with chronic pain"
  - duloxetine (agent)
  - fibromyalgia (target)
  - adults (population)
  - chronic-pain (condition)

**Actuellement dans HyphaGraph** :
- Presque toutes les relations sont binaires (subject/object)
- Les rôles "subject"/"object" sont des rôles grammaticaux génériques
- Pas encore de rôles sémantiques (agent, target, population, condition)

---

## 2. Problèmes Actuels de la Page Entity Detail

### Redondances Identifiées

**A. Double Affichage des Relations** :
```
Section "Computed Inference":
  - biomarker_for
    Connected to: mirna-223-3p, fibromyalgia  ← Liste les 2 entités

Section "Source Evidence":
  - biomarker_for
    • mirna-223-3p is biomarker for fibromyalgia  ← Même info !
```
→ **Redondance** : Les mêmes relations affichées 2 fois

**B. "Computed Inference" vs "Source Evidence"** :
- "Computed" : Agrégation par type (biomarker_for, affects_population)
- "Source" : Relations individuelles groupées par type
- **Redondance** : Quand il y a 1 seule relation, les 2 sections montrent la même chose

**C. Informations Confuses** :
- "Connected to: mirna-223-3p, fibromyalgia" inclut l'entité courante (fibromyalgia)
- On voit "fibromyalgia connecté à fibromyalgia" (pas clair)
- Les 2 entités ont le même poids visuel (pas de distinction)

---

## 3. Théorie des Hypergraphes Appliquée

### Définition Formelle

**Hypergraphe H = (V, E)** :
- V = ensemble de sommets (Entities)
- E = ensemble d'hyper-arêtes (Relations)
- Chaque e ∈ E peut connecter n ≥ 2 sommets

**Dans HyphaGraph** :
```
V = {fibromyalgia, mirna-223-3p, healthy-controls, ...}
E = {
  e1: biomarker_for(mirna-223-3p, fibromyalgia),
  e2: affects_population(fibromyalgia, healthy-controls),
  ...
}
```

### Visualisation Optimale

Pour une entité E, montrer :
1. **Relations Sortantes** : E est le "subject" (E → autres)
2. **Relations Entrantes** : E est l'"object" (autres → E)
3. **Relations N-aires** : E participe avec N-1 autres entités

**Regroupement** :
- Par TYPE de relation (treats, causes, etc.)
- Par DIRECTION par rapport à l'entité courante (outgoing/incoming)

---

## 4. Analyse UX.md Requirements

### Section 6.3 - Entity Detail (Required)

**Objectif** : "What do we actually know about this entity?"

**Sections Requises** :
1. ✅ Header (name, type) - Existe
2. ✅ Short summary - Existe
3. ❌ External references (Wikipedia, Vidal) - Manquant
4. ⚠️ Derived properties with consensus status - Partiellement (Computed Inference)
5. ⚠️ Ranked key sources - Manquant (sources non listées)

**Contraintes** :
- ✅ Clear distinction narrative vs computed
- ✅ Every property links to evidence (bouton Explain)
- ⚠️ But: Redondance entre Computed et Source Evidence

---

## 5. Proposition de Refonte

### Structure Simplifiée (Sans Redondance)

```
┌─────────────────────────────────────────────────────────┐
│ HEADER                                                  │
│ Fibromyalgia                                            │
│ [Discover Sources] [Edit] [Delete] [Create Relation]   │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ SUMMARY                                                 │
│ "Fibromyalgia is a chronic disorder..."                │
│ Terms: fibromyalgia-syndrome                            │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ KNOWLEDGE GRAPH (Consolidé - Plus de redondance)        │
│                                                          │
│ ┌─ Is Biomarker Target Of ────────────────────────┐    │
│ │ • mirna-223-3p [supports] confidence: 0.60      │    │
│ │   Source: The Association Between miRNA...       │    │
│ │   [View Source]                                  │    │
│ └──────────────────────────────────────────────────┘    │
│                                                          │
│ ┌─ Affects Populations ────────────────────────────┐    │
│ │ • healthy-controls [neutral] confidence: 0.60    │    │
│ │   Source: miRNA Association Study                │    │
│ │   [View Source]                                  │    │
│ └──────────────────────────────────────────────────┘    │
│                                                          │
│ [View All Evidence] [View Synthesis]                    │
└─────────────────────────────────────────────────────────┘
```

### Principes de la Refonte

**1. Une Seule Section Relations** (pas 2)
- Fusionne "Computed Inference" et "Source Evidence"
- Groupe par type de relation
- Montre les relations individuelles directement
- Les métriques (score, confidence) par relation, pas par type

**2. Orientation par Rapport à l'Entité Courante**
- "Is Biomarker Target Of" au lieu de "biomarker_for"
  - Clair : fibromyalgia EST la cible du biomarker
- "Affects Populations" au lieu de "affects_population"
  - Clair : fibromyalgia affecte des populations

**3. Filtre Entité Courante**
- Dans "Connected to: mirna-223-3p, fibromyalgia"
- Enlever "fibromyalgia" (c'est l'entité courante !)
- Montrer seulement : "Connected to: mirna-223-3p"

**4. Contexte par Relation**
- Chaque relation montre :
  - Entités connectées (hors entité courante)
  - Direction (supports/contradicts)
  - Confidence
  - Source (titre + lien)
- Pas d'agrégation inutile quand peu de relations

**5. Progressive Disclosure**
- Relations directes visibles immédiatement
- Boutons "View All Evidence" pour détail complet
- Boutons "View Synthesis" pour agrégation multi-sources

---

## 6. Layout Proposé (Détaillé)

### Header
```
Fibromyalgia
Category: Disease
Terms: fibromyalgia, fibromyalgia-syndrome

[Discover Sources] [Edit] [Delete] [Create Relation]
```

### Summary
```
"Fibromyalgia is a chronic disorder characterized by..."
```

### Relations (Unique Section)

**Organisé par type ET direction** :

```
┌─ Relationships ──────────────────────────────────────┐
│                                                       │
│ As Disease Target (relations where fibromyalgia      │
│ is studied/measured):                                 │
│                                                       │
│ • Biomarkers                                          │
│   mirna-223-3p is biomarker for fibromyalgia          │
│   [supports] Confidence: 60% | Source: The Association│
│   Between miRNA-223-3p... [View]                      │
│                                                        │
│ • Population Studies                                   │
│   Affects: healthy-controls                            │
│   [neutral] Confidence: 60% | Source: miRNA Study [View]│
│                                                        │
│ [Show More Relations] [View Detailed Evidence]         │
└────────────────────────────────────────────────────────┘
```

### Sources Citant Cette Entité (Nouveau)
```
┌─ Key Sources (3 sources mention fibromyalgia) ───────┐
│ 1. The Association Between miRNA-223-3p... (2025)    │
│    Quality: 60% | 2 relations                         │
│ 2. Effect of respiratory muscle training... (2025)   │
│    Quality: 100% (Systematic Review) | 0 relations   │
│ 3. ...                                                │
└───────────────────────────────────────────────────────┘
```

---

## 7. Améliorations Clés

### Avant (Actuel)
```
Computed Inference
  - biomarker_for
    Connected to: mirna-223-3p, fibromyalgia  ← Redondant
    Score: 1.0

Source Evidence
  - biomarker_for
    • mirna-223-3p is biomarker for fibromyalgia  ← Même info
```

### Après (Proposé)
```
Relationships

  As Biomarker Target
    • mirna-223-3p
      [supports] Confidence: 60%
      Source: The Association Between... [View]
```

**Avantages** :
- ✅ Pas de redondance (1 seule section)
- ✅ Clair : "As Biomarker Target" oriente par rapport à fibromyalgia
- ✅ Entité courante filtrée (on ne voit que mirna-223-3p)
- ✅ Source traçable (lien direct)
- ✅ Direction visible (supports)

---

## 8. Mapping Relations → Langage Naturel

### Pour Fibromyalgia

| Relation Type | Role de Fibromyalgia | Titre Section | Description |
|---------------|----------------------|---------------|-------------|
| **biomarker_for** | object (cible) | "Biomarkers" | mirna-223-3p is biomarker for fibromyalgia |
| **affects_population** | subject (source) | "Affected Populations" | fibromyalgia affects healthy-controls |
| **treats** | object (cible) | "Treatments" | duloxetine treats fibromyalgia |
| **causes** | object (cible) | "Caused By" | stress causes fibromyalgia |
| **measures** | object (mesuré) | "Assessment Tools" | VAS measures fibromyalgia severity |

### Orientation Automatique

**Si fibromyalgia est subject** :
- "Fibromyalgia affects..."
- "Fibromyalgia causes..."

**Si fibromyalgia est object** :
- "Treatments for fibromyalgia"
- "Biomarkers of fibromyalgia"
- "Causes of fibromyalgia"

---

## 9. Implementation Plan

### Phase 1: Simplifier (Enlever Redondance)
1. Fusionner "Computed Inference" et "Source Evidence" en une seule section
2. Filtrer entité courante de connected_entities
3. Titres orientés (pas juste le nom du relation type)

### Phase 2: Améliorer Lisibilité
4. Grouper par direction (relations entrantes vs sortantes)
5. Natural language pour chaque type de relation
6. Source visible et cliquable pour chaque relation

### Phase 3: Ajouter Contexte
7. Montrer scope si disponible (population, condition)
8. Afficher nombre total de sources par relation type
9. Indicateur de consensus (fort si >3 sources concordantes)

---

## 10. Success Metrics

**UX.md Criteria** :
- ✅ 30 seconds to understand what entity is
- ✅ 2 clicks to reach source (relation → source link)
- ✅ Clear narrative vs computed distinction
- ✅ Limitations visible (confidence %, disagreement)

**No Redundancy** :
- ✅ Each relation shown once
- ✅ Clear role orientation
- ✅ Focused on current entity

**Scientific Honesty** :
- ✅ Confidence scores visible
- ✅ Source attribution
- ✅ Direction (supports/contradicts) clear

---

## Next Steps

1. Implement unified Relations section
2. Remove Computed Inference duplication
3. Filter out current entity from connected_entities
4. Add relation orientation (as subject vs as object)
5. Test with fibromyalgia entity
