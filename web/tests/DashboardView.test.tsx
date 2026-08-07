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
//
// Extended per plans/briefs/2026-08-07-dashboard-card-delete-button.md with
// tests for that brief's Outputs: a "Delete" button rendered inside each
// card's `<li>`; clicking it and having `deleteCard` resolve removes only
// that card from the rendered list (siblings untouched), with no extra
// `fetchDashboard` refetch; clicking it and having `deleteCard` reject
// leaves the card in place and surfaces the error via a dedicated
// `actionError` state (kept separate from the initial-fetch `error` state,
// since that state's existing `if (error) return <p>...</p>` guard would
// otherwise blank the whole card list instead of leaving cards in place).
// `../src/api` is still mocked at the module boundary, so `deleteCard` is
// mocked alongside `fetchDashboard` below -- no real network/DELETE call is
// made.
//
// Extended again per plans/briefs/2026-08-07-dashboard-card-rerun-button.md
// with tests for a "Re-run" button per card: clicking it calls `runCard`
// (mocked alongside `fetchDashboard`/`deleteCard` below) and, on success,
// swaps that card's `chart_spec_json`/`rows` for the fresh response,
// leaving siblings untouched, with no extra `fetchDashboard` refetch and no
// error shown; on failure, the card's existing data is left unchanged and
// an error is surfaced without blanking the rest of the list. The brief
// explicitly calls out that the card's title text does NOT change on
// re-run, so title alone can't prove a real data swap happened -- a
// dedicated `REVISED_BAR_CARD` fixture (same `id: 10` as `BAR_CARD`, but
// with a bumped row count) is used instead, and `ChartView` is spied on
// (via `vi.fn(actual.ChartView)`, i.e. a call-through spy that still
// renders for real) so the props DashboardView passes to it -- in
// particular `rows` -- are directly inspectable. This spy preserves
// ChartView's real rendering behavior (so the existing bar/non-bar canvas
// assertions above are unaffected), it merely also records each call's
// props.
//
// Extended again per plans/briefs/2026-08-07-dashboard-card-rename-button.md
// with tests for a "Rename" button per card, backed by `window.prompt`
// (native browser API, per the brief's Constraints -- no new dependency,
// no custom inline-edit input/modal). Unlike re-run, a rename *does*
// change the card's title text, but the brief is explicit that the
// success response (`DashboardCardDetail`) has no `rows` field, so the
// component must merge only `title` from the response into the existing
// card object rather than swapping the whole card in -- naively swapping
// would silently wipe `rows`/`chart_spec_json` and blank the chart. The
// same `ChartView` call-through spy used for the re-run tests is reused
// here to prove `rows`/`chart_spec_json` are untouched by a rename, since
// the title text changing on its own doesn't prove that. `renameCard` is
// mocked alongside the other three api functions below; `window.prompt`
// is stubbed per test via the `mockPrompt` helper and restored in the
// shared `afterEach`.
//
// Extended again per
// plans/briefs/2026-08-08-dashboard-card-drag-reposition.md with tests for
// drag-to-reposition: dropping a card on another card's slot reorders the
// rendered list immediately (optimistic), then calls the also-new
// `repositionCard` (mocked alongside the other four api functions below)
// with the renumbered (0, 1, 2, ...) position for every card whose
// position actually changed -- not only the dragged card, since reordering
// shifts siblings too -- and reverts the local order plus surfaces
// `actionError` if any of those calls rejects, without corrupting cards
// unrelated to the drag. The brief specifies the native HTML5
// drag-and-drop API (`draggable` + `onDragStart`/`onDragOver`/`onDrop` on
// each card's `<li>`, no library), which jsdom does not natively drive, so
// the `dragCardOnto` helper below dispatches plain `dragstart`/`dragover`/
// `drop` events directly at the source/target `<li>` elements, sharing one
// fake `DataTransfer`-shaped object across all three (as a real drag
// would) since jsdom's own `DragEvent`/`DataTransfer` support is
// unreliable. A third bar-chart card fixture (`THIRD_CARD`) is added so a
// drag can be exercised against a list where only some siblings' positions
// shift, in addition to a full-reshuffle case.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createRoot, type Root } from 'react-dom/client'
import { act } from 'react-dom/test-utils'
import { deleteCard, fetchDashboard, renameCard, repositionCard, runCard } from '../src/api'
import { DashboardView } from '../src/components/DashboardView'
import { ChartView } from '../src/components/ChartView'

vi.mock('../src/api', () => ({
  fetchDashboard: vi.fn(),
  deleteCard: vi.fn(),
  runCard: vi.fn(),
  renameCard: vi.fn(),
  repositionCard: vi.fn(),
}))

vi.mock('../src/components/ChartView', async () => {
  const actual =
    await vi.importActual<typeof import('../src/components/ChartView')>(
      '../src/components/ChartView',
    )
  return {
    ...actual,
    // Call-through spy: real rendering behavior is preserved (`vi.fn`
    // wraps, rather than replaces, `actual.ChartView`), so this only adds
    // the ability to inspect what props each render call received.
    ChartView: vi.fn(actual.ChartView),
  }
})

const mockedFetchDashboard = fetchDashboard as unknown as ReturnType<typeof vi.fn>
const mockedDeleteCard = deleteCard as unknown as ReturnType<typeof vi.fn>
const mockedRunCard = runCard as unknown as ReturnType<typeof vi.fn>
const mockedRenameCard = renameCard as unknown as ReturnType<typeof vi.fn>
const mockedRepositionCard = repositionCard as unknown as ReturnType<typeof vi.fn>
const mockedChartView = ChartView as unknown as ReturnType<typeof vi.fn>

