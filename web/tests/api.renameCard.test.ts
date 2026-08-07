// Tests for the new `renameCard(id, title)` function from
// plans/briefs/2026-08-07-dashboard-card-rename-button.md.
//
// Runner: plain vitest-style tests (`describe`/`it`/`expect`/`vi` from the
// 'vitest' package), matching the precedent set by
// web/tests/api.runCard.test.ts. This repo has NO frontend test runner
// configured yet (confirmed via web/package.json: no test script, no
// vitest/jsdom devDependency) -- these cannot execute until one is added.
// Expected command once available: `cd web && npx vitest run`.
//
// Written from the brief alone, before `renameCard` exists in
// web/src/api.ts. The brief's Constraints section names the exact
// contract: `fetch` with `method: 'PATCH'`,
// `headers: { 'Content-Type': 'application/json' }`,
// `body: JSON.stringify({ title })`, against `${API_BASE}/api/cards/{id}`
// -- throwing an `Error` with the route + status on `!response.ok`
// (mirroring the existing throw shape), and resolving with the parsed
// JSON body on success. Unlike `deleteCard`'s bodyless DELETE, this is a
// PATCH with a JSON body; unlike `runCard`'s bodyless POST, this also
// sends a body. The brief is explicit that the success response type is
// `DashboardCardDetail`, NOT `DashboardCardWithRows` -- the PATCH route
// never touches or returns `rows`, so the fixture below deliberately has
// no `rows` field, matching the real route's response shape
// (app/main.py:416-437, out of scope here).
import { describe, expect, it } from 'vitest'
import { renameCard, type DashboardCardDetail } from '../src/api'
import { mockFetchOnce } from './helpers/mockFetch'

// A real-shaped DashboardCardDetail response body per the brief's Inputs
// section (app/main.py's patch_dashboard_card returns the card without
// `rows`).
const SAMPLE_CARD_DETAIL: DashboardCardDetail = {
  id: 10,
  dashboard_id: 1,
  title: 'Orders by category (renamed)',
  question_text: 'How many orders per category?',
  sql_text: 'SELECT product_category_name, count(*) FROM olist.orders GROUP BY 1',
  chart_spec_json: { chart_type: 'bar', x: 'product_category_name', y: 'count' },
  position: 0,
  created_at: '2026-08-01T00:00:00Z',
}

describe('renameCard', () => {
  it('calls PATCH on /api/cards/{id} for the given id', async () => {
    const { fetchMock } = mockFetchOnce({ ok: true, status: 200, body: SAMPLE_CARD_DETAIL })
    await renameCard(10, 'New title')
    expect(fetchMock).toHaveBeenCalledTimes(1)
    const [requestedUrl, init] = fetchMock.mock.calls[0]
    expect(String(requestedUrl)).toContain('/api/cards/10')
    expect((init as RequestInit | undefined)?.method).toBe('PATCH')
  })

  it('requests the id passed in, not a hardcoded one', async () => {
    const { fetchMock } = mockFetchOnce({
      ok: true,
      status: 200,
      body: { ...SAMPLE_CARD_DETAIL, id: 42 },
    })
    await renameCard(42, 'New title')
    const [requestedUrl] = fetchMock.mock.calls[0]
    expect(String(requestedUrl)).toContain('/api/cards/42')
    expect(String(requestedUrl)).not.toContain('/api/cards/10')
  })

  it("sends a Content-Type: application/json header", async () => {
    const { fetchMock } = mockFetchOnce({ ok: true, status: 200, body: SAMPLE_CARD_DETAIL })
    await renameCard(10, 'New title')
    const [, init] = fetchMock.mock.calls[0]
    expect((init as RequestInit | undefined)?.headers).toMatchObject({
      'Content-Type': 'application/json',
    })
  })

  it('sends a JSON body of exactly { title } -- the title passed in, not a hardcoded one', async () => {
    const { fetchMock } = mockFetchOnce({ ok: true, status: 200, body: SAMPLE_CARD_DETAIL })
    await renameCard(10, 'Revenue trend')
    const [, init] = fetchMock.mock.calls[0]
    expect((init as RequestInit | undefined)?.body).toBe(JSON.stringify({ title: 'Revenue trend' }))
  })

  it('resolves with the parsed DashboardCardDetail body on success', async () => {
    mockFetchOnce({ ok: true, status: 200, body: SAMPLE_CARD_DETAIL })
    const result = await renameCard(10, 'Orders by category (renamed)')
    expect(result).toEqual(SAMPLE_CARD_DETAIL)
  })

  it('the resolved body has no rows field (DashboardCardDetail, not DashboardCardWithRows)', async () => {
    mockFetchOnce({ ok: true, status: 200, body: SAMPLE_CARD_DETAIL })
    const result = await renameCard(10, 'Orders by category (renamed)')
    expect(result).not.toHaveProperty('rows')
  })

  it('calls response.json() to parse the success body', async () => {
    const { jsonFn } = mockFetchOnce({ ok: true, status: 200, body: SAMPLE_CARD_DETAIL })
    await renameCard(10, 'New title')
    expect(jsonFn).toHaveBeenCalledTimes(1)
  })

  it('throws an Error when the response is not ok', async () => {
    mockFetchOnce({ ok: false, status: 404 })
    await expect(renameCard(10, 'New title')).rejects.toBeInstanceOf(Error)
  })

  it('includes the route and status in the thrown error message', async () => {
    mockFetchOnce({ ok: false, status: 404 })
    await expect(renameCard(10, 'New title')).rejects.toThrow(/\/api\/cards\/10/)
    mockFetchOnce({ ok: false, status: 404 })
    await expect(renameCard(10, 'New title')).rejects.toThrow(/404/)
  })

  it('never calls response.json() on the non-ok path (throw-before-parse)', async () => {
    const { jsonFn } = mockFetchOnce({ ok: false, status: 500 })
    await expect(renameCard(10, 'New title')).rejects.toThrow()
    expect(jsonFn).not.toHaveBeenCalled()
  })
})
