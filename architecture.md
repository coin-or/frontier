# Frontier — Architecture Reference

**Related docs:** [`best-practices.md`](best-practices.md) — skill, prompt & MCP design guidelines | [`README.md`](README.md) — user setup and usage guide | [`CLAUDE.md`](CLAUDE.md) — project instructions for Claude

## Tools & Skills Reference

### MCP Tools

Frontier exposes 4 tools — 3 domain tools with multiple actions, plus a skill delivery tool:

| Tool | Action | Purpose |
|------|--------|---------|
| **model** | `create` | Start a new optimization problem (name, domain, context, approach) |
| | `update` | Add/modify objectives, options, scores, constraints, reference points, scenarios. Merge semantics for scores; full replacement for everything else. Marks results stale on structural changes. |
| | `get` | Return problem state. Optional `section` param for targeted slices: summary, objectives, options, scores, constraints, matrices, scenarios, run, runs, curated, references. Without section: full dump. |
| | `list` | List all problems with metadata snapshots |
| | `delete` | Remove a problem and its data file |
| **solve** | `validate` | Pre-flight check: ≥2 objectives, ≥3 options, complete score matrix, feasible constraints |
| | `run` | Validate then optimize. Returns compact result — `objective_ranges`, `preview` (per-objective extremes + balanced solution by id/objective_values only), `quality`, `seed_used`, `total_pareto_found` (pre-pruning count), `frontier_complete` (bool — true when returned set is the full Pareto frontier, false when pruning truncated it), `frontier_quality` (status GOOD/WARNING/POOR with progressive gates and issues), `metrics`, `full_result_path` (disk path to complete JSON with all solutions — preferred for bulk export or artifact assembly), and `next_steps` pointer. Full solution detail also retrievable via `explore solutions` / `explore solution <id>`. Optional `mode`: "fast" (default, quick iterations) or "thorough" (final convergence). Optional `max_solutions` caps Pareto set size (default 100). Optional `seed` (int) for reproducibility; omitted = fresh random seed drawn and echoed. Auto-selects NSGA-II (2-3 obj) or NSGA-III (4+ obj). Parameters adapt to solution space size and objective count. |
| | `run_scenarios` | Independently optimize each scenario with score overrides/adjustments. Accepts optional `mode`, `max_solutions`, and `seed` (per-scenario seeds are deterministically derived so each scenario reproduces while starting from distinct initializations). |
| **explore** | `tradeoffs` | Frontier overview: total solution count, objective ranges, correlations + normalized MI per pair (MI computed when n≥15), extremes, balanced solution (ideal-point closest), inflection-point candidates (diminishing-returns boundaries), frontier shape classification per conflicting pair (linear / concave / convex / discontinuous, with confidence), binding_analysis (shadow-price rates per binding constraint — how much each objective shifts per unit of slack relaxation, derived from frontier; objective_bound / cardinality / group_limit), objective_redundancy (classification per pair using Pearson + MI, flags Pearson/MI disagreement = non-linear dependence), vs references. Optional `scenario` param targets a specific scenario's frontier. |
| | `compare` | Side-by-side comparison of 2+ solutions (shared/differentiating options, tradeoff summary). Optional `scenario` param. |
| | `solutions` | Pareto frontier listing. Default: compact (solution_id + objective_values + content_signature). Pass `detail=true` for full dump including selected_options and allocations. Optional `scenario` param. |
| | `solution` | Single solution detail with reference point analysis. Optional `scenario` param. |
| | `feedback` | Record user feedback: solution_id or content_signature, rating (1-5), notes, stage. Links to content_signature (stable across runs) and attaches to matching curated solution. |
| | `compare_runs` | Diff run history: criteria changes, frontier diffs, option coverage |
| | `scenario_results` | Per-scenario analysis with frequency-weighted option importance. Returns option_robustness sorted by importance (avg_frequency x avg_weight) with tiers: core (>50% in all scenarios), common (>25%), marginal (<25%). Also: scenario-specific options, expected values (ideal-point, probability-weighted), scenario_risk per objective (expected / worst_case / best_case / cvar_<alpha>%). Optional `cvar_alpha` (float in (0,1), default 0.2) sets the CVaR tail fraction. |
| | `curate` | Add a solution to the curated set with custom name and notes. Optional `scenario` param for curating from scenario frontiers. |
| | `uncurate` | Remove a solution from the curated set by content signature |
| | `rename_curated` | Update a curated solution's custom name |
| | `curated` | List all curated solutions with `in_current_frontier` survival flag |
| | `compare_curated` | Compare curated solutions side-by-side by content signature. Default: compact (shared/differentiating options + objective values). Pass `detail=true` for full selected_options and allocations per solution. |
| | `marginal_analysis` | Marginal rate analysis: cost-per-unit between adjacent solutions, inflection point detection (where marginal cost jumps sharply). Default summary; `detail=true` for per-pair breakdown. Optional `scenario` param. |
| **get_skill** | *(single action)* | Retrieve workflow guidance by name. Returns full skill markdown. Works with all MCP clients (unlike resources, which require client-side resource support). Available skills: `problem_framing`, `data_collection`, `optimization_strategy`, `solution_interpreter`. |

