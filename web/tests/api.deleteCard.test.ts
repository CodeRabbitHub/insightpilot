// Tests for the new `deleteCard(id)` function from
// plans/briefs/2026-08-07-dashboard-card-delete-button.md.
//
// Runner: plain vitest-style tests (`describe`/`it`/`expect`/`vi` from the
// 'vitest' package), matching the precedent set by
// web/tests/api.fetchDashboard.test.ts. This repo has NO frontend test
// runner configured yet (confirmed via web/package.json: no test script,
// no vitest/jsdom devDependency) -- these cannot execute until one is
// added. Expected command once available: `cd web && npx vitest run`.
//
// Written from the brief alone, before `deleteCard` exists in
// web/src/api.ts. The brief's Constraints section names the exact
// contract to hold `deleteCard` to: `fetch` with `method: 'DELETE'`
// against `${API_BASE}/api/cards/{id}`, no request body, throwing an
// `Error` with the route + status on `!response.ok` (mirroring
// `fetchDashboard`'s existing throw shape), and resolving with nothing
// (`void`) on the real 204 empty-body success case -- explicitly without
// attempting to parse a JSON body from that 204 response.
import { afterEach, describe, expect, it, vi } from 'vitest'
import { deleteCard } from '../src/api'

function mockFetchOnce(response: { ok: boolean; status: number }) {
  const jsonFn = vi.fn().mockResolvedValue({})
  const fetchMock = vi.fn().mockResolvedValue({
    ok: response.ok,
    status: response.status,
    json: jsonFn,
  })
  vi.stubGlobal('fetch', fetchMock)
  return { fetchMock, jsonFn }
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('deleteCard', () => {
  it('calls DELETE on /api/cards/{id} for the given id', async () => {
    const { fetchMock } = mockFetchOnce({ ok: true, status: 204 })
    await deleteCard(10)
    expect(fetchMock).toHaveBeenCalledTimes(1)
    const [requestedUrl, init] = fetchMock.mock.calls[0]
    expect(String(requestedUrl)).toContain('/api/cards/10')
    expect((init as RequestInit | undefined)?.method).toBe('DELETE')
  })

  it('requests the id passed in, not a hardcoded one', async () => {
    const { fetchMock } = mockFetchOnce({ ok: true, status: 204 })
    await deleteCard(42)
    const [requestedUrl] = fetchMock.mock.calls[0]
    expect(String(requestedUrl)).toContain('/api/cards/42')
    expect(String(requestedUrl)).not.toContain('/api/cards/10')
  })

  it('resolves with undefined on a successful (204, no body) response', async () => {
    mockFetchOnce({ ok: true, status: 204 })
    const result = await deleteCard(10)
    expect(result).toBeUndefined()
  })

  it('never calls response.json() on the success path (a 204 has no body to parse)', async () => {
    const { jsonFn } = mockFetchOnce({ ok: true, status: 204 })
    await deleteCard(10)
    expect(jsonFn).not.toHaveBeenCalled()
  })

  it('throws an Error when the response is not ok', async () => {
    mockFetchOnce({ ok: false, status: 404 })
    await expect(deleteCard(10)).rejects.toBeInstanceOf(Error)
  })

  it('includes the route and status in the thrown error message', async () => {
    mockFetchOnce({ ok: false, status: 404 })
    await expect(deleteCard(10)).rejects.toThrow(/\/api\/cards\/10/)
    mockFetchOnce({ ok: false, status: 404 })
    await expect(deleteCard(10)).rejects.toThrow(/404/)
  })

  it('never calls response.json() on the non-ok path either (throw-before-parse)', async () => {
    const { jsonFn } = mockFetchOnce({ ok: false, status: 500 })
    await expect(deleteCard(10)).rejects.toThrow()
    expect(jsonFn).not.toHaveBeenCalled()
  })

  it('sends no request body', async () => {
    const { fetchMock } = mockFetchOnce({ ok: true, status: 204 })
    await deleteCard(10)
    const [, init] = fetchMock.mock.calls[0]
    expect((init as RequestInit | undefined)?.body).toBeUndefined()
  })
})
