# Issues and Limitations

## 1. Weighted-Average Volatility Approximation

**Impact: HIGH**

All portfolio volatility figures use weighted-average vol (sum of weight_i * vol_i) rather than the correct formula using the covariance matrix (sqrt of w' * Sigma * w)). This is a fundamental limitation because:

- Weighted-average vol assumes perfect positive correlation between all assets (correlation = 1.0)
- Real correlations between bonds and equities, gold and equities, etc. are typically much lower (often negative)
- This means our vol figures are **overstated**, potentially by 3-8 percentage points for diversified portfolios
- The Safety portfolio (6.45% wtd avg) likely has true vol closer to 4-5% given it mixes treasuries, TIPS, and high yield
- The Balanced portfolio (13.02% wtd avg) with 8 holdings across multiple asset classes likely has true vol closer to 9-11%
- The relative ordering of portfolios by risk is probably correct, but the absolute numbers are conservative
- Some portfolios currently close to the 20% vol ceiling (Aggressive Growth at 19.07, Max Return Push at 19.35) would have substantial headroom with true covariance-based vol, meaning even more aggressive portfolios would be feasible

## 2. Candidate Portfolios Considered

I constructed and evaluated approximately 10-12 candidate portfolios before settling on the final 8. Two were discarded for violating the vol constraint (>20%), and 1-2 were discarded for being clearly dominated by other candidates on all three objectives.

The initial Aggressive Growth attempt (VDE 30%, GLD 25%, VGT 15%, GSG 15%, VOO 15%) had wtd-avg vol of 20.43%, so it was revised by swapping weight from VDE to DBA and GLD.

## 3. Arithmetic Precision

**Impact: LOW-MEDIUM**

All arithmetic was performed by mental calculation with intermediate rounding to 4 decimal places. Potential rounding errors are estimated at +/- 0.05 percentage points on any individual portfolio metric. This is well within the noise of the approximation in item 1.

Specific calculations I'm most uncertain about:
- The Income portfolio return (2.69%) involves subtracting negative-return ETFs (VNQI -0.58%, VGLT -5.00%) which increases error risk in sign handling
- The Growth-Income Blend with 8 terms is the most complex sum and has the highest chance of accumulated rounding error

## 4. Potentially Dominated Solutions

**Impact: MEDIUM**

My honest assessment: the solutions I generated likely include near-optimal representatives for the extreme strategies (max return, min vol, max yield), but the interior of the Pareto frontier -- portfolios blending two or three objectives -- is almost certainly underexplored. A systematic optimizer would find portfolios that:

- Achieve the same return as my Balanced portfolio but with lower vol or higher yield
- Find intermediate points between Balanced and Growth that I didn't consider
- Exploit finer allocation increments (e.g., 7% vs round 10% blocks) for marginal improvements
- Consider ETFs I overlooked -- I relied heavily on a small set of "workhorses" (GLD, HYG, VGSH, DBA, VOO) and may have missed combinations using mid-tier performers like VEA, VPU, or VGK more effectively

## 5. Constraint Tracking Challenges

**Impact: LOW**

The easiest constraints to track manually were:
- Max allocation (just check no single ETF exceeds 30%)
- Holdings count (count the ETFs)
- Sector/Alternative limits (count ETFs by group)

The hardest constraint was the vol ceiling (<=20%) because it requires computing the full weighted sum each time, which is the most arithmetic-intensive step. I caught one violation (original Aggressive Growth) during construction.

## 6. ETF Selection Bias

**Impact: MEDIUM**

I tended to favor ETFs with clearly extreme characteristics (highest return, highest yield, lowest vol) and may have underweighted "middle of the pack" ETFs that could contribute to efficient intermediate portfolios. For example:
- VEA (8.82% return, 2.94% yield) appears in only 1 portfolio despite being a solid all-around performer
- VPU (10.60% return, 2.57% yield, 16.83% vol) appears in only 1 portfolio despite good efficiency
- EWJ (7.78% return, 4.33% yield) is underused given its strong yield-return combination

## 7. Proportional Allocation Granularity

**Impact: LOW**

I used round percentage allocations (5%, 10%, 15%, 20%, 25%, 30%) for simplicity. An optimizer could use 1% increments to find marginally better solutions. The impact is likely small -- perhaps 0.1-0.3 percentage points improvement on any single objective -- but across the full Pareto frontier, finer granularity would produce more solutions filling gaps between my 8 portfolios.

## 8. Missing Systematic Frontier Exploration

**Impact: HIGH**

A true multi-objective optimizer would produce 20-50+ Pareto-optimal solutions spanning the full tradeoff surface. My 8 solutions are hand-picked archetypes that likely miss:
- The exact transition points where it becomes "worth it" to take more risk
- Portfolios that are optimal for specific risk budgets (e.g., "best portfolio at exactly 12% vol")
- Non-obvious combinations that human intuition wouldn't construct

This is the fundamental limitation of the LLM-only approach: I can reason about what good portfolios look like, but I cannot systematically enumerate and compare all feasible combinations.