// Preserved so `window.prompt` (stubbed per rename test via `mockPrompt`)
// can be restored afterward, rather than leaking a stub into unrelated
// tests/files.
const originalWindowPrompt = window.prompt

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

// Same card id as BAR_CARD (a re-run replaces a card in place, it doesn't
// create a new one), but with different `rows` -- the fresh result a
// successful POST /api/cards/10/run would return. Used to prove the
// re-run actually swapped in new data, since the title text is identical
// to BAR_CARD's and can't be used as that proof on its own.
const REVISED_BAR_CARD = {
  ...BAR_CARD,
  rows: [
    { product_category_name: 'toys', count: 40 },
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

// A third real-shaped card (bar chart, so its own <canvas>/rows are
// independently checkable), added for the drag-to-reposition tests below
// -- a three-card list is the minimum needed to distinguish "the dragged
// card's own position changed" from "a sibling's position also shifted"
// from "a sibling's position was unaffected by this particular drag".
const THIRD_CARD = {
  id: 12,
  dashboard_id: 1,
  title: 'Average order value',
  question_text: 'What is the average order value by month?',
  sql_text: 'SELECT month, avg(payment_value) FROM olist.orders GROUP BY 1',
  chart_spec_json: { chart_type: 'bar', x: 'month', y: 'avg_value' },
  position: 2,
  created_at: '2026-08-01T00:00:00Z',
  rows: [{ month: '2026-01', avg_value: 150 }],
}

// The real PATCH /api/cards/{id} response shape per the brief's Inputs
// section: a `DashboardCardDetail` -- same id as BAR_CARD, new title,
// but deliberately NO `rows` field (the route never touches rows). Used
// to prove that DashboardView merges only `title` from this response
// rather than swapping the whole card object in, which would otherwise
// wipe BAR_CARD's rows/chart_spec_json.
const RENAMED_BAR_CARD_DETAIL = {
  id: BAR_CARD.id,
  dashboard_id: BAR_CARD.dashboard_id,
  title: 'Orders by category (renamed)',
  question_text: BAR_CARD.question_text,
  sql_text: BAR_CARD.sql_text,
  chart_spec_json: BAR_CARD.chart_spec_json,
  position: BAR_CARD.position,
  created_at: BAR_CARD.created_at,
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
  mockedDeleteCard.mockReset()
  mockedRunCard.mockReset()
  mockedRenameCard.mockReset()
  mockedRepositionCard.mockReset()
  // `.mockClear()`, not `.mockReset()` -- resetting would also wipe the
  // call-through implementation set up in the `vi.mock` factory above,
  // which would break real chart rendering for every test.
  mockedChartView.mockClear()
  container = document.createElement('div')
  document.body.appendChild(container)
  root = createRoot(container)
})

afterEach(async () => {
  await act(async () => {
    root.unmount()
  })
  container.remove()
  window.prompt = originalWindowPrompt
})

function headingTexts(): string[] {
  return Array.from(container.querySelectorAll('h1, h2, h3, h4, h5, h6')).map(
    (el) => el.textContent ?? '',
  )
}

// Finds the <li> whose own heading text matches the given card title, so
// per-card action-button tests can act on "the button belonging to this
// card" without assuming DOM ordering.
function liForTitle(title: string): HTMLElement {
  const li = Array.from(container.querySelectorAll('li')).find((el) =>
    (el.textContent ?? '').includes(title),
  )
  if (!li) throw new Error(`no <li> found for title ${title}`)
  return li as HTMLElement
}

function deleteButtonIn(li: HTMLElement): HTMLElement {
  const button = Array.from(li.querySelectorAll('button')).find((b) =>
    /delete/i.test(b.textContent ?? ''),
  )
  if (!button) throw new Error('no Delete button found in <li>')
  return button as HTMLElement
}

async function clickDelete(title: string) {
  const button = deleteButtonIn(liForTitle(title))
  await act(async () => {
    button.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }))
  })
}

function rerunButtonIn(li: HTMLElement): HTMLElement {
  const button = Array.from(li.querySelectorAll('button')).find((b) =>
    /re-?run/i.test(b.textContent ?? ''),
  )
  if (!button) throw new Error('no Re-run button found in <li>')
  return button as HTMLElement
}

async function clickRerun(title: string) {
  const button = rerunButtonIn(liForTitle(title))
  await act(async () => {
    button.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }))
  })
}

function renameButtonIn(li: HTMLElement): HTMLElement {
  const button = Array.from(li.querySelectorAll('button')).find((b) =>
    /rename/i.test(b.textContent ?? ''),
  )
  if (!button) throw new Error('no Rename button found in <li>')
  return button as HTMLElement
}

async function clickRename(title: string) {
  const button = renameButtonIn(liForTitle(title))
  await act(async () => {
    button.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }))
  })
}

// Stubs `window.prompt` to return a fixed value for the duration of a
// test (restored in the shared `afterEach` above), and returns the stub
// so a test can assert on how it was called (e.g. the default value
// passed as its second argument).
function mockPrompt(value: string | null) {
  const promptFn = vi.fn().mockReturnValue(value)
  window.prompt = promptFn
  return promptFn
}

// Extracts the `rows` prop from each recorded ChartView call, for
// asserting on which card's data a given render pass actually used.
function chartRowsSeen(): Record<string, unknown>[][] {
  return mockedChartView.mock.calls.map(
    ([props]) => (props as { rows: Record<string, unknown>[] }).rows,
  )
}

// Extracts the `chartSpec` prop from each recorded ChartView call, for
// asserting that a card's chart_spec_json survives untouched across
// actions (e.g. rename) that only intend to change its title.
function chartSpecsSeen(): Record<string, unknown>[] {
  return mockedChartView.mock.calls.map(
    ([props]) => (props as { chartSpec: Record<string, unknown> }).chartSpec,
  )
}

