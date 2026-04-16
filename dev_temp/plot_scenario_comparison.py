"""Plot multi-scenario Pareto fronts: Frontier vs pymoo vs LLM for each scenario."""

import json
import matplotlib.pyplot as plt
import matplotlib
import numpy as np

matplotlib.rcParams['font.size'] = 10

# ── Load Frontier solutions (329 per scenario) ──
frontier_files = {
    "Base Case": "/Users/cameronafzal/.claude/projects/-Users-cameronafzal-Documents-frontier/c22acb50-33fe-4fd8-99b3-73b5cdc084bd/tool-results/mcp-frontier-explore-1776109482679.txt",
    "Rate Cuts": "/Users/cameronafzal/.claude/projects/-Users-cameronafzal-Documents-frontier/c22acb50-33fe-4fd8-99b3-73b5cdc084bd/tool-results/mcp-frontier-explore-1776109483690.txt",
    "Recession": "/Users/cameronafzal/.claude/projects/-Users-cameronafzal-Documents-frontier/c22acb50-33fe-4fd8-99b3-73b5cdc084bd/tool-results/mcp-frontier-explore-1776109484148.txt",
    "Inflation": "/Users/cameronafzal/.claude/projects/-Users-cameronafzal-Documents-frontier/c22acb50-33fe-4fd8-99b3-73b5cdc084bd/tool-results/mcp-frontier-explore-1776109484750.txt",
}

frontier_data = {}
for name, path in frontier_files.items():
    with open(path) as f:
        raw = json.loads(f.read())
    data = json.loads(raw[0]["text"])
    sols = data["solutions"]
    frontier_data[name] = {
        "ret": [s["objective_values"]["Expected Return"] for s in sols],
        "vol": [s["objective_values"]["Volatility"] for s in sols],
        "yld": [s["objective_values"]["Dividend Yield"] for s in sols],
    }

# ── Load pymoo solutions ──
with open("/Users/cameronafzal/Documents/frontier/dev_temp/scenario_pymoo_raw.json") as f:
    pymoo_raw = json.load(f)

pymoo_scenario_map = {"base": "Base Case", "rate_cuts": "Rate Cuts", "recession": "Recession", "inflation": "Inflation"}
pymoo_data = {}
for result in pymoo_raw["all_results"]:
    name = pymoo_scenario_map[result["scenario"]]
    pymoo_data[name] = {
        "ret": [s["return_pct"] for s in result["solutions"]],
        "vol": [s["volatility_pct"] for s in result["solutions"]],
        "yld": [s["yield_pct"] for s in result["solutions"]],
    }

# ── Load LLM curated strategies ──
llm_raw = {
    "Base Case": {
        "Growth": {"ret": 15.46, "vol": 16.83, "yld": 1.46},
        "Balanced": {"ret": 11.47, "vol": 12.94, "yld": 2.08},
        "Income": {"ret": 6.36, "vol": 10.44, "yld": 4.27},
        "Safety": {"ret": 2.94, "vol": 5.80, "yld": 3.97},
    },
    "Rate Cuts": {
        "Growth": {"ret": 17.09, "vol": 16.93, "yld": 0.94},
        "Balanced": {"ret": 13.45, "vol": 14.10, "yld": 2.03},
        "Income": {"ret": 7.34, "vol": 10.70, "yld": 3.60},
        "Safety": {"ret": 2.71, "vol": 6.11, "yld": 2.97},
    },
    "Recession": {
        "Growth": {"ret": 11.97, "vol": 11.61, "yld": 2.29},
        "Balanced": {"ret": 9.09, "vol": 9.90, "yld": 2.96},
        "Income": {"ret": 3.12, "vol": 8.89, "yld": 4.09},
        "Safety": {"ret": 4.57, "vol": 5.23, "yld": 3.78},
    },
    "Inflation": {
        "Growth": {"ret": 19.69, "vol": 16.00, "yld": 1.22},
        "Balanced": {"ret": 14.33, "vol": 12.35, "yld": 2.18},
        "Income": {"ret": 6.29, "vol": 9.49, "yld": 4.40},
        "Safety": {"ret": 5.63, "vol": 6.69, "yld": 4.18},
    },
}

llm_data = {}
for name, strats in llm_raw.items():
    llm_data[name] = {
        "ret": [s["ret"] for s in strats.values()],
        "vol": [s["vol"] for s in strats.values()],
        "yld": [s["yld"] for s in strats.values()],
    }

# ── Load Frontier curated strategies ──
with open("/Users/cameronafzal/Documents/frontier/dev_temp/scenario_candidates.json") as f:
    frontier_curated_raw = json.load(f)

frontier_curated = {}
for name, strats in frontier_curated_raw.items():
    frontier_curated[name] = {
        label: {
            "ret": s["objectives"]["Expected Return"],
            "vol": s["objectives"]["Volatility"],
            "yld": s["objectives"]["Dividend Yield"],
        }
        for label, s in strats.items()
    }

