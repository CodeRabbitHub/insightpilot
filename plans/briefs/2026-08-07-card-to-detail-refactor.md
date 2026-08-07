# Brief — card-to-detail-refactor

Date: 2026-08-07
Milestone: M6 Dashboard (tech-debt cleanup surfaced by M6's card routes — no
new behavior)

Goal:
Extract the 4-times-duplicated `DashboardCard`→`DashboardCardDetail`
ORM-mapping logic in `app/main.py` into one `_card_to_detail(card)` helper
and use it at all four call sites, with zero behavior change.

Constraints:
- Byte-identical HTTP responses before and after — this is a pure
  refactor, not a behavior change. No route's status codes, field names,
  or field values may change.
- No new dependency, no new endpoint, no schema/model change.
- Backend only (`app/main.py`) — no frontend, no test-behavior change
  beyond what's needed to keep the existing suite green.
- Follow the codebase's existing style: a private module-level function
  (leading underscore, matching `_persist_exchange`'s existing naming
  convention in the same file), not a class or a new module.

Inputs:
- `app/main.py`'s four occurrences of the same 7-field construction
  (`id`, `dashboard_id`, `title`, `question_text`, `sql_text`,
  `chart_spec_json`, `position`, `created_at`), inside
  `create_dashboard_card` (line 344), `get_dashboard` (line 387),
  `patch_dashboard_card` (line 441), and `run_dashboard_card` (line 468).
- `run_dashboard_card`'s existing line 483
  (`DashboardCardWithRows(**card_detail.model_dump(), rows=rows)`) is the
  precedent for how to add `rows` on top of the shared
  `DashboardCardDetail` shape — `get_dashboard` should adopt the same
  pattern instead of its own separate 8-field `DashboardCardWithRows(...)`
  construction.
- `tests/test_api_dashboard_cards.py` (existing, ~76 tests) is the
  regression suite that must stay green — it already asserts on every
  route's exact response shape.

Outputs:
- A new `_card_to_detail(card: DashboardCard) -> DashboardCardDetail`
  function in `app/main.py`, used at all four sites. `get_dashboard` and
  `run_dashboard_card` build their `DashboardCardWithRows` via
  `DashboardCardWithRows(**_card_to_detail(card).model_dump(), rows=rows)`;
  `create_dashboard_card` and `patch_dashboard_card` return
  `_card_to_detail(card)` directly.

Done-check:
`.venv/Scripts/python -m unittest discover -s tests -p "test_api_dashboard_cards.py" -v`
passes with the same test count as before (76 tests, 0 failures).

Out-of-scope:
- Any new route, field, or behavior change to the four touched routes.
- The frontend (`DashboardView.tsx`/`App.tsx`) — not touched this slice.
- Any other duplication elsewhere in the codebase not part of this
  specific 4-occurrence mapping.
- The shipping-proof curl walkthrough (create/patch/run/delete against
  the real dev server) — that's Gate 2's job, not the done-check above.
