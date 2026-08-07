// Tests for the new `DashboardView` component from
// plans/briefs/2026-08-07-dashboard-view-frontend.md.
//
// Runner: plain vitest-style tests (`describe`/`it`/`expect`/`vi` from the
// 'vitest' package), rendered with `react-dom/client` directly against a
// jsdom `document` (no @testing-library), matching the precedent set by
// web/tests/SqlDetails.test.tsx and web/tests/FollowUpChips.test.tsx. This
// repo has NO frontend test runner configured yet (confirmed via
// web/package.json: no test script, no vitest/jsdom devDependency) --
// these cannot execute until one is added. Expected command once
// available: `cd web && npx vitest run` (requires `vitest` + a jsdom
// environment as new devDependencies).
//
// Written from the brief alone, before web/src/components/DashboardView.tsx
// exists. The brief's contract: `DashboardView({ dashboardId })` fetches
// `GET /api/dashboards/{dashboardId}` on mount (via the also-new
// `fetchDashboard`), then renders "loading/error states, then one block
// per card (title heading + ChartView), given a DashboardDetail." Rename,
// delete, re-run, and drag-to-reposition are explicitly out-of-scope per
// the brief and are not tested here.
//
// `fetchDashboard` is mocked at the module boundary (`../src/api`) so
// these tests exercise DashboardView's own fetch/render logic without a
// real network call, mirroring how api.fetchDashboard.test.ts covers the
// fetch function itself in isolation.
//
// Chart proof caveat: ChartView (existing, unmodified per the brief) only
// renders a non-null result for `chart_type: 'bar'` rows with valid
// x/y fields, and does so via `echarts-for-react`, which mounts a real
// `<canvas>` into the DOM on init. jsdom does not implement a real 2D
// canvas context, but canvas *elements* are still created as DOM nodes,
// so "a <canvas> appears for the bar card and none appears for the
// non-bar card" is used below as the recognizable, non-implementation-
// -detail proof that ChartView was invoked per-card with that card's own
// chart_spec_json/rows -- not an assertion on chart pixel output.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createRoot, type Root } from 'react-dom/client'
import { act } from 'react-dom/test-utils'
import { fetchDashboard } from '../src/api'
import { DashboardView } from '../src/components/DashboardView'

vi.mock('../src/api', () => ({
  fetchDashboard: vi.fn(),
}))

const mockedFetchDashboard = fetchDashboard as unknown as ReturnType<typeof vi.fn>

// Real card shapes per the brief's Inputs section (DashboardCardWithRows):
// id, dashboard_id, title, question_text, sql_text, chart_spec_json,
// position, created_at, rows.
const BAR_CARD = {
  id: 10,
  dashboard_id: 1,
  title: 'Orders by category',
  question_text: 'How many orders per category?',
  sql_text: 'SELECT product_category_name, count(*) FROM olist.orders GROUP BY 1',
  chart_spec_json: { chart_type: 'bar', x: 'product_category_name', y: 'count' },
  position: 0,
  created_at: '2026-08-01T00:00:00Z',
  rows: [
    { product_category_name: 'toys', count: 12 },
    { product_category_name: 'books', count: 7 },
  ],
}

// A second, real-shaped card whose chart_spec_json is not chart_type
// 'bar' -- ChartView (unmodified) renders null for this, so it proves the
// per-card wiring is really passing each card's own spec through, not a
// single shared/hardcoded one.
const NON_BAR_CARD = {
  id: 11,
  dashboard_id: 1,
  title: 'Revenue over time',
  question_text: 'What is the revenue trend by month?',
  sql_text: 'SELECT month, revenue FROM olist.monthly_revenue',
  chart_spec_json: { chart_type: 'line', x: 'month', y: 'revenue' },
  position: 1,
  created_at: '2026-08-01T00:00:00Z',
  rows: [{ month: '2026-01', revenue: 1000 }],
}

function dashboardWithCards(cards: unknown[]) {
  return {
    id: 1,
    name: 'Overview',
    created_at: '2026-08-01T00:00:00Z',
    cards,
  }
}

let container: HTMLDivElement
let root: Root

beforeEach(() => {
  mockedFetchDashboard.mockReset()
  container = document.createElement('div')
  document.body.appendChild(container)
  root = createRoot(container)
})

afterEach(async () => {
  await act(async () => {
    root.unmount()
  })
  container.remove()
})

function headingTexts(): string[] {
  return Array.from(container.querySelectorAll('h1, h2, h3, h4, h5, h6')).map(
    (el) => el.textContent ?? '',
  )
}

describe('DashboardView - loading state', () => {
  it('shows a loading indicator while the fetch is still pending', () => {
    mockedFetchDashboard.mockReturnValue(new Promise(() => {})) // never resolves
    act(() => {
      root.render(<DashboardView dashboardId={1} />)
    })
    expect(container.textContent).toMatch(/loading/i)
  })

  it('does not render any card titles while still loading', () => {
    mockedFetchDashboard.mockReturnValue(new Promise(() => {}))
    act(() => {
      root.render(<DashboardView dashboardId={1} />)
    })
    expect(headingTexts()).toEqual([])
  })
})

