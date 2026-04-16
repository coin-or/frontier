# pymoo ETF Portfolio Optimization Results

## Setup
- **Solver**: pymoo NSGA-III (evolutionary multi-objective)
- **Objectives**: Maximize Return, Minimize Volatility, Maximize Dividend Yield
- **Variables**: 25 integer decision variables (ETF allocations summing to 100%)
- **Constraints**: Vol <= 20%, max 2 sector ETFs, max 2 alt ETFs, 4-12 holdings, min 1% each
- **Algorithm**: NSGA-III with 91 reference directions, pop_size=200, 500 generations
- **Solve time**: 5.5s
- **Lines of code**: ~200 (problem + repair + selection logic)

## Pareto Front

| Metric | Min | Max |
|--------|-----|-----|
| Annual Return | 2.11% | 20.38% |
| Volatility | 2.70% | 20.00% |
| Dividend Yield | 0.04% | 6.58% |

**Pareto-optimal solutions found: 41**

## Representative Strategies

### GROWTH (Max Return)
- **Return**: 20.38%
- **Volatility**: 18.56%
- **Dividend Yield**: 0.59%
- **Holdings**: 4

| Ticker | Allocation |
|--------|------------|
| GLD | 74% |
| VDE | 24% |
| GSG | 1% |
| VGT | 1% |

### BALANCED (Return/Vol + Yield)
- **Return**: 9.28%
- **Volatility**: 10.52%
- **Dividend Yield**: 4.36%
- **Holdings**: 4

| Ticker | Allocation |
|--------|------------|
| HYG | 63% |
| GLD | 34% |
| VGSH | 2% |
| EMB | 1% |

### INCOME (Max Dividend Yield)
- **Return**: 3.68%
- **Volatility**: 7.70%
- **Dividend Yield**: 6.58%
- **Holdings**: 4

| Ticker | Allocation |
|--------|------------|
| HYG | 93% |
| VGSH | 3% |
| TIP | 3% |
| EMB | 1% |

### SAFETY (Min Volatility)
- **Return**: 2.29%
- **Volatility**: 2.70%
- **Dividend Yield**: 3.65%
- **Holdings**: 4

| Ticker | Allocation |
|--------|------------|
| VGSH | 97% |
| GLD | 1% |
| GSG | 1% |
| VGT | 1% |

## Commentary

### Setup Effort
- ~200 lines of Python code including the repair operator, problem class, and solution curation
- The main complexity is the **repair operator** (~80 lines) which enforces sum-to-100, cardinality limits, group constraints, and minimum allocation rules after each evolutionary step
- pymoo's API is clean but requires manual constraint handling for integer combinatorial problems

### Solve Time
- **5.5 seconds** for 500 generations with pop_size=200
- This is a stochastic metaheuristic -- runtime scales with population size x generations
- Much slower than exact MILP solvers for comparable problem sizes, but handles non-convex/black-box objectives naturally

### Solution Quality
- NSGA-III produces a diverse Pareto front of 41 non-dominated solutions
- The evolutionary approach explores the trade-off surface well, finding solutions across the full return/vol/yield spectrum
- **Stochastic nature**: results vary across runs (seed-dependent); no guarantee of global optimality
- **Integer handling**: pymoo doesn't natively handle integer constraints as elegantly as MILP solvers -- the repair operator does the heavy lifting
- The repair operator can introduce bias (e.g., favoring high-return ETFs when filling minimum holdings), which may skew the Pareto front
- For this problem size (25 variables, 3 objectives, linear constraints), a MILP/epsilon-constraint approach would likely find provably optimal solutions faster
