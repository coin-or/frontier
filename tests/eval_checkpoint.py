"""Eval checkpoint: deterministic end-to-end test of the Phase 0 workflow.

Exercises: model → score → solve → explore → refine → re-solve → feedback
using the SaaS Feature Prioritization test data from the design doc.

Run: python -m tests.eval_checkpoint
"""

from frontier.engine.metrics import compute_metrics, diagnostics
from frontier.engine.models import (
    CardinalityConstraint,
    Feedback,
    ForceIncludeConstraint,
    ObjectiveBoundConstraint,
    Objective,
    Option,
    Problem,
    Score,
)
from frontier.engine.optimizer import optimize, validate
from frontier.engine.explorer import compare_solutions, get_tradeoffs

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
    p.constraints.append(
        ObjectiveBoundConstraint(objective="Eng Effort", operator="max", value=30)
    )
    p.run = None  # Clear run (as server would)

    run_v2 = optimize(p)
    p.run = run_v2
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
