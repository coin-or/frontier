# Tool Description Polish, Injection Throttling, MCP Apps/Elicitation, Plugin Packaging

Status: draft (2026-04-24)

Seven small description/behavior improvements plus three larger bets: MCP Apps
for `explore` visualizations, Elicitation at two skill-flagged friction points,
and packaging Frontier as a Claude plugin.

> **When finished: update the product roadmap at
> `~/Documents/Obsidian_Vault/projects/frontier/roadmap.md`.**

---

## Decisions (2026-05-07)

- **Group 1 (description polish — items 3-6)** — proceed.
- **Group 2 (throttle)** — proceed; **single shared injection flag** for both
  `solve/run` and `solve/run_scenarios`.
- **Group 3 (schema dedup)** — **option (d)**: move constraint /
  interaction-matrix / scenario schemas into `problem_framing` skill; trim the
  `model` tool docstring to a one-line pointer; leave the `data_collection`
  injection at create unchanged.
- **Group 4 / A (MCP Apps for explore viz)** — **deferred**. ASCII output is
  fine for now. Keep the explore return shape extensible so a thin UI layer
  can attach later without churn — no restructuring required today, just
  don't paint into a corner.
- **Group 5 / B (Elicitation)** — **investigate first**. Confirm MCP SDK
  support, then design. **Trigger surface is broader** than the original two:
  also fire on solution-feedback events (rating-driven latent-constraint
  elicitation) and on follow-up formulation edits (constraint adds, score
  revisions after the first solve). Interactive by default; pegged to
  problem evolution.
- **Group 6 / C (Claude plugin packaging)** — **rejected**. Skills are
  private prompt IP; the MCP server is the distribution boundary precisely
  so skill files aren't shipped out as part of a public plugin bundle.
  Document this rationale in `architecture.md` so the question doesn't
  silently reopen.

---

## Grouping

- **Group 1 — tool-description polish** (items 3, 4, 5, 6): low-risk text edits
  + one small guardrail. One subagent, one PR.
- **Group 2 — injection throttling** (item 2): uses existing
  `_mark_injected` / `_reset_all_injections` plumbing. Low risk, same subagent
  can take it.
- **Group 3 — schema dedup** (item 1): blocked on an open question (below).
- **Group 4 — MCP Apps for `explore` viz** (item A): large; needs design +
  client-capability fallback. Plan, don't ship yet.
- **Group 5 — Elicitation hooks** (item B): needs MCP Elicitation capability
  probe + non-interactive fallback. Plan, don't ship yet.
- **Group 6 — Plugin packaging** (item C): mostly manifest work; independent.

---

## Group 1 — Tool-description polish (high confidence)

### Item 3 — "Side effects:" footers on three actions

Match style: append a short `Side effects:` section to the action bullets in
the relevant tool docstring (no existing precedent — define the convention
here, use it consistently).

- `model/update` (server.py:332–548): marks `results_stale=True` on structural
  change (line 477); resets `optimization_strategy` injection (line 545-546).
  Footer: *Side effects: structural edits (objectives/options/constraints/
  approach/matrices/scenarios) mark the latest run stale and re-arm the
  `optimization_strategy` skill injection on the next solve.*
- `model/delete` (server.py:623–632): calls `_reset_all_injections(pid)`.
  Footer: *Side effects: deletes the problem and all archived runs; resets
  every skill-injection flag for the problem id.*
- `solve/run` (server.py:734–809): archives previous run (756–757), clears
  `results_stale` (760), persists `full_result_path` (776).
  Footer: *Side effects: the previous run (if any) is archived to
  `runs[]`; `results_stale` clears; full results are persisted to
  `full_result_path` on disk.*

### Item 4 — Per-action required-param notes in `explore`

`explore` docstring (server.py:968–1016) mixes required/optional inline.
Normalize each action line to the form `<verb> — <desc>. Requires: ...` when
required params exist. Examples already partially do this (`compare`,
`solution`, `feedback`, `compare_runs`, `compare_curated`); complete the pass
for `curate` (solution_id), `uncurate` / `rename_curated` (content_signature),
`export_curated` (no required), etc. Do **not** split into separate tools.

### Item 5 — `solutions detail=true` cap + `full_result_path` in description

- Cap: at `server.py:1035-1039` (action `solutions`), when `detail=true` and
  the returned solution count exceeds a threshold (propose 50), truncate and
  attach a warning: `truncated: true`, `shown: N`, `total: M`,
  `full_result_path: <path>`. Threshold configurable via a module-level
  constant.
