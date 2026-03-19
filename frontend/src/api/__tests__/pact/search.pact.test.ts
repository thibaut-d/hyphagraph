// @vitest-environment node
/**
 * Pact consumer contract tests — Search API.
 * Covers: search, getSuggestions.
 */
import path from 'path'
import { PactV4, MatchersV3 } from '@pact-foundation/pact'

const { like, eachLike } = MatchersV3

const PACT_DIR = path.resolve(__dirname, '../../../../../pacts')
const ENTITY_ID = '123e4567-e89b-42d3-a456-426614174000'

const provider = new PactV4({
  consumer: 'hyphagraph-frontend',
  provider: 'hyphagraph-backend',
  dir: PACT_DIR,
  logLevel: 'error',
})

describe('Search API — consumer contract', () => {
  it('POST /api/search returns search results', () =>
    provider
      .addInteraction()
      .given('some entities exist')
      .uponReceiving('a search request for aspirin')
      .withRequest('POST', '/api/search', (builder) => {
        builder.query({ query: 'aspirin' })
      })
      .willRespondWith(200, (builder) => {
        builder.jsonBody(
          like({
            query: like('aspirin'),
            results: eachLike({
              id: like(ENTITY_ID),
              type: like('entity'),
              title: like('aspirin'),
            }),
            total: like(1),
            limit: like(20),
            offset: like(0),
            entity_count: like(1),
            source_count: like(0),
            relation_count: like(0),
          })
        )
      })
      .executeTest(async (mockServer) => {
        const res = await fetch(`${mockServer.url}/api/search?query=aspirin`, {
          method: 'POST',
        })
        const data = await res.json()
        expect(res.status).toBe(200)
        expect(data).toHaveProperty('query')
        expect(data).toHaveProperty('results')
        expect(data).toHaveProperty('total')
        expect(Array.isArray(data.results)).toBe(true)
      }))

  it('POST /api/search/suggestions returns autocomplete suggestions', () =>
    provider
      .addInteraction()
      .given('some entities exist')
      .uponReceiving('a suggestion request for asp')
      .withRequest('POST', '/api/search/suggestions', (builder) => {
        builder.query({ query: 'asp' })
      })
      .willRespondWith(200, (builder) => {
        builder.jsonBody(
          like({
            query: like('asp'),
            suggestions: eachLike({
              id: like(ENTITY_ID),
              type: like('entity'),
              label: like('aspirin'),
            }),
          })
        )
      })
      .executeTest(async (mockServer) => {
        const res = await fetch(`${mockServer.url}/api/search/suggestions?query=asp`, {
          method: 'POST',
        })
        const data = await res.json()
        expect(res.status).toBe(200)
        expect(data).toHaveProperty('query')
        expect(data).toHaveProperty('suggestions')
        expect(Array.isArray(data.suggestions)).toBe(true)
      }))
})
