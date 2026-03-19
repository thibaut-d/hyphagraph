// @vitest-environment node
/**
 * Pact consumer contract tests — Extraction API (JSON-only endpoints).
 *
 * Only covers saveExtraction (POST save-extraction) because:
 * - extractFromDocument / extractFromUrl require LLM service (unavailable in tests)
 * - uploadDocument / uploadAndExtract are multipart/form-data (not pact-compatible)
 */
import path from 'path'
import { PactV4, MatchersV3 } from '@pact-foundation/pact'

const { like, eachLike } = MatchersV3

const PACT_DIR = path.resolve(__dirname, '../../../../../pacts')
const SOURCE_ID = '223e4567-e89b-42d3-a456-426614174000'

const provider = new PactV4({
  consumer: 'hyphagraph-frontend',
  provider: 'hyphagraph-backend',
  dir: PACT_DIR,
  logLevel: 'error',
})

describe('Extraction API — consumer contract', () => {
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
