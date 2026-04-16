#!/usr/bin/env python3
"""Generate all evaluation comparison plots for run_001."""

import json
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

PLOT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.join(os.path.dirname(PLOT_DIR), 'base')
SCEN_DIR = os.path.join(os.path.dirname(PLOT_DIR), 'scenarios')

# Colors and markers per checklist
COLORS = {'Frontier': '#2563EB', 'Solver': '#16A34A', 'LLM': '#DC2626'}
MARKERS = {'Frontier': 'o', 'Solver': 'D', 'LLM': 's'}
CURATED_SIZE = 120
CLOUD_SIZE = 30
CLOUD_ALPHA = 0.25
CURATED_ALPHA = 1.0

# ─── Data Loading ────────────────────────────────────────────────────

def load_base():
    """Load base case data from all three methods."""
    methods = {}

    # Frontier base
    with open(os.path.join(BASE_DIR, 'frontier', 'results.json')) as f:
        fd = json.load(f)
    methods['Frontier'] = {
        'solutions': [(s['return_pct'], s['volatility_pct'], s['yield_pct']) for s in fd['base']['solutions']],
        'curated': {k: (v['return_pct'], v['volatility_pct'], v['yield_pct']) for k, v in fd['base']['curated'].items()}
    }

    # Solver base
    with open(os.path.join(BASE_DIR, 'solver', 'results.json')) as f:
        sd = json.load(f)
    methods['Solver'] = {
        'solutions': [(s['return_pct'], s['volatility_pct'], s['yield_pct']) for s in sd['base']['solutions']],
        'curated': {k: (v['return_pct'], v['volatility_pct'], v['yield_pct']) for k, v in sd['base']['curated'].items()}
    }

    # LLM base
    with open(os.path.join(BASE_DIR, 'llm', 'results.json')) as f:
        ld = json.load(f)
    methods['LLM'] = {
        'solutions': [(s['return_pct'], s['volatility_pct'], s['yield_pct']) for s in ld['base']['solutions']],
        'curated': {k: (v['return_pct'], v['volatility_pct'], v['yield_pct']) for k, v in ld['base']['curated'].items()}
    }

    return methods


def load_scenarios():
    """Load scenario data from all three methods."""
    methods = {}

    # Frontier scenarios
    # New structure: each scenario has 'curated' (4 strategies) + either 'solutions'
    # (in base) or 'solutions_sample' (in other scenarios). Base case also has
    # 'scenario_run_solutions' (a sparse sample of the 40-solution-per-scenario run).
    with open(os.path.join(SCEN_DIR, 'frontier', 'results.json')) as f:
        fd = json.load(f)
    methods['Frontier'] = {}
    for scen_key in ['base', 'rate_cuts', 'recession', 'inflation']:
        sd = fd[scen_key]
        # Prefer the 'solutions' list if present; otherwise fall back to
        # 'scenario_run_solutions' or 'solutions_sample'. Include curated points so
        # the cloud is never empty even when only the 4 curated strategies exist.
        sol_list = sd.get('solutions') or sd.get('scenario_run_solutions') or sd.get('solutions_sample') or []
        solution_tuples = [(s['return_pct'], s['volatility_pct'], s['yield_pct']) for s in sol_list]
        # Always union curated points into cloud for plot density
        curated = {k: (v['return_pct'], v['volatility_pct'], v['yield_pct']) for k, v in sd['curated'].items()}
        for cv in curated.values():
            if cv not in solution_tuples:
                solution_tuples.append(cv)
        methods['Frontier'][scen_key] = {
            'solutions': solution_tuples,
            'curated': curated
        }

    # Solver scenarios
    with open(os.path.join(SCEN_DIR, 'solver', 'results.json')) as f:
        sd_all = json.load(f)
    methods['Solver'] = {}
    for scen_key in ['base', 'rate_cuts', 'recession', 'inflation']:
        sd = sd_all[scen_key]
        methods['Solver'][scen_key] = {
            'solutions': [(s['return_pct'], s['volatility_pct'], s.get('dividend_yield_pct', s.get('yield_pct', 0))) for s in sd['solutions']],
            'curated': {k: (v['return_pct'], v['volatility_pct'], v.get('dividend_yield_pct', v.get('yield_pct', 0))) for k, v in sd['curated'].items()}
        }

    # LLM scenarios
    with open(os.path.join(SCEN_DIR, 'llm', 'results.json')) as f:
        ld = json.load(f)
    scen_map = {
        'scenario_1_base': 'base',
        'scenario_2_rate_cuts': 'rate_cuts',
        'scenario_3_recession': 'recession',
        'scenario_4_inflation': 'inflation'
    }
    methods['LLM'] = {}
    for src_key, dest_key in scen_map.items():
        ports = ld['scenarios'][src_key]['portfolios']
        solutions = []
        curated = {}
        for pname, pdata in ports.items():
            pt = (pdata['expected_return_pct'], pdata['volatility_pct'], pdata['dividend_yield_pct'])
            solutions.append(pt)
            # Map to standard curated names
            name_map = {'growth': 'Growth', 'balanced': 'Balanced', 'income': 'Income', 'safety': 'Safety'}
            if pname in name_map:
                curated[name_map[pname]] = pt
        methods['LLM'][dest_key] = {
            'solutions': solutions,
            'curated': curated
        }

    return methods