// Minimal HTML5 DataTransfer stand-in: jsdom does not implement a real
// one, but a real drag shares a single DataTransfer instance across its
// dragstart/dragover/drop events, so this is passed through to each
// dispatched event the same way.
class FakeDataTransfer {
  private store: Record<string, string> = {}
  dropEffect = 'move'
  effectAllowed = 'move'
  setData(format: string, data: string) {
    this.store[format] = data
  }
  getData(format: string) {
    return this.store[format] ?? ''
  }
}

function dispatchDragEvent(el: HTMLElement, type: string, dataTransfer: FakeDataTransfer) {
  // A plain Event, not `new DragEvent(...)` -- jsdom's own DragEvent
  // construction/`dataTransfer` support is unreliable, so `dataTransfer`
  // is attached directly instead, matching the one property
  // (`onDragStart`/`onDragOver`/`onDrop` handlers) the brief's contract
  // actually depends on.
  const event = new Event(type, { bubbles: true, cancelable: true })
  Object.defineProperty(event, 'dataTransfer', { value: dataTransfer, configurable: true })
  el.dispatchEvent(event)
}

// Simulates dragging the card titled `fromTitle` and dropping it onto the
// card titled `toTitle`'s slot, per the brief's Constraints (native HTML5
// drag-and-drop: `draggable` + `onDragStart`/`onDragOver`/`onDrop` on each
// card's `<li>`, no drag-and-drop library).
async function dragCardOnto(fromTitle: string, toTitle: string) {
  const fromLi = liForTitle(fromTitle)
  const toLi = liForTitle(toTitle)
  const dataTransfer = new FakeDataTransfer()
  await act(async () => {
    dispatchDragEvent(fromLi, 'dragstart', dataTransfer)
    dispatchDragEvent(toLi, 'dragover', dataTransfer)
    dispatchDragEvent(toLi, 'drop', dataTransfer)
  })
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

// Tests below are from plans/briefs/2026-08-07-dashboard-card-delete-button.md.
describe('DashboardView - delete button presence', () => {
  it('renders a Delete button inside each card\'s <li>', async () => {
    mockedFetchDashboard.mockResolvedValue(dashboardWithCards([BAR_CARD, NON_BAR_CARD]))
    await act(async () => {
      root.render(<DashboardView dashboardId={1} />)
    })
    expect(() => deleteButtonIn(liForTitle('Orders by category'))).not.toThrow()
    expect(() => deleteButtonIn(liForTitle('Revenue over time'))).not.toThrow()
  })

  it('renders exactly one Delete button per card -- not a shared/global one', async () => {
    mockedFetchDashboard.mockResolvedValue(dashboardWithCards([BAR_CARD, NON_BAR_CARD]))
    await act(async () => {
      root.render(<DashboardView dashboardId={1} />)
    })
    const allDeleteButtons = Array.from(container.querySelectorAll('button')).filter((b) =>
      /delete/i.test(b.textContent ?? ''),
    )
    expect(allDeleteButtons).toHaveLength(2)
  })
})

describe('DashboardView - successful delete', () => {
  it('calls deleteCard with the clicked card\'s own id', async () => {
    mockedFetchDashboard.mockResolvedValue(dashboardWithCards([BAR_CARD, NON_BAR_CARD]))
    mockedDeleteCard.mockResolvedValue(undefined)
    await act(async () => {
      root.render(<DashboardView dashboardId={1} />)
    })
    await clickDelete('Orders by category')
    expect(mockedDeleteCard).toHaveBeenCalledWith(BAR_CARD.id)
  })

  it('removes only the deleted card from the rendered list, leaving its sibling in place', async () => {
    mockedFetchDashboard.mockResolvedValue(dashboardWithCards([BAR_CARD, NON_BAR_CARD]))
    mockedDeleteCard.mockResolvedValue(undefined)
    await act(async () => {
      root.render(<DashboardView dashboardId={1} />)
    })
    await clickDelete('Orders by category')
    const texts = headingTexts()
    expect(texts).not.toContain('Orders by category')
    expect(texts).toContain('Revenue over time')
  })

  it('does not trigger an extra fetchDashboard call on a successful delete (no full refetch)', async () => {
    mockedFetchDashboard.mockResolvedValue(dashboardWithCards([BAR_CARD, NON_BAR_CARD]))
    mockedDeleteCard.mockResolvedValue(undefined)
    await act(async () => {
      root.render(<DashboardView dashboardId={1} />)
    })
    mockedFetchDashboard.mockClear()
    await clickDelete('Orders by category')
    expect(mockedFetchDashboard).not.toHaveBeenCalled()
  })

  it('does not surface an error after a successful delete', async () => {
    mockedFetchDashboard.mockResolvedValue(dashboardWithCards([BAR_CARD, NON_BAR_CARD]))
    mockedDeleteCard.mockResolvedValue(undefined)
    await act(async () => {
      root.render(<DashboardView dashboardId={1} />)
    })
    await clickDelete('Orders by category')
    expect(container.textContent).not.toMatch(/error/i)
  })
})

describe('DashboardView - failed delete', () => {
  it('leaves the card in place when deleteCard rejects', async () => {
    mockedFetchDashboard.mockResolvedValue(dashboardWithCards([BAR_CARD, NON_BAR_CARD]))
    mockedDeleteCard.mockRejectedValue(new Error('DELETE /api/cards/10 failed: 404'))
    await act(async () => {
      root.render(<DashboardView dashboardId={1} />)
    })
    await clickDelete('Orders by category')
    const texts = headingTexts()
    expect(texts).toContain('Orders by category')
    expect(texts).toContain('Revenue over time')
  })

  it('surfaces an error message when deleteCard rejects, instead of failing silently', async () => {
    mockedFetchDashboard.mockResolvedValue(dashboardWithCards([BAR_CARD, NON_BAR_CARD]))
    mockedDeleteCard.mockRejectedValue(new Error('DELETE /api/cards/10 failed: 404'))
    await act(async () => {
      root.render(<DashboardView dashboardId={1} />)
    })
    await clickDelete('Orders by category')
    expect(container.textContent).toMatch(/error/i)
  })

  it('surfaces the real rejection message somewhere in the rendered output', async () => {
    mockedFetchDashboard.mockResolvedValue(dashboardWithCards([BAR_CARD, NON_BAR_CARD]))
    mockedDeleteCard.mockRejectedValue(new Error('DELETE /api/cards/10 failed: 404'))
    await act(async () => {
      root.render(<DashboardView dashboardId={1} />)
    })
    await clickDelete('Orders by category')
    expect(container.textContent).toContain('DELETE /api/cards/10 failed: 404')
  })

  it('does not remove the sibling card when a delete on a different card fails', async () => {
    mockedFetchDashboard.mockResolvedValue(dashboardWithCards([BAR_CARD, NON_BAR_CARD]))
    mockedDeleteCard.mockRejectedValue(new Error('DELETE /api/cards/10 failed: 404'))
    await act(async () => {
      root.render(<DashboardView dashboardId={1} />)
    })
    await clickDelete('Orders by category')
    expect(headingTexts()).toHaveLength(2)
  })
})

// Tests below are from plans/briefs/2026-08-07-dashboard-card-rerun-button.md.
describe('DashboardView - re-run button presence', () => {
  it("renders a Re-run button inside each card's <li>", async () => {
    mockedFetchDashboard.mockResolvedValue(dashboardWithCards([BAR_CARD, NON_BAR_CARD]))
    await act(async () => {
      root.render(<DashboardView dashboardId={1} />)
    })
    expect(() => rerunButtonIn(liForTitle('Orders by category'))).not.toThrow()
    expect(() => rerunButtonIn(liForTitle('Revenue over time'))).not.toThrow()
  })

  it('renders exactly one Re-run button per card -- not a shared/global one', async () => {
    mockedFetchDashboard.mockResolvedValue(dashboardWithCards([BAR_CARD, NON_BAR_CARD]))
    await act(async () => {
      root.render(<DashboardView dashboardId={1} />)
    })
    const allRerunButtons = Array.from(container.querySelectorAll('button')).filter((b) =>
      /re-?run/i.test(b.textContent ?? ''),
    )
    expect(allRerunButtons).toHaveLength(2)
  })
})

describe('DashboardView - successful re-run', () => {
  it("calls runCard with the clicked card's own id", async () => {
    mockedFetchDashboard.mockResolvedValue(dashboardWithCards([BAR_CARD, NON_BAR_CARD]))
    mockedRunCard.mockResolvedValue(REVISED_BAR_CARD)
    await act(async () => {
      root.render(<DashboardView dashboardId={1} />)
    })
    await clickRerun('Orders by category')
    expect(mockedRunCard).toHaveBeenCalledWith(BAR_CARD.id)
  })

  it("updates only the re-run card's data -- proven by ChartView receiving the fresh rows -- leaving the sibling's rows untouched", async () => {
    mockedFetchDashboard.mockResolvedValue(dashboardWithCards([BAR_CARD, NON_BAR_CARD]))
    mockedRunCard.mockResolvedValue(REVISED_BAR_CARD)
    await act(async () => {
      root.render(<DashboardView dashboardId={1} />)
    })
    mockedChartView.mockClear()
    await clickRerun('Orders by category')

    const rowsSeen = chartRowsSeen()
    expect(rowsSeen).toContainEqual(REVISED_BAR_CARD.rows)
    // the stale, pre-rerun rows must no longer be what any card renders with
    expect(rowsSeen).not.toContainEqual(BAR_CARD.rows)
    // the sibling's own rows are exactly as before -- untouched
    expect(rowsSeen).toContainEqual(NON_BAR_CARD.rows)

    const texts = headingTexts()
    expect(texts).toContain('Orders by category')
    expect(texts).toContain('Revenue over time')
  })

  it('does not trigger an extra fetchDashboard call on a successful re-run (no full refetch)', async () => {
    mockedFetchDashboard.mockResolvedValue(dashboardWithCards([BAR_CARD, NON_BAR_CARD]))
    mockedRunCard.mockResolvedValue(REVISED_BAR_CARD)
    await act(async () => {
      root.render(<DashboardView dashboardId={1} />)
    })
    mockedFetchDashboard.mockClear()
    await clickRerun('Orders by category')
    expect(mockedFetchDashboard).not.toHaveBeenCalled()
  })

  it('does not surface an error after a successful re-run', async () => {
    mockedFetchDashboard.mockResolvedValue(dashboardWithCards([BAR_CARD, NON_BAR_CARD]))
    mockedRunCard.mockResolvedValue(REVISED_BAR_CARD)
    await act(async () => {
      root.render(<DashboardView dashboardId={1} />)
    })
    await clickRerun('Orders by category')
    expect(container.textContent).not.toMatch(/error/i)
  })
})

describe('DashboardView - failed re-run', () => {
  it("leaves the card's existing rows unchanged when runCard rejects", async () => {
    mockedFetchDashboard.mockResolvedValue(dashboardWithCards([BAR_CARD, NON_BAR_CARD]))
    mockedRunCard.mockRejectedValue(new Error('POST /api/cards/10/run failed: 502'))
    await act(async () => {
      root.render(<DashboardView dashboardId={1} />)
    })
    mockedChartView.mockClear()
    await clickRerun('Orders by category')

    const rowsSeen = chartRowsSeen()
    expect(rowsSeen).toContainEqual(BAR_CARD.rows)
    expect(rowsSeen).not.toContainEqual(REVISED_BAR_CARD.rows)

    const texts = headingTexts()
    expect(texts).toContain('Orders by category')
    expect(texts).toContain('Revenue over time')
  })

  it('surfaces an error message when runCard rejects, instead of failing silently', async () => {
    mockedFetchDashboard.mockResolvedValue(dashboardWithCards([BAR_CARD, NON_BAR_CARD]))
    mockedRunCard.mockRejectedValue(new Error('POST /api/cards/10/run failed: 502'))
    await act(async () => {
      root.render(<DashboardView dashboardId={1} />)
    })
    await clickRerun('Orders by category')
    expect(container.textContent).toMatch(/error/i)
  })

  it('surfaces the real rejection message somewhere in the rendered output', async () => {
    mockedFetchDashboard.mockResolvedValue(dashboardWithCards([BAR_CARD, NON_BAR_CARD]))
    mockedRunCard.mockRejectedValue(new Error('POST /api/cards/10/run failed: 502'))
    await act(async () => {
      root.render(<DashboardView dashboardId={1} />)
    })
    await clickRerun('Orders by category')
    expect(container.textContent).toContain('POST /api/cards/10/run failed: 502')
  })

  it('does not remove or alter the sibling card when a re-run on a different card fails', async () => {
    mockedFetchDashboard.mockResolvedValue(dashboardWithCards([BAR_CARD, NON_BAR_CARD]))
    mockedRunCard.mockRejectedValue(new Error('POST /api/cards/10/run failed: 502'))
    await act(async () => {
      root.render(<DashboardView dashboardId={1} />)
    })
    mockedChartView.mockClear()
    await clickRerun('Orders by category')

    expect(headingTexts()).toHaveLength(2)
    expect(headingTexts()).toContain('Revenue over time')
    expect(chartRowsSeen()).toContainEqual(NON_BAR_CARD.rows)
  })
})

// Tests below are from plans/briefs/2026-08-07-dashboard-card-rename-button.md.
describe('DashboardView - rename button presence', () => {
  it("renders a Rename button inside each card's <li>", async () => {
    mockedFetchDashboard.mockResolvedValue(dashboardWithCards([BAR_CARD, NON_BAR_CARD]))
    await act(async () => {
      root.render(<DashboardView dashboardId={1} />)
    })
    expect(() => renameButtonIn(liForTitle('Orders by category'))).not.toThrow()
    expect(() => renameButtonIn(liForTitle('Revenue over time'))).not.toThrow()
  })

  it('renders exactly one Rename button per card -- not a shared/global one', async () => {
    mockedFetchDashboard.mockResolvedValue(dashboardWithCards([BAR_CARD, NON_BAR_CARD]))
    await act(async () => {
      root.render(<DashboardView dashboardId={1} />)
    })
    const allRenameButtons = Array.from(container.querySelectorAll('button')).filter((b) =>
      /rename/i.test(b.textContent ?? ''),
    )
    expect(allRenameButtons).toHaveLength(2)
  })
})

describe('DashboardView - rename prompt interaction', () => {
  it("calls window.prompt with 'New title' and the card's current title as the default value", async () => {
    mockedFetchDashboard.mockResolvedValue(dashboardWithCards([BAR_CARD, NON_BAR_CARD]))
    const promptFn = mockPrompt(null)
    await act(async () => {
      root.render(<DashboardView dashboardId={1} />)
    })
    await clickRename('Orders by category')
    expect(promptFn).toHaveBeenCalledWith('New title', BAR_CARD.title)
  })

  it('sends no renameCard request when the prompt is cancelled (returns null)', async () => {
    mockedFetchDashboard.mockResolvedValue(dashboardWithCards([BAR_CARD, NON_BAR_CARD]))
    mockPrompt(null)
    await act(async () => {
      root.render(<DashboardView dashboardId={1} />)
    })
    await clickRename('Orders by category')
    expect(mockedRenameCard).not.toHaveBeenCalled()
  })

  it('leaves the title unchanged when the prompt is cancelled', async () => {
    mockedFetchDashboard.mockResolvedValue(dashboardWithCards([BAR_CARD, NON_BAR_CARD]))
    mockPrompt(null)
    await act(async () => {
      root.render(<DashboardView dashboardId={1} />)
    })
    await clickRename('Orders by category')
    expect(headingTexts()).toContain('Orders by category')
  })

  it('sends no renameCard request when the prompt result is an empty string', async () => {
    mockedFetchDashboard.mockResolvedValue(dashboardWithCards([BAR_CARD, NON_BAR_CARD]))
    mockPrompt('')
    await act(async () => {
      root.render(<DashboardView dashboardId={1} />)
    })
    await clickRename('Orders by category')
    expect(mockedRenameCard).not.toHaveBeenCalled()
  })

  it('sends no renameCard request when the prompt result is whitespace-only', async () => {
    mockedFetchDashboard.mockResolvedValue(dashboardWithCards([BAR_CARD, NON_BAR_CARD]))
    mockPrompt('   ')
    await act(async () => {
      root.render(<DashboardView dashboardId={1} />)
    })
    await clickRename('Orders by category')
    expect(mockedRenameCard).not.toHaveBeenCalled()
  })

  it('does not trigger an extra fetchDashboard call when the prompt is cancelled or empty', async () => {
    mockedFetchDashboard.mockResolvedValue(dashboardWithCards([BAR_CARD, NON_BAR_CARD]))
    mockPrompt(null)
    await act(async () => {
      root.render(<DashboardView dashboardId={1} />)
    })
    mockedFetchDashboard.mockClear()
    await clickRename('Orders by category')
    expect(mockedFetchDashboard).not.toHaveBeenCalled()
  })
})

describe('DashboardView - successful rename', () => {
  it('calls renameCard with the clicked card\'s own id and the trimmed prompt result', async () => {
    mockedFetchDashboard.mockResolvedValue(dashboardWithCards([BAR_CARD, NON_BAR_CARD]))
    mockPrompt('  Orders by category (renamed)  ')
    mockedRenameCard.mockResolvedValue(RENAMED_BAR_CARD_DETAIL)
    await act(async () => {
      root.render(<DashboardView dashboardId={1} />)
    })
    await clickRename('Orders by category')
    expect(mockedRenameCard).toHaveBeenCalledWith(BAR_CARD.id, 'Orders by category (renamed)')
  })

  it("updates only the renamed card's title in the heading text, leaving the sibling's title untouched", async () => {
    mockedFetchDashboard.mockResolvedValue(dashboardWithCards([BAR_CARD, NON_BAR_CARD]))
    mockPrompt('Orders by category (renamed)')
    mockedRenameCard.mockResolvedValue(RENAMED_BAR_CARD_DETAIL)
    await act(async () => {
      root.render(<DashboardView dashboardId={1} />)
    })
    await clickRename('Orders by category')

    const texts = headingTexts()
    expect(texts).toContain('Orders by category (renamed)')
    expect(texts).not.toContain('Orders by category')
    expect(texts).toContain('Revenue over time')
  })

  it("preserves the renamed card's own rows/chart_spec_json -- the DashboardCardDetail response has no rows field, so a naive whole-object swap would blank the chart", async () => {
    mockedFetchDashboard.mockResolvedValue(dashboardWithCards([BAR_CARD, NON_BAR_CARD]))
    mockPrompt('Orders by category (renamed)')
    mockedRenameCard.mockResolvedValue(RENAMED_BAR_CARD_DETAIL)
    await act(async () => {
      root.render(<DashboardView dashboardId={1} />)
    })
    mockedChartView.mockClear()
    await clickRename('Orders by category')

    const rowsSeen = chartRowsSeen()
    const specsSeen = chartSpecsSeen()
    // the renamed card's rows/chart_spec_json are exactly as before
    expect(rowsSeen).toContainEqual(BAR_CARD.rows)
    expect(specsSeen).toContainEqual(BAR_CARD.chart_spec_json)
    // and the chart itself is still rendered (a <canvas> for the bar card)
    expect(container.querySelectorAll('canvas').length).toBeGreaterThan(0)
    // the sibling's rows/chart_spec_json are untouched
    expect(rowsSeen).toContainEqual(NON_BAR_CARD.rows)
    expect(specsSeen).toContainEqual(NON_BAR_CARD.chart_spec_json)
  })

  it('does not trigger an extra fetchDashboard call on a successful rename (no full refetch)', async () => {
    mockedFetchDashboard.mockResolvedValue(dashboardWithCards([BAR_CARD, NON_BAR_CARD]))
    mockPrompt('Orders by category (renamed)')
    mockedRenameCard.mockResolvedValue(RENAMED_BAR_CARD_DETAIL)
    await act(async () => {
      root.render(<DashboardView dashboardId={1} />)
    })
    mockedFetchDashboard.mockClear()
    await clickRename('Orders by category')
    expect(mockedFetchDashboard).not.toHaveBeenCalled()
  })

  it('does not surface an error after a successful rename', async () => {
    mockedFetchDashboard.mockResolvedValue(dashboardWithCards([BAR_CARD, NON_BAR_CARD]))
    mockPrompt('Orders by category (renamed)')
    mockedRenameCard.mockResolvedValue(RENAMED_BAR_CARD_DETAIL)
    await act(async () => {
      root.render(<DashboardView dashboardId={1} />)
    })
    await clickRename('Orders by category')
    expect(container.textContent).not.toMatch(/error/i)
  })
})

describe('DashboardView - failed rename', () => {
  it('leaves the title unchanged when renameCard rejects', async () => {
    mockedFetchDashboard.mockResolvedValue(dashboardWithCards([BAR_CARD, NON_BAR_CARD]))
    mockPrompt('Orders by category (renamed)')
    mockedRenameCard.mockRejectedValue(new Error('PATCH /api/cards/10 failed: 404'))
    await act(async () => {
      root.render(<DashboardView dashboardId={1} />)
    })
    await clickRename('Orders by category')

    const texts = headingTexts()
    expect(texts).toContain('Orders by category')
    expect(texts).not.toContain('Orders by category (renamed)')
    expect(texts).toContain('Revenue over time')
  })

  it('surfaces an actionError message when renameCard rejects, instead of failing silently', async () => {
    mockedFetchDashboard.mockResolvedValue(dashboardWithCards([BAR_CARD, NON_BAR_CARD]))
    mockPrompt('Orders by category (renamed)')
    mockedRenameCard.mockRejectedValue(new Error('PATCH /api/cards/10 failed: 404'))
    await act(async () => {
      root.render(<DashboardView dashboardId={1} />)
    })
    await clickRename('Orders by category')
    expect(container.textContent).toMatch(/error/i)
  })

  it('surfaces the real rejection message somewhere in the rendered output', async () => {
    mockedFetchDashboard.mockResolvedValue(dashboardWithCards([BAR_CARD, NON_BAR_CARD]))
    mockPrompt('Orders by category (renamed)')
    mockedRenameCard.mockRejectedValue(new Error('PATCH /api/cards/10 failed: 404'))
    await act(async () => {
      root.render(<DashboardView dashboardId={1} />)
    })
    await clickRename('Orders by category')
    expect(container.textContent).toContain('PATCH /api/cards/10 failed: 404')
  })

  it('does not blank the rest of the card list on a failed rename', async () => {
    mockedFetchDashboard.mockResolvedValue(dashboardWithCards([BAR_CARD, NON_BAR_CARD]))
    mockPrompt('Orders by category (renamed)')
    mockedRenameCard.mockRejectedValue(new Error('PATCH /api/cards/10 failed: 404'))
    await act(async () => {
      root.render(<DashboardView dashboardId={1} />)
    })
    await clickRename('Orders by category')
    expect(headingTexts()).toHaveLength(2)
  })

  it('does not remove or alter the sibling card when a rename on a different card fails', async () => {
    mockedFetchDashboard.mockResolvedValue(dashboardWithCards([BAR_CARD, NON_BAR_CARD]))
    mockPrompt('Orders by category (renamed)')
    mockedRenameCard.mockRejectedValue(new Error('PATCH /api/cards/10 failed: 404'))
    await act(async () => {
      root.render(<DashboardView dashboardId={1} />)
    })
    mockedChartView.mockClear()
    await clickRename('Orders by category')

    expect(headingTexts()).toContain('Revenue over time')
    expect(chartRowsSeen()).toContainEqual(NON_BAR_CARD.rows)
  })

  it('does not trigger an extra fetchDashboard call on a failed rename', async () => {
    mockedFetchDashboard.mockResolvedValue(dashboardWithCards([BAR_CARD, NON_BAR_CARD]))
    mockPrompt('Orders by category (renamed)')
    mockedRenameCard.mockRejectedValue(new Error('PATCH /api/cards/10 failed: 404'))
    await act(async () => {
      root.render(<DashboardView dashboardId={1} />)
    })
    mockedFetchDashboard.mockClear()
    await clickRename('Orders by category')
    expect(mockedFetchDashboard).not.toHaveBeenCalled()
  })
})

// Tests below are from
// plans/briefs/2026-08-08-dashboard-card-drag-reposition.md.
describe('DashboardView - drag-to-reposition, optimistic reorder', () => {
  it('reorders the local list immediately on drop, before repositionCard resolves', async () => {
    mockedFetchDashboard.mockResolvedValue(
      dashboardWithCards([BAR_CARD, NON_BAR_CARD, THIRD_CARD]),
    )
    // Never resolves -- isolates the assertion to the optimistic,
    // pre-persistence reorder, per the brief's "reorder the local
    // dashboard.cards array immediately (optimistic UI)" Constraint.
    mockedRepositionCard.mockReturnValue(new Promise(() => {}))
    await act(async () => {
      root.render(<DashboardView dashboardId={1} />)
    })
    expect(headingTexts()).toEqual([
      'Orders by category',
      'Revenue over time',
      'Average order value',
    ])

    // Drag the last card onto the first card's slot.
    await dragCardOnto('Average order value', 'Orders by category')

    expect(headingTexts()).toEqual([
      'Average order value',
      'Orders by category',
      'Revenue over time',
    ])
  })

  it('does not corrupt any card\'s own rows/chart_spec_json while reordering', async () => {
    mockedFetchDashboard.mockResolvedValue(
      dashboardWithCards([BAR_CARD, NON_BAR_CARD, THIRD_CARD]),
    )
    mockedRepositionCard.mockReturnValue(new Promise(() => {}))
    await act(async () => {
      root.render(<DashboardView dashboardId={1} />)
    })
    mockedChartView.mockClear()
    await dragCardOnto('Average order value', 'Orders by category')

    const rowsSeen = chartRowsSeen()
    expect(rowsSeen).toContainEqual(BAR_CARD.rows)
    expect(rowsSeen).toContainEqual(THIRD_CARD.rows)
    // NON_BAR_CARD is not chart_type 'bar' so ChartView is never invoked
    // for it, per the existing bar/non-bar precedent above.
  })
})

describe('DashboardView - drag-to-reposition, persisted positions', () => {
  it('calls repositionCard with the correct renumbered position for every card whose position changed, including siblings shifted by the drag (not just the dragged card)', async () => {
    mockedFetchDashboard.mockResolvedValue(
      dashboardWithCards([BAR_CARD, NON_BAR_CARD, THIRD_CARD]),
    )
    mockedRepositionCard.mockResolvedValue({ ...BAR_CARD, rows: undefined })
    await act(async () => {
      root.render(<DashboardView dashboardId={1} />)
    })

    // Drag the last card (position 2) to the first slot (position 0):
    // every one of the three cards' positions shifts, not only the
    // dragged one.
    await dragCardOnto('Average order value', 'Orders by category')

    expect(mockedRepositionCard).toHaveBeenCalledWith(THIRD_CARD.id, 0)
    expect(mockedRepositionCard).toHaveBeenCalledWith(BAR_CARD.id, 1)
    expect(mockedRepositionCard).toHaveBeenCalledWith(NON_BAR_CARD.id, 2)
    expect(mockedRepositionCard).toHaveBeenCalledTimes(3)
  })

  it('does not call repositionCard for a sibling whose position is unaffected by the drag', async () => {
    mockedFetchDashboard.mockResolvedValue(
      dashboardWithCards([BAR_CARD, NON_BAR_CARD, THIRD_CARD]),
    )
    mockedRepositionCard.mockResolvedValue({ ...BAR_CARD, rows: undefined })
    await act(async () => {
      root.render(<DashboardView dashboardId={1} />)
    })

    // Swap the first two cards; THIRD_CARD (already last) keeps position 2.
    await dragCardOnto('Orders by category', 'Revenue over time')

    expect(mockedRepositionCard).toHaveBeenCalledWith(NON_BAR_CARD.id, 0)
    expect(mockedRepositionCard).toHaveBeenCalledWith(BAR_CARD.id, 1)
    expect(mockedRepositionCard).not.toHaveBeenCalledWith(THIRD_CARD.id, expect.anything())
    expect(mockedRepositionCard).toHaveBeenCalledTimes(2)
  })

  it('does not trigger an extra fetchDashboard call on a successful reposition (no full refetch)', async () => {
    mockedFetchDashboard.mockResolvedValue(
      dashboardWithCards([BAR_CARD, NON_BAR_CARD, THIRD_CARD]),
    )
    mockedRepositionCard.mockResolvedValue({ ...BAR_CARD, rows: undefined })
    await act(async () => {
      root.render(<DashboardView dashboardId={1} />)
    })
    mockedFetchDashboard.mockClear()
    await dragCardOnto('Orders by category', 'Revenue over time')
    expect(mockedFetchDashboard).not.toHaveBeenCalled()
  })

  it('does not surface an error after a successful reposition', async () => {
    mockedFetchDashboard.mockResolvedValue(
      dashboardWithCards([BAR_CARD, NON_BAR_CARD, THIRD_CARD]),
    )
    mockedRepositionCard.mockResolvedValue({ ...BAR_CARD, rows: undefined })
    await act(async () => {
      root.render(<DashboardView dashboardId={1} />)
    })
    await dragCardOnto('Orders by category', 'Revenue over time')
    expect(container.textContent).not.toMatch(/error/i)
  })
})

describe('DashboardView - drag-to-reposition, failed persist', () => {
  it('reverts the local order back to its pre-drag arrangement when a repositionCard call rejects', async () => {
    mockedFetchDashboard.mockResolvedValue(
      dashboardWithCards([BAR_CARD, NON_BAR_CARD, THIRD_CARD]),
    )
    // Only the non-dragged sibling's persist call fails -- proves a
    // revert happens even when the dragged card's own call would have
    // succeeded, since the brief requires reverting "on any
    // repositionCard failure".
    mockedRepositionCard.mockImplementation((id: number) => {
      if (id === NON_BAR_CARD.id) {
        return Promise.reject(new Error('PATCH /api/cards/11 failed: 500'))
      }
      return Promise.resolve({ ...BAR_CARD, rows: undefined })
    })
    await act(async () => {
      root.render(<DashboardView dashboardId={1} />)
    })

    await dragCardOnto('Orders by category', 'Revenue over time')

    expect(headingTexts()).toEqual([
      'Orders by category',
      'Revenue over time',
      'Average order value',
    ])
  })

  it('surfaces the failure via actionError instead of failing silently', async () => {
    mockedFetchDashboard.mockResolvedValue(
      dashboardWithCards([BAR_CARD, NON_BAR_CARD, THIRD_CARD]),
    )
    mockedRepositionCard.mockImplementation((id: number) => {
      if (id === NON_BAR_CARD.id) {
        return Promise.reject(new Error('PATCH /api/cards/11 failed: 500'))
      }
      return Promise.resolve({ ...BAR_CARD, rows: undefined })
    })
    await act(async () => {
      root.render(<DashboardView dashboardId={1} />)
    })

    await dragCardOnto('Orders by category', 'Revenue over time')

    expect(container.textContent).toMatch(/error/i)
  })

  it('surfaces the real rejection message somewhere in the rendered output', async () => {
    mockedFetchDashboard.mockResolvedValue(
      dashboardWithCards([BAR_CARD, NON_BAR_CARD, THIRD_CARD]),
    )
    mockedRepositionCard.mockImplementation((id: number) => {
      if (id === NON_BAR_CARD.id) {
        return Promise.reject(new Error('PATCH /api/cards/11 failed: 500'))
      }
      return Promise.resolve({ ...BAR_CARD, rows: undefined })
    })
    await act(async () => {
      root.render(<DashboardView dashboardId={1} />)
    })

    await dragCardOnto('Orders by category', 'Revenue over time')

    expect(container.textContent).toContain('PATCH /api/cards/11 failed: 500')
  })

  it("leaves a card unrelated to the drag's own rows/chart_spec_json untouched after a failed reposition", async () => {
    mockedFetchDashboard.mockResolvedValue(
      dashboardWithCards([BAR_CARD, NON_BAR_CARD, THIRD_CARD]),
    )
    mockedRepositionCard.mockImplementation((id: number) => {
      if (id === NON_BAR_CARD.id) {
        return Promise.reject(new Error('PATCH /api/cards/11 failed: 500'))
      }
      return Promise.resolve({ ...BAR_CARD, rows: undefined })
    })
    await act(async () => {
      root.render(<DashboardView dashboardId={1} />)
    })
    mockedChartView.mockClear()

    // The drag only involves BAR_CARD and NON_BAR_CARD; THIRD_CARD is
    // unrelated to this drag entirely.
    await dragCardOnto('Orders by category', 'Revenue over time')

    expect(headingTexts()).toContain('Average order value')
    expect(chartRowsSeen()).toContainEqual(THIRD_CARD.rows)
  })

  it('does not trigger an extra fetchDashboard call on a failed reposition', async () => {
    mockedFetchDashboard.mockResolvedValue(
      dashboardWithCards([BAR_CARD, NON_BAR_CARD, THIRD_CARD]),
    )
    mockedRepositionCard.mockRejectedValue(new Error('PATCH /api/cards/10 failed: 500'))
    await act(async () => {
      root.render(<DashboardView dashboardId={1} />)
    })
    mockedFetchDashboard.mockClear()
    await dragCardOnto('Orders by category', 'Revenue over time')
    expect(mockedFetchDashboard).not.toHaveBeenCalled()
  })
})
