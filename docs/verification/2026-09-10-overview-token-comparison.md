# Historical Overview token comparison

These are observed provider-reported token totals, not dollar costs or a controlled format benchmark. No new model calls were made for this comparison.

Both groups used Gemini 3.8 Flash and reused saved paper reading. The old group is Excalidraw bento-v7; the new group is the first successful ToolCallingAgent HTML/SVG v2 run. Both groups had visual review, but generated different designs with different review/revision behavior. New outputs passed automated review but were not accepted by the user as final designs.

| Paper | Old total tokens | New total tokens | Ratio | Old calls | New calls |
|---|---:|---:|---:|---:|---:|
| PRO | 24,654 | 377,968 | 15.33x | 4 | 14 |
| Attention Is All You Need | 23,035 | 223,131 | 9.69x | 4 | 12 |
| Black-box uncertainty evaluation | 31,245 | 520,130 | 16.65x | 5 | 14 |

Combined: 78,934 old versus 1,121,229 new, 14.20x. Input tokens account for 94.1% of new total tokens. Totals use the provider's `total_tokens`, which sometimes exceeds prompt plus visible completion tokens; the logs do not expose a complete billing/cache breakdown.

## Sources

- PRO and black-box old runs: read-only library `generations` rows, kind `bento`, prompt revision `bento-v7`, reading.reused=true.
- Attention old run: `.scratch/bento-fiziko-live/bento.json`, bento-v7, reading.reused=true. This is the later retained cached run; the library row is an earlier bento-v3 run and is not used here.
- New group: `.scratch/toolcalling-six-cases.json`, Overview rows. Detailed log `.scratch/tool-agent-live.log`.

## Failure cost and interpretation

Two subsequent layered Attention attempts consumed 505,255 and 618,358 tokens, respectively, and both failed approval. These 1,123,613 tokens are additional development attempts and are excluded from the successful-run table. A tokens-per-accepted-output benchmark must include failed attempts in its numerator.

The old workflow asked the model for compact plans and expanded them into Excalidraw elements locally. The new workflow asks for full HTML/SVG, carries a growing history of previous candidates and tool observations, and uses more author/review turns. A PRO author request grew from 8,903 prompt tokens initially to 44,560 on the final author call. These mechanisms explain why repeated input dominates; the logs do not isolate the effect of each mechanism. This is not evidence that HTML/SVG is inherently less token-efficient.

## A defensible future comparison

Use the same paper, model, reading cache, content requirements, and acceptance criteria. Repeat each condition. Report input/output/provider total tokens, failed attempts, acceptance rate, latency, and human-rated factual correctness, coverage, and readability. Treat architecture, methodology, and survey/evaluation separately. The useful measure is total tokens spent per human-accepted explanation, not merely tokens emitted per file.

The evidence currently supports a flexibility/reliability tradeoff discussion, not a token-saving claim or a demonstrated learning benefit. Potential optimizations include bounding history to the current candidate and review, reading layout guidance once, and repairing only affected figures; they have not been implemented or benchmarked here.
