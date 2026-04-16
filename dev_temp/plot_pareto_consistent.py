"""Apples-to-apples Pareto comparison: consistent sample points across methods.

Instead of subjectively curated strategies, sample at fixed return targets
and find each method's nearest solution. Shows what each method achieves
at the same return level.
"""

import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D

# --- Load data ---

frontier_raw = json.loads(open("/Users/cameronafzal/Documents/frontier/dev_temp/run2_frontier.md").read().split("```json\n")[1].split("\n```")[0])
pymoo_raw = json.loads(open("/Users/cameronafzal/Documents/frontier/dev_temp/run2_pymoo.md").read().split("```json\n")[1].split("\n```")[0])
llm_raw = json.loads(open("/Users/cameronafzal/Documents/frontier/dev_temp/run2_llm_only.md").read().split("```json\n")[1].split("\n```")[0])

frontier_sols = frontier_raw["solutions"]
pymoo_sols = pymoo_raw["solutions"]
llm_sols = llm_raw["solutions"]

# --- Find nearest solution to a target return ---
def nearest(solutions, target_return):
    best = min(solutions, key=lambda s: abs(s["return"] - target_return))
    return best

# Fixed return targets spanning the common range
targets = [4, 6, 8, 10, 12, 14, 18]

# For each target, find nearest from each method (skip if method's range doesn't cover it)
def in_range(sols, target, margin=3.0):
    return any(abs(s["return"] - target) < margin for s in sols)

frontier_at = [nearest(frontier_sols, t) for t in targets]
pymoo_at = [nearest(pymoo_sols, t) for t in targets if in_range(pymoo_sols, t)]
pymoo_targets = [t for t in targets if in_range(pymoo_sols, t)]
llm_at = [nearest(llm_sols, t) for t in targets if in_range(llm_sols, t)]
llm_targets = [t for t in targets if in_range(llm_sols, t)]

# --- Colors ---
c_f = "#2563EB"
c_p = "#16A34A"
c_l = "#DC2626"

# --- Plot 1a: 3-panel raw clouds (no annotations) ---
fig, axes = plt.subplots(1, 3, figsize=(20, 6.5))
fig.suptitle("Pareto Fronts: All Solutions (No Curation)", fontsize=14, fontweight="bold", y=0.98)

pairs = [
    ("vol", "return", "Volatility (%)", "Expected Return (%)", "Return vs Volatility"),
    ("vol", "yield", "Volatility (%)", "Dividend Yield (%)", "Yield vs Volatility"),
    ("return", "yield", "Expected Return (%)", "Dividend Yield (%)", "Yield vs Return"),
]

for idx, (xkey, ykey, xlabel, ylabel, title) in enumerate(pairs):
    a = axes[idx]
    a.scatter([s[xkey] for s in frontier_sols], [s[ykey] for s in frontier_sols],
              c=c_f, alpha=0.3, s=14, zorder=2)
    a.scatter([s[xkey] for s in pymoo_sols], [s[ykey] for s in pymoo_sols],
              c=c_p, alpha=0.5, s=25, marker="D", zorder=3)
    a.scatter([s[xkey] for s in llm_sols], [s[ykey] for s in llm_sols],
              c=c_l, s=80, marker="s", zorder=5, edgecolors="black", linewidths=0.5)
    a.set_xlabel(xlabel, fontsize=10)
    a.set_ylabel(ylabel, fontsize=10)
    a.set_title(title, fontsize=11)
    a.grid(True, alpha=0.3)

legend_elements_3p = [
    Line2D([0], [0], marker='o', color='w', markerfacecolor=c_f, markersize=7, alpha=0.5,
           label=f'Frontier — {len(frontier_sols)} solutions'),
    Line2D([0], [0], marker='D', color='w', markerfacecolor=c_p, markersize=7, alpha=0.7,
           label=f'pymoo — {len(pymoo_sols)} solutions'),
    Line2D([0], [0], marker='s', color='w', markerfacecolor=c_l, markersize=9,
           markeredgecolor='black', markeredgewidth=0.5, label=f'LLM — {len(llm_sols)} solutions'),
]
fig.legend(handles=legend_elements_3p, loc='lower center', ncol=3, fontsize=10,
           bbox_to_anchor=(0.5, -0.01))
plt.tight_layout(rect=[0, 0.05, 1, 0.95])
plt.savefig("/Users/cameronafzal/Documents/frontier/dev_temp/pareto_raw.png", dpi=150, bbox_inches="tight")
print("Saved: pareto_raw.png")
plt.close()

# --- Plot 1b: Single-panel Return vs Volatility with annotated highlights ---
fig, ax = plt.subplots(figsize=(12, 8))
fig.suptitle("Pareto Fronts: All Solutions with Highlighted Strategies",
             fontsize=14, fontweight="bold", y=0.97)

# Raw clouds
ax.scatter([s["vol"] for s in frontier_sols], [s["return"] for s in frontier_sols],
           c=c_f, alpha=0.25, s=18, zorder=2)
ax.scatter([s["vol"] for s in pymoo_sols], [s["return"] for s in pymoo_sols],
           c=c_p, alpha=0.4, s=30, marker="D", zorder=3)
