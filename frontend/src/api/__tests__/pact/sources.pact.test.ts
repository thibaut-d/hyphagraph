// @vitest-environment node
/**
 * Pact consumer contract tests — Sources API.
 * Covers: listSources, getSource, createSource, getSourceFilterOptions.
 */
import path from 'path'
import { PactV4, MatchersV3 } from '@pact-foundation/pact'

const { like, eachLike } = MatchersV3

const PACT_DIR = path.resolve(__dirname, '../../../../../pacts')
const SOURCE_ID = '223e4567-e89b-42d3-a456-426614174000'
const USER_ID = '223e4567-e89b-42d3-a456-426614174099'

const provider = new PactV4({
  consumer: 'hyphagraph-frontend',
  provider: 'hyphagraph-backend',
  dir: PACT_DIR,
  logLevel: 'error',
})

describe('Sources API — consumer contract', () => {
  it('GET /api/sources returns a paginated source list', () =>
    provider
      .addInteraction()
      .given('some sources exist')
      .uponReceiving('a request to list all sources')
      .withRequest('GET', '/api/sources')
      .willRespondWith(200, (builder) => {
        builder.jsonBody(
          like({
            items: eachLike({
              id: like(SOURCE_ID),
              kind: like('study'),
              title: like('Test Study'),
              created_at: like('2024-01-01T00:00:00'),
              authors: eachLike('Author One'),
              year: like(2024),
              origin: like('PubMed'),
              url: like('https://example.com'),
              trust_level: like(0.8),
              summary: like({ en: 'Trial summary' }),
              source_metadata: like({ doi: '10.1000/test' }),
              created_with_llm: like(null),
              created_by_user_id: like(USER_ID),
              status: like('confirmed'),
              llm_review_status: like(null),
              document_format: like(null),
              document_file_name: like(null),
              document_extracted_at: like(null),
            }),
            total: like(1),
            limit: like(50),
            offset: like(0),
          })
        )
      })
      .executeTest(async (mockServer) => {
        const res = await fetch(`${mockServer.url}/api/sources`)
        const data = await res.json()
        expect(res.status).toBe(200)
        expect(data).toHaveProperty('items')
        expect(data).toHaveProperty('total')
        expect(Array.isArray(data.items)).toBe(true)
      }))

  it('GET /api/sources/:id returns a single source', () =>
    provider
      .addInteraction()
      .given(`source with id ${SOURCE_ID} exists`)
      .uponReceiving(`a request for source ${SOURCE_ID}`)
      .withRequest('GET', `/api/sources/${SOURCE_ID}`)
      .willRespondWith(200, (builder) => {
        builder.jsonBody(
          like({
            id: like(SOURCE_ID),
            kind: like('study'),
            title: like('Test Study'),
            authors: eachLike('Author One'),
            year: like(2024),
            origin: like('PubMed'),
            url: like('https://example.com'),
            trust_level: like(0.8),
            created_at: like('2024-01-01T00:00:00'),
            summary: like({ en: 'Trial summary' }),
            source_metadata: like({ doi: '10.1000/test' }),
            created_with_llm: like(null),
            created_by_user_id: like(null),
            status: like('confirmed'),
            llm_review_status: like(null),
            document_format: like(null),
            document_file_name: like(null),
            document_extracted_at: like(null),
          })
        )
      })
      .executeTest(async (mockServer) => {
        const res = await fetch(`${mockServer.url}/api/sources/${SOURCE_ID}`)
        const data = await res.json()
        expect(res.status).toBe(200)
        expect(data).toHaveProperty('id')
        expect(data).toHaveProperty('kind')
        expect(data).toHaveProperty('title')
        expect(data).toHaveProperty('status')
        expect(data).toHaveProperty('created_at')
      }))

  it('POST /api/sources creates a source when authenticated', () =>
    provider
      .addInteraction()
      .given('user is authenticated')
      .uponReceiving('an authenticated request to create a source')
      .withRequest('POST', '/api/sources/', (builder) => {
        builder
          .headers({ 'Content-Type': 'application/json', Authorization: like('Bearer token') })
          .jsonBody(
            like({ kind: 'study', title: 'New Study', url: 'https://example.com/new', trust_level: 0.8 })
          )
      })
      .willRespondWith(200, (builder) => {
        builder.jsonBody(
          like({
            id: like(SOURCE_ID),
            kind: like('study'),
            title: like('New Study'),
            authors: like(null),
            year: like(null),
            origin: like(null),
            url: like('https://example.com/new'),
            trust_level: like(0.8),
            created_at: like('2024-01-01T00:00:00'),
            summary: like(null),
            source_metadata: like(null),
            created_with_llm: like(null),
            created_by_user_id: like(null),
            status: like('confirmed'),
            llm_review_status: like(null),
            document_format: like(null),
            document_file_name: like(null),
            document_extracted_at: like(null),
          })
        )
      })
      .executeTest(async (mockServer) => {
        const res = await fetch(`${mockServer.url}/api/sources/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Authorization: 'Bearer test-token' },
          body: JSON.stringify({ kind: 'study', title: 'New Study', url: 'https://example.com/new', trust_level: 0.8 }),
        })
        const data = await res.json()
        expect(res.status).toBe(200)
        expect(data).toHaveProperty('id')
        expect(data).toHaveProperty('kind')
        expect(data).toHaveProperty('title')
      }))

  it('GET /api/sources/filter-options returns available filter values', () =>
    provider
      .addInteraction()
      .given('some sources exist')
      .uponReceiving('a request for source filter options')
      .withRequest('GET', '/api/sources/filter-options')
      .willRespondWith(200, (builder) => {
        builder.jsonBody(
          like({
            kinds: eachLike(like('study')),
            year_range: like([2000, 2024]),
            domains: eachLike(like('clinical')),
            roles: eachLike(like('pillar')),
          })
        )
      })
      .executeTest(async (mockServer) => {
        const res = await fetch(`${mockServer.url}/api/sources/filter-options`)
        const data = await res.json()
        expect(res.status).toBe(200)
        expect(data).toHaveProperty('kinds')
        expect(Array.isArray(data.kinds)).toBe(true)
      }))
})
