# Knowledge Extraction UI

## Overview

The Hyphagraph frontend now includes a comprehensive UI for knowledge extraction from documents using AI. This allows users to upload PDF or text documents, automatically extract entities and relations, review and approve suggestions, and save them to the knowledge graph.

## Features

### 1. Document Upload & Extraction

- **Location**: Source Detail View (`/sources/{id}`)
- **Supported formats**: PDF (.pdf), Plain Text (.txt)
- **File size limit**: 10 MB
- **Text length limit**: 50,000 characters

### 2. Extraction Preview

After uploading a document, the system:

1. **Extracts text** from the document
2. **Identifies entities** (drugs, diseases, symptoms, treatments, etc.)
3. **Identifies relations** between entities (treats, causes, prevents, etc.)
4. **Finds matches** to existing entities in the knowledge graph
5. **Suggests links** based on exact slug matches or synonyms

### 3. Entity Linking

For each extracted entity, users can choose:

- **Create New**: Add as a new entity to the graph
- **Link to Existing**: Connect to an existing entity (when matches are found)
- **Skip**: Don't include this entity

The UI shows:
- Entity confidence levels (high/medium/low)
- Entity categories (drug, disease, symptom, etc.)
- Source text span where the entity was mentioned
- Match suggestions with confidence scores

### 4. Relation Selection

Users can review and select which relations to save:

- View subject → relation type → object
- See confidence levels
- Review source quotes
- See additional context (dosage, population, etc.)

### 5. Save to Graph

Once approved, the system:
- Creates new entities or links to existing ones
- Creates relations using the entity mappings
- Associates all items with the source
- Provides summary of saved items

## Components

### Frontend Components

1. **`ExtractionPreview`** - Main preview component with stats and save actions
2. **`EntityLinkingSuggestions`** - Displays entities with linking options
3. **`ExtractedRelationsList`** - Shows relations with selection checkboxes
4. **`ClaimsList`** - (Future) Displays extracted claims with evidence strength

### API Client Functions

Located in `src/api/extraction.ts`:

- `uploadDocument(sourceId, file)` - Upload document only
- `extractFromDocument(sourceId)` - Extract from previously uploaded document
- `uploadAndExtract(sourceId, file)` - Combined upload + extract (recommended)
- `saveExtraction(sourceId, request)` - Save user-approved data to graph

### TypeScript Types

Located in `src/types/extraction.ts`:

- `ExtractedEntity` - Entity with metadata
- `ExtractedRelation` - Relation between entities
- `ExtractedClaim` - Factual claim with evidence
- `EntityLinkMatch` - Matching suggestion
- `DocumentExtractionPreview` - Full preview response
- `SaveExtractionRequest` - Save request payload
- `SaveExtractionResult` - Save result summary

## Usage Flow

### Basic Workflow

1. Navigate to a source detail page
2. Click "Upload Document" in the Knowledge Extraction section
3. Select a PDF or TXT file
4. Wait for extraction (may take 10-60 seconds depending on document size)
5. Review extracted entities:
   - Exact matches are auto-selected for linking
   - Synonym matches show suggestions
   - New entities default to "Create New"
6. Review extracted relations:
   - All relations are selected by default
   - Uncheck any you don't want to save
7. Click "Save to Graph"
8. See success message with counts of created/linked items
9. Relations list refreshes to show new items

### Example Use Case

**Uploading a medical research paper:**

1. Upload "aspirin_study.pdf" to a source
2. System extracts entities:
   - "aspirin" (exact match found)
   - "myocardial-infarction" (synonym match: "heart-attack")
   - "cardiovascular-disease" (new entity)
3. System extracts relations:
   - aspirin → prevents → myocardial-infarction
   - aspirin → decreases_risk → cardiovascular-disease
4. User reviews and approves all
5. Graph is updated with 1 new entity, 2 linked entities, and 2 new relations

## Backend Integration

The UI integrates with these backend endpoints:

- `POST /api/sources/{id}/upload-document` - Upload document
- `POST /api/sources/{id}/extract-from-document` - Extract from document
- `POST /api/sources/{id}/upload-and-extract` - Combined operation
- `POST /api/sources/{id}/save-extraction` - Save to graph

## Configuration

### Environment Variables

- `VITE_API_URL` - Backend API URL (default: `http://localhost:8000`)

### Backend Requirements

- OpenAI API key configured (`OPENAI_API_KEY`)
- LLM model: `gpt-4o-mini` (configurable in backend settings)

## Future Enhancements

### Planned Features

1. **Claims Extraction** - Extract factual claims with evidence strength
2. **Batch Processing** - Upload multiple documents at once
3. **Extraction History** - View past extractions and re-extract
4. **Custom Prompts** - Allow users to customize extraction prompts
5. **Entity Disambiguation** - Better UI for resolving ambiguous matches
6. **Extraction Confidence Filtering** - Filter by confidence level
7. **Export/Import** - Export extraction results as JSON

### Potential Improvements

- Progressive loading for large documents
- Real-time extraction status updates
- Undo/redo for linking decisions
- Keyboard shortcuts for faster review
- Bulk actions (select all, deselect all, etc.)
- Search/filter within extraction results

## Troubleshooting

### Common Issues

**"LLM service not available"**
- Ensure `OPENAI_API_KEY` is set in backend environment
- Check backend logs for API errors

**"Failed to extract text from PDF"**
- Ensure PDF is not scanned image (OCR not supported)
- Check if PDF is encrypted or password-protected
- Verify file size is under 10 MB

**"No entities extracted"**
- Document may not contain biomedical entities
- Try a different document or adjust extraction prompts
- Check LLM logs for parsing errors

**Build errors**
- Run `npm install` in frontend directory
- Ensure all TypeScript types are properly imported
- Check for missing dependencies

## Development

### Running Locally

```bash
# Backend
cd backend
docker-compose up

# Frontend
cd frontend
npm install
npm run dev
```

### Testing

```bash
# Frontend build test
cd frontend
npm run build

# Backend API test
cd backend
python test_combined_endpoint.py
```

### File Structure

```
frontend/
├── src/
│   ├── api/
│   │   └── extraction.ts           # API client functions
│   ├── components/
│   │   ├── ExtractionPreview.tsx
│   │   ├── EntityLinkingSuggestions.tsx
│   │   ├── ExtractedRelationsList.tsx
│   │   └── ClaimsList.tsx
│   ├── types/
│   │   └── extraction.ts           # TypeScript types
│   └── views/
│       └── SourceDetailView.tsx    # Integrated upload UI
```

## License

Same as Hyphagraph project.
