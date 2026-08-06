// Tests for the new `FollowUpChips` component from
// plans/briefs/2026-08-06-follow-up-chips.md.
//
// Runner: plain vitest-style tests (`describe`/`it`/`expect` from the
// 'vitest' package), rendered with `react-dom/client` directly against a
// jsdom `document` (no @testing-library -- kept to the minimum extra
// tooling: a test runner + a DOM environment), matching the precedent set
// by web/tests/SqlDetails.test.tsx. This repo has NO frontend test runner
// configured yet (confirmed via web/package.json) -- these cannot execute
// until one is added. Expected command once available:
// `cd web && npx vitest run` (requires `vitest` + a jsdom environment as
// new devDependencies -- not installed by this change, per CLAUDE.md's "no
// new dependencies without asking").
//
// Written from the brief alone, before web/src/components/FollowUpChips.tsx
// exists. The brief's contract: `FollowUpChips({ followUps, onSelect })`
// renders `null` when `followUps.length === 0`; otherwise one
// `<button type="button">` per entry, `onClick={() => onSelect(text)}`.
// Explicitly out-of-scope per the brief: "Deduplicating, capping, or
// reordering the follow-ups list" -- render exactly what's given,
// including duplicate entries. Tests below hold that line: they assert
// the exact rendered set (including duplicates), not a de-duplicated or
// re-ordered one.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createRoot, type Root } from 'react-dom/client'
import { act } from 'react-dom/test-utils'
import { FollowUpChips } from '../src/components/FollowUpChips'

let container: HTMLDivElement
let root: Root

beforeEach(() => {
  container = document.createElement('div')
  document.body.appendChild(container)
  root = createRoot(container)
})

afterEach(() => {
  act(() => {
    root.unmount()
  })
  container.remove()
})

function renderChips(followUps: string[], onSelect: (text: string) => void) {
  act(() => {
    root.render(<FollowUpChips followUps={followUps} onSelect={onSelect} />)
  })
}

function click(el: HTMLElement) {
  act(() => {
    el.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }))
  })
}

describe('FollowUpChips', () => {
  it('renders nothing when followUps is empty', () => {
    renderChips([], vi.fn())
    expect(container.innerHTML).toBe('')
  })

  it('renders no buttons when followUps is empty', () => {
    renderChips([], vi.fn())
    expect(container.querySelectorAll('button')).toHaveLength(0)
  })

  it('renders exactly one button per follow-up entry', () => {
    renderChips(
      ['What about last quarter?', 'Which category grew fastest?', 'And by region?'],
      vi.fn(),
    )
    const buttons = container.querySelectorAll('button')
    expect(buttons).toHaveLength(3)
    expect(Array.from(buttons).map((b) => b.textContent)).toEqual([
      'What about last quarter?',
      'Which category grew fastest?',
      'And by region?',
    ])
  })

  it('renders every button with type="button" (never submits a surrounding form)', () => {
    renderChips(['What about last quarter?', 'And by region?'], vi.fn())
    const buttons = container.querySelectorAll('button')
    expect(buttons).toHaveLength(2)
    buttons.forEach((button) => {
      expect(button.getAttribute('type')).toBe('button')
    })
  })

  it('renders duplicate entries as separate buttons -- no deduplication', () => {
    renderChips(['same follow-up', 'same follow-up', 'different one'], vi.fn())
    const buttons = container.querySelectorAll('button')
    expect(buttons).toHaveLength(3)
    expect(Array.from(buttons).map((b) => b.textContent)).toEqual([
      'same follow-up',
      'same follow-up',
      'different one',
    ])
  })

  it('renders entries in the exact order given -- no reordering', () => {
    renderChips(['third', 'first', 'second'], vi.fn())
    const buttons = container.querySelectorAll('button')
    expect(Array.from(buttons).map((b) => b.textContent)).toEqual([
      'third',
      'first',
      'second',
    ])
  })

  it('calls onSelect with the exact clicked button\'s text', () => {
    const onSelect = vi.fn()
    renderChips(['What about last quarter?', 'And by region?'], onSelect)
    const buttons = container.querySelectorAll('button')
    click(buttons[1] as HTMLElement)
    expect(onSelect).toHaveBeenCalledTimes(1)
    expect(onSelect).toHaveBeenCalledWith('And by region?')
  })

  it('calls onSelect once per click, matching the specific button clicked among duplicates', () => {
    const onSelect = vi.fn()
    renderChips(['same follow-up', 'same follow-up', 'different one'], onSelect)
    const buttons = container.querySelectorAll('button')
    click(buttons[2] as HTMLElement)
    expect(onSelect).toHaveBeenCalledTimes(1)
    expect(onSelect).toHaveBeenCalledWith('different one')
  })

  it('does not call onSelect on render alone', () => {
    const onSelect = vi.fn()
    renderChips(['What about last quarter?'], onSelect)
    expect(onSelect).not.toHaveBeenCalled()
  })
})
