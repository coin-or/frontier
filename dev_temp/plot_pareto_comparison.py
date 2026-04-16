"""Plot Pareto fronts from all three approaches on one figure."""

import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

# --- Load data ---

# Frontier (182 solutions)
frontier_data = json.loads('''{"solutions": [{"return": 19.0056, "vol": 17.5606, "yield": 0.7003}, {"return": 18.9716, "vol": 17.3002, "yield": 0.6406}, {"return": 18.8864, "vol": 17.8619, "yield": 0.709}, {"return": 18.84, "vol": 15.8066, "yield": 0.2596}, {"return": 18.702, "vol": 15.591, "yield": 0.3317}, {"return": 18.6622, "vol": 16.5935, "yield": 0.5795}, {"return": 18.5299, "vol": 17.9593, "yield": 1.0322}, {"return": 18.4961, "vol": 15.5592, "yield": 0.357}, {"return": 18.388, "vol": 18.2697, "yield": 1.1151}, {"return": 18.3378, "vol": 17.422, "yield": 0.7847}, {"return": 18.2613, "vol": 18.3096, "yield": 1.1283}, {"return": 18.2051, "vol": 15.8158, "yield": 0.5353}, {"return": 18.1893, "vol": 18.4628, "yield": 1.2239}, {"return": 18.1587, "vol": 17.1526, "yield": 0.9051}, {"return": 17.979, "vol": 16.8403, "yield": 0.9944}, {"return": 17.9296, "vol": 15.7297, "yield": 0.4171}, {"return": 17.915, "vol": 15.4174, "yield": 0.617}, {"return": 17.907, "vol": 16.8197, "yield": 0.9233}, {"return": 17.8443, "vol": 15.2609, "yield": 0.4699}, {"return": 17.6773, "vol": 17.7178, "yield": 1.2052}, {"return": 17.6563, "vol": 16.0726, "yield": 0.861}, {"return": 17.5505, "vol": 15.1154, "yield": 0.7506}, {"return": 17.4085, "vol": 16.4418, "yield": 1.1886}, {"return": 17.4037, "vol": 16.2897, "yield": 1.1037}, {"return": 17.287, "vol": 17.0707, "yield": 1.193}, {"return": 17.232, "vol": 16.9607, "yield": 1.266}, {"return": 17.147, "vol": 15.477, "yield": 0.8281}, {"return": 17.0425, "vol": 16.2319, "yield": 1.2406}, {"return": 16.9378, "vol": 18.7586, "yield": 1.725}, {"return": 16.7916, "vol": 14.9367, "yield": 0.9815}, {"return": 16.6922, "vol": 16.6063, "yield": 1.3097}, {"return": 16.4899, "vol": 16.4035, "yield": 1.6524}, {"return": 16.366, "vol": 14.7459, "yield": 1.1525}, {"return": 16.2745, "vol": 17.455, "yield": 1.7885}, {"return": 16.1367, "vol": 14.5625, "yield": 1.0442}, {"return": 15.8056, "vol": 14.381, "yield": 1.3148}, {"return": 15.7084, "vol": 14.9569, "yield": 1.5034}, {"return": 15.68, "vol": 14.87, "yield": 1.53}, {"return": 15.5184, "vol": 14.8102, "yield": 1.4496}, {"return": 15.4795, "vol": 14.6762, "yield": 1.3354}, {"return": 15.452, "vol": 14.8765, "yield": 1.6219}, {"return": 15.3426, "vol": 14.0226, "yield": 1.4298}, {"return": 15.1387, "vol": 14.4722, "yield": 1.4487}, {"return": 15.1075, "vol": 12.8136, "yield": 1.0748}, {"return": 15.033, "vol": 14.0131, "yield": 1.6033}, {"return": 14.8837, "vol": 17.4796, "yield": 2.3172}, {"return": 14.847, "vol": 13.0227, "yield": 1.2562}, {"return": 14.8353, "vol": 15.6797, "yield": 2.1274}, {"return": 14.7092, "vol": 14.1466, "yield": 1.7581}, {"return": 14.598, "vol": 14.1883, "yield": 1.9016}, {"return": 14.5372, "vol": 13.1938, "yield": 1.3731}, {"return": 14.4869, "vol": 14.3943, "yield": 1.9584}, {"return": 14.387, "vol": 15.6898, "yield": 2.2996}, {"return": 14.3137, "vol": 15.93, "yield": 2.4951}, {"return": 14.3002, "vol": 14.4986, "yield": 2.0094}, {"return": 14.1213, "vol": 13.7277, "yield": 1.9307}, {"return": 13.9845, "vol": 13.2824, "yield": 1.6988}, {"return": 13.9025, "vol": 12.0774, "yield": 1.2964}, {"return": 13.7418, "vol": 13.2485, "yield": 2.1426}, {"return": 13.6612, "vol": 13.4155, "yield": 2.1531}, {"return": 13.6371, "vol": 12.1889, "yield": 1.5625}, {"return": 13.5492, "vol": 15.1943, "yield": 2.5746}, {"return": 13.437, "vol": 11.6315, "yield": 1.5112}, {"return": 13.3248, "vol": 14.8042, "yield": 2.2542}, {"return": 13.1928, "vol": 13.5363, "yield": 2.4551}, {"return": 13.1641, "vol": 12.1388, "yield": 1.7754}, {"return": 12.9563, "vol": 12.4304, "yield": 1.8748}, {"return": 12.9078, "vol": 12.3428, "yield": 1.8399}, {"return": 12.7439, "vol": 11.3608, "yield": 1.8101}, {"return": 12.6742, "vol": 13.3067, "yield": 2.3573}, {"return": 12.5965, "vol": 11.6105, "yield": 1.8562}, {"return": 12.4806, "vol": 12.0693, "yield": 2.0767}, {"return": 12.414, "vol": 13.8256, "yield": 2.6487}, {"return": 12.2921, "vol": 12.4647, "yield": 2.5262}, {"return": 12.2493, "vol": 13.9103, "yield": 3.0393}, {"return": 12.0604, "vol": 13.9224, "yield": 3.0716}, {"return": 12.0597, "vol": 12.2719, "yield": 2.198}, {"return": 11.9134, "vol": 11.7554, "yield": 2.403}, {"return": 11.8366, "vol": 12.3771, "yield": 2.8159}, {"return": 11.7925, "vol": 13.9587, "yield": 3.1637}, {"return": 11.6855, "vol": 11.7401, "yield": 2.5932}, {"return": 11.6356, "vol": 11.9933, "yield": 2.8393}, {"return": 11.4668, "vol": 10.3407, "yield": 2.1046}, {"return": 11.2898, "vol": 11.2835, "yield": 2.374}, {"return": 11.1836, "vol": 11.4188, "yield": 2.614}, {"return": 11.1682, "vol": 12.7836, "yield": 3.3446}, {"return": 11.0321, "vol": 11.1933, "yield": 2.6989}, {"return": 10.8732, "vol": 12.6562, "yield": 3.1816}, {"return": 10.7481, "vol": 9.5962, "yield": 2.0403}, {"return": 10.5825, "vol": 9.9501, "yield": 2.2442}, {"return": 10.4649, "vol": 10.8526, "yield": 2.7766}, {"return": 10.4053, "vol": 11.382, "yield": 3.3091}, {"return": 10.3004, "vol": 12.6977, "yield": 3.4296}, {"return": 10.2273, "vol": 10.778, "yield": 2.8526}, {"return": 10.0727, "vol": 10.2171, "yield": 2.7236}, {"return": 10.0101, "vol": 9.5278, "yield": 2.429}, {"return": 9.8857, "vol": 11.0682, "yield": 3.516}, {"return": 9.689, "vol": 10.9735, "yield": 3.4115}, {"return": 9.5781, "vol": 10.7578, "yield": 3.4978}, {"return": 9.4296, "vol": 9.6464, "yield": 2.7091}, {"return": 9.3918, "vol": 10.0426, "yield": 2.8334}, {"return": 9.3189, "vol": 13.6781, "yield": 4.4892}, {"return": 9.2684, "vol": 10.1163, "yield": 2.8936}, {"return": 9.2056, "vol": 9.8937, "yield": 2.9227}, {"return": 9.1163, "vol": 8.7903, "yield": 2.7478}, {"return": 9.0408, "vol": 12.9101, "yield": 3.8159}, {"return": 8.9863, "vol": 12.8737, "yield": 3.8128}, {"return": 8.8091, "vol": 10.6787, "yield": 3.7196}, {"return": 8.7309, "vol": 10.4605, "yield": 3.7764}, {"return": 8.687, "vol": 10.2503, "yield": 3.6912}, {"return": 8.5998, "vol": 7.7347, "yield": 2.5121}, {"return": 8.4738, "vol": 9.3652, "yield": 3.0531}, {"return": 8.3345, "vol": 8.8823, "yield": 2.9985}, {"return": 8.26, "vol": 8.3044, "yield": 2.6277}, {"return": 8.2267, "vol": 8.871, "yield": 3.0258}, {"return": 8.1085, "vol": 11.1785, "yield": 4.165}, {"return": 7.9283, "vol": 8.4855, "yield": 3.2119}, {"return": 7.8518, "vol": 11.853, "yield": 4.6138}, {"return": 7.5081, "vol": 11.5606, "yield": 4.2946}, {"return": 7.4397, "vol": 10.6556, "yield": 4.3423}, {"return": 7.329, "vol": 11.4746, "yield": 4.4636}, {"return": 7.114, "vol": 9.139, "yield": 3.8902}, {"return": 6.8486, "vol": 8.6304, "yield": 3.58}, {"return": 6.7994, "vol": 10.5831, "yield": 4.5424}, {"return": 6.7186, "vol": 7.868, "yield": 3.6256}, {"return": 6.6024, "vol": 9.2944, "yield": 4.2115}, {"return": 6.493, "vol": 6.9954, "yield": 3.276}, {"return": 6.4353, "vol": 7.1058, "yield": 3.2806}, {"return": 6.3719, "vol": 8.1371, "yield": 3.8372}, {"return": 6.2359, "vol": 10.1423, "yield": 5.0075}, {"return": 6.1816, "vol": 8.1815, "yield": 3.9673}, {"return": 6.1387, "vol": 7.899, "yield": 4.0203}, {"return": 6.104, "vol": 7.1481, "yield": 3.4613}, {"return": 6.0312, "vol": 7.2375, "yield": 3.5968}, {"return": 5.837, "vol": 9.584, "yield": 4.6107}, {"return": 5.7576, "vol": 7.3221, "yield": 4.0997}, {"return": 5.6811, "vol": 9.7902, "yield": 5.035}, {"return": 5.5938, "vol": 6.8301, "yield": 3.7165}, {"return": 5.5806, "vol": 9.3925, "yield": 4.9449}, {"return": 5.4878, "vol": 9.178, "yield": 4.2909}, {"return": 5.3165, "vol": 9.3045, "yield": 4.8042}, {"return": 5.3084, "vol": 9.1473, "yield": 5.1787}, {"return": 5.1533, "vol": 7.8395, "yield": 4.2616}, {"return": 5.1124, "vol": 8.8924, "yield": 5.2731}, {"return": 5.0777, "vol": 6.6005, "yield": 3.6674}, {"return": 4.9741, "vol": 8.9269, "yield": 5.3308}, {"return": 4.9381, "vol": 6.4312, "yield": 4.0803}, {"return": 4.8878, "vol": 8.2421, "yield": 4.7707}, {"return": 4.6425, "vol": 8.6927, "yield": 5.3522}, {"return": 4.4939, "vol": 8.5564, "yield": 5.3841}, {"return": 4.3265, "vol": 8.4283, "yield": 5.4158}, {"return": 4.3224, "vol": 8.585, "yield": 5.463}, {"return": 4.2678, "vol": 8.4637, "yield": 5.5013}, {"return": 4.2042, "vol": 7.7147, "yield": 4.8782}, {"return": 4.1286, "vol": 6.7434, "yield": 4.5513}, {"return": 4.0766, "vol": 7.5157, "yield": 5.0387}, {"return": 4.0411, "vol": 6.0262, "yield": 4.326}, {"return": 3.9972, "vol": 5.4308, "yield": 3.8906}, {"return": 3.9905, "vol": 7.3829, "yield": 5.0651}, {"return": 3.95, "vol": 6.3653, "yield": 4.6425}, {"return": 3.9438, "vol": 6.2054, "yield": 4.5566}, {"return": 3.9194, "vol": 5.5786, "yield": 4.0712}, {"return": 3.8091, "vol": 6.9291, "yield": 4.9662}, {"return": 3.7575, "vol": 5.3386, "yield": 4.0349}, {"return": 3.6287, "vol": 6.244, "yield": 4.7198}, {"return": 3.6014, "vol": 6.1254, "yield": 4.6702}, {"return": 3.5318, "vol": 5.1779, "yield": 4.1529}, {"return": 3.4352, "vol": 4.9621, "yield": 4.1289}, {"return": 3.3964, "vol": 5.7638, "yield": 4.6987}, {"return": 3.3802, "vol": 5.6808, "yield": 4.7108}, {"return": 3.1721, "vol": 4.6866, "yield": 4.2168}, {"return": 3.151, "vol": 5.0852, "yield": 4.4136}, {"return": 3.1111, "vol": 5.0432, "yield": 4.4126}, {"return": 2.9746, "vol": 4.4588, "yield": 4.1351}, {"return": 2.9257, "vol": 4.1248, "yield": 4.0562}, {"return": 2.8091, "vol": 4.3389, "yield": 4.1906}, {"return": 2.7076, "vol": 3.7449, "yield": 3.7994}, {"return": 2.582, "vol": 3.6865, "yield": 3.8445}, {"return": 2.5146, "vol": 3.5275, "yield": 3.8812}, {"return": 2.4141, "vol": 3.356, "yield": 3.927}, {"return": 2.3778, "vol": 3.1455, "yield": 3.9069}, {"return": 2.3102, "vol": 3.055, "yield": 3.914}]}''')

