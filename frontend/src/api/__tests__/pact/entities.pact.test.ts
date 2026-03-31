// @vitest-environment node
/**
 * Pact consumer contract tests — Entities API.
 *
 * Defines what the frontend expects from the backend API.
 * Running these tests generates a pact file that the backend verifies.
 *
 * Generate pacts:
 *   npm run test:pact
 *
 * Output: <project-root>/pacts/hyphagraph-frontend-hyphagraph-backend.json
 */
import path from 'path'
import { PactV4, MatchersV3 } from '@pact-foundation/pact'

const { like, eachLike } = MatchersV3

const PACT_DIR = path.resolve(__dirname, '../../../../../pacts')

const ENTITY_ID = '123e4567-e89b-42d3-a456-426614174000'
const CATEGORY_ID = '123e4567-e89b-42d3-a456-426614174001'

const provider = new PactV4({
  consumer: 'hyphagraph-frontend',
  provider: 'hyphagraph-backend',
  dir: PACT_DIR,
  logLevel: 'error',
})

describe('Entities API — consumer contract', () => {
  it('GET /api/entities returns a paginated entity list', () =>
    provider
      .addInteraction()
      .given('some entities exist')
      .uponReceiving('a request to list all entities')
      .withRequest('GET', '/api/entities')
      .willRespondWith(200, (builder) => {
        builder.jsonBody(
          like({
            items: eachLike({
              id: like(ENTITY_ID),
              slug: like('aspirin'),
              created_at: like('2024-01-01T00:00:00'),
              summary: like(null),
              ui_category_id: like(null),
            }),
            total: like(1),
            limit: like(50),
            offset: like(0),
          })
        )
      })
      .executeTest(async (mockServer) => {
        const res = await fetch(`${mockServer.url}/api/entities`)
        const data = await res.json()
        expect(res.status).toBe(200)
        expect(data).toHaveProperty('items')
        expect(data).toHaveProperty('total')
        expect(data).toHaveProperty('limit')
        expect(data).toHaveProperty('offset')
        expect(Array.isArray(data.items)).toBe(true)
      }))

  it('GET /api/entities/:id returns a single entity', () =>
    provider
      .addInteraction()
      .given(`entity with id ${ENTITY_ID} exists`)
      .uponReceiving(`a request for entity ${ENTITY_ID}`)
      .withRequest('GET', `/api/entities/${ENTITY_ID}`)
      .willRespondWith(200, (builder) => {
        builder.jsonBody(
          like({
            id: like(ENTITY_ID),
            slug: like('aspirin'),
            created_at: like('2024-01-01T00:00:00'),
            updated_at: like('2024-01-01T00:00:00'),
            summary: like(null),
            ui_category_id: like(null),
            created_with_llm: like(null),
            created_by_user_id: like(null),
            status: like('confirmed'),
            llm_review_status: like(null),
          })
        )
      })
      .executeTest(async (mockServer) => {
        const res = await fetch(`${mockServer.url}/api/entities/${ENTITY_ID}`)
        const data = await res.json()
        expect(res.status).toBe(200)
        expect(data).toHaveProperty('id')
        expect(data).toHaveProperty('slug')
        expect(data).toHaveProperty('created_at')
        expect(data).toHaveProperty('updated_at')
        expect(data).toHaveProperty('status')
      }))

  it('GET /api/entities/filter-options returns filter option lists', () =>
    provider
      .addInteraction()
      .given('some UI categories exist')
      .uponReceiving('a request for entity filter options')
      .withRequest('GET', '/api/entities/filter-options')
      .willRespondWith(200, (builder) => {
        builder.jsonBody(
          like({
            ui_categories: eachLike({
              id: like(CATEGORY_ID),
              label: like({ en: 'Drug' }),
            }),
          })
        )
      })
      .executeTest(async (mockServer) => {
        const res = await fetch(`${mockServer.url}/api/entities/filter-options`)
        const data = await res.json()
        expect(res.status).toBe(200)
        expect(data).toHaveProperty('ui_categories')
        expect(Array.isArray(data.ui_categories)).toBe(true)
      }))

  it('POST /api/entities creates an entity when authenticated', () =>
    provider
      .addInteraction()
      .given('user is authenticated')
      .uponReceiving('an authenticated request to create an entity')
      .withRequest('POST', '/api/entities', (builder) => {
        builder
          .headers({
            'Content-Type': 'application/json',
            Authorization: like('Bearer token'),
          })
          .jsonBody(like({ slug: 'new-entity' }))
      })
      .willRespondWith(201, (builder) => {
        builder.jsonBody(
          like({
            id: like(ENTITY_ID),
            slug: like('new-entity'),
            created_at: like('2024-01-01T00:00:00'),
            summary: like(null),
            ui_category_id: like(null),
          })
        )
      })
      .executeTest(async (mockServer) => {
        const res = await fetch(`${mockServer.url}/api/entities`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: 'Bearer test-token',
          },
          body: JSON.stringify({ slug: 'new-entity' }),
        })
        const data = await res.json()
        expect(res.status).toBe(201)
        expect(data).toHaveProperty('id')
        expect(data).toHaveProperty('slug')
        expect(data).toHaveProperty('created_at')
      }))
})
