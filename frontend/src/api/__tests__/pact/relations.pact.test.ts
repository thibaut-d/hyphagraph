// @vitest-environment node
/**
 * Pact consumer contract tests — Relations API.
 * Covers: listRelationsBySource, getRelation, createRelation.
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

describe('Relations API — consumer contract', () => {
  it('GET /api/relations/by-source/:id returns relations for a source', () =>
    provider
      .addInteraction()
      .given(`relations exist for source ${SOURCE_ID}`)
      .uponReceiving(`a request to list relations for source ${SOURCE_ID}`)
      .withRequest('GET', `/api/relations/by-source/${SOURCE_ID}`)
      .willRespondWith(200, (builder) => {
        builder.jsonBody(
          eachLike({
            id: like(RELATION_ID),
            source_id: like(SOURCE_ID),
            kind: like('treats'),
            direction: like('positive'),
            confidence: like(0.8),
            roles: eachLike({
              entity_id: like(ENTITY_ID),
              role_type: like('drug'),
            }),
          })
        )
      })
      .executeTest(async (mockServer) => {
        const res = await fetch(`${mockServer.url}/api/relations/by-source/${SOURCE_ID}`)
        const data = await res.json()
        expect(res.status).toBe(200)
        expect(Array.isArray(data)).toBe(true)
        if (data.length > 0) {
          expect(data[0]).toHaveProperty('id')
          expect(data[0]).toHaveProperty('source_id')
          expect(data[0]).toHaveProperty('roles')
        }
      }))

  it('GET /api/relations/:id returns a single relation', () =>
    provider
      .addInteraction()
      .given(`relation with id ${RELATION_ID} exists`)
      .uponReceiving(`a request for relation ${RELATION_ID}`)
      .withRequest('GET', `/api/relations/${RELATION_ID}`)
      .willRespondWith(200, (builder) => {
        builder.jsonBody(
          like({
            id: like(RELATION_ID),
            source_id: like(SOURCE_ID),
            kind: like('treats'),
            direction: like('positive'),
            confidence: like(0.8),
            roles: eachLike({
              entity_id: like(ENTITY_ID),
              role_type: like('drug'),
            }),
          })
        )
      })
      .executeTest(async (mockServer) => {
        const res = await fetch(`${mockServer.url}/api/relations/${RELATION_ID}`)
        const data = await res.json()
        expect(res.status).toBe(200)
        expect(data).toHaveProperty('id')
        expect(data).toHaveProperty('source_id')
        expect(data).toHaveProperty('roles')
        expect(Array.isArray(data.roles)).toBe(true)
      }))

  it('POST /api/relations creates a relation when authenticated', () =>
    provider
      .addInteraction()
      .given('user is authenticated')
      .uponReceiving('an authenticated request to create a relation')
      .withRequest('POST', '/api/relations/', (builder) => {
        builder
          .headers({ 'Content-Type': 'application/json', Authorization: like('Bearer token') })
          .jsonBody(
            like({
              source_id: SOURCE_ID,
              kind: 'treats',
              direction: 'positive',
              confidence: 0.8,
              roles: [{ entity_id: ENTITY_ID, role_type: 'drug' }],
            })
          )
      })
      .willRespondWith(200, (builder) => {
        builder.jsonBody(
          like({
            id: like(RELATION_ID),
            source_id: like(SOURCE_ID),
            kind: like('treats'),
            roles: eachLike({ entity_id: like(ENTITY_ID), role_type: like('drug') }),
          })
        )
      })
      .executeTest(async (mockServer) => {
        const res = await fetch(`${mockServer.url}/api/relations/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Authorization: 'Bearer test-token' },
          body: JSON.stringify({
            source_id: SOURCE_ID,
            kind: 'treats',
            direction: 'positive',
            confidence: 0.8,
            roles: [{ entity_id: ENTITY_ID, role_type: 'drug' }],
          }),
        })
        const data = await res.json()
        expect(res.status).toBe(200)
        expect(data).toHaveProperty('id')
        expect(data).toHaveProperty('roles')
      }))
})