# pymoo (45 solutions)
pymoo_data = json.loads('''{"solutions": [{"return": 8.5, "vol": 12.12, "yield": 3.38}, {"return": 6.29, "vol": 10.0, "yield": 3.42}, {"return": 5.77, "vol": 9.52, "yield": 3.51}, {"return": 14.17, "vol": 16.87, "yield": 1.78}, {"return": 5.7, "vol": 10.94, "yield": 4.01}, {"return": 3.75, "vol": 9.82, "yield": 4.41}, {"return": 12.69, "vol": 15.48, "yield": 2.38}, {"return": 7.71, "vol": 11.91, "yield": 3.7}, {"return": 11.29, "vol": 16.76, "yield": 3.09}, {"return": 11.5, "vol": 14.96, "yield": 2.85}, {"return": 8.65, "vol": 12.74, "yield": 3.74}, {"return": 8.9, "vol": 15.29, "yield": 3.8}, {"return": 12.26, "vol": 17.37, "yield": 2.99}, {"return": 7.25, "vol": 10.44, "yield": 3.18}, {"return": 12.69, "vol": 16.66, "yield": 2.75}, {"return": 10.33, "vol": 12.42, "yield": 2.65}, {"return": 10.44, "vol": 13.54, "yield": 2.96}, {"return": 11.15, "vol": 13.18, "yield": 2.31}, {"return": 5.11, "vol": 9.87, "yield": 4.04}, {"return": 9.34, "vol": 14.29, "yield": 3.66}, {"return": 4.12, "vol": 10.8, "yield": 4.53}, {"return": 5.66, "vol": 11.97, "yield": 4.22}, {"return": 6.02, "vol": 13.19, "yield": 4.21}, {"return": 6.79, "vol": 10.94, "yield": 3.76}, {"return": 11.55, "vol": 14.07, "yield": 2.4}, {"return": 8.27, "vol": 11.25, "yield": 3.0}, {"return": 3.93, "vol": 10.02, "yield": 4.26}, {"return": 6.7, "vol": 11.83, "yield": 4.03}, {"return": 10.46, "vol": 14.62, "yield": 3.27}, {"return": 12.3, "vol": 14.09, "yield": 2.2}, {"return": 4.97, "vol": 11.5, "yield": 4.43}, {"return": 9.04, "vol": 11.51, "yield": 2.75}, {"return": 4.93, "vol": 9.23, "yield": 3.7}, {"return": 4.14, "vol": 9.39, "yield": 4.0}, {"return": 10.35, "vol": 16.05, "yield": 3.52}, {"return": 13.81, "vol": 17.43, "yield": 2.06}, {"return": 3.93, "vol": 9.44, "yield": 4.16}, {"return": 9.4, "vol": 13.3, "yield": 3.33}, {"return": 7.56, "vol": 10.99, "yield": 3.4}, {"return": 7.59, "vol": 13.06, "yield": 3.97}, {"return": 6.77, "vol": 14.33, "yield": 4.2}, {"return": 4.79, "vol": 10.9, "yield": 4.27}, {"return": 9.28, "vol": 12.25, "yield": 2.98}, {"return": 8.26, "vol": 14.37, "yield": 3.92}, {"return": 5.4, "vol": 9.88, "yield": 3.7}]}''')

