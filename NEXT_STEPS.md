# Next Steps - Auto-Extraction Ready

**Date**: 2026-01-11
**Status**: ✅ **Ready for Auto-Extraction**

---

## Current State

### Database:
- ✅ **Entities**: 2 (duloxetine, fibromyalgia) - Seeds for extraction
- ✅ **Sources**: 13 (10 from Smart Discovery, ready to extract)
- ⏭️ **Relations**: 0 (will be created during extraction)

### Configuration:
- ✅ **OpenAI API Key**: Added to backend/.env
- ✅ **Model**: gpt-4o-mini
- ✅ **Backend**: All code ready
- ✅ **Frontend**: Build successful

---

## Why Only 2 Entities?

This is **correct and expected**! Here's the workflow:

### Smart Discovery Phase ✅ (COMPLETE)
- **Input**: 2 seed entities (duloxetine, fibromyalgia)
- **Process**: Search PubMed for "Duloxetine AND Fibromyalgia"
- **Output**: 10 scientific sources (articles)
- **Does NOT create entities** - only imports sources

### Auto-Extraction Phase ⏭️ (NEXT)
- **Input**: 10 sources with full text
- **Process**: LLM reads each article and extracts:
  - Entities mentioned (drugs, symptoms, conditions)
  - Relations between entities (treats, causes, prevents)
- **Output**: 40-60 new entities + 60-100 relations
- **THIS creates the bulk of entities!**

---

## What Will Be Created During Extraction

### From 10 Sources, LLM Will Extract:

**Entities** (~40-60 total):
- duloxetine (link to existing ✓)
- fibromyalgia (link to existing ✓)
- chronic-pain (new)
- nausea (new, side effect)
- fatigue (new, symptom)
- depression (new, comorbidity)
- anxiety (new, comorbidity)
- sleep-disturbance (new)
- pregabalin (new, alternative treatment)
- milnacipran (new, alternative treatment)
- serotonin (new, mechanism)
- norepinephrine (new, mechanism)
- alexithymia (new, mentioned in RCT)
- cognitive-impairment (new)
- pain-relief (new, outcome)
- ... +25-40 more entities

**Relations** (~60-100 total):
- duloxetine → treats → fibromyalgia (from multiple sources)
- duloxetine → treats → chronic-pain
- duloxetine → treats → depression
- duloxetine → causes → nausea (side effect)
- duloxetine → mechanism → serotonin
- duloxetine → mechanism → norepinephrine
- fibromyalgia → has-symptom → chronic-pain
- fibromyalgia → has-symptom → fatigue
- fibromyalgia → has-symptom → sleep-disturbance
- pregabalin → treats → fibromyalgia (comparison)
- ... +50-90 more relations

---

## How to Run Auto-Extraction

### Option 1: Via Docker (Recommended)

```bash
# 1. Start environment
docker-compose up -d

# 2. Access UI
http://localhost:80

# 3. For each of 10 sources:
   - Navigate to /sources
   - Click source (with "smart_discovery" tag)
   - Click "🤖 Auto-Extract Knowledge from URL"
   - Wait ~15-20 seconds (LLM processing)
   - Review extracted entities and relations
   - Click "Quick Save" or "Save to Graph"
   
# 4. Repeat 10 times (~4 minutes total)

# 5. Result:
   ✅ 40-60 entities created
   ✅ 60-100 relations created
   ✅ Complete knowledge graph for Duloxetine ↔ Fibromyalgia
```

### Option 2: Via Script (Requires Python Environment)

```bash
cd backend

# Ensure dependencies installed
pip install openai asyncio python-dotenv

# Run extraction script
python run_auto_extraction.py

# This will:
# - Extract from first source (test)
# - Create ~10 entities
# - Create ~8 relations
# - Show statistics
# - Can be extended to process all 10 sources
```

---

## Expected Results After Extraction

### Database State:

**Before Extraction**:
```
Entities: 2
Sources: 13
Relations: 0
```

**After Extraction** (all 10 sources):
```
Entities: 40-60  ← +38-58 new!
Sources: 13  ← unchanged
Relations: 60-100  ← +60-100 new!
```

### Knowledge Graph Structure:

```
duloxetine (central node)
  ├─ treats → fibromyalgia [8 sources, confidence 90%]
  ├─ treats → chronic-pain [6 sources, confidence 85%]
  ├─ treats → depression [5 sources, confidence 80%]
  ├─ causes → nausea [4 sources, confidence 70%]
  ├─ causes → fatigue [3 sources, confidence 60%]
  ├─ mechanism → serotonin [6 sources]
  ├─ mechanism → norepinephrine [6 sources]
  └─ interacts-with → pregabalin [2 sources]

fibromyalgia (central node)
  ├─ treated-by ← duloxetine [inferred, 8 sources]
  ├─ treated-by ← pregabalin [4 sources]
  ├─ treated-by ← milnacipran [3 sources]
  ├─ has-symptom → chronic-pain [7 sources]
  ├─ has-symptom → fatigue [6 sources]
  ├─ has-symptom → sleep-disturbance [5 sources]
  └─ has-symptom → cognitive-impairment [3 sources]
```

### Inference Calculations:

Once relations are created, system automatically computes:

**duloxetine as treatment for fibromyalgia**:
- Score: 0.7-0.8 (positive, strong)
- Coverage: 8.0 (8 sources)
- Confidence: 92% (high coverage)
- Disagreement: <10% (strong consensus)
- Evidence: 1 RCT + 1 case-control + 6 observational

---

## Performance Estimates

### Single Source Extraction:
- Fetch document: 2s
- LLM extraction: 15s
- Entity linking: 1s
- Create entities: 2s
- Create relations: 2s
**Total**: ~22 seconds per source

### Batch (10 Sources):
- Sequential: 10 × 22s = **3 minutes 40 seconds**
- **Entities created**: 38-58
- **Relations created**: 60-100

---

## To Execute Now

### Quick Test (1 source):

```bash
cd /home/thibaut/code/hyphagraph/backend
python run_auto_extraction.py
```

Expected output:
- ✅ OpenAI API key detected
- ✅ Document fetched from PubMed
- ✅ LLM extraction (~15s)
- ✅ 8-12 entities extracted
- ✅ 6-10 relations extracted
- ✅ Entities created/linked
- ✅ Relations saved to database

### Full Extraction (All 10 sources):

Would require extending the script to loop through all sources, or using the UI to click "Auto-Extract" 10 times.

---

## Status

- ✅ OpenAI API key configured
- ✅ Smart Discovery complete (10 sources)
- ✅ Entities ready (duloxetine, fibromyalgia)
- ✅ Scripts ready
- ⏭️ **Ready to execute extraction**

**The system is primed and ready for knowledge graph generation!** 🚀
