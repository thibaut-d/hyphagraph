// @vitest-environment node
/**
 * Pact consumer contract tests — Extraction API (JSON-only endpoints).
 *
 * Covers: saveExtraction, extractFromDocument response shape.
 * Excluded from pact: uploadDocument / uploadAndExtract (multipart/form-data).
 *
 * Note: extractFromDocument / extractFromUrl require a live LLM service for
 * provider verification. The consumer interactions below pin the response
 * shape so frontend type drift is caught without needing the LLM pipeline.
 */
import path from 'path'
import { PactV4, MatchersV3 } from '@pact-foundation/pact'

const { like, eachLike, nullValue } = MatchersV3

const PACT_DIR = path.resolve(__dirname, '../../../../../pacts')
const SOURCE_ID = '223e4567-e89b-42d3-a456-426614174000'

const provider = new PactV4({
  consumer: 'hyphagraph-frontend',
  provider: 'hyphagraph-backend',
  dir: PACT_DIR,
  logLevel: 'error',
})

describe('Extraction API — consumer contract', () => {
  it('POST /api/sources/:id/extract-from-document returns DocumentExtractionPreview with review metadata', () =>
    provider
      .addInteraction()
      .given(`source with id ${SOURCE_ID} exists`)
      .uponReceiving(`an authenticated request to extract from document for source ${SOURCE_ID}`)
      .withRequest('POST', `/api/sources/${SOURCE_ID}/extract-from-document`, (builder) => {
        builder.headers({ Authorization: like('Bearer token') })
      })
      .willRespondWith(200, (builder) => {
        builder.jsonBody(
          like({
            source_id: like(SOURCE_ID),
            entities: like([]),
            relations: like([]),
            entity_count: like(0),
            relation_count: like(0),
            link_suggestions: like([]),
            needs_review_count: like(0),
            auto_verified_count: like(0),
            avg_validation_score: like(0.9),
          })
        )
      })
      .executeTest(async (mockServer) => {
        const res = await fetch(`${mockServer.url}/api/sources/${SOURCE_ID}/extract-from-document`, {
          method: 'POST',
          headers: { Authorization: 'Bearer test-token' },
        })
        const data = await res.json()
        expect(res.status).toBe(200)
        expect(data).toHaveProperty('source_id')
        expect(data).toHaveProperty('entities')
        expect(data).toHaveProperty('relations')
        expect(data).toHaveProperty('entity_count')
        expect(data).toHaveProperty('relation_count')
        expect(data).toHaveProperty('link_suggestions')
        expect(data).toHaveProperty('needs_review_count')
        expect(data).toHaveProperty('auto_verified_count')
        expect(data).toHaveProperty('avg_validation_score')
      }))

  it('POST /api/sources/:id/save-extraction saves approved extraction to graph', () =>
    provider
      .addInteraction()
      .given(`source with id ${SOURCE_ID} exists`)
      .uponReceiving(`an authenticated request to save extraction for source ${SOURCE_ID}`)
      .withRequest('POST', `/api/sources/${SOURCE_ID}/save-extraction`, (builder) => {
        builder
          .headers({ 'Content-Type': 'application/json', Authorization: like('Bearer token') })
          .jsonBody(
            like({
              entities_to_create: [],
              entity_links: {},
              relations_to_create: [],
            })
          )
      })
      .willRespondWith(200, (builder) => {
        builder.jsonBody(
          like({
            entities_created: like(0),
            entities_linked: like(0),
            relations_created: like(0),
            created_entity_ids: like([]),
            created_relation_ids: like([]),
            warnings: like([]),
            skipped_relations: like([]),
          })
        )
      })
      .executeTest(async (mockServer) => {
        const res = await fetch(`${mockServer.url}/api/sources/${SOURCE_ID}/save-extraction`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Authorization: 'Bearer test-token' },
          body: JSON.stringify({
            entities_to_create: [],
            entity_links: {},
            relations_to_create: [],
          }),
        })
        const data = await res.json()
        expect(res.status).toBe(200)
        expect(data).toHaveProperty('entities_created')
        expect(data).toHaveProperty('entities_linked')
        expect(data).toHaveProperty('relations_created')
        expect(data).toHaveProperty('created_entity_ids')
        expect(Array.isArray(data.created_entity_ids)).toBe(true)
      }))
})
