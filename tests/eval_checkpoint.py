"""Eval checkpoint: deterministic end-to-end test of the full workflow.

Exercises: model → score → solve → explore → refine → re-solve → feedback
Plus v1 features: aggregation, run comparison, proportional allocation.

Run: python -m tests.eval_checkpoint
"""

from engine.metrics import compute_metrics, diagnostics
from engine.models import (
    CardinalityConstraint,
    ExclusionPairConstraint,
    DependencyConstraint,
    Feedback,
    ForceIncludeConstraint,
    GroupLimitConstraint,
    ObjectiveBoundConstraint,
    Objective,
    Option,
    Problem,
    ReferencePoint,
    Scenario,
    ScenarioConfig,
    Score,
)
from engine.optimizer import optimize, optimize_scenarios, validate
from engine.explorer import (
    compare_runs, compare_solutions, curate_solution, list_curated,
    compare_curated, get_scenario_results, get_solution, get_tradeoffs,
)

# --- Test data (from design doc checkpoint) ---

OBJECTIVES = [
    Objective(name="Revenue Impact", direction="maximize", unit="1-10"),
    Objective(name="Eng Effort", direction="minimize", unit="days"),
    Objective(name="User Satisfaction", direction="maximize", unit="1-10"),
]

OPTIONS = [
    Option(name="Real-time Collaboration"),
    Option(name="Analytics Dashboard"),
    Option(name="AI Content Generation"),
    Option(name="Template Library"),
    Option(name="Workflow Automation"),
    Option(name="Third-party Integrations"),
    Option(name="Mobile App"),
    Option(name="SSO Integration"),
    Option(name="Version Control"),
    Option(name="API Access"),
]

SCORES = [
    # Real-time Collaboration
    Score(option="Real-time Collaboration", objective="Revenue Impact", value=9),
    Score(option="Real-time Collaboration", objective="Eng Effort", value=21),
    Score(option="Real-time Collaboration", objective="User Satisfaction", value=9),
    # Analytics Dashboard
    Score(option="Analytics Dashboard", objective="Revenue Impact", value=8),
    Score(option="Analytics Dashboard", objective="Eng Effort", value=18),
    Score(option="Analytics Dashboard", objective="User Satisfaction", value=7),
    # AI Content Generation
    Score(option="AI Content Generation", objective="Revenue Impact", value=9),
    Score(option="AI Content Generation", objective="Eng Effort", value=25),
    Score(option="AI Content Generation", objective="User Satisfaction", value=8),
    # Template Library
    Score(option="Template Library", objective="Revenue Impact", value=6),
    Score(option="Template Library", objective="Eng Effort", value=8),
    Score(option="Template Library", objective="User Satisfaction", value=7),
    # Workflow Automation
    Score(option="Workflow Automation", objective="Revenue Impact", value=8),
    Score(option="Workflow Automation", objective="Eng Effort", value=15),
    Score(option="Workflow Automation", objective="User Satisfaction", value=7),
    # Third-party Integrations
    Score(option="Third-party Integrations", objective="Revenue Impact", value=7),
    Score(option="Third-party Integrations", objective="Eng Effort", value=12),
    Score(option="Third-party Integrations", objective="User Satisfaction", value=8),
    # Mobile App
    Score(option="Mobile App", objective="Revenue Impact", value=7),
    Score(option="Mobile App", objective="Eng Effort", value=45),
    Score(option="Mobile App", objective="User Satisfaction", value=6),
    # SSO Integration
    Score(option="SSO Integration", objective="Revenue Impact", value=5),
    Score(option="SSO Integration", objective="Eng Effort", value=8),
    Score(option="SSO Integration", objective="User Satisfaction", value=8),
    # Version Control
    Score(option="Version Control", objective="Revenue Impact", value=6),
    Score(option="Version Control", objective="Eng Effort", value=10),
    Score(option="Version Control", objective="User Satisfaction", value=7),
    # API Access
    Score(option="API Access", objective="Revenue Impact", value=7),
    Score(option="API Access", objective="Eng Effort", value=14),
    Score(option="API Access", objective="User Satisfaction", value=5),
]

