// @vitest-environment node
/**
 * Pact consumer contract tests — Entity Terms API.
 * Covers: listEntityTerms, createEntityTerm.
 */
import path from 'path'
import { PactV4, MatchersV3 } from '@pact-foundation/pact'

const { like, eachLike } = MatchersV3

const PACT_DIR = path.resolve(__dirname, '../../../../../pacts')
const ENTITY_ID = '123e4567-e89b-42d3-a456-426614174000'
const TERM_ID = '523e4567-e89b-42d3-a456-426614174000'

const provider = new PactV4({
  consumer: 'hyphagraph-frontend',
  provider: 'hyphagraph-backend',
  dir: PACT_DIR,
  logLevel: 'error',
})

describe('Entity Terms API — consumer contract', () => {
  it('GET /api/entities/:id/terms returns terms for an entity', () =>
    provider
      .addInteraction()
      .given(`entity with id ${ENTITY_ID} has terms`)
      .uponReceiving(`a request to list terms for entity ${ENTITY_ID}`)
      .withRequest('GET', `/api/entities/${ENTITY_ID}/terms`)
      .willRespondWith(200, (builder) => {
        builder.jsonBody(
          eachLike({
            id: like(TERM_ID),
            entity_id: like(ENTITY_ID),
            term: like('Aspirin'),
            language: like('en'),
            display_order: like(0),
            created_at: like('2024-01-01T00:00:00'),
          })
        )
      })
      .executeTest(async (mockServer) => {
        const res = await fetch(`${mockServer.url}/api/entities/${ENTITY_ID}/terms`)
        const data = await res.json()
        expect(res.status).toBe(200)
        expect(Array.isArray(data)).toBe(true)
        if (data.length > 0) {
          expect(data[0]).toHaveProperty('id')
          expect(data[0]).toHaveProperty('entity_id')
          expect(data[0]).toHaveProperty('term')
        }
      }))

  it('POST /api/entities/:id/terms creates a term when authenticated', () =>
    provider
      .addInteraction()
      .given('user is authenticated')
      .uponReceiving(`an authenticated request to create a term for entity ${ENTITY_ID}`)
      .withRequest('POST', `/api/entities/${ENTITY_ID}/terms`, (builder) => {
        builder
          .headers({ 'Content-Type': 'application/json', Authorization: like('Bearer token') })
          .jsonBody(like({ term: 'Aspirin', language: 'en', display_order: 0 }))
      })
      .willRespondWith(201, (builder) => {
        builder.jsonBody(
          like({
            id: like(TERM_ID),
            entity_id: like(ENTITY_ID),
            term: like('Aspirin'),
            language: like('en'),
            display_order: like(0),
            created_at: like('2024-01-01T00:00:00'),
          })
        )
      })
      .executeTest(async (mockServer) => {
        const res = await fetch(`${mockServer.url}/api/entities/${ENTITY_ID}/terms`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Authorization: 'Bearer test-token' },
          body: JSON.stringify({ term: 'Aspirin', language: 'en', display_order: 0 }),
        })
        const data = await res.json()
        expect(res.status).toBe(201)
        expect(data).toHaveProperty('id')
        expect(data).toHaveProperty('entity_id')
        expect(data).toHaveProperty('term')
      }))
})
