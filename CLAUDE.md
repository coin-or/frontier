# Project Instructions

## Key Locations

| Location | Purpose |
|----------|---------|
| `~/Documents/Obsidian_Vault/projects/frontier/` | Product requirements, overview, and roadmap (written by product lead) — informs development |
| `~/Documents/Obsidian_Vault/projects/frontier/roadmap.md` | Product roadmap (written by product lead) — informs development |
| `.claude/plans/` | Active engineering designs and development plans |
| `.claude/plans/archived/` | Completed or irrelevant plans |
| [`README.md`](README.md) | User-facing setup and usage guide — **must be kept up to date** |
| [`architecture.md`](architecture.md) | Technical architecture — **must be kept up to date** |
| [`best-practices.md`](best-practices.md) | Skill, prompt, and MCP design guidelines (Anthropic-sourced) |
| [`frontier/skills/`](frontier/skills/) | Agent skill files (MCP resources + Claude plugin skills) — see best-practices.md for design principles |

## Plans & Designs
- Store new plans, designs, and updates to existing ones in `.claude/plans/`.
- Keep plans active until the user confirms completion post-user-testing, then archive to `.claude/plans/archived/`.

## Documentation Requirements
- When implementing a feature or change, update `README.md` (user guide) and `architecture.md` (technical architecture) as needed.
- Consult `~/Documents/Obsidian_Vault/projects/frontier/` for product context and requirements.

## Applying Best Practices (`best-practices.md`)

Consult `best-practices.md` throughout the development lifecycle:

- **Designing** new skills or MCP tools: follow §1 (Skill File Design) for structure, agent usability, and progressive disclosure; §3 (MCP Tool Description Design) for the responsibility split between tools and skills; §4 (Context Engineering) for how the three layers fit together.
- **Developing** prompts, tool descriptions, or skill content: follow §2 (Prompt Best Practices) — use principles and heuristics over keyword mapping, positive framing with reasoning, general instructions over prescriptive steps, and generic placeholders over domain-specific anchoring.
- **Reviewing** skills or prompt changes: check §1 agent usability criteria (discovery, navigation, adaptation, self-sufficiency, negative test) and conciseness guidelines. Verify cross-references and MECE boundaries.
- **Testing** new features: use §1 safety patterns (confirmation gates, validation loops) to ensure destructive actions are gated and verifiable outputs are validated.