# ─── Plot Helpers ────────────────────────────────────────────────────

def plot_cloud(ax, methods_data, x_idx, y_idx, x_label, y_label, title=None, annotate_curated=True):
    """Plot overlaid solution clouds with curated highlights."""
    idx_labels = {0: 'Return', 1: 'Vol', 2: 'Yield'}

    for method_name in ['Frontier', 'Solver', 'LLM']:
        md = methods_data[method_name]
        sols = md['solutions']
        if not sols:
            continue
        xs = [s[x_idx] for s in sols]
        ys = [s[y_idx] for s in sols]

        ax.scatter(xs, ys, c=COLORS[method_name], marker=MARKERS[method_name],
                  s=CLOUD_SIZE, alpha=CLOUD_ALPHA, label=f'{method_name} ({len(sols)})')

        # Curated highlights
        for cname, cvals in md['curated'].items():
            ax.scatter([cvals[x_idx]], [cvals[y_idx]], c=COLORS[method_name],
                      marker=MARKERS[method_name], s=CURATED_SIZE, alpha=CURATED_ALPHA,
                      edgecolors='black', linewidth=0.8, zorder=5)
            if annotate_curated:
                ax.annotate(f'{cname[0]}', (cvals[x_idx], cvals[y_idx]),
                          fontsize=6, ha='center', va='bottom', fontweight='bold',
                          color=COLORS[method_name],
                          xytext=(0, 5), textcoords='offset points')

    ax.set_xlabel(f'{idx_labels[x_idx]} (%)', fontsize=9)
    ax.set_ylabel(f'{idx_labels[y_idx]} (%)', fontsize=9)
    if title:
        ax.set_title(title, fontsize=10)
    ax.grid(True, alpha=0.3)


# ─── Plot B1: Pairwise Pareto Clouds ────────────────────────────────

def plot_B1(methods_data):
    fig, axes = plt.subplots(1, 3, figsize=(18, 5.5))

    pairs = [(0, 1, 'Return vs Volatility'), (2, 1, 'Yield vs Volatility'), (2, 0, 'Yield vs Return')]

    for ax, (xi, yi, title) in zip(axes, pairs):
        plot_cloud(ax, methods_data, xi, yi, '', '', title=title)

    # Legend
    handles = [mpatches.Patch(color=COLORS[m], label=f'{m} ({len(methods_data[m]["solutions"])} sol)')
               for m in ['Frontier', 'Solver', 'LLM']]
    fig.legend(handles=handles, loc='upper center', ncol=3, fontsize=10,
              bbox_to_anchor=(0.5, 1.02))

    fig.suptitle('Base Case: Pairwise Pareto Clouds — All Methods Overlaid', fontsize=13, y=1.06)
    fig.tight_layout()
    fig.savefig(os.path.join(PLOT_DIR, 'base_B1_pairwise_clouds.png'), dpi=150, bbox_inches='tight')
    plt.close(fig)
    print('  Saved base_B1_pairwise_clouds.png')


