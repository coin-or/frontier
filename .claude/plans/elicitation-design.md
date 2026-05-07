# Elicitation Design

## SDK status
- **Pinned**: `mcp[cli]>=1.0` (pyproject + requirements). Latest is `1.27.0` (Apr 2026); local `.venv` absent so installed version unverified.
- **API**: `result = await ctx.elicit(message=..., schema=PydanticModel)` from inside `@mcp.tool()`. `result.action` in `{accept, decline, cancel}`; `result.data` only on `accept`.
- **Schema**: Pydantic `BaseModel` with `Field(description=...)`. Spec types: string (enum via `Literal`), number (with min/max), boolean, defaults. Flat only — no nested objects or arrays.
- **Capability**: auto-negotiated at initialize via `ClientCapabilities.elicitation`. Read `ctx.session.client_params.capabilities`; if absent, branch to text fallback.
- **Upgrade**: tighten to `mcp[cli]>=1.13` (first stable elicitation release). `Context` already injected by FastMCP — no breaking changes expected.

## Trigger surface

### 1. Score conflict (data_collection)
- **Precondition**: in `model/update`, two sources disagree on the same `(option, objective)` cell beyond tolerance, or an existing score is being overwritten with a materially different value.
- **Form**: "Conflicting scores for {option}/{objective}: {a} vs {b}. Which should we keep?" Fields: `chosen_value: Literal["a","b","manual"]`, `manual_value: float | None`, `note: str`, `mark_low_confidence: bool`.
- **Fallback**: return `next_steps: {kind: "score_conflict", options: [...], prompt: ...}` for text clients.
- **Default**: auto-fire on conflict; gated by `interactive: bool = True`.

### 2. Infeasibility (optimization_strategy)
- **Precondition**: `solve/run` returns zero feasible solutions and diagnosis identifies the smallest conflicting constraint set.
- **Form**: "No feasible portfolio under current constraints. {diagnosis}." Fields: `action: Literal["relax","drop","keep_and_abort"]`, `target_constraint_id: str` (enum of binding ids), `relax_to: float | None`, `confirm_rerun: bool`.
- **Fallback**: include the same options in the existing `infeasibility_report` block.
- **Default**: auto-fire on zero solutions; suppressible via `interactive=false`.

### 3. Solution feedback (problem_framing)
- **Precondition**: in `_explore_feedback` (`server.py:1111`), `rating <= 2` or notes parse as rejection — and at least one solve exists. Per problem-framing SKILL.md L118-120, rejection reveals latent constraint.
- **Form**: "You rated {solution} {rating}/5. What's missing?" Fields: `latent_kind: Literal["absolute_bound","change_bound","soft_preference","other"]`, `dimension: str` (enum of objectives + "constraint"), `threshold: float | None`, `would_relax_for_value: bool`, `freeform: str`.
- **Fallback**: append a `probe` block to the feedback response with the same enums.
- **Default**: fire only on low rating or rejection signal — not neutral/positive. Honor `interactive`.

### 4. Post-solve formulation edits (problem_framing / data_collection)
- **Precondition**: `model/update` tightens a constraint or revises a score after `p.run` exists, AND the change would invalidate any `curated_solutions` (re-evaluate against new bounds before commit).
- **Form**: "Tightening {constraint} to {new} would eliminate {N} curated solutions ({names}). Proceed?" Fields: `proceed: bool`, `keep_curated_as_history: bool`, `re_solve_now: bool`.
- **Fallback**: return a `pending_edit` envelope with the same diff; require explicit `confirm=true` on follow-up.
- **Default**: fire only when curated impact > 0 OR the edit shifts a frontier-defining bound; otherwise apply silently.

## Open questions
- Confirm 1.13 is the right floor — verify by inspecting installed wheel once `.venv` is hydrated.
- Capability detection: does FastMCP expose `ctx.client_supports("elicitation")`, or do we read `session.client_params.capabilities` directly?
- Test strategy: add a fake `Session` that scripts elicit responses (`accept`/`decline`/`cancel`); run the four trigger paths through it. The current non-interactive suite stays green by defaulting `interactive=false` in fixtures.
- Caller surprise: gate every trigger behind `interactive: bool = False` at tool-arg level (opt-in); advertise via skill docs so agentic callers flip it on. Fallback `next_steps` block is always returned so non-interactive callers see the same information shape.

## Recommended next step
Prototype **trigger 3 (solution feedback)** first. It is the most novel per user direction ("pegged to problem evolution, esp given solution feedback"), the precondition is already isolated in `_explore_feedback`, and the form is small enough to validate the elicit + fallback pattern end-to-end. Once the dual-mode return contract is proven there, triggers 1, 2, and 4 reduce to mechanical applications of the same pattern.
