// Tests for the new `repositionCard(id, position)` function from
// plans/briefs/2026-08-08-dashboard-card-drag-reposition.md.
//
// Runner: plain vitest-style tests (`describe`/`it`/`expect`/`vi` from the
// 'vitest' package), matching the precedent set by
// web/tests/api.renameCard.test.ts. This repo has NO frontend test runner
// configured yet (confirmed via web/package.json: no test script, no
// vitest/jsdom devDependency) -- these cannot execute until one is added.
// Expected command once available: `cd web && npx vitest run`.
//
// Written from the brief alone, before `repositionCard` exists in
// web/src/api.ts. The brief's Constraints section is explicit that
// `repositionCard` mirrors `renameCard`'s PATCH+JSON-body shape exactly,
// just swapping the body field -- `fetch` with `method: 'PATCH'`,
// `headers: { 'Content-Type': 'application/json' }`,
// `body: JSON.stringify({ position })`, against `${API_BASE}/api/cards/{id}`
// -- throwing an `Error` with the route + status on `!response.ok`, and
// resolving with the parsed JSON body (`DashboardCardDetail`) on success.
// As with renameCard, the brief is explicit the response type is
// `DashboardCardDetail`, NOT `DashboardCardWithRows` -- the PATCH route
// never touches or returns `rows` -- so the fixture below deliberately has
// no `rows` field, matching the real route's response shape
// (app/main.py:416-437, out of scope here). The brief also states the
// backend contract (`get_dashboard`'s `ORDER BY DashboardCard.position`,
// app/main.py:380) is untouched and out of scope; these tests only cover
// what `repositionCard` itself sends and returns, not sort behavior.
import { describe, expect, it } from 'vitest'
import { repositionCard, type DashboardCardDetail } from '../src/api'
import { mockFetchOnce } from './helpers/mockFetch'

// A real-shaped DashboardCardDetail response body per the brief's Inputs
// section (app/main.py's patch_dashboard_card returns the card without
// `rows`, regardless of whether `title` or `position` was patched).
const SAMPLE_CARD_DETAIL: DashboardCardDetail = {
  id: 10,
  dashboard_id: 1,
  title: 'Orders by category',
  question_text: 'How many orders per category?',
  sql_text: 'SELECT product_category_name, count(*) FROM olist.orders GROUP BY 1',
  chart_spec_json: { chart_type: 'bar', x: 'product_category_name', y: 'count' },
  position: 2,
  created_at: '2026-08-01T00:00:00Z',
}

describe('repositionCard', () => {
  it('calls PATCH on /api/cards/{id} for the given id', async () => {
    const { fetchMock } = mockFetchOnce({ ok: true, status: 200, body: SAMPLE_CARD_DETAIL })
    await repositionCard(10, 2)
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
    await repositionCard(42, 2)
    const [requestedUrl] = fetchMock.mock.calls[0]
    expect(String(requestedUrl)).toContain('/api/cards/42')
    expect(String(requestedUrl)).not.toContain('/api/cards/10')
  })

  it("sends a Content-Type: application/json header", async () => {
    const { fetchMock } = mockFetchOnce({ ok: true, status: 200, body: SAMPLE_CARD_DETAIL })
    await repositionCard(10, 2)
    const [, init] = fetchMock.mock.calls[0]
    expect((init as RequestInit | undefined)?.headers).toMatchObject({
      'Content-Type': 'application/json',
    })
  })

  it('sends a JSON body of exactly { position } -- the position passed in, not a hardcoded one', async () => {
    const { fetchMock } = mockFetchOnce({ ok: true, status: 200, body: SAMPLE_CARD_DETAIL })
    await repositionCard(10, 3)
    const [, init] = fetchMock.mock.calls[0]
    expect((init as RequestInit | undefined)?.body).toBe(JSON.stringify({ position: 3 }))
  })

  it('sends position 0 correctly (not dropped as a falsy value)', async () => {
    const { fetchMock } = mockFetchOnce({ ok: true, status: 200, body: SAMPLE_CARD_DETAIL })
    await repositionCard(10, 0)
    const [, init] = fetchMock.mock.calls[0]
    expect((init as RequestInit | undefined)?.body).toBe(JSON.stringify({ position: 0 }))
  })

  it('resolves with the parsed DashboardCardDetail body on success', async () => {
    mockFetchOnce({ ok: true, status: 200, body: SAMPLE_CARD_DETAIL })
    const result = await repositionCard(10, 2)
    expect(result).toEqual(SAMPLE_CARD_DETAIL)
  })

  it('the resolved body has no rows field (DashboardCardDetail, not DashboardCardWithRows)', async () => {
    mockFetchOnce({ ok: true, status: 200, body: SAMPLE_CARD_DETAIL })
    const result = await repositionCard(10, 2)
    expect(result).not.toHaveProperty('rows')
  })

  it('calls response.json() to parse the success body', async () => {
    const { jsonFn } = mockFetchOnce({ ok: true, status: 200, body: SAMPLE_CARD_DETAIL })
    await repositionCard(10, 2)
    expect(jsonFn).toHaveBeenCalledTimes(1)
  })

  it('throws an Error when the response is not ok', async () => {
    mockFetchOnce({ ok: false, status: 404 })
    await expect(repositionCard(10, 2)).rejects.toBeInstanceOf(Error)
  })

  it('includes the route and status in the thrown error message', async () => {
    mockFetchOnce({ ok: false, status: 404 })
    await expect(repositionCard(10, 2)).rejects.toThrow(/\/api\/cards\/10/)
    mockFetchOnce({ ok: false, status: 404 })
    await expect(repositionCard(10, 2)).rejects.toThrow(/404/)
  })

  it('never calls response.json() on the non-ok path (throw-before-parse)', async () => {
    const { jsonFn } = mockFetchOnce({ ok: false, status: 500 })
    await expect(repositionCard(10, 2)).rejects.toThrow()
    expect(jsonFn).not.toHaveBeenCalled()
  })
})