### MCP Skills (Resources + Tool)

Skills are available two ways for maximum client compatibility:
1. **`get_skill` tool** (universal) — works with any MCP client. Call `get_skill('problem_framing')` etc.
2. **MCP resources** (backward compat) — `frontier://skills/*` URIs, for clients that support resource reads.

Skills provide domain guidance the agent consults at each workflow stage:

| Skill | Purpose |
|-------|---------|
| **problem_framing** | Translate decision language into objectives/options/constraints. Covers objective vs constraint classification (principle-based, not keyword matching), hidden objective detection, approach selection (binary vs proportional — "does quantity matter?"), aggregation modes (canonical definition — sum/avg/min/max/quadratic), interaction matrices for quadratic aggregation, reference points, scenario definition, question anchors for guiding problem exploration. Cross-referenced by other skills. |
| **data_collection** | Guide score elicitation. Covers data readiness levels, anchoring techniques, batch efficiency, source evaluation, conflict resolution, score quality signals (variance, scale mismatch), aggregation implications on scoring (cross-references problem_framing), completeness drive. |
| **optimization_strategy** | Drive solve progression. Covers iteration expectations, validate→run→examine flow, constraint strategy (cross-references problem_framing for types), infeasibility response, binding constraint detection, curated solution survival tracking, run comparison, scenario interpretation, stale results and re-run judgment. |
| **solution_interpreter** | Present results without bias. Core Judgment (always apply): "never say best", five explanation dimensions, presentation order (Extremes → Balanced → Inflection → Risk → Preference), tradeoff framing, objective ranking elicitation, dominance explanation, question anchor (connect results back to user's original decision question). Presentation Refinements (situational): visualization, run diffs, reference point narration, scenario presentation, diagnostics, preference learning, curation guidance. Reference: `references/explore-diagnostics.md` for detailed field schemas of tradeoff and scenario result blocks. |

---

## 1. User Workflow

How an end-user interacts with the AI agent, which drives Frontier on their behalf.

```mermaid
flowchart TD
    subgraph USER["End User"]
        U1([Describe decision problem])
        U2([Provide scores, constraints,<br/>reference points & scenarios])
        U3([Review tradeoffs])
        U4([Refine & iterate])
        U5([Curate final selections])
    end

    subgraph AGENT["AI Agent (Claude)"]
        A1[Translate business language<br/>into objectives, options, approach]
        A2[Guide score collection, constraint<br/>setup, reference points & scenarios]
        A3[Run optimization &<br/>interpret Pareto frontier]
        A3b[Run scenario optimization<br/>& identify robust options]
        A4[Present tradeoffs, comparisons,<br/>dominance, scenario analysis]
        A5[Elicit preferences via<br/>marginal tradeoff questions]
        A6[Track curated solutions<br/>& collect feedback]
    end

    subgraph SKILLS["Agent Skills (Resources)"]
        S1[problem_framing.md]
        S2[data_collection.md]
        S3[optimization_strategy.md]
        S4[solution_interpreter.md]
    end

    subgraph FRONTIER["Frontier MCP Tools"]
        T1["model (create/update)"]
        T2["solve (validate/run/run_scenarios)"]
        T3["explore (tradeoffs/compare/curate)"]
    end

    U1 --> A1
    A1 -.->|reads| S1
    A1 -->|"create problem, set approach"| T1

    U2 --> A2
    A2 -.->|reads| S1 & S2
    A2 -->|"update scores, constraints,<br/>reference points, scenarios"| T1

    A3 -.->|reads| S3
    T1 -->|problem ready| A3
    A3 -->|validate & run| T2
    A3b -.->|reads| S3
    A3b -->|run_scenarios| T2
    T2 -->|"Pareto frontier<br/>+ scenario runs"| A4

    A4 -.->|reads| S4
    A4 -->|"tradeoffs, compare, scenarios,<br/>reference comparisons"| T3
    T3 -->|insights| A4
    A4 --> U3

    U3 --> U4
    U4 --> A5
    A5 -->|"update scores, constraints,<br/>scenarios / re-run"| T1
    A5 -->|re-solve| T2

    U3 --> U5
    U5 --> A6
    A6 -->|curate & feedback| T3
```

## 2. System Architecture

MCP tools, skills, engine internals, and how they connect to the agent client.

```mermaid
flowchart TB
    subgraph CLIENT["Agent Client (Claude Code / Desktop / claude.ai / any MCP host)"]
        CC[Claude Agent]
    end

    subgraph MCP_LAYER["Frontier MCP Server"]
        direction TB
        subgraph TOOLS["Tools (stdio / SSE)"]
            GETSKILL["get_skill<br/><i>Retrieve workflow guidance by name</i>"]
            MODEL["model<br/><i>create | update | get | list | delete</i>"]
            SOLVE["solve<br/><i>validate | run | run_scenarios</i>"]
            EXPLORE["explore<br/><i>tradeoffs | compare | solutions | solution<br/>feedback | compare_runs | scenario_results<br/>curate | uncurate | rename_curated<br/>curated | export_curated | compare_curated | marginal_analysis</i>"]
        end
        subgraph RESOURCES["Skills (MCP Resources)"]
            R1["problem_framing<br/><i>Objective/option/constraint guidance</i>"]
            R2["data_collection<br/><i>Scoring strategies & quality signals</i>"]
            R3["optimization_strategy<br/><i>Solve progression & iteration</i>"]
            R4["solution_interpreter<br/><i>Presentation & preference elicitation</i>"]
        end
    end

    subgraph ENGINE["Engine Layer"]
        direction TB
        MODELS["models.py<br/><i>Problem, Objective, Option, Score,<br/>Constraint (8 types incl. max_allocation),<br/>InteractionMatrix (mode: replace/upsert,<br/>scale_groups for regime shifts),<br/>InteractionScaleGroup,<br/>Run (mode, total_pareto_found, seed_used),<br/>QualityIndicators,<br/>Scenario (incl. interaction_matrix_overrides),<br/>ScenarioConfig, ScenarioRun,<br/>ScoreAdjustment, CuratedSolution<br/>(+ feedback history), ReferencePoint,<br/>Feedback, ValidationResult</i>"]
        OPT["optimizer.py<br/><i>NSGA-II/III (pymoo)<br/>Binary & Proportional modes<br/>Adaptive parameter tuning<br/>Constraint encoding (8 types)<br/>Quadratic aggregation (interaction matrices)<br/>Scenario optimization<br/>Infeasibility analysis</i>"]
        EXP["explorer.py<br/><i>Tradeoff analysis, comparisons,<br/>balanced solution detection,<br/>scenario aggregation, curation,<br/>reference point analysis,<br/>marginal rate analysis,<br/>built-in ASCII visualizations</i>"]
        MET["metrics.py<br/><i>Framing, data, solve,<br/>outcome metrics, diagnostics,<br/>frontier_quality classifier<br/>(GOOD/WARNING/POOR)</i>"]
        STORE["store.py<br/><i>File-based JSON persistence</i>"]
    end

    subgraph STORAGE["Persistence"]
        FS[("./data/<br/>{problem_id}.json")]
    end

    CC <-->|"tool calls / results<br/>(JSON over stdio/SSE)"| TOOLS
    CC -.->|"reads skill content<br/>(Claude Code only)"| RESOURCES
    GETSKILL -.->|reads| RESOURCES

    MODEL --> MODELS
    MODEL --> MET
    MODEL --> STORE
    SOLVE --> OPT
    SOLVE --> MET
    SOLVE --> STORE
    EXPLORE --> EXP
    EXPLORE --> STORE

    OPT --> MODELS
    EXP --> MODELS
    MET --> MODELS
    STORE --> FS
```

### Skill Auto-Injection

Tool responses include the relevant skill content for the *next* workflow phase, so agents receive guidance at the right time without manually calling `get_skill()`. This is the primary delivery mechanism — `get_skill` exists as a manual fallback.

| Trigger | Injected Skill |
|---------|---------------|
| MCP connect (server instructions) | Condensed `problem_framing` + constraint schemas + scores schema |
| `model/create` response | `data_collection` |
| `model/update` (objectives/options) | `data_collection` (if not already injected) |
| `model/update` (scores hit 100%) | `optimization_strategy` |
| `solve/validate` (ready=true) | `optimization_strategy` (if not already injected) |
| `solve/run` response | `solution_interpreter` (always, on every solve) |

Re-injection of `optimization_strategy` only fires on problem *shape* changes (objectives or options). Refinements (constraints, interaction_matrices, scenarios, reference_points, approach flip, score updates) don't re-trigger — the methodology guidance hasn't changed.

### Visualization & Compaction Layers

**Built-in visualizations** — `explorer.py` renders ASCII/text visualizations inline with explore results, avoiding a separate rendering step:
- `_render_tradeoffs_viz` — scatter plot of objective pairs with labeled extremes
- `_render_parallel_coords` — parallel coordinates chart for compare and compare_curated
- `_render_scenario_viz` — robust vs scenario-specific option summary
- `_render_marginal_rates` — cost-per-unit bar chart with knee marker

**Response compaction** — `server.py/_format_explore` trims redundant bulk from explore output (e.g. strips option lists from extreme_solutions, restructures scenario_specific_options) to prevent MCP truncation while keeping the dict shape stable for consumers. `solve/run` responses are also compacted: full solution bodies are not returned inline — only objective ranges plus a preview (extremes + balanced by id/values), with a `next_steps` pointer to `explore` for full detail. The complete run payload (all solutions with allocations) is persisted to disk at `full_result_path` for bulk export and artifact assembly without token overhead.

### Evaluation Framework

`dev_temp/eval/` contains structured comparison runs — Frontier vs LLM-only vs pymoo/pyomo solver on portfolio optimization scenarios. Each run (e.g. `run_002/`, `run_003/`) is organized by scenario type (`base/`, `scenarios/`) with per-approach subdirectories (`frontier/`, `llm/`, `solver/`). Each approach produces `results.json`, `results.md`, `curated.md`, `issues.md`, and `response.md`. Runs include a top-level `comparison.md` synthesizing outcomes and a `plots/` directory with visualization scripts and generated charts (pairwise clouds, return-vol annotations, strategy migration). These artifacts validate the gap Frontier closes between unaided LLM reasoning and structured optimization.

## 3. Problem State Lifecycle

The state machine that bridges user actions (diagram 1) to data mutations (diagram 4). Shows when results go stale, runs get archived, and curated solutions are tested for survival.

```mermaid
stateDiagram-v2
    [*] --> Empty: model/create

    Empty --> Framing: add objectives & options
    Framing --> Framing: update objectives/options

    Framing --> Scoring: first score added
    Scoring --> Scoring: update scores\n(merge semantics)

    Scoring --> Solvable: score matrix complete\n+ ≥2 objectives + ≥3 options
    Solvable --> Solvable: add/update constraints,\nreference points, scenarios\n(non-structural, no stale flag)

    Solvable --> Solved: solve/run\n→ NSGA-II/III produces Run
    Solvable --> ScenarioSolved: solve/run_scenarios\n→ per-scenario Runs
    Solvable --> Infeasible: solve/run\n→ no feasible solutions

    Infeasible --> Solvable: relax constraints\nor remove scenario constraint overrides

    ScenarioSolved --> Exploring: explore/scenario_results\n→ robust vs specific options,\nexpected values

    Solved --> Exploring: explore/* calls\n(tradeoffs, compare, dominance)
    Exploring --> Exploring: navigate frontier,\ncompare solutions,\nreference point analysis

    Exploring --> Curating: explore/curate\n→ snapshot solution with\ncontent_signature
    Curating --> Curating: curate more,\nrename, uncurate

    Curating --> Feedback: explore/feedback\n→ rating, notes, stage\n→ linked via content_signature\n→ attaches to curated solution

    state stale_fork <<fork>>
    Solved --> stale_fork: update objectives, options,\nscores, constraints, or approach
    ScenarioSolved --> stale_fork
    Exploring --> stale_fork
    Curating --> stale_fork
    Feedback --> stale_fork

    state stale_join <<join>>
    stale_fork --> stale_join

    stale_join --> Stale: results_stale = true\ncurrent Run archived to runs[]

    Stale --> Solved: re-solve\n→ new Run replaces current\n→ results_stale = false
    Stale --> ScenarioSolved: re-solve scenarios\n→ new ScenarioRun

    note right of Stale
        Curated solutions persist across re-runs.
        content_signature used to check if
        a curated pick survived in the new frontier
        (in_current_frontier flag).
        Feedback accumulates on curated solutions
        via content_signature — survives re-runs
        and problem variations.
    end note

    note right of Solved
        Run: solutions[], quality (hypervolume,
        spacing CV), constraints_snapshot.
        Each solution: selected_options,
        objective_values, allocations,
        content_signature (MD5).
    end note

    note left of ScenarioSolved
        ScenarioRun: dict of scenario_name → Run.
        Each scenario independently optimized
        with score overrides/adjustments
        and constraint overrides applied.
    end note
```

## 4. Data Flow

What data is user-provided, system-collected, and engine-generated at each phase.

```mermaid
flowchart LR
    subgraph PROVIDED["User-Provided Data"]
        direction TB
        P1["Problem framing<br/><i>name, domain, context,<br/>approach (binary/proportional)</i>"]
        P2["Objectives<br/><i>name, direction, unit,<br/>aggregation (sum/avg/min/max)</i>"]
        P3["Options<br/><i>name, description</i>"]
        P4["Score matrix<br/><i>(option, objective) → value</i>"]
        P5["Constraints<br/><i>cardinality, force include/exclude,<br/>objective bounds, exclusion pairs,<br/>dependencies, group limits</i>"]
        P6["Reference points<br/><i>baseline (current portfolio +<br/>objective values) &<br/>aspirational (target outcomes)</i>"]
        P7["Scenarios<br/><i>name, probability, description,<br/>score overrides, score adjustments<br/>(multiply/add), constraint overrides</i>"]
        P8["Feedback<br/><i>rating (1-5), notes, stage,<br/>linked via content_signature<br/>(stable across runs)</i>"]
        P9["Curation<br/><i>solution picks, custom names, notes,<br/>accumulated feedback history</i>"]
    end

    subgraph COLLECTED["System-Collected Metrics"]
        direction TB
        C1["Framing metrics<br/><i>objective/option/constraint counts,<br/>directions completeness</i>"]
        C2["Data metrics<br/><i>score completeness %,<br/>missing scores list,<br/>variance by objective,<br/>dominated options</i>"]
        C3["Solve metrics<br/><i>solution count, hypervolume,<br/>spacing CV, objective variation,<br/>option coverage</i>"]
        C4["Outcome metrics<br/><i>selected solution, rating,<br/>feedback count</i>"]
        C5["Diagnostics<br/><i>zero solutions, clustering,<br/>low variation, never-selected options,<br/>binding constraints</i>"]
    end

    subgraph GENERATED["Engine-Generated Results"]
        direction TB
        G1["Pareto frontier<br/><i>set of non-dominated solutions<br/>(dominance filtering via NSGA-II/III)</i>"]
        G2["Solutions<br/><i>selected options, objective values,<br/>allocations (proportional),<br/>content signatures (MD5)</i>"]
        G3["Quality & diversity<br/><i>normalized hypervolume (coverage),<br/>spacing CV (spread uniformity)</i>"]
        G4["Tradeoff analysis<br/><i>correlations, extremes,<br/>balanced solution (min distance<br/>to ideal point),<br/>frontier shape per pair<br/>(linear/concave/convex/discontinuous),<br/>reference point comparisons</i>"]
        G5["Scenario results<br/><i>per-scenario frontiers,<br/>robust options (all scenarios),<br/>scenario-specific options,<br/>expected values (prob-weighted)</i>"]
        G6["Run history<br/><i>archived runs, constraint snapshots,<br/>frontier diffs, option coverage</i>"]
        G7["Infeasibility analysis<br/><i>binding constraints,<br/>relaxation suggestions</i>"]
        G8["Curation tracking<br/><i>in_current_frontier survival flag,<br/>cross-run signature matching,<br/>feedback history + avg rating</i>"]
    end

    P1 & P2 & P3 --> C1
    P4 --> C2
    P2 & P3 & P4 & P5 -->|"validate & optimize<br/>(NSGA-II/III)"| G1
    G1 --> G2
    G1 --> G3
    G2 --> G4
    P7 & P4 & P5 -->|"per-scenario optimization<br/>(adjustments → overrides applied)"| G5
    P6 --> G4
    G2 --> C3
    P8 --> C4
    P5 -->|"infeasible?"| G7
    P9 -->|"snapshot + signature"| G8
    G8 -.->|"survival check<br/>against new frontier"| G2

    C1 & C2 -->|"returned with<br/>model updates"| AGENT1([Agent])
    C3 & C5 -->|"returned with<br/>solve results"| AGENT1
    G4 & G5 & G6 & G8 -->|"returned with<br/>explore results"| AGENT1
```