# LLM-only (4 solutions)
llm_data = json.loads('''{"solutions": [{"return": 18.58, "vol": 19.98, "yield": 0.90}, {"return": 9.82, "vol": 12.90, "yield": 2.72}, {"return": 2.81, "vol": 10.78, "yield": 5.06}, {"return": 1.56, "vol": 4.52, "yield": 4.04}]}''')
llm_labels = ["Growth", "Balanced", "Income", "Safety"]

# Frontier curated
frontier_curated = [
    {"return": 19.01, "vol": 17.56, "yield": 0.70, "name": "Growth"},
    {"return": 9.89, "vol": 11.07, "yield": 3.52, "name": "Balanced"},
    {"return": 4.27, "vol": 8.46, "yield": 5.50, "name": "Income"},
    {"return": 2.31, "vol": 3.06, "yield": 3.91, "name": "Safety"},
]

# pymoo curated
pymoo_curated = [
    {"return": 14.17, "vol": 16.87, "yield": 1.78, "name": "Growth"},
    {"return": 9.40, "vol": 13.30, "yield": 3.33, "name": "Balanced"},
    {"return": 4.12, "vol": 10.80, "yield": 4.53, "name": "Income"},
    {"return": 4.93, "vol": 9.23, "yield": 3.70, "name": "Safety"},
]