- Elevate `full_result_path`: add a single top-level line near the action
  list: *"Large results (`solutions detail=true`, `marginal_analysis
  detail=true`) write a full JSON dump to `full_result_path` on disk —
  reference it instead of re-requesting."*

### Item 6 — `content_signature` one-line gloss

In the `explore` tool docstring (server.py:968), add directly after the
`solution_interpreter` line:

> *`content_signature` is a stable hash of a solution's selected options /
> allocations — use it (not `solution_id`) to reference curated solutions
> across re-runs, since IDs change.*

---

## Group 2 — Throttle `solution_interpreter` re-injection (high confidence)

**Locations:** server.py:801-809 (`_solve_run`) and ~line 909
(`_solve_run_scenarios`). Both unconditionally call `_inject_skill(...,
"solution_interpreter", ...)`.

**Change:** wrap each call with the existing `_mark_injected` pattern used for
other skills. Inject only if not already marked for this problem; mark on
inject. Reset on structural `model/update` alongside `optimization_strategy`
(server.py:545-546) so the next solve re-arms the hint.

Savings per duplicate solve: ~5k tokens (skill body).

**Open sub-question:** should `solve/run_scenarios` and `solve/run` share a
single flag, or separate flags? Recommend **single** — the skill text is the
same and the goal is "agent saw it once this problem".

---

## Group 3 — Schema dedup (OPEN QUESTION)

The task says "problem_framing auto-injects at model/create (server.py:325)"
— but the actual injection at that line is `data_collection` (server.py:
324-328). `problem_framing` is referenced in its own SKILL.md as *"Read
frontier://skills/problem_framing before creating a problem"* (skills/problem-
framing/SKILL.md:3) — i.e., it's meant to be read by the agent, not injected
by the server.

Neither `problem_framing` nor `data_collection` currently contains the exact
JSON schemas for constraints / scenarios / interaction-matrix overrides
(server.py:234-270). So removing them from the tool description without
re-homing them risks the agent having to guess structure.

**Three options — need to pick before implementing:**

1. **Move the schemas into `problem_framing/SKILL.md`**, then trim the tool
   docstring. Clean, but problem_framing is currently prose-oriented; adding
   JSON schemas changes its character.
2. **Change the injection at server.py:325 to `problem_framing`** (or inject
   both), and move schemas into `problem_framing`. Matches the task's stated
   premise.
3. **Keep schemas in the tool description** but collapse them to shape-only
   (drop inline commentary like "recession: equity correlations × 1.5" at
   server.py:258 — that prose belongs in a skill). Lower-risk partial dedup.

Recommend **option 3** for the immediate cleanup (preserves agent
self-sufficiency) and defer option 1/2 to a follow-up plan.

---

## Group 4 — MCP Apps for `explore` visualizations (design-only pass)

**Targets — all in `frontier/engine/explorer.py`:**
- `_render_tradeoffs_viz` / `_render_scatter` (explorer.py:922-1038) — tradeoff
  scatter
- `_render_parallel_coords` (explorer.py:1066-1154) — parallel-coordinates
  frontier
- `_render_scenario_viz` (explorer.py:1155-1228) — per-scenario comparison
- `_render_marginal_rates` (explorer.py:833-890) — cost-per-unit chart

**Plan shape (not implementation):**
1. Introduce a `VisualizationPayload` that carries both an ASCII `text` field
   and an MCP App descriptor (App URL + props JSON). Keep the ASCII as
   fallback.
2. Probe client support via the MCP session capability (or a config flag) and
   attach the App descriptor only when supported.
3. Pick one viz to pilot — recommend **tradeoffs scatter** (most-used, best
   payoff). Build the App, validate on Claude.ai/Cowork, then port the
   other three.
4. Keep all four ASCII renderers intact permanently for non-App clients and
   for tests.

**Why design-only now:** MCP Apps are client-specific; need to confirm which
Frontier-consuming clients will render them and what the App hosting story is
(static bundle? served from render.yaml?).

---

## Group 5 — Elicitation hooks (design-only pass)

Two canonical form-mode moments the skills already flag:

- **Score-conflict resolution** (`data_collection/SKILL.md:66-72`): when a
  `model/update scores` call carries conflicting values for the same
  (option, objective), return an Elicitation request naming the candidate
  sources and asking which to trust. Falls back to the current
  "disagreement noted" prose when Elicitation isn't supported.
- **Infeasibility relaxation** (`optimization_strategy/SKILL.md:95,97,169`):
  when `solve/run` returns infeasible, return an Elicitation form listing the
  binding constraints with proposed minimal relaxations; the chosen answer
  patches the problem and retries.

**Open questions:**
- Which clients along our distribution chain support Elicitation today?
- Where do the non-Elicitation fallbacks live — in skill prose (current), or
  as structured `next_steps` suggestions in the tool response? Recommend both.

---

## Group 6 — Package Frontier as a Claude plugin

Bundle: MCP server (pyproject.toml:19 entry point) + 4 skills
(`frontier/skills/*/SKILL.md`) + any hooks (none today — `.claude/` only has
`launch.json`).

**Tasks:**
1. Add a plugin manifest at repo root (`plugin.json` or equivalent per the
   Claude plugin spec) referencing the MCP entry point and the four skill
   directories.
2. Verify skill `description` frontmatter on all four SKILL.md files matches
   plugin-discovery conventions.
3. Document install path in `README.md`; cross-link from
   `architecture.md` and `extensible-architecture.md`.
4. Smoke test: install the plugin in a clean Claude Code project and run
   through the etf-portfolio-demo flow.

**Open question:** official plugin manifest spec as of 2026-04-24 — confirm
the current shape before writing the manifest (don't guess from memory).

---

## Rollout order

1. Ship Group 1 + Group 2 together (one PR, pure server.py description +
   small throttle).
2. Resolve Group 3 open question → ship dedup.
3. Pick one of Group 4 / 5 / 6 based on product priority. Recommend Group 6
   first (unblocks distribution), then Group 4 tradeoffs-scatter pilot.
4. **Update `~/Documents/Obsidian_Vault/projects/frontier/roadmap.md`** when
   each group lands.
