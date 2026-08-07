// Shared by any api.ts test that needs global `fetch` stubbed for one
// call with an auto-unstub afterEach -- extracted once the same block
// appeared in a third test file (no-slop rubric: third occurrence means
// extract).
import { afterEach, vi } from 'vitest'

export function mockFetchOnce(response: { ok: boolean; status: number; body?: unknown }) {
  const jsonFn = vi.fn().mockResolvedValue(response.body ?? {})
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
