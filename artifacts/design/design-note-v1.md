# Design note — chat + dashboard surfaces (v1)

Date: 2026-08-02
Slice: pre-M5/M6 design contract (approved ahead of build)
Surface: the app's two pages — chat (PRD F1) and dashboard (PRD F6)

## Who uses this and what are they trying to do
Analyst asks questions and wants to trust answers fast; executive opens the
dashboard and reads numbers with zero interaction; a reviewer must find it
polished in a 3-minute demo.

## The decision
Design-in-code: HTML/Tailwind mockups in this folder are the visual
contracts (chat-v1.html, dashboard-v1.html). shadcn/ui idiom — zinc
neutrals, white cards, hairline borders, rounded-xl, Inter, single indigo
accent for brand moments only. Charts follow the dataviz method: validated
reference palette (series-1 blue #2a78d6 for all single-measure charts;
slots 1–3 only for the donut), thin marks, hairline grid, muted ink,
tabular numerals, direct labels only on the headline point (Nov '17 peak).
Safety posture is visible in the chrome: "Olist dataset connected" badge,
"AI-generated — verify before decisions" under the chat input, read-only
note in the footer.

Approved: chat-v1 ✅ and dashboard-v1 ✅ (user, 2026-08-02, in-session).
Both mockups are now the binding visual contracts for the M5/M6 slices —
gate check #2 compares the built surfaces against these files.

## Rejected alternative
External design tools (Google Stitch / Figma-via-MCP). Rejected because
exports must be re-implemented in the stack (drift at the translation
boundary), live outside git, and this session's MCP registry has no design
connector anyway. Tailwind mockups carry their classes straight into the
React build.

## Why
Zero new tools; contracts versioned next to the code they bind; gate
check #2 ("built matches approved design") becomes a near-mechanical diff.

## Open design debts
- Dark mode: not designed in v1 (light-only demo). Palette dark steps are
  documented if it's ever promoted to a slice.
- Chat answer state (summary + chart + table + explanation blocks) is not
  yet mocked — only the empty state. Mock it when the M5 slice is briefed.
- Mobile: grid collapses to one column by construction, but nothing below
  ~768px has been reviewed.
- Tailwind CDN in mockups is mockup-only; the app uses the Vite build.
