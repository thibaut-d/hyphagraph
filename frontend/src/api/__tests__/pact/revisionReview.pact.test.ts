// @vitest-environment node
/**
 * Pact consumer contract tests — Revision Review API.
 * Covers: getDraftRevisionCounts.
 *
 * Pins the exact wire shape of GET /api/review/revisions/counts so that
 * backend schema changes cannot silently break the review-queue badge.
 */
import path from 'path'
import { PactV4, MatchersV3 } from '@pact-foundation/pact'

const { like } = MatchersV3

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
})