CONSTRAINTS = [
    CardinalityConstraint(min=3, max=5),
    ForceIncludeConstraint(option="SSO Integration"),
]


def run_checkpoint():
    passed = 0
    failed = 0

    def check(name, condition, detail=""):
        nonlocal passed, failed
        status = "PASS" if condition else "FAIL"
        if not condition:
            failed += 1
        else:
            passed += 1
        suffix = f" — {detail}" if detail else ""
        print(f"  [{status}] {name}{suffix}")

    # === Phase 1: Framing ===
    print("\n=== Phase 1: Framing ===")

    p = Problem(
        name="SaaS Feature Prioritization",
        domain="SaaS product management",
        context="Pick features for public beta",
        objectives=OBJECTIVES,
        options=OPTIONS,
        constraints=CONSTRAINTS,
    )

    m = compute_metrics(p)
    check("Objective count", m["framing"]["objective_count"] == 3, f"got {m['framing']['objective_count']}")
    check("Option count", m["framing"]["option_count"] == 10, f"got {m['framing']['option_count']}")
    check("Directions set", m["framing"]["directions_set"])
    check("Has constraints", m["framing"]["constraint_count"] > 0)
    check("Score completeness 0%", m["data"]["score_completeness"] == 0.0)

    # === Phase 2: Scoring ===
    print("\n=== Phase 2: Scoring ===")

    p.scores = SCORES
    m = compute_metrics(p)
    check("Score completeness 100%", m["data"]["score_completeness"] == 1.0, f"got {m['data']['score_completeness']}")
    check("No missing scores", len(m["data"]["missing_scores"]) == 0, f"missing: {len(m['data']['missing_scores'])}")
    check("Revenue variance > 0", m["data"]["score_variance_by_objective"].get("Revenue Impact", 0) > 0)
    check("Effort variance > 0", m["data"]["score_variance_by_objective"].get("Eng Effort", 0) > 0)

    # === Phase 3: Validation ===
    print("\n=== Phase 3: Validation ===")

    vr = validate(p)
    check("Validation passes", vr.ready, f"issues: {[i.message for i in vr.issues]}")

    # === Phase 4: Optimization ===
    print("\n=== Phase 4: First Solve ===")

    run = optimize(p)
    p.run = run
    m = compute_metrics(p)

    check("Solve success", m["solve"]["solve_success"])
    check("Solutions found >= 5", m["solve"]["solution_count"] >= 5, f"got {m['solve']['solution_count']}")
    check("Feasible", m["solve"]["solve_success"])
    check("Hypervolume > 0.3", (m["solve"]["hypervolume"] or 0) > 0.3, f"got {m['solve']['hypervolume']}")

    # All solutions respect constraints
    for sol in run.solutions:
        check(
            f"Solution {sol.solution_id}: cardinality 3-5",
            3 <= len(sol.selected_options) <= 5,
            f"selected {len(sol.selected_options)}",
        )
        check(
            f"Solution {sol.solution_id}: includes SSO",
            "SSO Integration" in sol.selected_options,
        )

    # No zero_solutions diagnostic
    diags = diagnostics(p)
    check("No zero_solutions diagnostic", not any(d["pattern"] == "zero_solutions" for d in diags))

    # === Phase 5: Exploration ===
    print("\n=== Phase 5: Exploration ===")

    tradeoffs = get_tradeoffs(p)
    check("Tradeoffs has objective_ranges", "objective_ranges" in tradeoffs)
    check("Tradeoffs has balanced_solution", "balanced_solution" in tradeoffs)
    check("Tradeoffs has extreme_solutions", "extreme_solutions" in tradeoffs)

    # Compare two solutions
    if len(run.solutions) >= 2:
        comp = compare_solutions(p, [0, 1])
        check("Compare returns shared_options", "shared_options" in comp)
        check("Compare returns differentiating_options", "differentiating_options" in comp)

    # === Phase 6: Refinement ===
    print("\n=== Phase 6: Refinement (add effort bound) ===")

    solution_count_v1 = len(run.solutions)
    # Stale flag: mark stale rather than clearing
    p.results_stale = True
    run_v1_id = run.run_id
    p.constraints.append(
        ObjectiveBoundConstraint(objective="Eng Effort", operator="max", value=30)
    )

    run_v2 = optimize(p)
    run_v2.constraints_snapshot = [c.model_dump() for c in p.constraints]
    # Archive previous run
    p.runs.append(p.run)
    p.run = run_v2
    p.results_stale = False
    m_v2 = compute_metrics(p)

    check("Re-solve success", m_v2["solve"]["solve_success"])
    check(
        "Fewer solutions after constraint",
        m_v2["solve"]["solution_count"] <= solution_count_v1,
        f"v1={solution_count_v1}, v2={m_v2['solve']['solution_count']}",
    )

    # All solutions respect effort bound
    for sol in run_v2.solutions:
        total_effort = sol.objective_values.get("Eng Effort", 0)
        check(
            f"Solution {sol.solution_id}: effort ≤ 30",
            total_effort <= 30,
            f"effort={total_effort}",
        )

    # === Phase 7: Feedback ===
    print("\n=== Phase 7: Feedback ===")

    p.feedback.append(
        Feedback(solution_id=0, rating=4, notes="Good balance", stage="decision")
    )
    m_final = compute_metrics(p)
    check("Feedback recorded", m_final["outcome"]["feedback_count"] == 1)
    check("Selected solution recorded", m_final["outcome"]["user_selected_solution"] == 0)
    check("Rating recorded", m_final["outcome"]["user_rating"] == 4)

    # === Phase 8: Aggregation ===
    print("\n=== Phase 8: Aggregation (avg objective) ===")

    p_agg = Problem(
        name="Aggregation Test",
        objectives=[
            Objective(name="TotalRev", direction="maximize", aggregation="sum"),
            Objective(name="AvgSat", direction="maximize", aggregation="avg"),
        ],
        options=[Option(name=n) for n in ["A", "B", "C", "D", "E"]],
        scores=[
            Score(option="A", objective="TotalRev", value=10), Score(option="A", objective="AvgSat", value=9),
            Score(option="B", objective="TotalRev", value=6),  Score(option="B", objective="AvgSat", value=4),
            Score(option="C", objective="TotalRev", value=8),  Score(option="C", objective="AvgSat", value=7),
            Score(option="D", objective="TotalRev", value=3),  Score(option="D", objective="AvgSat", value=8),
            Score(option="E", objective="TotalRev", value=5),  Score(option="E", objective="AvgSat", value=6),
        ],
        constraints=[CardinalityConstraint(min=2, max=3)],
    )
    run_agg = optimize(p_agg)
    p_agg.run = run_agg
    check("Aggregation solve success", len(run_agg.solutions) > 0)

    # Verify avg is actually computed as average, not sum
    for sol in run_agg.solutions:
        sat_scores = [
            s.value for s in p_agg.scores
            if s.objective == "AvgSat" and s.option in sol.selected_options
        ]
        expected_avg = sum(sat_scores) / len(sat_scores)
        check(
            f"Sol {sol.solution_id}: avg correct",
            abs(sol.objective_values["AvgSat"] - expected_avg) < 0.01,
            f"got {sol.objective_values['AvgSat']}, expected {expected_avg}",
        )

    # === Phase 9: Run Comparison ===
    print("\n=== Phase 9: Run Comparison ===")

    run_v2_id = run_v2.run_id
    check("Run history has archived run", len(p.runs) >= 1)
    check("Current run has constraints_snapshot", len(p.run.constraints_snapshot) > 0)

    # We need the first run to also have a snapshot for comparison
    # Stamp it if missing (Phase 0 runs won't have it)
    if not p.runs[0].constraints_snapshot:
        p.runs[0].constraints_snapshot = [
            c.model_dump() for c in [
                CardinalityConstraint(min=3, max=5),
                ForceIncludeConstraint(option="SSO Integration"),
            ]
        ]

    comp = compare_runs(p, [p.runs[0].run_id, p.run.run_id])
    check("Compare returns runs_compared", len(comp["runs_compared"]) == 2)
    check("Compare returns criteria_diffs", len(comp["criteria_diffs"]) > 0)
    check("Compare returns frontier_diffs", len(comp["frontier_diffs"]) == 2)
    check("Compare returns option_coverage", len(comp["option_coverage"]) == 2)
    check("Criteria diff shows added constraint", len(comp["criteria_diffs"][0]["added"]) > 0)

    # === Phase 10: Proportional Allocation ===
    print("\n=== Phase 10: Proportional Allocation ===")

    p_prop = Problem(
        name="Budget Allocation Test",
        approach="proportional",
        objectives=[
            Objective(name="ROI", direction="maximize", unit="%"),
            Objective(name="Risk", direction="minimize", unit="score"),
        ],
        options=[Option(name=n) for n in ["Channel A", "Channel B", "Channel C", "Channel D"]],
        scores=[
            Score(option="Channel A", objective="ROI", value=12), Score(option="Channel A", objective="Risk", value=8),
            Score(option="Channel B", objective="ROI", value=8),  Score(option="Channel B", objective="Risk", value=3),
            Score(option="Channel C", objective="ROI", value=15), Score(option="Channel C", objective="Risk", value=9),
            Score(option="Channel D", objective="ROI", value=5),  Score(option="Channel D", objective="Risk", value=2),
        ],
        constraints=[CardinalityConstraint(min=2, max=3)],
    )
    run_prop = optimize(p_prop)
    p_prop.run = run_prop
    check("Proportional solve success", len(run_prop.solutions) > 0)

    for sol in run_prop.solutions:
        check(
            f"Sol {sol.solution_id}: has allocations",
            sol.allocations is not None,
        )
        if sol.allocations:
            total = sum(sol.allocations.values())
            check(
                f"Sol {sol.solution_id}: allocations sum to ~100",
                abs(total - 100) <= 1,
                f"sum={total}",
            )
            n_allocated = sum(1 for v in sol.allocations.values() if v > 0)
            check(
                f"Sol {sol.solution_id}: cardinality 2-3",
                2 <= n_allocated <= 3,
                f"allocated to {n_allocated}",
            )

    # === Phase 11: New Constraint Types ===
    print("\n=== Phase 11: New Constraint Types ===")

    p_constr = Problem(
        name="Constraint Test",
        objectives=[
            Objective(name="Value", direction="maximize"),
            Objective(name="Cost", direction="minimize"),
        ],
        options=[Option(name=n) for n in ["A", "B", "C", "D", "E", "F"]],
        scores=[
            Score(option="A", objective="Value", value=10), Score(option="A", objective="Cost", value=8),
            Score(option="B", objective="Value", value=7),  Score(option="B", objective="Cost", value=4),
            Score(option="C", objective="Value", value=9),  Score(option="C", objective="Cost", value=7),
            Score(option="D", objective="Value", value=5),  Score(option="D", objective="Cost", value=2),
            Score(option="E", objective="Value", value=6),  Score(option="E", objective="Cost", value=3),
            Score(option="F", objective="Value", value=8),  Score(option="F", objective="Cost", value=5),
        ],
        constraints=[
            CardinalityConstraint(min=2, max=3),
            ExclusionPairConstraint(option_a="A", option_b="C"),
            DependencyConstraint(if_option="B", then_option="D"),
            GroupLimitConstraint(options=["A", "C", "F"], max=1),
        ],
    )
    run_constr = optimize(p_constr)
    p_constr.run = run_constr
    check("Constraint test solve success", len(run_constr.solutions) > 0)
    for sol in run_constr.solutions:
        check(f"Sol {sol.solution_id}: exclusion pair", not ("A" in sol.selected_options and "C" in sol.selected_options))
        if "B" in sol.selected_options:
            check(f"Sol {sol.solution_id}: dependency B→D", "D" in sol.selected_options)
        group_count = sum(1 for o in ["A", "C", "F"] if o in sol.selected_options)
        check(f"Sol {sol.solution_id}: group limit ≤1", group_count <= 1)

    # === Phase 12: Reference Points ===
    print("\n=== Phase 12: Reference Points ===")

    p.reference_points = [
        ReferencePoint(type="baseline", name="Current", objective_values={"Revenue Impact": 20, "Eng Effort": 50, "User Satisfaction": 25}),
        ReferencePoint(type="aspirational", name="Target", objective_values={"Revenue Impact": 35, "Eng Effort": 20, "User Satisfaction": 35}),
    ]
    sol_detail = get_solution(p, 0)
    check("Solution has vs_references", "vs_references" in sol_detail)
    check("Two reference comparisons", len(sol_detail["vs_references"]) == 2)
    ref_baseline = sol_detail["vs_references"][0]
    check("Baseline has objectives", len(ref_baseline["objectives"]) > 0)

    tradeoffs_ref = get_tradeoffs(p)
    check("Tradeoffs has balanced_vs_references", "balanced_vs_references" in tradeoffs_ref)

    # === Phase 13: Scenarios ===
    print("\n=== Phase 13: Scenarios ===")

    p_scen = Problem(
        name="Scenario Test",
        objectives=OBJECTIVES,
        options=OPTIONS,
        scores=SCORES,
        constraints=[CardinalityConstraint(min=3, max=5), ForceIncludeConstraint(option="SSO Integration")],
        scenario_config=ScenarioConfig(enabled=True, scenarios=[
            Scenario(name="Base", probability=0.5, score_overrides=[]),
            Scenario(name="Growth", probability=0.3, score_overrides=[
                Score(option="Real-time Collaboration", objective="Revenue Impact", value=15),
                Score(option="AI Content Generation", objective="Revenue Impact", value=14),
            ]),
            Scenario(name="Contraction", probability=0.2, score_overrides=[
                Score(option="Mobile App", objective="Revenue Impact", value=2),
                Score(option="Analytics Dashboard", objective="Revenue Impact", value=3),
            ]),
        ]),
    )
    scenario_results = optimize_scenarios(p_scen)
    from engine.models import ScenarioRun
    p_scen.scenario_run = ScenarioRun(scenario_runs=scenario_results)
    check("3 scenarios optimized", len(scenario_results) == 3)
    for name, run in scenario_results.items():
        check(f"Scenario '{name}' has solutions", len(run.solutions) > 0)

    analysis = get_scenario_results(p_scen)
    check("Has robust_options", "robust_options" in analysis)
    check("Has scenario_specific_options", "scenario_specific_options" in analysis)
    check("Has expected_values", "expected_values" in analysis)
    check("Has per_scenario", len(analysis["per_scenario"]) == 3)

    # === Phase 14: Solution Curation ===
    print("\n=== Phase 14: Solution Curation ===")

    # Use the main problem p (which has run_v2 from Phase 6)
    # Curate two solutions
    if len(p.run.solutions) >= 2:
        r1 = curate_solution(p, 0, custom_name="Conservative Pick", notes="Low effort")
        check("Curate first solution", r1.get("curated") is True)
        r2 = curate_solution(p, 1, custom_name="Growth Bet")
        check("Curate second solution", r2.get("curated") is True)

        # List curated
        curated = list_curated(p)
        check("Two curated solutions", curated["total_curated"] == 2)
        check("Both in frontier", all(c["in_current_frontier"] for c in curated["curated_solutions"]))

        # Compare curated
        sigs = [c["content_signature"] for c in curated["curated_solutions"]]
        comp = compare_curated(p, sigs)
        check("Compare has shared_options", "shared_options" in comp)
        check("Compare has custom names", comp["solutions"][0]["custom_name"] == "Conservative Pick")

        # Content signatures are stable
        check("Signature length", all(len(s) == 12 for s in sigs))

        # Duplicate detection
        dup = curate_solution(p, 0, custom_name="Duplicate")
        check("Duplicate blocked", "error" in dup)

    # === Summary ===
    print(f"\n{'=' * 40}")
    print(f"CHECKPOINT RESULTS: {passed} passed, {failed} failed")
    if failed == 0:
        print("ALL CHECKS PASSED")
    else:
        print(f"WARNING: {failed} check(s) failed")
    print(f"{'=' * 40}")

    return failed == 0


if __name__ == "__main__":
    success = run_checkpoint()
    exit(0 if success else 1)