ax.scatter([s["vol"] for s in llm_sols], [s["return"] for s in llm_sols],
           c=c_l, s=100, marker="s", zorder=5, edgecolors="black", linewidths=0.5)

# --- Frontier auto-identified (3 extremes + balanced via explore/tradeoffs) ---
frontier_highlights = [
    {"vol": 17.56, "return": 19.01, "label": "Growth\n(extreme: return)"},
    {"vol": 8.46,  "return": 4.27,  "label": "Income\n(extreme: yield)"},
    {"vol": 3.06,  "return": 2.31,  "label": "Safety\n(extreme: vol)"},
    {"vol": 11.07, "return": 9.89,  "label": "Balanced\n(ideal-point)"},
]
f_offsets = [(-85, 10), (-80, -20), (12, -8), (12, -16)]
for sol, (dx, dy) in zip(frontier_highlights, f_offsets):
    ax.scatter([sol["vol"]], [sol["return"]], c=c_f, s=110, marker="o", zorder=6,
               edgecolors="black", linewidths=1.3)
    ax.annotate(sol["label"], (sol["vol"], sol["return"]), fontsize=8, fontweight="bold",
                xytext=(dx, dy), textcoords="offset points",
                arrowprops=dict(arrowstyle="-", color=c_f, lw=1), color="#1e3a5f")

# --- pymoo auto-selected (argmax/argmin + center-distance in script) ---
pymoo_highlights = [
    {"vol": 16.87, "return": 14.17, "label": "Growth\n(argmax return)"},
    {"vol": 10.80, "return": 4.12,  "label": "Income\n(argmax yield)"},
    {"vol": 9.23,  "return": 4.93,  "label": "Safety\n(argmin vol)"},
    {"vol": 13.30, "return": 9.40,  "label": "Balanced\n(center-dist)"},
]
p_offsets = [(12, 6), (12, 8), (-75, 14), (12, 8)]
for sol, (dx, dy) in zip(pymoo_highlights, p_offsets):
    ax.scatter([sol["vol"]], [sol["return"]], c=c_p, s=80, marker="D", zorder=6,
               edgecolors="black", linewidths=1.3)
    ax.annotate(sol["label"], (sol["vol"], sol["return"]), fontsize=7.5, fontstyle="italic",
                xytext=(dx, dy), textcoords="offset points",
                arrowprops=dict(arrowstyle="-", color=c_p, lw=1), color="#0d5c2e")

# --- LLM hand-constructed (all 4 are the full output, no selection from pool) ---
llm_highlights = [
    {"vol": 19.98, "return": 18.58, "label": "Growth"},
    {"vol": 10.78, "return": 2.81,  "label": "Income"},
    {"vol": 4.52,  "return": 1.56,  "label": "Safety"},
    {"vol": 12.90, "return": 9.82,  "label": "Balanced"},
]
l_offsets = [(10, -14), (10, -14), (10, 8), (10, -14)]
for sol, (dx, dy) in zip(llm_highlights, l_offsets):
    ax.annotate(sol["label"], (sol["vol"], sol["return"]), fontsize=8,
                xytext=(dx, dy), textcoords="offset points",
                arrowprops=dict(arrowstyle="-", color=c_l, lw=1), color="#8b1a1a")

ax.set_xlabel("Volatility (%)", fontsize=12)
ax.set_ylabel("Expected Return (%)", fontsize=12)
ax.grid(True, alpha=0.25)

# Subtitle explaining selection methods
ax.text(0.02, 0.98,
        "Frontier: auto-identified by explorer (extremes + ideal-point balanced)\n"
        "pymoo: programmatically selected in agent-written script (argmax/argmin + center-distance)\n"
        "LLM: hand-constructed from scratch (no selection from pool)",
        transform=ax.transAxes, fontsize=7.5, verticalalignment='top',
        fontstyle='italic', color='#444444',
        bbox=dict(boxstyle='round,pad=0.4', facecolor='white', edgecolor='#cccccc', alpha=0.9))

legend_elements = [
    Line2D([0], [0], marker='o', color='w', markerfacecolor=c_f, markersize=7, alpha=0.5,
           label=f'Frontier — {len(frontier_sols)} solutions'),
    Line2D([0], [0], marker='D', color='w', markerfacecolor=c_p, markersize=7, alpha=0.7,
           label=f'pymoo — {len(pymoo_sols)} solutions'),
    Line2D([0], [0], marker='s', color='w', markerfacecolor=c_l, markersize=9,
           markeredgecolor='black', markeredgewidth=0.5, label=f'LLM — {len(llm_sols)} solutions'),
    Line2D([0], [0], marker='o', color='w', markerfacecolor='white', markersize=9,
           markeredgecolor='black', markeredgewidth=1.3, label='Highlighted strategy'),
]
ax.legend(handles=legend_elements, loc='upper left', fontsize=9,
          framealpha=0.9, edgecolor='#cccccc')

plt.tight_layout(rect=[0, 0, 1, 0.95])
plt.savefig("/Users/cameronafzal/Documents/frontier/dev_temp/pareto_annotated.png", dpi=150, bbox_inches="tight")
print("Saved: pareto_annotated.png")
plt.close()

