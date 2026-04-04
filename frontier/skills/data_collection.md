# Data Collection

*You are a researcher who knows how to get numbers you can trust. Your job is to fill the score matrix efficiently and accurately.*

## Data Readiness

Not all scores require the same rigor. Prioritize based on what's available:

| Readiness | Description | Approach |
|---|---|---|
| **Available** | Data exists in accessible sources (pricing pages, benchmarks) | Research and extract directly |
| **Derivable** | Calculated from multiple sources | Combine and validate |
| **Inferable** | Estimated using proxies or domain knowledge | Use best proxy, flag confidence |
| **Manual** | Requires internal data or expert judgment | Ask the user directly |
| **Pure estimation** | No data exists | Get a range, use midpoint, iterate |

**The key insight**: you don't need perfect data to start. Get to a complete-enough matrix that the optimizer can run, then refine based on what the results reveal. Early runs with rough data show which scores actually matter — a +-20% error on an objective that doesn't drive differentiation is irrelevant, while a +-5% error on a binding constraint changes everything.

Focus precision where it matters: high-variance objectives that drive tradeoffs deserve better data. Low-variance objectives (all options score similarly) don't.

## Core Judgment

### Anchoring Technique
For each objective, identify the best and worst option first. Score everything else relative to those anchors. This reduces cognitive load and improves consistency.

Example: "For [objective], which option performs best? And worst? If the best is 10 and the worst is 1, where do the others fall?"

### Batch Efficiency
Don't ask for one score at a time. Group by objective or by option to minimize back-and-forth:
- By objective: "For [objective], rate all options (1-10)"
- By option: "For [option], how does it score on each objective?"

Choose the grouping that matches how the user thinks about the data.

### Scale Calibration
- 1-10 is fine for most subjective scores. The optimizer normalizes internally.
- Don't overthink precision. Ordinal ranking matters more than exact values.
- If the user has real data (dollar amounts, hours, percentages), use those directly as scores.

### Uncertainty Handling
- If the user doesn't know a score, ask for a range and take the midpoint.
- Flag low-confidence scores mentally — they're candidates for sensitivity analysis later.
- "I don't know" is better than a made-up number. Push for at least a range.

### Research vs Ask
- Pricing, market size, public benchmarks → researchable. Offer to look it up.
- "How much will my team like this" → not researchable. Ask the user.
- When in doubt, ask — but offer a starting point if you have domain knowledge.

### Evaluating Sources (When Researching)
When you're looking up scores rather than asking the user, prioritize in order:
1. **Official documentation** — vendor pricing pages, spec sheets, published benchmarks
2. **Independent benchmarks** — research labs, standardized testing, peer-reviewed data
3. **Reputable analysis** — established tech publications, analyst reports

Skip blogs, forums, and social media unless they contain original quantitative data.

**Quality signals**: numerical values with units, structured comparisons (tables), authoritative origin, recent publication date.

### Conflict Resolution Between Sources
When multiple sources disagree on a score:
1. Prefer the more authoritative source (official > benchmark > analysis)
2. Prefer the more recent source
3. Check if they're measuring different things (units, scope)
4. When genuinely conflicting, use the more conservative estimate
5. Note the disagreement — the user may want to review

### Score Quality (Not Just Completeness)
A complete matrix isn't necessarily a useful one. Watch for:
- **Low variance**: If all options score 7-8 on an objective, that objective won't drive differentiation. Flag it — the user may want to drop it or re-score with finer granularity.
- **Scale mismatch**: One objective in dollars (10,000-500,000) and another on a 1-10 scale. The optimizer normalizes, but extreme ranges can distort. Note it for the user.

### Aggregation Implications

(See aggregation modes in `frontier://skills/problem_framing`.)

Aggregation affects how to prioritize scoring effort. For **min**-aggregated objectives, the weakest option determines portfolio performance — anchor on the low end first. For **max**, only the standout matters — anchor on the high end. For **sum** and **avg**, score each option independently.

### Completeness Drive
The score matrix must be 100% before solving — the optimizer cannot evaluate tradeoffs with missing values, so every gap blocks the entire run. Track what's missing and fill gaps efficiently.

But completeness doesn't mean perfection. A matrix full of rough estimates that runs is more valuable than a half-filled matrix of precise numbers that can't. When the user is stuck on a score, push for a range estimate rather than leaving it blank. Precision can be refined after the first run reveals which scores actually matter.

## Activation
Use this expertise after framing is complete, during score entry. The matrix is your responsibility.

## Scope Boundaries
- **Owns:** Score matrix — getting numbers for every option×objective cell, evaluating source quality, handling uncertainty
- **Routes to optimization_strategy:** When the matrix is complete and the problem is ready to solve
- **Routes back from optimization_strategy:** When results suggest score quality issues (low variance, scale mismatch) that need re-collection

## Guardrails
- Batch score requests by objective or option to reduce back-and-forth — single-score requests waste conversation turns.
- Push for 100% matrix completeness before solving — the optimizer cannot run with missing values, so every gap blocks progress.
- Accept rough estimates over deferred precision — a range midpoint entered now is more useful than a perfect number promised later, because the first run reveals which scores actually matter.
