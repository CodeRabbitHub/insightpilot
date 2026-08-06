// Tests for the sql/explanation extraction added to `asAssistantContent()`
// by plans/briefs/2026-08-06-sql-explanation-viewer.md.
//
// Runner: these are plain vitest-style tests (`describe`/`it`/`expect` from
// the 'vitest' package). This repo has NO frontend test runner configured
// yet (confirmed via web/package.json: no test script, no vitest/jest
// devDependency) -- they cannot execute until one is added. Expected
// command once available: `cd web && npx vitest run`.
//
// Written from the brief alone, before the sql/explanation extraction
// exists in web/src/api.ts. The brief's Outputs section names
// `asAssistantContent()` first ("... (or a small sibling accessor) exposes
// sql and analysis.explanation alongside the existing rows/chartSpec"),
// so these tests target that function directly. If the implementation
// instead adds a differently-named sibling accessor, this import will
// fail to resolve and that mismatch should be reconciled against the
// brief, not silently patched here.
//
// Null-safety contract assumed below: a message missing/mistyping any of
// {rows, analysis, chart_spec, sql, explanation} returns null from
// asAssistantContent(), mirroring the exact defensive style the function
// already uses today for rows/analysis/chart_spec (api.ts's own comment:
// "the one runtime check that a given message actually has the shape
// [it] needs"). This is a genuine design choice the brief leaves open
// ("or a small sibling accessor") -- flag it for reconciliation if the
// implementation instead partially degrades instead of returning null.
import { describe, expect, it } from 'vitest'
import { asAssistantContent } from '../src/api'

const validChartSpec = { chart_type: 'bar', x: 'category', y: 'count' }

function realShapedMessage(overrides: Record<string, unknown> = {}) {
  return {
    sql: 'SELECT product_category_name, count(*) FROM olist.orders GROUP BY 1',
    rows: [{ category: 'toys', count: 12 }],
    analysis: {
      summary: 'Toys lead.',
      explanation: 'The query joined orders to order_items and grouped by category.',
      chart_spec: validChartSpec,
      follow_ups: ['What about last quarter?'],
    },
    ...overrides,
  }
}

describe('asAssistantContent - sql/explanation extraction', () => {
  it('exposes sql and explanation for a fully-shaped assistant message', () => {
    const content = asAssistantContent(realShapedMessage())
    expect(content).not.toBeNull()
    expect(content?.sql).toBe(
      'SELECT product_category_name, count(*) FROM olist.orders GROUP BY 1',
    )
    expect(content?.explanation).toBe(
      'The query joined orders to order_items and grouped by category.',
    )
  })

  it('still exposes the existing rows/chartSpec fields unchanged alongside the new ones', () => {
    const content = asAssistantContent(realShapedMessage())
    expect(content?.rows).toEqual([{ category: 'toys', count: 12 }])
    expect(content?.chartSpec).toEqual(validChartSpec)
  })

  it('returns null (matching the existing shape-check convention used for rows/chart_spec) when sql is missing entirely', () => {
    const { sql: _drop, ...withoutSql } = realShapedMessage()
    expect(asAssistantContent(withoutSql)).toBeNull()
  })

  it('returns null when sql is present but the wrong type (not a string)', () => {
    const content = asAssistantContent(realShapedMessage({ sql: 12345 }))
    expect(content).toBeNull()
  })

  it('returns null when analysis.explanation is missing', () => {
    const message = realShapedMessage()
    const analysis = message.analysis as Record<string, unknown>
    delete analysis.explanation
    expect(asAssistantContent(message)).toBeNull()
  })

  it('returns null when analysis.explanation is present but the wrong type (not a string)', () => {
    const message = realShapedMessage()
    const analysis = message.analysis as Record<string, unknown>
    analysis.explanation = { nested: 'not a string' }
    expect(asAssistantContent(message)).toBeNull()
  })

  it('does not throw and returns null for a legacy message with no sql/analysis field at all (pre-analysis-field message)', () => {
    let content: ReturnType<typeof asAssistantContent> = null
    expect(() => {
      content = asAssistantContent({ question: 'How many orders were placed?' })
    }).not.toThrow()
    expect(content).toBeNull()
  })

  it('does not throw and returns null for a legacy chart-only message shape (rows/chart_spec but no sql, no explanation)', () => {
    // This is the exact shape the previous (chart-view) slice's
    // AssistantContent covered on its own; this slice's brief adds sql/
    // explanation "alongside" that shape, so a message missing the new
    // fields entirely must not crash the accessor.
    const legacyChartOnly = {
      rows: [{ category: 'toys', count: 12 }],
      analysis: { summary: 'x', chart_spec: validChartSpec, follow_ups: [] },
    }
    let content: ReturnType<typeof asAssistantContent> = null
    expect(() => {
      content = asAssistantContent(legacyChartOnly)
    }).not.toThrow()
    expect(content).toBeNull()
  })
})

