# Live bento orchestration audit

The final live Gemini run produced a bento with cached paper reading, a separate composition stage, and no retries. The output was also inspected locally in landscape and portrait. This is one public-paper case, not a cross-paper quality benchmark.

## Measured runs

All runs used the saved public Attention Is All You Need paper, the configured gemini-3.8-flash endpoint, an 8,192-token output allowance, and figure inspection. Inputs, outputs, timing and usage were recorded. Image bodies were replaced in traces by sizes and hashes; API keys were never logged.

| Run | Calls | Seconds | Provider total tokens |
| --- | ---: | ---: | ---: |
| Baseline: fresh reading, failed at JSON planning | 12 | 156.08 | 89,597 |
| Size batching and low planner thinking: fresh reading, completed | 9 | 71.84 | 82,351 |
| Separate composition: cached reading, visual review rejected | 6 | 30.32 | 29,883 |
| Candidate-preserving retry: cached reading, completed with two retries | 6 | 26.88 | 36,328 |
| Final: cached reading, completed without retries | 4 | 16.57 | 20,672 |

Across all five development runs: 37 provider calls and 258,831 provider-reported total tokens. These totals are usage measurements, not a dollar invoice. Fresh and cached runs are intentionally separated; the final time is not a fresh-paper latency claim.

## Findings and changes

1. Three-heading batching made ten calls for 38,012 characters, including a 530-character batch. Size-based batching now prefers section boundaries near 10,000 characters, preserves every passage, and merges tiny tails. This paper takes four reading calls. Reading-only reported tokens fell from 63,188 to 34,526 in the observed runs.
2. The synthesis expanded to 3,476 visible tokens, including an ASCII architecture drawing. It is now a compact orientation index, with detailed notes retained separately. The observed revised synthesis was 374 words and 849 visible tokens.
3. Default Gemini Flash thinking exhausted the planning response budget. The failing call reported only 323 visible completion tokens but 8,185 tokens beyond its prompt, consistent with thinking consuming most of the generation allowance. Structured selection/composition uses low thinking; scientific content review uses medium. Other providers retain their defaults.
4. Scientific review redesigned the card arrangement. Composition is now a separate small request that returns geometry only; it cannot rewrite approved claims. The final composition request used 1,240 reported total tokens.
5. Format retries restarted from the original candidate, losing scientific corrections. They now carry the current parsed candidate as untrusted data and identify the invalid field. Diagram labels target 24 characters but can use 40 when needed to preserve operators, eliminating two avoidable retries in the final observed run.
6. A visual reviewer falsely claimed the correct bar chart had reversed or exaggerated bar lengths. The renderer now verifies serialized scene widths and common origins against numerical values and passes those measurements into visual review. Shared-unit values such as BLEU can use zero-based bars.
7. Reviews were repeatedly receiving all reading notes plus source text. Bento content and image review now use the original passages referenced by the candidate, including visual references. This also limits review citations to the supplied supporting passages.

## Verification and limits

- 17 focused reading/bento tests passed; UI checks, Python/JavaScript syntax checks and diff whitespace checks passed.
- Regression coverage includes all-passage batching, small context bounds, reading-cache reuse, current-candidate retries, role/focus preservation, Gemini planner thinking, layout containment and serialized chart geometry.
- Six original raster image assets from four source passages were supplied during reading. Another visualization passage, p00124, was omitted by the six-image limit. PDF-only and SVG-only figures remain outside the current image path.
- The final bento received model visual approval and local visual inspection. Earlier traces demonstrate that model approval can miss scientific nuances and that a visual rejection can itself be wrong; it is not proof of complete scientific fidelity.
- Live testing covered bento generation. Tests verify that a blog request starts at its planner using cached notes. Full blog generation, including its final visual narration review, was not exercised during this audit.
- The original retained source has different English-to-French values in Table 2 and the narrative, which the notes flagged. This audit does not establish whether the discrepancy originates in the paper version or conversion. The final bento uses the consistent English-to-German comparison.
- Changes are in the workspace; no installed-app rebuild, commit or push was performed.

## Retained artifacts

- [trace-20260909-205637.jsonl](../../.scratch/bento-v5-live/trace-20260909-205637.jsonl)
- [trace-20260909-210050.jsonl](../../.scratch/bento-v5-live/trace-20260909-210050.jsonl)
- [trace-20260909-210516.jsonl](../../.scratch/bento-v5-live/trace-20260909-210516.jsonl)
- [trace-20260909-210745.jsonl](../../.scratch/bento-v5-live/trace-20260909-210745.jsonl)
- [trace-20260909-210925.jsonl](../../.scratch/bento-v5-live/trace-20260909-210925.jsonl)
- [Final generation JSON](../../.scratch/bento-v5-live/bento.json)
- [Machine-readable run summary](../../.scratch/bento-v5-live/trace-summary.json)
- [Exact local test runner](../../.scratch/bento-v5-live/runner.py)

Gemini thinking behavior was checked against the [official provider documentation](https://ai.google.dev/gemini-api/docs/generate-content/thinking).
