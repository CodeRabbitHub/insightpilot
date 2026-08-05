// Tests for the new collapsed-by-default "View SQL" section from
// plans/briefs/2026-08-06-sql-explanation-viewer.md.
//
// Runner: plain vitest-style tests (`describe`/`it`/`expect` from the
// 'vitest' package), rendered with `react-dom/client` directly against a
// jsdom `document` (no @testing-library -- kept to the minimum extra
// tooling: a test runner + a DOM environment). This repo has NO frontend
// test runner configured yet (confirmed via web/package.json) -- these
// cannot execute until one is added. Expected command once available:
// `cd web && npx vitest run` (requires `vitest` + a jsdom environment as
// new devDependencies -- not installed by this change, per CLAUDE.md's "no
// new dependencies without asking").
//
// The brief allows either a native `<details>`/`<summary>` disclosure
// widget or a toggle button + conditional render for the collapsed
// section ("a collapsed-by-default `<details>`/toggle-button section").
// Tests below detect which was used and assert the matching invariant,
// rather than assuming one specific implementation. Note: jsdom does not
// perform real layout/CSS, so it cannot verify visual hiding the way the
// brief's own done-check (Playwright screenshot) does -- these tests
// verify DOM state (the `open` property, or conditional mounting) as the
// closest same-tool proxy for "collapsed by default".
//
// Written from the brief alone, before web/src/components/SqlDetails.tsx
// exists.
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { createRoot, type Root } from 'react-dom/client'
import { act } from 'react-dom/test-utils'
import { SqlDetails } from '../src/components/SqlDetails'

const SQL = 'SELECT product_category_name, count(*) FROM olist.orders GROUP BY 1'
const EXPLANATION =
  'The query joined orders to order_items and grouped by category.'

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

function renderSqlDetails() {
  act(() => {
    root.render(<SqlDetails sql={SQL} explanation={EXPLANATION} />)
  })
}

function findToggle(): HTMLElement {
  const summary = container.querySelector('summary')
  if (summary) return summary as HTMLElement
  const button = container.querySelector('button')
  if (button) return button as HTMLElement
  throw new Error(
    'SqlDetails rendered neither a <summary> nor a <button> toggle control',
  )
}

function click(el: HTMLElement) {
  act(() => {
    el.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }))
  })
}

describe('SqlDetails - collapsed-by-default "View SQL" section', () => {
  it('renders a toggle control labeled for viewing the SQL', () => {
    renderSqlDetails()
    expect(findToggle().textContent).toMatch(/view sql/i)
  })

  it('starts collapsed: a native <details> element (if used) has open=false before any click', () => {
    renderSqlDetails()
    const details = container.querySelector('details')
    if (details) {
      expect((details as HTMLDetailsElement).open).toBe(false)
    }
  })

  it('starts collapsed: if SQL/explanation are conditionally rendered (no <details> used), neither appears in the DOM before any click', () => {
    renderSqlDetails()
    const details = container.querySelector('details')
    if (!details) {
      expect(container.textContent).not.toContain(SQL)
      expect(container.textContent).not.toContain(EXPLANATION)
    }
  })

  it('clicking the toggle reveals the real SQL text inside a <pre> element', () => {
    renderSqlDetails()
    click(findToggle())
    const pre = container.querySelector('pre')
    expect(pre).not.toBeNull()
    expect(pre?.textContent).toContain(SQL)
  })

  it('clicking the toggle reveals the real explanation text', () => {
    renderSqlDetails()
    click(findToggle())
    expect(container.textContent).toContain(EXPLANATION)
  })

  it('clicking a native <details> toggle (if used) flips it to open=true', () => {
    renderSqlDetails()
    const details = container.querySelector('details')
    if (details) {
      click(findToggle())
      expect((details as HTMLDetailsElement).open).toBe(true)
    }
  })

  it('renders the SQL as plain text with no syntax-highlighting markup (no nested span/code inside the <pre>)', () => {
    renderSqlDetails()
    click(findToggle())
    const pre = container.querySelector('pre')
    expect(pre).not.toBeNull()
    expect(pre?.querySelector('span, code')).toBeNull()
  })
})
