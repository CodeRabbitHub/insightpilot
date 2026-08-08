// Tests for plans/briefs/2026-08-08-app-strictmode-fetch-guard.md.
//
// Runner: plain vitest-style tests (`describe`/`it`/`expect`/`vi` from the
// 'vitest' package), rendered with `react-dom/client` directly against a
// jsdom `document` (no @testing-library), matching the precedent set by
// web/tests/SqlDetails.test.tsx, web/tests/FollowUpChips.test.tsx, and
// web/tests/DashboardView.test.tsx. This repo has NO frontend test runner
// configured yet (confirmed via web/package.json: no test script, no
// vitest/jsdom devDependency) -- these cannot execute until one is added.
// Expected command once available: `cd web && npx vitest run` (requires
// `vitest` + a jsdom environment as new devDependencies).
//
// Scope, per the brief's Outputs, is ONLY the conversations-list mount
// effect's StrictMode double-invoke race -- not a full App.tsx test suite.
// The conversation-detail effect (already correctly guarded),
// ConversationList, ConversationDetailView, message-sending, and
// view-switching are all out of scope and untouched here.
//
// Deviation from DashboardView.test.tsx's testing trick: that component's
// mount effect is keyed on a `dashboardId` prop, so its tests forced a
// second invocation via a prop change on rerender. App.tsx's
// conversations-list effect has a `[]` dependency array -- it only ever
// re-runs via React 18 StrictMode's own dev-only double-invoke, not via any
// prop/state change, so a prop-change trick doesn't transfer here. Instead,
// these tests render `<StrictMode><App /></StrictMode>` directly (matching
// web/src/main.tsx's real production wrapping exactly) and let React's real
// double-invoke fire for real: Vitest runs under a non-production
// `NODE_ENV`, so StrictMode's dev-only extra mount/cleanup/remount pass
// genuinely happens within the same `act()` call that performs the initial
// render, giving deterministic control (via the `deferred()` helper below,
// same shape as DashboardView.test.tsx's) over which of the two overlapping
// `fetchConversations` calls resolves/rejects first.
//
// `../src/api` is mocked at the module boundary, but `errorMessage` and
// `asAssistantContent` are kept as their REAL implementations via
// `vi.importActual` (they are pure sync utilities the component depends on
// for correct rendering, not part of what this slice is fixing) -- only
// `fetchConversations`, `fetchConversation`, and `postConversationMessage`
// are replaced with `vi.fn()`. The latter two are mocked but never driven
// by any test below (every test keeps `selectedId === null`, so the
// conversation-detail effect and send handler never fire) -- they're
// stubbed only so the whole `../src/api` module resolves without a real
// `fetch` call, matching every test's need to avoid network access.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { StrictMode } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { act } from 'react-dom/test-utils'
import { fetchConversations, type ConversationSummary } from '../src/api'
import App from '../src/App'

vi.mock('../src/api', async () => {
  const actual =
    await vi.importActual<typeof import('../src/api')>('../src/api')
  return {
    ...actual,
    fetchConversations: vi.fn(),
    fetchConversation: vi.fn(),
    postConversationMessage: vi.fn(),
  }
})

const mockedFetchConversations = fetchConversations as unknown as ReturnType<typeof vi.fn>

// Real ConversationSummary shape per web/src/api.ts: id, title, created_at.
const STALE_CONVERSATIONS: ConversationSummary[] = [
  { id: 1, title: 'Stale conversation', created_at: '2026-08-01T00:00:00Z' },
]
const FRESH_CONVERSATIONS: ConversationSummary[] = [
  { id: 2, title: 'Fresh conversation', created_at: '2026-08-02T00:00:00Z' },
]

let container: HTMLDivElement
let root: Root

