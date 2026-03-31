// @vitest-environment node
/**
 * Pact consumer contract tests — Revision Review API.
 * Covers: getDraftRevisionCounts, listDraftRevisions.
 *
 * Pins the wire shapes so backend schema changes cannot silently break
 * the review-queue badge or the queue item list.
 */
import path from 'path'
import { PactV4, MatchersV3 } from '@pact-foundation/pact'

const { like, eachLike, nullValue } = MatchersV3

const PACT_DIR = path.resolve(__dirname, '../../../../../pacts')

const provider = new PactV4({
  consumer: 'hyphagraph-frontend',
  provider: 'hyphagraph-backend',
  dir: PACT_DIR,
  logLevel: 'error',
})

describe('Revision Review API — consumer contract', () => {
  it('GET /api/review/revisions/counts returns entity/relation/source/total counts', () =>
    provider
      .addInteraction()
      .given('some draft revisions exist')
      .uponReceiving('a request for draft revision counts')
      .withRequest('GET', '/api/review/revisions/counts')
      .willRespondWith(200, (builder) => {
        builder.jsonBody(
          like({
            entity: like(2),
            relation: like(5),
            source: like(1),
            total: like(8),
          })
        )
      })
      .executeTest(async (mockServer) => {
        const res = await fetch(`${mockServer.url}/api/review/revisions/counts`)
        const data = await res.json()
        expect(res.status).toBe(200)
        expect(data).toHaveProperty('entity')
        expect(data).toHaveProperty('relation')
        expect(data).toHaveProperty('source')
        expect(data).toHaveProperty('total')
        expect(typeof data.entity).toBe('number')
        expect(typeof data.relation).toBe('number')
        expect(typeof data.source).toBe('number')
        expect(typeof data.total).toBe('number')
      }))

  it('GET /api/review/revisions returns paginated draft revisions with llm_review_status', () =>
    provider
      .addInteraction()
      .given('some draft revisions exist')
      .uponReceiving('a request to list draft revisions')
      .withRequest('GET', '/api/review/revisions')
      .willRespondWith(200, (builder) => {
        builder.jsonBody(
          like({
            items: eachLike({
              id: like('00000000-0000-0000-0000-000000000001'),
              revision_kind: like('entity'),
              parent_id: like('00000000-0000-0000-0000-000000000002'),
              created_with_llm: like('claude-sonnet-4-6'),
              created_by_user_id: nullValue(),
              created_at: like('2025-01-01T00:00:00Z'),
              slug: like('aspirin'),
              kind: nullValue(),
              title: nullValue(),
              status: like('draft'),
              llm_review_status: nullValue(),
            }),
            total: like(3),
            page: like(1),
            page_size: like(20),
            has_more: like(false),
          })
        )
      })
      .executeTest(async (mockServer) => {
        const res = await fetch(`${mockServer.url}/api/review/revisions`)
        const data = await res.json()
        expect(res.status).toBe(200)
        expect(data).toHaveProperty('items')
        expect(Array.isArray(data.items)).toBe(true)
        const item = data.items[0]
        expect(item).toHaveProperty('id')
        expect(item).toHaveProperty('revision_kind')
        expect(item).toHaveProperty('parent_id')
        expect(item).toHaveProperty('status')
        expect(item).toHaveProperty('llm_review_status')
        expect(data).toHaveProperty('total')
        expect(data).toHaveProperty('page')
        expect(data).toHaveProperty('page_size')
        expect(data).toHaveProperty('has_more')
      }))
})
