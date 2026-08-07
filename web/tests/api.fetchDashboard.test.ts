// Tests for the new `fetchDashboard(id)` function from
// plans/briefs/2026-08-07-dashboard-view-frontend.md.
//
// Runner: plain vitest-style tests (`describe`/`it`/`expect`/`vi` from the
// 'vitest' package), matching the precedent set by
// web/tests/api.asAssistantContent.test.ts and
// web/tests/FollowUpChips.test.tsx. This repo has NO frontend test runner
// configured yet (confirmed via web/package.json: no test script, no
// vitest/jsdom devDependency) -- these cannot execute until one is added.
// Expected command once available: `cd web && npx vitest run`.
//
// Written from the brief alone, before `fetchDashboard` exists in
// web/src/api.ts. The brief's Inputs section names the pattern to mirror
// exactly: `fetchConversation`'s "fetch-plus-throw-on-`!response.ok`"
// shape (api.ts today: `fetch(`${API_BASE}/api/conversations/${id}`)`,
// throw on non-ok, otherwise `response.json()`). These tests hold
// `fetchDashboard` to that same contract against
// `GET /api/dashboards/{id}`, using `global.fetch` mocked directly (no
// network, no MSW -- consistent with this repo's "no new dependencies
// without asking").
import { afterEach, describe, expect, it, vi } from 'vitest'
import { fetchDashboard } from '../src/api'

// Real DashboardDetail/DashboardCardWithRows shape per the brief's Inputs
// section (app/main.py's DashboardDetail response model): id, name,
// created_at, cards: [{ id, dashboard_id, title, question_text, sql_text,
// chart_spec_json, position, created_at, rows }].
const REAL_DASHBOARD_BODY = {
  id: 1,
  name: 'Overview',
  created_at: '2026-08-01T00:00:00Z',
  cards: [
    {
      id: 3,
      dashboard_id: 1,
      title: 'Orders by category',
      question_text: 'How many orders per category?',
      sql_text: 'SELECT product_category_name, count(*) FROM olist.orders GROUP BY 1',
      chart_spec_json: { chart_type: 'bar', x: 'product_category_name', y: 'count' },
      position: 0,
      created_at: '2026-08-01T00:00:00Z',
      rows: [{ product_category_name: 'toys', count: 12 }],
    },
  ],
}

function mockFetchOnce(response: { ok: boolean; status: number; body: unknown }) {
  const jsonFn = vi.fn().mockResolvedValue(response.body)
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

describe('fetchDashboard', () => {
  it('calls GET on /api/dashboards/{id} for the given id', async () => {
    const { fetchMock } = mockFetchOnce({ ok: true, status: 200, body: REAL_DASHBOARD_BODY })
    await fetchDashboard(1)
    expect(fetchMock).toHaveBeenCalledTimes(1)
    const [requestedUrl] = fetchMock.mock.calls[0]
    expect(String(requestedUrl)).toContain('/api/dashboards/1')
  })

  it('requests the id passed in, not a hardcoded one', async () => {
    const { fetchMock } = mockFetchOnce({ ok: true, status: 200, body: REAL_DASHBOARD_BODY })
    await fetchDashboard(42)
    const [requestedUrl] = fetchMock.mock.calls[0]
    expect(String(requestedUrl)).toContain('/api/dashboards/42')
    expect(String(requestedUrl)).not.toContain('/api/dashboards/1')
  })

  it('returns the parsed JSON body on a successful (ok) response', async () => {
    const { jsonFn } = mockFetchOnce({ ok: true, status: 200, body: REAL_DASHBOARD_BODY })
    const result = await fetchDashboard(1)
    expect(result).toEqual(REAL_DASHBOARD_BODY)
    expect(jsonFn).toHaveBeenCalledTimes(1)
  })

  it('throws an Error when the response is not ok (mirrors fetchConversation)', async () => {
    mockFetchOnce({ ok: false, status: 404, body: { detail: 'not found' } })
    await expect(fetchDashboard(1)).rejects.toBeInstanceOf(Error)
  })

  it('never calls response.json() on the non-ok path (matches fetchConversation\'s throw-before-parse order)', async () => {
    const { jsonFn } = mockFetchOnce({ ok: false, status: 500, body: { detail: 'server error' } })
    await expect(fetchDashboard(1)).rejects.toThrow()
    expect(jsonFn).not.toHaveBeenCalled()
  })
})