# --- Plot ---
fig, axes = plt.subplots(1, 3, figsize=(20, 6))
fig.suptitle("Pareto Front Comparison: 30-ETF Portfolio (3 Objectives)", fontsize=14, fontweight="bold")

# Color scheme
c_frontier = "#2563EB"  # blue
c_pymoo = "#16A34A"     # green
c_llm = "#DC2626"       # red

pairs = [
    ("return", "vol", "Expected Return (%)", "Volatility (%)", "Return vs Volatility"),
    ("return", "yield", "Expected Return (%)", "Dividend Yield (%)", "Return vs Dividend Yield"),
    ("vol", "yield", "Volatility (%)", "Dividend Yield (%)", "Volatility vs Dividend Yield"),
]

for idx, (xkey, ykey, xlabel, ylabel, title) in enumerate(pairs):
    ax = axes[idx]

    # Frontier Pareto cloud
    fx = [s[xkey] for s in frontier_data["solutions"]]
    fy = [s[ykey] for s in frontier_data["solutions"]]
    ax.scatter(fx, fy, c=c_frontier, alpha=0.25, s=12, zorder=2)

    # pymoo Pareto cloud
    px = [s[xkey] for s in pymoo_data["solutions"]]
    py = [s[ykey] for s in pymoo_data["solutions"]]
    ax.scatter(px, py, c=c_pymoo, alpha=0.35, s=20, marker="D", zorder=3)

    # LLM points
    lx = [s[xkey] for s in llm_data["solutions"]]
    ly = [s[ykey] for s in llm_data["solutions"]]
    ax.scatter(lx, ly, c=c_llm, s=120, marker="*", zorder=5, edgecolors="black", linewidths=0.5)
    for i, label in enumerate(llm_labels):
        ax.annotate(label, (lx[i], ly[i]), textcoords="offset points",
                    xytext=(8, -4), fontsize=7, color=c_llm, fontweight="bold")

    # Frontier curated markers
    for cs in frontier_curated:
        ax.scatter(cs[xkey], cs[ykey], c=c_frontier, s=80, marker="o",
                   zorder=4, edgecolors="black", linewidths=1)

    # pymoo curated markers
    for cs in pymoo_curated:
        ax.scatter(cs[xkey], cs[ykey], c=c_pymoo, s=80, marker="D",
                   zorder=4, edgecolors="black", linewidths=1)

    ax.set_xlabel(xlabel, fontsize=10)
    ax.set_ylabel(ylabel, fontsize=10)
    ax.set_title(title, fontsize=11)
    ax.grid(True, alpha=0.3)