describe('DashboardView - error state', () => {
  it('shows an error message when the fetch rejects, instead of crashing', async () => {
    mockedFetchDashboard.mockRejectedValue(new Error('network down'))
    await act(async () => {
      root.render(<DashboardView dashboardId={1} />)
    })
    expect(container.textContent).toMatch(/error/i)
  })

  it('surfaces the real rejection message somewhere in the rendered output', async () => {
    mockedFetchDashboard.mockRejectedValue(new Error('GET /api/dashboards/1 failed: 500'))
    await act(async () => {
      root.render(<DashboardView dashboardId={1} />)
    })
    expect(container.textContent).toContain('GET /api/dashboards/1 failed: 500')
  })

  it('no longer shows the loading indicator once an error has resolved', async () => {
    mockedFetchDashboard.mockRejectedValue(new Error('network down'))
    await act(async () => {
      root.render(<DashboardView dashboardId={1} />)
    })
    expect(container.textContent).not.toMatch(/loading/i)
  })
})

describe('DashboardView - fetching on mount', () => {
  it('calls fetchDashboard with the dashboardId prop it was given (not a hardcoded id)', async () => {
    mockedFetchDashboard.mockResolvedValue(dashboardWithCards([BAR_CARD]))
    await act(async () => {
      root.render(<DashboardView dashboardId={7} />)
    })
    expect(mockedFetchDashboard).toHaveBeenCalledWith(7)
  })

  it('fetches exactly once on mount for a given dashboardId', async () => {
    mockedFetchDashboard.mockResolvedValue(dashboardWithCards([BAR_CARD]))
    await act(async () => {
      root.render(<DashboardView dashboardId={1} />)
    })
    expect(mockedFetchDashboard).toHaveBeenCalledTimes(1)
  })
})

describe('DashboardView - successful render with cards', () => {
  it("renders each pinned card's title as a heading", async () => {
    mockedFetchDashboard.mockResolvedValue(dashboardWithCards([BAR_CARD, NON_BAR_CARD]))
    await act(async () => {
      root.render(<DashboardView dashboardId={1} />)
    })
    const texts = headingTexts()
    expect(texts).toContain('Orders by category')
    expect(texts).toContain('Revenue over time')
  })

  it('renders both card titles even when one card has no renderable chart', async () => {
    mockedFetchDashboard.mockResolvedValue(dashboardWithCards([BAR_CARD, NON_BAR_CARD]))
    await act(async () => {
      root.render(<DashboardView dashboardId={1} />)
    })
    expect(headingTexts()).toHaveLength(2)
  })

  it("invokes ChartView with the bar card's own chart_spec_json/rows -- a <canvas> is rendered for it", async () => {
    mockedFetchDashboard.mockResolvedValue(dashboardWithCards([BAR_CARD]))
    await act(async () => {
      root.render(<DashboardView dashboardId={1} />)
    })
    expect(container.querySelectorAll('canvas').length).toBeGreaterThan(0)
  })

  it('does not render a chart for a card whose chart_spec_json is not chart_type "bar" (ChartView returns null for it)', async () => {
    mockedFetchDashboard.mockResolvedValue(dashboardWithCards([NON_BAR_CARD]))
    await act(async () => {
      root.render(<DashboardView dashboardId={1} />)
    })
    expect(container.querySelectorAll('canvas')).toHaveLength(0)
    // the title still renders even though its card has no chart
    expect(headingTexts()).toContain('Revenue over time')
  })

  it('renders exactly one chart canvas when only one of two cards qualifies as a bar chart', async () => {
    mockedFetchDashboard.mockResolvedValue(dashboardWithCards([BAR_CARD, NON_BAR_CARD]))
    await act(async () => {
      root.render(<DashboardView dashboardId={1} />)
    })
    expect(container.querySelectorAll('canvas').length).toBe(1)
  })

  it('stops showing the loading indicator once cards have rendered', async () => {
    mockedFetchDashboard.mockResolvedValue(dashboardWithCards([BAR_CARD]))
    await act(async () => {
      root.render(<DashboardView dashboardId={1} />)
    })
    expect(container.textContent).not.toMatch(/loading/i)
  })
})

describe('DashboardView - empty cards case', () => {
  it('renders without throwing when the dashboard has no pinned cards', async () => {
    mockedFetchDashboard.mockResolvedValue(dashboardWithCards([]))
    let thrown: unknown = null
    try {
      await act(async () => {
        root.render(<DashboardView dashboardId={1} />)
      })
    } catch (e) {
      thrown = e
    }
    expect(thrown).toBeNull()
  })

  it('shows some non-empty message text when there are no cards, rather than an empty view', async () => {
    mockedFetchDashboard.mockResolvedValue(dashboardWithCards([]))
    await act(async () => {
      root.render(<DashboardView dashboardId={1} />)
    })
    expect((container.textContent ?? '').trim()).not.toBe('')
    expect(container.textContent).not.toMatch(/loading/i)
    expect(container.textContent).not.toMatch(/error/i)
  })

  it('renders no card title headings and no chart canvases when there are no cards', async () => {
    mockedFetchDashboard.mockResolvedValue(dashboardWithCards([]))
    await act(async () => {
      root.render(<DashboardView dashboardId={1} />)
    })
    expect(headingTexts()).toEqual([])
    expect(container.querySelectorAll('canvas')).toHaveLength(0)
  })
})
