// @vitest-environment node
/**
 * Pact consumer contract tests — Inferences API.
 * Covers: getInferenceForEntity, getInferenceDetailForEntity.
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

describe('Inferences API — consumer contract', () => {
  it('GET /api/inferences/entity/:id returns inference summary', () =>
    provider
      .addInteraction()
      .given(`entity with id ${ENTITY_ID} has inferences`)
      .uponReceiving(`an inference summary request for entity ${ENTITY_ID}`)
      .withRequest('GET', `/api/inferences/entity/${ENTITY_ID}`)
      .willRespondWith(200, (builder) => {
        builder.jsonBody(
          like({
            entity_id: like(ENTITY_ID),
            relations_by_kind: like({}),
            role_inferences: eachLike({
              role_type: like('drug'),
              score: like(0.8),
              coverage: like(1),
              confidence: like(0.7),
              disagreement: like(0.0),
            }),
          })
        )
      })
      .executeTest(async (mockServer) => {
        const res = await fetch(`${mockServer.url}/api/inferences/entity/${ENTITY_ID}`)
        const data = await res.json()
        expect(res.status).toBe(200)
        expect(data).toHaveProperty('entity_id')
        expect(data).toHaveProperty('relations_by_kind')
      }))

  it('GET /api/inferences/entity/:id/detail returns detailed inference', () =>
    provider
      .addInteraction()
      .given(`entity with id ${ENTITY_ID} has inferences`)
      .uponReceiving(`a detailed inference request for entity ${ENTITY_ID}`)
      .withRequest('GET', `/api/inferences/entity/${ENTITY_ID}/detail`)
      .willRespondWith(200, (builder) => {
        builder.jsonBody(
          like({
            entity_id: like(ENTITY_ID),
            relations_by_kind: like({}),
            stats: like({
              total_relations: like(1),
              unique_sources_count: like(1),
              average_confidence: like(0.8),
              confidence_count: like(1),
              high_confidence_count: like(1),
              low_confidence_count: like(0),
              contradiction_count: like(0),
              relation_type_count: like(1),
            }),
            relation_kind_summaries: eachLike({
              kind: like('treats'),
              relation_count: like(1),
              average_confidence: like(0.8),
              supporting_count: like(1),
              contradicting_count: like(0),
              neutral_count: like(0),
            }),
            evidence_items: like([]),
            disagreement_groups: like([]),
          })
        )
      })
      .executeTest(async (mockServer) => {
        const res = await fetch(`${mockServer.url}/api/inferences/entity/${ENTITY_ID}/detail`)
        const data = await res.json()
        expect(res.status).toBe(200)
        expect(data).toHaveProperty('entity_id')
        expect(data).toHaveProperty('stats')
        expect(data).toHaveProperty('relation_kind_summaries')
        expect(data).toHaveProperty('evidence_items')
      }))
})
