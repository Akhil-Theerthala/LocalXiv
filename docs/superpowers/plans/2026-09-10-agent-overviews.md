# Agent overview migration

Implement the requested smolagents migration for visual Overview and Blog. Keep existing persisted generation kinds and figure markers so old outputs and exports remain readable. Generate new explanatory figures as restricted HTML with inline SVG, rendered locally to PNG/PDF. Do not execute model code or load external assets.

The overview must identify the paper's question, what it contributes or establishes, and a supported limitation. Teaching examples support that account; they cannot substitute for it. Blog visuals answer a question in the surrounding narrative. All claims cite retained passages in metadata; invented examples are labeled beside the visual.

Use the saved compatible provider through a smolagents model adapter, bounded tool steps, source-reading tools, candidate submission, rendered inspection and mandatory evidence review. Preserve the last successful generation on failure. Record model usage and review outcomes.

Use diagram-design's semantic-first layout guidance with the already approved LocalXiv palette and sans typography. Keep dependency loading lazy so reading/conversion works without AI packages. Package the pinned Python dependency closure and native renderer in release builds.

Validate with offline provider/tool tests, hostile markup tests, real renderer checks and the three approved Gemini papers. Report live review failures rather than publishing them as successful generations. Do not modify the installed app or push a release.
