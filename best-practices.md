# Frontier — Skill, Prompt & MCP Design Best Practices

A living reference for designing skills, tool descriptions, and agent instructions in this project. Seeded from [Anthropic's official prompting best practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices) and refined through iterative auditing of Frontier's skill files.

**Related docs:** [`architecture.md`](architecture.md) — system architecture, tool/skill reference, data flow | [`README.md`](README.md) — user setup and usage guide

**Using this guide (by lifecycle phase)** — pull up the part that applies at each phase instead of re-reading the whole file:
- **Designing** a new skill or MCP tool → §1 (Skill File Design), §3 (MCP Tool Description Design), §4 (Context Engineering), §5 (Division of Labor — which side of the code↔LLM boundary each piece belongs on)
- **Developing** prompts, tool descriptions, or skill content → §2 (Prompt Best Practices), §5 payload-English cap
- **Reviewing** a skill or prompt change → §1 agent-usability criteria + conciseness; verify cross-references and MECE boundaries; §5 gate rule (every scaffold ships with its regression gate)
- **Testing** a new feature → §1 safety patterns (confirmation gates, validation loops)

---

## 1. Skill File Design

Skills are MCP resources (markdown files) that provide contextual judgment the agent consults at different stages of a workflow. They are not tool documentation — they guide *when* and *why*, while tool descriptions handle *how*.

### Structure

Every skill file should follow this structure:

```
# Skill Name
*One-sentence role definition.*

## [Context / Framing Section]
Why this skill exists and what mindset to adopt.

## Core Judgment
The critical principles that shape every interaction. Get these right first.

## [Situational Sections]
Guidance that applies in specific circumstances.

## Activation
When to use this skill (stage of workflow).

## Guardrails
Positive guidance with reasoning — what to do and why.
```

### Principles

**Role definition matters.** Even a single sentence ("You are a decision analyst") focuses behavior and tone. (Source: [Anthropic — Give Claude a role](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices#give-claude-a-role))

**Separate judgment from API details.** Skills guide contextual reasoning — when to use scenarios, why to set reference points, how to interpret results. Tool parameter documentation belongs in tool descriptions. Skills should say "Define scenarios via `model update` with `scenario_config`" and stop — not list every parameter.

**Priority hierarchy.** In long prompts, everything competes for attention. Mark critical principles explicitly ("Core Judgment") and separate them from refinements. The LLM will weight sections by apparent importance. (Source: [Anthropic — Long context prompting](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/long-context-tips))

**Cross-reference, don't duplicate.** When two skills need the same concept (e.g., aggregation modes), define it once in a canonical location and cross-reference: `(See aggregation modes in frontier://skills/problem_framing.)` Duplication wastes tokens and risks inconsistency.

**Consistent section names.** Use the same heading names across files (`## Core Judgment`, `## Activation`, `## Guardrails`) so the LLM builds a structural expectation.

### Agent Usability

The ultimate quality gate for any skill. If an agent can't discover, navigate, adapt, and execute from the skill alone, the skill isn't done.

- **Discovery:** Does the skill's description trigger for realistic user tasks (and not trigger for unrelated ones)?
- **Navigation:** Can an agent find the right section in 1–2 lookups, not wandering?
- **Pattern adaptation:** Given a novel problem, can an agent locate a relevant example and adapt it without hallucinating?
- **Self-sufficiency:** Can an agent go from skill content to working output without external docs or guessing?
- **Negative test:** Does the skill clearly redirect when the task is out of scope?

### Progressive Disclosure

Manage context window budget by layering information:

- **SKILL.md** loads on trigger — keep it lean (under 2,000 words / 500 lines). Contains judgment and workflow.
- **references/** loads only when explicitly read. Contains schemas, lookup tables, detailed examples.
- References should be one level deep from SKILL.md (no deep nesting).

### Conciseness

- **No explaining the obvious:** Omit what the model already knows (general concepts, standard libraries). Every token should earn its place.
- **Concise over exhaustive:** Stepwise guidance with a working example beats encyclopedic coverage. If content covers every edge case, most are better left to model judgment.
- **Defaults over menus:** When multiple approaches apply, pick one as default with a brief escape hatch — not equal-weight lists.

### Safety Patterns

- **Confirmation gates:** For destructive or external-facing actions, pause and show proposed changes before executing.
- **Validation loops:** For tasks with verifiable output, instruct the agent to validate its own work before moving on (run → fix → re-validate).

---

## 2. Prompt Best Practices (Anthropic)

Key principles from Anthropic's official guides, applied to this project.

### Tell Claude what to do, not what not to do

**Instead of:** "Don't say 'the best solution'"
**Write:** "Present tradeoffs, never 'the best solution' — every Pareto solution is optimal at its particular tradeoff."

Positive instructions with reasoning are more reliably followed than bare prohibitions. (Source: [Anthropic — Control the format of responses](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices#control-the-format-of-responses))

### Add context / motivation

Explain *why* an instruction matters. The LLM generalizes from the reasoning, not just the rule:

**Instead of:** "Score matrix must be 100% before solving"
**Write:** "Score matrix must be 100% before solving — the optimizer cannot evaluate tradeoffs with missing values, so every gap blocks the entire run."

(Source: [Anthropic — Add context to improve performance](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices#add-context-to-improve-performance))

### Prefer general instructions over prescriptive steps

The LLM's reasoning frequently exceeds what a hand-written step-by-step plan would produce. Give the principle and let the model figure out the execution:

**Instead of:** 30 lines of rules for when to use scatter plots vs parallel coordinates
**Write:** "Choose the visualization that best reveals the tradeoff structure. Scatter plots for pairwise comparisons, parallel coordinates for multi-objective views, tables when there are few solutions."

(Source: [Anthropic — Thinking and reasoning](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices#leverage-thinking--interleaved-thinking-capabilities))

### Avoid keyword matching and lookup tables

LLMs can classify intent from natural language. Teaching keyword triggers ("user says X → do Y") is fragile and narrows generalization. Instead, teach the *classification principle*:

**Instead of:** `| "Pick N", "Choose a few" | Cardinality |`
**Write:** "When a user describes a limit on how many options are selected, that's a cardinality constraint."

### Avoid domain-specific anchoring

Listing domain examples (Investment → proportional, Hiring → binary) creates anchoring bias. Users in unlisted domains get worse results. Instead, teach the *reasoning heuristic*:

**Instead of:** "Investment/portfolio → proportional. Budget allocation → proportional."
**Write:** "Does the quantity assigned to each option matter, or is it a yes/no decision? If swapping allocations produces a meaningfully different outcome, use proportional."

Domain-agnostic examples are fine for illustrating concepts. Domain-specific lookup tables are not.

### Use generic placeholders in examples

When examples are for illustrating a *pattern* (not a specific domain), use "[Option A]", "[objective]" etc. rather than "SSO", "Revenue", "Engineering Effort". Domain-specific names anchor the LLM to that domain.

---

## 3. MCP Tool Description Design

Tool descriptions are the primary interface between the agent and the system. They should be precise, complete, and complementary to skills.

### Responsibility split: Tools vs Skills

| Aspect | Tool description | Skill file |
|--------|-----------------|------------|
| **What parameters exist** | Yes | No — cross-reference |
| **Valid parameter values** | Yes (types, enums, ranges) | No |
| **When to use this action** | Brief heuristic | Detailed judgment |
| **Why / strategic reasoning** | No | Yes |
| **Error interpretation** | Brief | Detailed (infeasibility, diagnostics) |

### Principles

**Be explicit about parameter semantics.** Don't assume the LLM knows that `scores` uses merge semantics while `objectives` uses full replacement. State it.

**Document side effects.** If an action marks results stale, clears cached data, or archives a run, say so in the tool description. The agent can't reason about what it doesn't know.

**Use the description to prevent common mistakes.** If users frequently pass wrong parameter formats, add a brief note. Tool descriptions are read every time; skills are read when prompted.

**Exception — bulky, rarely-needed schemas.** When full JSON shapes would bloat an always-visible tool description, put them in a skill's `references/` fetched per section (e.g. `problem_framing/references/schemas.md`) and point to them from both layers — the §4 token-budget rule outranks the responsibility-split table for content that is large and needed only at payload-construction time.

---

## 4. Context Engineering

How skills, tool descriptions, and server instructions work together as a system.

### The three layers

1. **Server instructions** (system prompt in MCP server): brief, high-level workflow guidance. Points to skills.
2. **Tool descriptions** (per-tool docstrings): parameter documentation, API semantics, side effects.
3. **Skills** (MCP resources): contextual judgment, principles, guardrails. Read on-demand by the agent.

### Design principles

**Minimize total token budget.** Every token of instruction competes for attention. Be concise. If something can be derived from the code, don't document it in a skill. If something is said once in a tool description, don't repeat it in a skill.

**Put critical instructions in the layer that's always visible.** Server instructions and tool descriptions are always in context. Skills are read on-demand. The most important guardrails should be in the always-visible layer, with skills providing depth.

**Skills should be stage-aware.** Each skill has an Activation section that says *when* to use it. This lets the agent load the right context at the right time rather than flooding the context with all guidance at once.

**Cross-reference convention.** Use `(See [section name] in frontier://skills/[skill_name].)` for cross-references between skills. Use "See the `[tool]` tool description for API details" to point from skills to tools.

---

## 5. Division of Labor — Deterministic Code vs LLM Judgment

Frontier scaffolds a probabilistic agent with deterministic Python. The strategy is deliberate, and it has a boundary; when adding a feature, decide which side each piece belongs on before writing it.

**Deterministic code earns its place in exactly three areas:**

1. **Math** — compute what the LLM can't: the solve itself, hypervolume, regret, duals, dominance. Never ask the model to estimate what the engine can prove.
2. **Structured classification** — compress raw results into a stable vocabulary of enums and verdicts (`linear_redundant`, `under_covered`, `frontier_inferred`, scale bands, certificate blocks). This vocabulary is what skills teach against ("when you see X, say Y"), what answer-key evals assert on, and what makes claims traceable. It also makes behavior portable across models — classification in code is redundancy for strong models and load-bearing for weak ones.
3. **Guidance routing** — the injection throttle, `guidance_pointer`s, and section resolver. *When* to deliver skill content is a state-machine problem (once per phase, re-arm on shape change, point at the section governing this payload), not a judgment call.

**The boundary rule: code decides what is true; skills decide how to say it and when it matters; the model decides what the user meant.** Semantic mapping of user intent stays with the model (see §2 — no keyword tables); narration and judgment stay in skills; facts, labels, and state stay in code.

**No deterministic scaffold ships without its gate.** Deterministic scaffolding is brittle by nature — hardcoded section titles, payload contracts, workflow beats. That brittleness is affordable only when each scaffold has a regression gate: the resolver-integrity test guards every pointer target and heading, wire-level tests guard payload contracts, answer-key evals guard workflow beats. A scaffold without a gate is rot waiting to happen; add the gate in the same PR.

**Cap payload English — a caption, not a copy.** Hand-written English inside tool responses (`note` / `next_steps` / `recommendation` / `hint`) is the bloat- and drift-prone stratum: it double-bookkeeps with skills, it's invisible to prose review, and it's where terminology drift happens. Two kinds earn their place:
- **Epistemic captions** — a per-response fact the skill can't know: a truncation ("table capped at N"), an absence ("no adjacent-cardinality solutions to estimate from"), an artifact label ("rounding of the continuous optimum, not an infeasible plan").
- **Routing pointers** — the next tool call or the skill section that governs the read.

If a payload string starts *explaining* — teaching semantics, coaching narration, restating what a skill section says — it belongs in that skill section, with the payload shrunk to a pointer. The feature template: **new structured fields + one skill section + a pointer wiring it + at most a sentence of payload English.** When a `guidance_pointer` on the same response already names the covering section, the prose it covers is redundant — trim it.

---

## 6. Patterns Applied in This Project

Patterns discovered during skill file auditing and refactoring:

| Pattern | Before | After |
|---------|--------|-------|
| Keyword trigger table | `"Pick N" → cardinality` | Principle: "limit on selection count → cardinality" |
| Domain lookup | `Investment → proportional` | Heuristic: "does quantity matter?" |
| Negative anti-patterns | "Don't say 'best'" | "Present tradeoffs — every solution is optimal at its tradeoff" |
| Missing motivation | "Score matrix must be 100%" | "...because the optimizer can't run with gaps" |
| API details in skills | 15 lines of `score_adjustments` parameters | "Define via `model update`. See tool description." |
| Domain-specific examples | "SSO, Mobile App, Analytics Dashboard" | "[Option A], [Option B]" or pattern description |
| Redundancy across files | Aggregation explained in 3 files | Canonical in `problem_framing`, cross-referenced |
| Flat priority | All sections at same heading level | "Core Judgment" (critical) vs "Presentation Refinements" |

---

## Sources

- [Anthropic — Prompting best practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices)
- [Anthropic — System prompts](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/system-prompts)
- [Anthropic — Long context prompting tips](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/long-context-tips)
- [Anthropic — Prompt engineering overview](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/overview)
