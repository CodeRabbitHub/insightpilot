// Tests for the new `runCard(id)` function from
// plans/briefs/2026-08-07-dashboard-card-rerun-button.md.
//
// Runner: plain vitest-style tests (`describe`/`it`/`expect`/`vi` from the
// 'vitest' package), matching the precedent set by
// web/tests/api.deleteCard.test.ts. This repo has NO frontend test
// runner configured yet (confirmed via web/package.json: no test script,
// no vitest/jsdom devDependency) -- these cannot execute until one is
// added. Expected command once available: `cd web && npx vitest run`.
//
// Written from the brief alone, before `runCard` exists in web/src/api.ts.
// The brief's Constraints section names the exact contract: `fetch` with
// `method: 'POST'` against `${API_BASE}/api/cards/{id}/run`, no request
// body, throwing an `Error` with the route + status on `!response.ok`
// (mirroring `fetchDashboard`'s existing throw shape) -- but, unlike
// `deleteCard`'s 204-no-body success case, `runCard` resolves with the
// parsed `DashboardCardWithRows` JSON body, since the route
// (app/main.py's run_dashboard_card, out of scope here) returns a real
// 200 body on success.
import { describe, expect, it } from 'vitest'
import { runCard, type DashboardCardWithRows } from '../src/api'
import { mockFetchOnce } from './helpers/mockFetch'

// A real-shaped DashboardCardWithRows response body per the brief's
// Inputs section (app/main.py:440-459 returns the full card + fresh rows).
const SAMPLE_CARD: DashboardCardWithRows = {
  id: 10,
  dashboard_id: 1,
  title: 'Orders by category',
  question_text: 'How many orders per category?',
  sql_text: 'SELECT product_category_name, count(*) FROM olist.orders GROUP BY 1',
  chart_spec_json: { chart_type: 'bar', x: 'product_category_name', y: 'count' },
  position: 0,
  created_at: '2026-08-01T00:00:00Z',
  rows: [
    { product_category_name: 'toys', count: 99 },
    { product_category_name: 'books', count: 7 },
  ],
}

describe('runCard', () => {
  it('calls POST on /api/cards/{id}/run for the given id', async () => {
    const { fetchMock } = mockFetchOnce({ ok: true, status: 200, body: SAMPLE_CARD })
    await runCard(10)
    expect(fetchMock).toHaveBeenCalledTimes(1)
    const [requestedUrl, init] = fetchMock.mock.calls[0]
    expect(String(requestedUrl)).toContain('/api/cards/10/run')
    expect((init as RequestInit | undefined)?.method).toBe('POST')
  })

  it('requests the id passed in, not a hardcoded one', async () => {
    const { fetchMock } = mockFetchOnce({
      ok: true,
      status: 200,
      body: { ...SAMPLE_CARD, id: 42 },
    })
    await runCard(42)
    const [requestedUrl] = fetchMock.mock.calls[0]
    expect(String(requestedUrl)).toContain('/api/cards/42/run')
    expect(String(requestedUrl)).not.toContain('/api/cards/10/run')
  })

  it('resolves with the parsed DashboardCardWithRows body on success', async () => {
    mockFetchOnce({ ok: true, status: 200, body: SAMPLE_CARD })
    const result = await runCard(10)
    expect(result).toEqual(SAMPLE_CARD)
    expect(result.rows).toEqual(SAMPLE_CARD.rows)
    expect(result.chart_spec_json).toEqual(SAMPLE_CARD.chart_spec_json)
  })

  it("calls response.json() to parse the success body (unlike deleteCard's 204 no-body case)", async () => {
    const { jsonFn } = mockFetchOnce({ ok: true, status: 200, body: SAMPLE_CARD })
    await runCard(10)
    expect(jsonFn).toHaveBeenCalledTimes(1)
  })

  it('throws an Error when the response is not ok', async () => {
    mockFetchOnce({ ok: false, status: 404 })
    await expect(runCard(10)).rejects.toBeInstanceOf(Error)
  })

  it('includes the route and status in the thrown error message', async () => {
    mockFetchOnce({ ok: false, status: 404 })
    await expect(runCard(10)).rejects.toThrow(/\/api\/cards\/10\/run/)
    mockFetchOnce({ ok: false, status: 404 })
    await expect(runCard(10)).rejects.toThrow(/404/)
  })

  it('includes a 502 status in the thrown error message on SQL execution failure', async () => {
    mockFetchOnce({ ok: false, status: 502 })
    await expect(runCard(10)).rejects.toThrow(/502/)
  })

  it('never calls response.json() on the non-ok path (throw-before-parse)', async () => {
    const { jsonFn } = mockFetchOnce({ ok: false, status: 500 })
    await expect(runCard(10)).rejects.toThrow()
    expect(jsonFn).not.toHaveBeenCalled()
  })

  it('sends no request body', async () => {
    const { fetchMock } = mockFetchOnce({ ok: true, status: 200, body: SAMPLE_CARD })
    await runCard(10)
    const [, init] = fetchMock.mock.calls[0]
    expect((init as RequestInit | undefined)?.body).toBeUndefined()
  })
})