// Tests for the `followUps` extraction added to `asAssistantContent()` by
// plans/briefs/2026-08-06-follow-up-chips.md.
//
// Written from that brief alone, before the extraction exists in
// web/src/api.ts. The brief specifies: "`asAssistantContent()` extracts
// [followUps] from `analysis.follow_ups` with an `Array.isArray` guard
// (same looseness as the existing `rows` guard -- no per-element
// validation), returning `null` for the whole object if it's not an
// array (matching the existing all-or-nothing guard-clause style already
// tested ... for `sql`/`explanation`)." Tests below target exactly that:
// the guard is Array.isArray only, applied to the whole result the same
// way the other fields' guards are, with no inspection of individual
// entries' types.
describe('asAssistantContent - followUps extraction', () => {
  it('exposes followUps unchanged for a fully-shaped assistant message', () => {
    const content = asAssistantContent(
      realShapedMessage({
        analysis: {
          ...realShapedMessage().analysis,
          follow_ups: ['What about last quarter?', 'Which category grew fastest?'],
        },
      }),
    )
    expect(content).not.toBeNull()
    expect(content?.followUps).toEqual([
      'What about last quarter?',
      'Which category grew fastest?',
    ])
  })

  it('treats an empty follow_ups array as valid (not null) and exposes it as an empty array', () => {
    const content = asAssistantContent(
      realShapedMessage({
        analysis: { ...realShapedMessage().analysis, follow_ups: [] },
      }),
    )
    expect(content).not.toBeNull()
    expect(content?.followUps).toEqual([])
  })

  it('does not validate individual entries -- an array containing non-string elements still passes the guard (same looseness as the rows check)', () => {
    const content = asAssistantContent(
      realShapedMessage({
        analysis: {
          ...realShapedMessage().analysis,
          follow_ups: ['a real follow-up', 42, null],
        },
      }),
    )
    expect(content).not.toBeNull()
    expect(content?.followUps).toEqual(['a real follow-up', 42, null])
  })

  it('returns null for the whole object when follow_ups is present but not an array (a string)', () => {
    const content = asAssistantContent(
      realShapedMessage({
        analysis: {
          ...realShapedMessage().analysis,
          follow_ups: 'What about last quarter?',
        },
      }),
    )
    expect(content).toBeNull()
  })

  it('returns null for the whole object when follow_ups is present but not an array (an object)', () => {
    const content = asAssistantContent(
      realShapedMessage({
        analysis: {
          ...realShapedMessage().analysis,
          follow_ups: { text: 'What about last quarter?' },
        },
      }),
    )
    expect(content).toBeNull()
  })

  it('returns null for the whole object when follow_ups is missing entirely', () => {
    const message = realShapedMessage()
    const analysis = message.analysis as Record<string, unknown>
    delete analysis.follow_ups
    expect(asAssistantContent(message)).toBeNull()
  })
})