# ─── Plot B2: Annotated Return vs Vol Deep Dive ─────────────────────

def plot_B2(methods_data):
    fig, ax = plt.subplots(1, 1, figsize=(12, 8))

    curated_names = ['Growth', 'Balanced', 'Income', 'Safety']

    # Solution clouds
    for method_name in ['Frontier', 'Solver', 'LLM']:
        md = methods_data[method_name]
        sols = md['solutions']
        xs = [s[0] for s in sols]  # return
        ys = [s[1] for s in sols]  # vol
        ax.scatter(xs, ys, c=COLORS[method_name], marker=MARKERS[method_name],
                  s=CLOUD_SIZE, alpha=CLOUD_ALPHA, label=f'{method_name} ({len(sols)} solutions)')

    # Curated highlights with full annotations
    for cname in curated_names:
        points = {}
        for method_name in ['Frontier', 'Solver', 'LLM']:
            md = methods_data[method_name]
            if cname in md['curated']:
                cv = md['curated'][cname]
                points[method_name] = cv
                ax.scatter([cv[0]], [cv[1]], c=COLORS[method_name],
                          marker=MARKERS[method_name], s=CURATED_SIZE * 1.5,
                          edgecolors='black', linewidth=1.0, zorder=6)
                ax.annotate(f'{cname}\n{cv[0]:.1f}% ret / {cv[1]:.1f}% vol',
                          (cv[0], cv[1]), fontsize=7, ha='left',
                          color=COLORS[method_name], fontweight='bold',
                          xytext=(8, 5), textcoords='offset points',
                          arrowprops=dict(arrowstyle='->', color=COLORS[method_name], lw=0.5))

        # Connect matched strategies across methods with dotted lines
        method_list = list(points.keys())
        for i in range(len(method_list)):
            for j in range(i+1, len(method_list)):
                m1, m2 = method_list[i], method_list[j]
                ax.plot([points[m1][0], points[m2][0]], [points[m1][1], points[m2][1]],
                       'k--', alpha=0.2, linewidth=0.8)

    ax.set_xlabel('Expected Return (%)', fontsize=11)
    ax.set_ylabel('Volatility (%)', fontsize=11)
    ax.set_title('Return vs Volatility: Deep Dive — Frontier fills the tradeoff space,\nSolver matches extremes, LLM overestimates volatility', fontsize=12)
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)

    fig.tight_layout()
    fig.savefig(os.path.join(PLOT_DIR, 'base_B2_return_vol_annotated.png'), dpi=150, bbox_inches='tight')
    plt.close(fig)
    print('  Saved base_B2_return_vol_annotated.png')


# ─── Plot S1: Per-Scenario Pairwise Clouds ──────────────────────────

