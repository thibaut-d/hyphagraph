// @vitest-environment node
/**
 * Pact consumer contract tests — Explanations API.
 * Covers: getExplanation.
 */
import path from 'path'
import { PactV4, MatchersV3 } from '@pact-foundation/pact'

const { like, eachLike } = MatchersV3

const PACT_DIR = path.resolve(__dirname, '../../../../../pacts')
const ENTITY_ID = '123e4567-e89b-42d3-a456-426614174000'
const SOURCE_ID = '223e4567-e89b-42d3-a456-426614174000'
const RELATION_ID = '323e4567-e89b-42d3-a456-426614174000'

const provider = new PactV4({
  consumer: 'hyphagraph-frontend',
  provider: 'hyphagraph-backend',
  dir: PACT_DIR,
  logLevel: 'error',
})

describe('Explanations API — consumer contract', () => {
  it('GET /api/explain/inference/:entityId/:roleType returns an explanation', () =>
    provider
      .addInteraction()
      .given(`entity with id ${ENTITY_ID} has inferences`)
      .uponReceiving(`an explanation request for entity ${ENTITY_ID} role drug`)
      .withRequest('GET', `/api/explain/inference/${ENTITY_ID}/drug`)
      .willRespondWith(200, (builder) => {
        builder.jsonBody(
          like({
            entity_id: like(ENTITY_ID),
            role_type: like('drug'),
            score: like(0.8),
            confidence: like(0.7),
            disagreement: like(0.0),
            summary: like('Strong evidence supporting this role.'),
            confidence_factors: eachLike({
              factor: like('source_quality'),
              value: like(0.8),
              explanation: like('High-quality sources'),
            }),
            source_chain: eachLike({
              source_id: like(SOURCE_ID),
              source_title: like('Test Study'),
              source_kind: like('study'),
              source_url: like('https://example.com'),
              relation_id: like(RELATION_ID),
              relation_kind: like('treats'),
              relation_direction: like('positive'),
              relation_confidence: like(0.8),
              contribution_percentage: like(100.0),
            }),
          })
        )
      })
      .executeTest(async (mockServer) => {
        const res = await fetch(`${mockServer.url}/api/explain/inference/${ENTITY_ID}/drug`)
        const data = await res.json()
        expect(res.status).toBe(200)
        expect(data).toHaveProperty('entity_id')
        expect(data).toHaveProperty('role_type')
        expect(data).toHaveProperty('confidence')
        expect(data).toHaveProperty('source_chain')
        expect(Array.isArray(data.source_chain)).toBe(true)
      }))
})
