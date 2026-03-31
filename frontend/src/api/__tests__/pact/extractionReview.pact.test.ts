// @vitest-environment node
/**
 * Pact consumer contract tests — Extraction Review API.
 * Covers: listPendingExtractions, getReviewStats.
 */
import path from 'path'
import { PactV4, MatchersV3 } from '@pact-foundation/pact'

const { like, eachLike } = MatchersV3

const PACT_DIR = path.resolve(__dirname, '../../../../../pacts')
const EXTRACTION_ID = '423e4567-e89b-42d3-a456-426614174000'
const SOURCE_ID = '223e4567-e89b-42d3-a456-426614174000'

const provider = new PactV4({
  consumer: 'hyphagraph-frontend',
  provider: 'hyphagraph-backend',
  dir: PACT_DIR,
  logLevel: 'error',
})

describe('Extraction Review API — consumer contract', () => {
  it('GET /api/extraction-review/stats returns review statistics', () =>
    provider
      .addInteraction()
      .given('some staged extractions exist')
      .uponReceiving('a request for extraction review stats')
      .withRequest('GET', '/api/extraction-review/stats')
      .willRespondWith(200, (builder) => {
        builder.jsonBody(
          like({
            total_pending: like(1),
            total_approved: like(0),
            total_rejected: like(0),
            total_auto_verified: like(0),
            pending_entities: like(1),
            pending_relations: like(0),
            pending_claims: like(0),
            avg_validation_score: like(0.9),
            high_confidence_count: like(0),
            flagged_count: like(0),
          })
        )
      })
      .executeTest(async (mockServer) => {
        const res = await fetch(`${mockServer.url}/api/extraction-review/stats`)
        const data = await res.json()
        expect(res.status).toBe(200)
        expect(data).toHaveProperty('total_pending')
        expect(data).toHaveProperty('total_approved')
        expect(data).toHaveProperty('avg_validation_score')
      }))

  it('GET /api/extraction-review/pending returns pending extractions', () =>
    provider
      .addInteraction()
      .given('some staged extractions exist')
      .uponReceiving('a request to list pending extractions')
      .withRequest('GET', '/api/extraction-review/pending')
      .willRespondWith(200, (builder) => {
        builder.jsonBody(
          like({
            extractions: eachLike({
              id: like(EXTRACTION_ID),
              extraction_type: like('entity'),
              status: like('pending'),
              source_id: like(SOURCE_ID),
              validation_score: like(0.9),
              confidence_adjustment: like(0.0),
              validation_flags: like([]),
              auto_commit_eligible: like(false),
              auto_approved: like(false),
              created_at: like('2024-01-01T00:00:00'),
              extraction_data: like({ slug: 'aspirin' }),
            }),
            total: like(1),
            page: like(1),
            page_size: like(20),
            has_more: like(false),
          })
        )
      })
      .executeTest(async (mockServer) => {
        const res = await fetch(`${mockServer.url}/api/extraction-review/pending`)
        const data = await res.json()
        expect(res.status).toBe(200)
        expect(data).toHaveProperty('extractions')
        expect(data).toHaveProperty('total')
        expect(data).toHaveProperty('page')
        expect(Array.isArray(data.extractions)).toBe(true)
      }))
})