def plot_S1(methods_scen):
    scenarios = ['base', 'rate_cuts', 'recession', 'inflation']
    scen_labels = {'base': 'Base Case', 'rate_cuts': 'Rate Cuts', 'recession': 'Recession', 'inflation': 'Inflation'}
    pairs = [(0, 1, 'Return vs Vol'), (2, 1, 'Yield vs Vol'), (2, 0, 'Yield vs Return')]

    fig, axes = plt.subplots(4, 3, figsize=(18, 20))

    for row, scen in enumerate(scenarios):
        for col, (xi, yi, pair_label) in enumerate(pairs):
            ax = axes[row][col]
            # Build per-scenario method data
            scen_data = {}
            for method_name in ['Frontier', 'Solver', 'LLM']:
                if scen in methods_scen[method_name]:
                    scen_data[method_name] = methods_scen[method_name][scen]
                else:
                    scen_data[method_name] = {'solutions': [], 'curated': {}}

            plot_cloud(ax, scen_data, xi, yi, '', '',
                      title=f'{scen_labels[scen]}: {pair_label}', annotate_curated=True)

            if row == 0 and col == 0:
                handles = [mpatches.Patch(color=COLORS[m], label=m) for m in ['Frontier', 'Solver', 'LLM']]
                ax.legend(handles=handles, fontsize=7, loc='upper left')

    fig.suptitle('Multi-Scenario: Pairwise Pareto Clouds by Scenario', fontsize=14, y=1.01)
    fig.tight_layout()
    fig.savefig(os.path.join(PLOT_DIR, 'scenario_S1_pairwise_clouds.png'), dpi=150, bbox_inches='tight')
    plt.close(fig)
    print('  Saved scenario_S1_pairwise_clouds.png')


# ─── Plot S2: Per-Scenario Return vs Vol Annotated ───────────────────

def plot_S2(methods_scen):
    scenarios = ['base', 'rate_cuts', 'recession', 'inflation']
    scen_labels = {'base': 'Base Case', 'rate_cuts': 'Rate Cuts', 'recession': 'Recession', 'inflation': 'Inflation'}
    curated_names = ['Growth', 'Balanced', 'Income', 'Safety']

    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    axes_flat = axes.flatten()

    for idx, scen in enumerate(scenarios):
        ax = axes_flat[idx]

        for method_name in ['Frontier', 'Solver', 'LLM']:
            md = methods_scen[method_name].get(scen, {'solutions': [], 'curated': {}})
            sols = md['solutions']
            if sols:
                xs = [s[0] for s in sols]
                ys = [s[1] for s in sols]
                ax.scatter(xs, ys, c=COLORS[method_name], marker=MARKERS[method_name],
                          s=CLOUD_SIZE, alpha=CLOUD_ALPHA)

        # Curated highlights
        for cname in curated_names:
            points = {}
            for method_name in ['Frontier', 'Solver', 'LLM']:
                md = methods_scen[method_name].get(scen, {'solutions': [], 'curated': {}})
                if cname in md['curated']:
                    cv = md['curated'][cname]
                    points[method_name] = cv
                    ax.scatter([cv[0]], [cv[1]], c=COLORS[method_name],
                              marker=MARKERS[method_name], s=CURATED_SIZE,
                              edgecolors='black', linewidth=0.8, zorder=6)
                    ax.annotate(f'{cname[0]}', (cv[0], cv[1]),
                              fontsize=6, ha='center', va='bottom', fontweight='bold',
                              color=COLORS[method_name],
                              xytext=(0, 4), textcoords='offset points')

            # Connect
            ml = list(points.keys())
            for i in range(len(ml)):
                for j in range(i+1, len(ml)):
                    ax.plot([points[ml[i]][0], points[ml[j]][0]],
                           [points[ml[i]][1], points[ml[j]][1]],
                           'k--', alpha=0.15, linewidth=0.6)

        ax.set_xlabel('Return (%)', fontsize=9)
        ax.set_ylabel('Vol (%)', fontsize=9)
        ax.set_title(scen_labels[scen], fontsize=11)
        ax.grid(True, alpha=0.3)

    handles = [mpatches.Patch(color=COLORS[m], label=m) for m in ['Frontier', 'Solver', 'LLM']]
    fig.legend(handles=handles, loc='upper center', ncol=3, fontsize=10, bbox_to_anchor=(0.5, 1.02))
    fig.suptitle('Multi-Scenario: Return vs Volatility — Annotated Deep Dive', fontsize=13, y=1.05)
    fig.tight_layout()
    fig.savefig(os.path.join(PLOT_DIR, 'scenario_S2_return_vol_annotated.png'), dpi=150, bbox_inches='tight')
    plt.close(fig)
    print('  Saved scenario_S2_return_vol_annotated.png')