# ── Load pymoo curated strategies ──
pymoo_strat_map = {"base": "Base Case", "rate_cuts": "Rate Cuts", "recession": "Recession", "inflation": "Inflation"}
pymoo_curated = {}
for key, name in pymoo_strat_map.items():
    strats = pymoo_raw["all_strategies"][key]
    pymoo_curated[name] = {
        label: {
            "ret": s["return_pct"],
            "vol": s["volatility_pct"],
            "yld": s["yield_pct"],
        }
        for label, s in strats.items()
    }

scenarios = ["Base Case", "Rate Cuts", "Recession", "Inflation"]

# ══════════════════════════════════════════════════════════════
# PLOT 1: 4-panel Return vs Volatility (one per scenario)
# ══════════════════════════════════════════════════════════════
fig, axes = plt.subplots(2, 2, figsize=(16, 12))
fig.suptitle("Pareto Fronts by Scenario: Frontier vs pymoo vs LLM", fontsize=16, fontweight='bold', y=0.98)

for idx, scenario in enumerate(scenarios):
    ax = axes[idx // 2][idx % 2]

    # Frontier cloud
    f = frontier_data[scenario]
    ax.scatter(f["vol"], f["ret"], c='#4A90D9', alpha=0.25, s=15, label=f'Frontier — {len(f["ret"])} solutions', zorder=2)

    # pymoo diamonds
    p = pymoo_data[scenario]
    ax.scatter(p["vol"], p["ret"], c='#2ECC71', marker='D', alpha=0.5, s=30, label=f'pymoo — {len(p["ret"])} solutions', zorder=3)

    # LLM squares
    l = llm_data[scenario]
    ax.scatter(l["vol"], l["ret"], c='#E74C3C', marker='s', s=80, label='LLM — 4 solutions', zorder=5, edgecolors='black', linewidths=0.5)

    # Frontier curated - large circles
    fc = frontier_curated.get(scenario, frontier_curated.get("Base Case"))
    for label, vals in fc.items():
        ax.scatter(vals["vol"], vals["ret"], c='#4A90D9', s=150, zorder=6, edgecolors='black', linewidths=1.5)

    # pymoo curated - large diamonds
    pc = pymoo_curated[scenario]
    for label, vals in pc.items():
        ax.scatter(vals["vol"], vals["ret"], c='#2ECC71', marker='D', s=120, zorder=6, edgecolors='black', linewidths=1.5)

    # Labels for LLM points
    for label, vals in llm_raw[scenario].items():
        offset = (5, 5) if label != "Safety" else (5, -12)
        ax.annotate(label, (vals["vol"], vals["ret"]), fontsize=7, color='#E74C3C',
                   xytext=offset, textcoords='offset points', style='italic')

    ax.set_title(scenario, fontsize=13, fontweight='bold')
    ax.set_xlabel('Volatility (%)')
    ax.set_ylabel('Expected Return (%)')
    ax.set_xlim(0, 22)
    ax.set_ylim(0, 22)
    ax.grid(True, alpha=0.3)

    if idx == 0:
        ax.legend(fontsize=8, loc='upper left')

plt.tight_layout(rect=[0, 0, 1, 0.96])
plt.savefig('/Users/cameronafzal/Documents/frontier/dev_temp/scenario_pareto_comparison.png', dpi=150, bbox_inches='tight')
print("Saved scenario_pareto_comparison.png")

# ══════════════════════════════════════════════════════════════
# PLOT 2: 3x4 grid (3 objective pairs x 4 scenarios)
# ══════════════════════════════════════════════════════════════
fig2, axes2 = plt.subplots(3, 4, figsize=(22, 14))
fig2.suptitle("All Objective Pairs by Scenario (No Curation Highlights)", fontsize=16, fontweight='bold', y=0.99)

pairs = [
    ("vol", "ret", "Return vs Volatility", "Volatility (%)", "Expected Return (%)"),
    ("vol", "yld", "Yield vs Volatility", "Volatility (%)", "Dividend Yield (%)"),
    ("ret", "yld", "Yield vs Return", "Expected Return (%)", "Dividend Yield (%)"),
]

for row, (xkey, ykey, pair_title, xlabel, ylabel) in enumerate(pairs):
    for col, scenario in enumerate(scenarios):
        ax = axes2[row][col]

        f = frontier_data[scenario]
        ax.scatter(f[xkey], f[ykey], c='#4A90D9', alpha=0.25, s=12, zorder=2)

        p = pymoo_data[scenario]
        ax.scatter(p[xkey], p[ykey], c='#2ECC71', marker='D', alpha=0.5, s=25, zorder=3)

        l = llm_data[scenario]
        ax.scatter(l[xkey], l[ykey], c='#E74C3C', marker='s', s=60, zorder=5, edgecolors='black', linewidths=0.5)

        if row == 0:
            ax.set_title(scenario, fontsize=11, fontweight='bold')
        if col == 0:
            ax.set_ylabel(ylabel, fontsize=9)
        ax.set_xlabel(xlabel, fontsize=8)
        ax.grid(True, alpha=0.3)

# Add shared legend
from matplotlib.lines import Line2D
legend_elements = [
    Line2D([0], [0], marker='o', color='w', markerfacecolor='#4A90D9', markersize=8, label=f'Frontier — 329/scenario'),
    Line2D([0], [0], marker='D', color='w', markerfacecolor='#2ECC71', markersize=8, label=f'pymoo — ~40/scenario'),
    Line2D([0], [0], marker='s', color='w', markerfacecolor='#E74C3C', markersize=8, label='LLM — 4/scenario'),
]
fig2.legend(handles=legend_elements, loc='lower center', ncol=3, fontsize=11, bbox_to_anchor=(0.5, -0.01))

plt.tight_layout(rect=[0, 0.02, 1, 0.97])
plt.savefig('/Users/cameronafzal/Documents/frontier/dev_temp/scenario_pareto_all_pairs.png', dpi=150, bbox_inches='tight')
print("Saved scenario_pareto_all_pairs.png")

# ══════════════════════════════════════════════════════════════
# PLOT 3: Curated strategy comparison (4 panels, strategies labeled)
# ══════════════════════════════════════════════════════════════
fig3, axes3 = plt.subplots(2, 2, figsize=(16, 12))
fig3.suptitle("Curated Strategies by Scenario: Frontier vs pymoo vs LLM", fontsize=16, fontweight='bold', y=0.98)

strategy_labels = ["Growth", "Balanced", "Income", "Safety"]

for idx, scenario in enumerate(scenarios):
    ax = axes3[idx // 2][idx % 2]

    # Background: Frontier cloud (faded)
    f = frontier_data[scenario]
    ax.scatter(f["vol"], f["ret"], c='#4A90D9', alpha=0.08, s=8, zorder=1)

    # pymoo cloud (faded)
    p = pymoo_data[scenario]
    ax.scatter(p["vol"], p["ret"], c='#2ECC71', marker='D', alpha=0.15, s=15, zorder=1)

    # Curated strategies with labels
    fc = frontier_curated.get(scenario, frontier_curated.get("Base Case"))
    pc = pymoo_curated[scenario]
    lc = llm_raw[scenario]

    for label in strategy_labels:
        # Frontier
        fv = fc[label]
        ax.scatter(fv["vol"], fv["ret"], c='#4A90D9', s=140, zorder=6, edgecolors='black', linewidths=1.5)

        # pymoo
        pv = pc[label]
        ax.scatter(pv["vol"], pv["ret"], c='#2ECC71', marker='D', s=110, zorder=6, edgecolors='black', linewidths=1.5)

        # LLM
        lv = lc[label]
        ax.scatter(lv["vol"], lv["ret"], c='#E74C3C', marker='s', s=90, zorder=6, edgecolors='black', linewidths=0.5)

        # Label at centroid of three
        cx = np.mean([fv["vol"], pv["vol"], lv["vol"]])
        cy = np.mean([fv["ret"], pv["ret"], lv["ret"]])
        ax.annotate(label, (cx, cy), fontsize=8, fontweight='bold', color='#333',
                   xytext=(8, 8), textcoords='offset points',
                   bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.7, edgecolor='gray'))

    ax.set_title(scenario, fontsize=13, fontweight='bold')
    ax.set_xlabel('Volatility (%)')
    ax.set_ylabel('Expected Return (%)')
    ax.set_xlim(0, 22)
    ax.set_ylim(0, 22)
    ax.grid(True, alpha=0.3)

    if idx == 0:
        legend_elements2 = [
            Line2D([0], [0], marker='o', color='w', markerfacecolor='#4A90D9', markersize=10, markeredgecolor='black', markeredgewidth=1, label='Frontier'),
            Line2D([0], [0], marker='D', color='w', markerfacecolor='#2ECC71', markersize=10, markeredgecolor='black', markeredgewidth=1, label='pymoo'),
            Line2D([0], [0], marker='s', color='w', markerfacecolor='#E74C3C', markersize=10, markeredgecolor='black', markeredgewidth=0.5, label='LLM'),
        ]
        ax.legend(handles=legend_elements2, fontsize=9, loc='upper left')

plt.tight_layout(rect=[0, 0, 1, 0.96])
plt.savefig('/Users/cameronafzal/Documents/frontier/dev_temp/scenario_curated_comparison.png', dpi=150, bbox_inches='tight')
print("Saved scenario_curated_comparison.png")

plt.close('all')
print("\nDone. 3 plots saved.")