# Legend
from matplotlib.lines import Line2D
legend_elements = [
    Line2D([0], [0], marker='o', color='w', markerfacecolor=c_frontier, markersize=6,
           alpha=0.5, label=f'Frontier (182 solutions)'),
    Line2D([0], [0], marker='o', color='w', markerfacecolor=c_frontier, markersize=9,
           markeredgecolor='black', markeredgewidth=1, label='Frontier curated'),
    Line2D([0], [0], marker='D', color='w', markerfacecolor=c_pymoo, markersize=6,
           alpha=0.5, label=f'pymoo (45 solutions)'),
    Line2D([0], [0], marker='D', color='w', markerfacecolor=c_pymoo, markersize=9,
           markeredgecolor='black', markeredgewidth=1, label='pymoo curated'),
    Line2D([0], [0], marker='*', color='w', markerfacecolor=c_llm, markersize=14,
           markeredgecolor='black', markeredgewidth=0.5, label='LLM-only (4 points)'),
]
fig.legend(handles=legend_elements, loc='lower center', ncol=5, fontsize=9,
           bbox_to_anchor=(0.5, -0.02))

plt.tight_layout(rect=[0, 0.05, 1, 0.95])
plt.savefig("/Users/cameronafzal/Documents/frontier/dev_temp/pareto_comparison.png", dpi=150, bbox_inches="tight")
print("Saved: dev_temp/pareto_comparison.png")
