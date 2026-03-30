// @vitest-environment node
/**
 * Pact consumer contract tests — Auth API.
 * Covers: register, getMe (authenticated).
 */
import path from 'path'
import { PactV4, MatchersV3 } from '@pact-foundation/pact'

const { like } = MatchersV3

const PACT_DIR = path.resolve(__dirname, '../../../../../pacts')
const USER_ID = '623e4567-e89b-42d3-a456-426614174000'

const provider = new PactV4({
  consumer: 'hyphagraph-frontend',
  provider: 'hyphagraph-backend',
  dir: PACT_DIR,
  logLevel: 'error',
})

describe('Auth API — consumer contract', () => {
  it('POST /api/auth/register creates a new user', () =>
    provider
      .addInteraction()
      .given('no user with email newuser@example.com exists')
      .uponReceiving('a registration request')
      .withRequest('POST', '/api/auth/register', (builder) => {
        builder
          .headers({ 'Content-Type': 'application/json' })
          .jsonBody(like({ email: 'newuser@example.com', password: 'securepass123', password_confirmation: 'securepass123' }))
      })
      .willRespondWith(201, (builder) => {
        builder.jsonBody(
          like({
            id: like(USER_ID),
            email: like('newuser@example.com'),
            is_active: like(true),
            is_superuser: like(false),
            is_verified: like(false),
            created_at: like('2024-01-01T00:00:00'),
          })
        )
      })
      .executeTest(async (mockServer) => {
        const res = await fetch(`${mockServer.url}/api/auth/register`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email: 'newuser@example.com', password: 'securepass123', password_confirmation: 'securepass123' }),
        })
        const data = await res.json()
        expect(res.status).toBe(201)
        expect(data).toHaveProperty('id')
        expect(data).toHaveProperty('email')
        expect(data).toHaveProperty('is_active')
        expect(data).toHaveProperty('created_at')
      }))

  it('GET /api/auth/me returns the current user', () =>
    provider
      .addInteraction()
      .given('user is authenticated')
      .uponReceiving('a request for current user profile')
      .withRequest('GET', '/api/auth/me', (builder) => {
        builder.headers({ Authorization: like('Bearer token') })
      })
      .willRespondWith(200, (builder) => {
        builder.jsonBody(
          like({
            id: like(USER_ID),
            email: like('pact@example.com'),
            is_active: like(true),
            is_superuser: like(false),
            is_verified: like(true),
            created_at: like('2024-01-01T00:00:00'),
          })
        )
      })
      .executeTest(async (mockServer) => {
        const res = await fetch(`${mockServer.url}/api/auth/me`, {
          headers: { Authorization: 'Bearer test-token' },
        })
        const data = await res.json()
        expect(res.status).toBe(200)
        expect(data).toHaveProperty('id')
        expect(data).toHaveProperty('email')
        expect(data).toHaveProperty('is_active')
      }))
})