# ─── Plot S3: Curated Strategy Migration ─────────────────────────────

def plot_S3(methods_scen):
    scenarios = ['base', 'rate_cuts', 'recession', 'inflation']
    scen_labels = {'base': 'Base', 'rate_cuts': 'Rate Cuts', 'recession': 'Recession', 'inflation': 'Inflation'}
    curated_names = ['Growth', 'Safety', 'Balanced', 'Income']

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    axes_flat = axes.flatten()

    for idx, cname in enumerate(curated_names):
        ax = axes_flat[idx]

        for method_name in ['Frontier', 'Solver', 'LLM']:
            rets, vols = [], []
            labels = []
            for scen in scenarios:
                md = methods_scen[method_name].get(scen, {'solutions': [], 'curated': {}})
                if cname in md['curated']:
                    cv = md['curated'][cname]
                    rets.append(cv[0])
                    vols.append(cv[1])
                    labels.append(scen_labels[scen])

            if rets:
                ax.plot(rets, vols, color=COLORS[method_name], marker=MARKERS[method_name],
                       markersize=8, linewidth=1.5, alpha=0.8, label=method_name)
                # Label each point with scenario name
                for r, v, lbl in zip(rets, vols, labels):
                    ax.annotate(lbl, (r, v), fontsize=5.5, color=COLORS[method_name],
                              xytext=(3, 3), textcoords='offset points')

        ax.set_xlabel('Return (%)', fontsize=9)
        ax.set_ylabel('Vol (%)', fontsize=9)
        ax.set_title(f'{cname} Strategy Migration Across Scenarios', fontsize=10)
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=8)

    fig.suptitle('Curated Strategy Migration: How Each Method Adapts Across Scenarios', fontsize=13, y=1.02)
    fig.tight_layout()
    fig.savefig(os.path.join(PLOT_DIR, 'scenario_S3_strategy_migration.png'), dpi=150, bbox_inches='tight')
    plt.close(fig)
    print('  Saved scenario_S3_strategy_migration.png')


# ─── Main ────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print('Loading base case data...')
    base_data = load_base()
    for m, md in base_data.items():
        print(f'  {m}: {len(md["solutions"])} solutions, {len(md["curated"])} curated')

    print('\nLoading scenario data...')
    scen_data = load_scenarios()
    for m in scen_data:
        for s in scen_data[m]:
            print(f'  {m}/{s}: {len(scen_data[m][s]["solutions"])} solutions, {len(scen_data[m][s]["curated"])} curated')

    print('\nGenerating plots...')
    print('Plot B1: Pairwise Pareto Clouds')
    plot_B1(base_data)

    print('Plot B2: Annotated Return vs Vol')
    plot_B2(base_data)

    print('Plot S1: Per-Scenario Pairwise Grid')
    plot_S1(scen_data)

    print('Plot S2: Per-Scenario Return vs Vol Annotated')
    plot_S2(scen_data)

    print('Plot S3: Curated Strategy Migration')
    plot_S3(scen_data)

    print('\nAll plots generated successfully.')

    # Verify files exist
    expected = [
        'base_B1_pairwise_clouds.png',
        'base_B2_return_vol_annotated.png',
        'scenario_S1_pairwise_clouds.png',
        'scenario_S2_return_vol_annotated.png',
        'scenario_S3_strategy_migration.png'
    ]
    for f in expected:
        path = os.path.join(PLOT_DIR, f)
        if os.path.exists(path):
            size = os.path.getsize(path) / 1024
            print(f'  OK: {f} ({size:.0f} KB)')
        else:
            print(f'  MISSING: {f}')