beforeEach(() => {
  mockedFetchConversations.mockReset()
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

// Resolves/rejects on demand from outside the executor, letting a test
// control exactly when a given `fetchConversations` call settles,
// independent of when React's StrictMode double-invoke fires its second
// effect run -- needed to simulate a "stale" call whose own effect's
// cleanup has already run by the time it settles, per
// plans/briefs/2026-08-08-app-strictmode-fetch-guard.md.
function deferred<T>() {
  let resolve!: (value: T) => void
  let reject!: (reason?: unknown) => void
  const promise = new Promise<T>((res, rej) => {
    resolve = res
    reject = rej
  })
  return { promise, resolve, reject }
}

describe('App - StrictMode conversations-list fetch guard (stale call ignored)', () => {
  it('does not render a stale fetchConversations resolution that lands after the double-invoke\'s first (cleaned-up) run', async () => {
    const staleCall = deferred<ConversationSummary[]>()
    const freshCall = deferred<ConversationSummary[]>()
    mockedFetchConversations.mockImplementationOnce(() => staleCall.promise)
    mockedFetchConversations.mockImplementationOnce(() => freshCall.promise)

    await act(async () => {
      root.render(
        <StrictMode>
          <App />
        </StrictMode>,
      )
    })
    // Sanity check that StrictMode's real double-invoke actually fired
    // twice here, not that the effect merely ran once.
    expect(mockedFetchConversations).toHaveBeenCalledTimes(2)

    await act(async () => {
      freshCall.resolve(FRESH_CONVERSATIONS)
    })
    expect(container.textContent).toContain('Fresh conversation')

    // The stale (first-invocation) call resolves late -- well after its
    // own effect's cleanup already ran during the double-invoke -- and
    // must be ignored.
    await act(async () => {
      staleCall.resolve(STALE_CONVERSATIONS)
    })

    expect(container.textContent).not.toContain('Stale conversation')
    expect(container.textContent).toContain('Fresh conversation')
  })

  it('does not surface a stale fetchConversations rejection that lands after the double-invoke\'s first (cleaned-up) run', async () => {
    const staleCall = deferred<ConversationSummary[]>()
    const freshCall = deferred<ConversationSummary[]>()
    mockedFetchConversations.mockImplementationOnce(() => staleCall.promise)
    mockedFetchConversations.mockImplementationOnce(() => freshCall.promise)

    await act(async () => {
      root.render(
        <StrictMode>
          <App />
        </StrictMode>,
      )
    })

    await act(async () => {
      freshCall.resolve(FRESH_CONVERSATIONS)
    })
    expect(container.textContent).toContain('Fresh conversation')
    expect(container.textContent).not.toMatch(/error/i)

    // The stale call rejects late -- after its own effect's cleanup
    // already ran -- and must not surface as an error, nor replace the
    // already-loaded fresh conversation list.
    await act(async () => {
      staleCall.reject(new Error('GET /api/conversations failed: 500'))
    })

    expect(container.textContent).not.toMatch(/error/i)
    expect(container.textContent).toContain('Fresh conversation')
    expect(container.textContent).not.toContain('Stale conversation')
  })

  it('does not clear the loading indicator or render stale data when the stale call settles before the fresh call, while the fresh call is still pending', async () => {
    // Distinct from the two tests above (stale settling AFTER the fresh
    // one already loaded): here the stale call settles FIRST, while the
    // fresh call is still in flight. Without the `finally`-guard
    // specifically, the stale invocation's unconditional `setLoading(false)`
    // would flip the view out of "loading" while the fresh fetch is still
    // pending -- and since `setConversations` would also fire unguarded,
    // the stale list would render as if it were the real answer.
    const staleCall = deferred<ConversationSummary[]>()
    const freshCall = deferred<ConversationSummary[]>()
    mockedFetchConversations.mockImplementationOnce(() => staleCall.promise)
    mockedFetchConversations.mockImplementationOnce(() => freshCall.promise)

    await act(async () => {
      root.render(
        <StrictMode>
          <App />
        </StrictMode>,
      )
    })

    await act(async () => {
      staleCall.resolve(STALE_CONVERSATIONS)
    })

    expect(container.textContent).toMatch(/loading/i)
    expect(container.textContent).not.toContain('Stale conversation')

    await act(async () => {
      freshCall.resolve(FRESH_CONVERSATIONS)
    })

    expect(container.textContent).not.toMatch(/loading/i)
    expect(container.textContent).toContain('Fresh conversation')
    expect(container.textContent).not.toContain('Stale conversation')
  })
})

describe('App - conversations-list mount effect, normal single-invocation path unaffected', () => {
  it('shows loading then loaded exactly once, with fetchConversations called exactly once, when rendered without StrictMode', async () => {
    const call = deferred<ConversationSummary[]>()
    mockedFetchConversations.mockReturnValueOnce(call.promise)

    act(() => {
      root.render(<App />)
    })
    expect(container.textContent).toMatch(/loading/i)

    await act(async () => {
      call.resolve(FRESH_CONVERSATIONS)
    })

    expect(container.textContent).not.toMatch(/loading/i)
    expect(container.textContent).toContain('Fresh conversation')
    expect(mockedFetchConversations).toHaveBeenCalledTimes(1)
  })

  it('shows loading then an error exactly once, with fetchConversations called exactly once, when rendered without StrictMode', async () => {
    const call = deferred<ConversationSummary[]>()
    mockedFetchConversations.mockReturnValueOnce(call.promise)

    act(() => {
      root.render(<App />)
    })
    expect(container.textContent).toMatch(/loading/i)

    await act(async () => {
      call.reject(new Error('GET /api/conversations failed: 500'))
    })

    expect(container.textContent).not.toMatch(/loading/i)
    expect(container.textContent).toContain('GET /api/conversations failed: 500')
    expect(mockedFetchConversations).toHaveBeenCalledTimes(1)
  })
})