# --- Plot 2: Matched at consistent return targets ---
fig, axes = plt.subplots(1, 2, figsize=(16, 7))
fig.suptitle("Matched Comparison at Same Return Targets", fontsize=14, fontweight="bold", y=0.98)

# Panel 1: Return vs Vol — what vol does each method need for a given return?
ax = axes[0]
# Faint background clouds
ax.scatter([s["vol"] for s in frontier_sols], [s["return"] for s in frontier_sols],
           c=c_f, alpha=0.12, s=8, zorder=1)
ax.scatter([s["vol"] for s in pymoo_sols], [s["return"] for s in pymoo_sols],
           c=c_p, alpha=0.15, s=10, zorder=1)

# Connected matched points
f_vols = [s["vol"] for s in frontier_at]
f_rets = [s["return"] for s in frontier_at]
ax.plot(f_vols, f_rets, '-o', c=c_f, markersize=8, linewidth=2, zorder=4, label="Frontier")

p_vols = [nearest(pymoo_sols, t)["vol"] for t in pymoo_targets]
p_rets = [nearest(pymoo_sols, t)["return"] for t in pymoo_targets]
ax.plot(p_vols, p_rets, '-D', c=c_p, markersize=8, linewidth=2, zorder=4, label="pymoo")

l_vols = [nearest(llm_sols, t)["vol"] for t in llm_targets]
l_rets = [nearest(llm_sols, t)["return"] for t in llm_targets]
ax.plot(l_vols, l_rets, '-*', c=c_l, markersize=14, linewidth=2, zorder=5, label="LLM")

# Horizontal reference lines at targets
for t in targets:
    ax.axhline(y=t, color='gray', alpha=0.2, linewidth=0.5, linestyle='--')
    ax.text(2.5, t + 0.3, f"{t}%", fontsize=7, color='gray')

ax.set_xlabel("Volatility (%)", fontsize=11)
ax.set_ylabel("Expected Return (%)", fontsize=11)
ax.set_title("At the same return, which method needs less volatility?", fontsize=10)
ax.legend(fontsize=10)
ax.grid(True, alpha=0.2)

# Panel 2: Return vs Yield — what yield does each method achieve at given return?
ax = axes[1]
ax.scatter([s["return"] for s in frontier_sols], [s["yield"] for s in frontier_sols],
           c=c_f, alpha=0.12, s=8, zorder=1)
ax.scatter([s["return"] for s in pymoo_sols], [s["yield"] for s in pymoo_sols],
           c=c_p, alpha=0.15, s=10, zorder=1)

f_yields = [s["yield"] for s in frontier_at]
ax.plot(f_rets, f_yields, '-o', c=c_f, markersize=8, linewidth=2, zorder=4, label="Frontier")

p_yields = [nearest(pymoo_sols, t)["yield"] for t in pymoo_targets]
ax.plot(p_rets, p_yields, '-D', c=c_p, markersize=8, linewidth=2, zorder=4, label="pymoo")

l_yields = [nearest(llm_sols, t)["yield"] for t in llm_targets]
ax.plot(l_rets, l_yields, '-*', c=c_l, markersize=14, linewidth=2, zorder=5, label="LLM")

for t in targets:
    ax.axvline(x=t, color='gray', alpha=0.2, linewidth=0.5, linestyle='--')

ax.set_xlabel("Expected Return (%)", fontsize=11)
ax.set_ylabel("Dividend Yield (%)", fontsize=11)
ax.set_title("At the same return, which method achieves more yield?", fontsize=10)
ax.legend(fontsize=10)
ax.grid(True, alpha=0.2)

plt.tight_layout(rect=[0, 0, 1, 0.95])
plt.savefig("/Users/cameronafzal/Documents/frontier/dev_temp/pareto_matched.png", dpi=150, bbox_inches="tight")
print("Saved: pareto_matched.png")
plt.close()

# Print the matched data table
print("\n=== Matched solutions at consistent return targets ===")
print(f"{'Target':>8} | {'Frontier':>30} | {'pymoo':>30} | {'LLM':>30}")
print(f"{'Return':>8} | {'ret':>8} {'vol':>8} {'yld':>8} | {'ret':>8} {'vol':>8} {'yld':>8} | {'ret':>8} {'vol':>8} {'yld':>8}")
print("-" * 105)
for t in targets:
    f = nearest(frontier_sols, t)
    p = nearest(pymoo_sols, t) if in_range(pymoo_sols, t) else None
    l = nearest(llm_sols, t) if in_range(llm_sols, t) else None
    f_str = f"{f['return']:8.2f} {f['vol']:8.2f} {f['yield']:8.2f}"
    p_str = f"{p['return']:8.2f} {p['vol']:8.2f} {p['yield']:8.2f}" if p else "       —        —        —"
    l_str = f"{l['return']:8.2f} {l['vol']:8.2f} {l['yield']:8.2f}" if l else "       —        —        —"
    print(f"{t:>7}% | {f_str} | {p_str} | {l_str}")
