# Overview rebuild — live observations

Compiled from `.scratch/overview-rebuild/live/runs/` on 2026-09-13. The pilot runs the production Overview path against retained papers in an isolated library; it never touches the user library. Offline contract and recovery verification is in `docs/verification/2026-09-13-overview-rebuild-p2.md`; this file is the live companion. Regenerate with `.scratch/overview-rebuild/live/compile_observations.py`.

Models: gemini `gemini-3.8-flash`, deepseek `deepseek-flash`, and OpenRouter `openai/gpt-5.6-luna`, `openai/gpt-5.6-terra`, `openai/gpt-5.6-sol`. Reasoning: default (on) for every run. `overview_vision` off.

**Turn** = one model request attempt in the persisted run record (planning requests + drawing creation/repair attempts, including transport retries). **Tokens** are provider-reported counts summed from the run record; cache hits are included in prompt tokens and shown separately. Dollar cost is not estimated here because provider pricing and cache discounts are not recorded in the run.

## Summary matrix

| Provider | Paper | Status | Turns (plan/draw) | Tokens | Elapsed | Panels c/r/s | Reduced |
| --- | --- | --- | --- | --- | --- | --- | --- |
| gemini-3.8-flash | architecture | ok | 12 (4/8) | in 74,945 / out 19,620 / total 94,565 | 54.4 s | 2/2/1 | no |
| gemini-3.8-flash | method (PRO) | ok | 11 (4/7) | in 63,928 / out 13,626 / total 77,554 | 39.0 s | 1/2/1 | no |
| gemini-3.8-flash | survey / comparison (UQ) | ok | 12 (5/7) | in 125,685 / out 19,742 / total 145,427 | 57.7 s | 1/2/1 | yes |
| deepseek-flash | architecture | ok | 15 (4/11) | in 96,861 / out 75,943 / total 172,804 / cached 24,832 | 256.8 s | 3/2/2 | no |
| deepseek-flash | method (PRO) | ok | 17 (4/13) | in 98,772 / out 64,740 / total 163,512 / cached 33,536 | 239.3 s | 1/3/3 | no |
| deepseek-flash | survey / comparison (UQ) | ok | 13 (5/8) | in 156,446 / out 97,877 / total 254,323 / cached 25,984 | 383.4 s | 0/2/2 | yes |
| openai/gpt-5.6-luna | architecture | ok | 12 (5/7) | in 79,054 / out 31,789 / total 110,843 | 173.2 s | 1/2/1 | yes |
| openai/gpt-5.6-luna | method (PRO) | ok | 11 (5/6) | in 64,084 / out 25,104 / total 89,188 | 160.9 s | 2/2/0 | yes |
| openai/gpt-5.6-luna | survey / comparison (UQ) | ok | 12 (5/7) | in 77,069 / out 29,403 / total 106,472 | 146.3 s | 1/2/1 | yes |
| openai/gpt-5.6-terra | architecture | ok | 10 (5/5) | in 66,358 / out 21,103 / total 87,461 | 129.3 s | 3/1/0 | yes |
| openai/gpt-5.6-terra | method (PRO) | ok | 11 (5/6) | in 63,276 / out 24,845 / total 88,121 / cached 2,183 | 135.1 s | 2/1/1 | yes |
| openai/gpt-5.6-terra | survey / comparison (UQ) | ok | 13 (5/8) | in 88,197 / out 28,334 / total 116,531 | 143.0 s | 0/2/2 | yes |
| openai/gpt-5.6-sol | architecture | stopped | — | — | — | — | — |
| openai/gpt-5.6-sol | method (PRO) | stopped | — | — | — | — | — |
| openai/gpt-5.6-sol | survey / comparison (UQ) | ok | 11 (5/6) | in 126,531 / out 39,319 / total 165,850 | 377.0 s | 2/1/1 | yes |

c/r/s = created / repaired / simplified panels.

## Final images

### gemini-3.8-flash · architecture

- PNG (pilot copy): `.scratch/overview-rebuild/live/runs/gemini/1706.03762v7/overview.png`
- PNG (source): `.scratch/overview-rebuild/live/library/papers/1706.03762v7/reader/overview-figures/0250f6d011a34834b95e7a7e976526ce/fig1.png`
- Dimensions: 1223×3102 px · geometry issues: 0
- sha256: `01dc22396c306474ca3970f9fa20eb99e7c8e8b6d4e8d6c94c337f31e7e7c1dd`

### gemini-3.8-flash · method (PRO)

- PNG (pilot copy): `.scratch/overview-rebuild/live/runs/gemini/2511.07694v1/overview.png`
- PNG (source): `.scratch/overview-rebuild/live/library/papers/2511.07694v1/reader/overview-figures/620b9293e7e740518e814178777bd763/fig1.png`
- Dimensions: 991×1860 px · geometry issues: 0
- sha256: `5106cd7d789bb2a2ca790f80f4616df36b702a1c024187ac9b5df3e91a8207ec`

### gemini-3.8-flash · survey / comparison (UQ)

- PNG (pilot copy): `.scratch/overview-rebuild/live/runs/gemini/2606.19868v1/overview.png`
- PNG (source): `.scratch/overview-rebuild/live/library/papers/2606.19868v1/reader/overview-figures/c01d422a9cc24a7995cf755c89daf9ab/fig1.png`
- Dimensions: 1017×2157 px · geometry issues: 0
- sha256: `12124e860dd8729af89610e358b7c5fa0d91df705e68e664766dc907a9c184d8`

### deepseek-flash · architecture

- PNG (pilot copy): `.scratch/overview-rebuild/live/runs/deepseek/1706.03762v7/overview.png`
- PNG (source): `.scratch/overview-rebuild/live/library/papers/1706.03762v7/reader/overview-figures/0c434026bf7244c1bc86f50c755fb765/fig1.png`
- Dimensions: 1197×5487 px · geometry issues: 0
- sha256: `e533dc6b831c0b633525bd789e9ea075bc34500979611aebfe6605519dce169e`

### deepseek-flash · method (PRO)

- PNG (pilot copy): `.scratch/overview-rebuild/live/runs/deepseek/2511.07694v1/overview.png`
- PNG (source): `.scratch/overview-rebuild/live/library/papers/2511.07694v1/reader/overview-figures/5746a7e6504d496d9215177b5e3ef2a1/fig1.png`
- Dimensions: 1197×3700 px · geometry issues: 0
- sha256: `0481c1cf1be145716c0509de2aed36d152bef9767e21c63bd07d9c10af971242`

### deepseek-flash · survey / comparison (UQ)

- PNG (pilot copy): `.scratch/overview-rebuild/live/runs/deepseek/2606.19868v1/overview.png`
- PNG (source): `.scratch/overview-rebuild/live/library/papers/2606.19868v1/reader/overview-figures/bf26eb0b38a842a4bdda365073caca33/fig1.png`
- Dimensions: 966×2174 px · geometry issues: 0
- sha256: `605c56dea8d23a26ffc52f5db50b3c818da11b910e3e8cda4d8dd1d9049b13ff`

### openai/gpt-5.6-luna · architecture

- PNG (pilot copy): `.scratch/overview-rebuild/live/runs/openrouter/1706.03762v7/overview.png`
- PNG (source): `.scratch/overview-rebuild/live/library/papers/1706.03762v7/reader/overview-figures/823eee410a394a9aa0b40d80f9fb43b7/fig1.png`
- Dimensions: 2635×1617 px · geometry issues: 0
- sha256: `7e8560804c4127169bcdc7f938b0b99982facb233abbb1cf7d3c109174ac498f`

### openai/gpt-5.6-luna · method (PRO)

- PNG (pilot copy): `.scratch/overview-rebuild/live/runs/openrouter/2511.07694v1/overview.png`
- PNG (source): `.scratch/overview-rebuild/live/library/papers/2511.07694v1/reader/overview-figures/75dd47c743e24f299fd42ceed06765c4/fig1.png`
- Dimensions: 1454×3259 px · geometry issues: 0
- sha256: `3593d6e8cbd47937000e384d9650710fb985cf23b4f58b931df37469d11d1a27`

### openai/gpt-5.6-luna · survey / comparison (UQ)

- PNG (pilot copy): `.scratch/overview-rebuild/live/runs/openrouter/2606.19868v1/overview.png`
- PNG (source): `.scratch/overview-rebuild/live/library/papers/2606.19868v1/reader/overview-figures/047f00b6c4f744adab2cc1baead4425a/fig1.png`
- Dimensions: 4202×1223 px · geometry issues: 0
- sha256: `4584ff70bbddb66136ebc67ba6f88671d57cd9fa226ffaf7902a8855d8eecd7e`

### openai/gpt-5.6-terra · architecture

- PNG (pilot copy): `.scratch/overview-rebuild/live/runs/terra/1706.03762v7/overview.png`
- PNG (source): `.scratch/overview-rebuild/live/library/papers/1706.03762v7/reader/overview-figures/399cf15db73f413b8d311a0b9c5c4ef2/fig1.png`
- Dimensions: 5207×1412 px · geometry issues: 0
- sha256: `9c1aa4c47a993253fea0c23f4b14f479bdfbc046e42da997c56bbaf034418f6e`

### openai/gpt-5.6-terra · method (PRO)

- PNG (pilot copy): `.scratch/overview-rebuild/live/runs/terra/2511.07694v1/overview.png`
- PNG (source): `.scratch/overview-rebuild/live/library/papers/2511.07694v1/reader/overview-figures/3d75229a64b740baab75ac366daf8ba3/fig1.png`
- Dimensions: 2020×2298 px · geometry issues: 0
- sha256: `88f51110f949830492fe713253c06ce9d7a90eead9234ce009c18fb80ca402ce`

### openai/gpt-5.6-terra · survey / comparison (UQ)

- PNG (pilot copy): `.scratch/overview-rebuild/live/runs/terra/2606.19868v1/overview.png`
- PNG (source): `.scratch/overview-rebuild/live/library/papers/2606.19868v1/reader/overview-figures/ba4a634a05724b45a020b2d3ee9fb5a2/fig1.png`
- Dimensions: 3381×1017 px · geometry issues: 0
- sha256: `979f20b4f146194ccecb11443548e8ef437587af2e8b1b9fa05740e1fe19e237`

### openai/gpt-5.6-sol · survey / comparison (UQ)

- PNG (pilot copy): `.scratch/overview-rebuild/live/runs/sol/2606.19868v1/overview.png`
- PNG (source): `.scratch/overview-rebuild/live/library/papers/2606.19868v1/reader/overview-figures/04abad807dc345a4a12f4a73fb811d42/fig1.png`
- Dimensions: 1454×2903 px · geometry issues: 0
- sha256: `a61a6e15633ce5393525c573b777f43f0f6d146c610670465cd0acce07e80f78`

## Run detail

### gemini-3.8-flash · architecture

- Delivery: `completed` · assignment source: `planner` · local checks: `pass`
- Elapsed: 54.4 s · max concurrent drawing requests: 3
- Panels: created ['attention_mechanisms', 'decoder_stack'], repaired ['motivation_and_complexity', 'translation_results'], simplified ['encoder_stack']
- Original drawing defects for encoder_stack: Label is 539 units wide but its container /svg/rect[7] is 269 units wide. It escapes by 79.3px: Sublayer 2: FFN(x) = max(0, xW_1 + b_1)W_2 +; Label is 49 units wide but its container /svg/rect[8] is 382 units wide. It escapes by 19.0px: residual. Widen the container by about -333 u; Label is 479 units wide but its container /svg/rect[9] is 269 units wide. It escapes by 49.5px: Sublayer 1: Multi-head self-attention follow
- Turns: 12 (planning 4, drawing 8)

| Stage | Requests | Tokens | Options |
| --- | --- | --- | --- |
| selection | 1 | in 3,385 / out 135 / total 3,520 | {"gemini_thinking_level":"low"} |
| narrative | 1 | in 5,361 / out 1,038 / total 6,399 | {"gemini_thinking_level":"low"} |
| panel_plan | 1 | in 6,465 / out 2,400 / total 8,865 | {"gemini_thinking_level":"low"} |
| panel_plan_clarify | 1 | in 8,280 / out 2,407 / total 10,687 | {"gemini_thinking_level":"low"} |
| drawing attention_mechanisms · panel #1 | 1 | in 6,353 / out 1,429 / total 7,782 | {"gemini_thinking_level":"low"} |
| drawing motivation_and_complexity · panel #1 | 1 | in 6,183 / out 1,821 / total 8,004 | {"gemini_thinking_level":"low"} |
| drawing encoder_stack · panel #1 | 1 | in 6,359 / out 2,586 / total 8,945 | {"gemini_thinking_level":"low"} |
| drawing translation_results · panel #1 | 1 | in 5,289 / out 940 / total 6,229 | {"gemini_thinking_level":"low"} |
| drawing motivation_and_complexity · panel_repair #1 | 1 | in 8,038 / out 1,821 / total 9,859 | {"gemini_thinking_level":"low"} |
| drawing decoder_stack · panel #1 | 1 | in 6,111 / out 2,226 / total 8,337 | {"gemini_thinking_level":"low"} |
| drawing encoder_stack · panel_repair #1 | 1 | in 6,424 / out 1,831 / total 8,255 | {"gemini_thinking_level":"low"} |
| drawing translation_results · panel_repair #1 | 1 | in 6,697 / out 986 / total 7,683 | {"gemini_thinking_level":"low"} |
| **Total** | **12** | **in 74,945 / out 19,620 / total 94,565** | |

**Image check**: Strong 4-panel overview. Question, encoder/decoder mechanism, and the finding all read cleanly; 28.4 / 41.8 / 92.7 F1 and the >2.0 BLEU margin match the paper. The “values used here” block in panel 3 is dense, and a masked-self-attention label in panel 4 is awkwardly worded.

### gemini-3.8-flash · method (PRO)

- Delivery: `completed` · assignment source: `planner` · local checks: `pass`
- Elapsed: 39.0 s · max concurrent drawing requests: 3
- Panels: created ['pro_entropy_formulation'], repaired ['sampling_and_truncation', 'empirical_benchmark'], simplified ['methodological_limitations']
- Original drawing defects for methodological_limitations: Overlapping text: PRO OPERATIONAL BOUNDARY CONDITIONS / TECHNICAL CONSTRAINT AND SCOPE
- Turns: 11 (planning 4, drawing 7)

| Stage | Requests | Tokens | Options |
| --- | --- | --- | --- |
| selection | 1 | in 2,431 / out 115 / total 2,546 | {"gemini_thinking_level":"low"} |
| narrative | 1 | in 3,668 / out 987 / total 4,655 | {"gemini_thinking_level":"low"} |
| panel_plan | 1 | in 4,659 / out 1,989 / total 6,648 | {"gemini_thinking_level":"low"} |
| panel_plan_clarify | 1 | in 6,426 / out 2,377 / total 8,803 | {"gemini_thinking_level":"low"} |
| drawing pro_entropy_formulation · panel #1 | 1 | in 5,533 / out 857 / total 6,390 | {"gemini_thinking_level":"low"} |
| drawing sampling_and_truncation · panel #1 | 1 | in 6,302 / out 1,376 / total 7,678 | {"gemini_thinking_level":"low"} |
| drawing empirical_benchmark · panel #1 | 1 | in 6,250 / out 1,151 / total 7,401 | {"gemini_thinking_level":"low"} |
| drawing sampling_and_truncation · panel_repair #1 | 1 | in 7,754 / out 1,376 / total 9,130 | {"gemini_thinking_level":"low"} |
| drawing methodological_limitations · panel #1 | 1 | in 5,977 / out 1,099 / total 7,076 | {"gemini_thinking_level":"low"} |
| drawing empirical_benchmark · panel_repair #1 | 1 | in 7,583 / out 1,145 / total 8,728 | {"gemini_thinking_level":"low"} |
| drawing methodological_limitations · panel_repair #1 | 1 | in 7,345 / out 1,154 / total 8,499 | {"gemini_thinking_level":"low"} |
| **Total** | **11** | **in 63,928 / out 13,626 / total 77,554** | |

**Image check**: Strong 4-panel overview. The mechanism panel walks generation → scoring → rank sorting → top-K threshold → PRO and shows the lower bound and the K=1 NLL reduction. 0.739 / 0.715 / 0.709 and 11 of 15 match the brief. Limitations cover black-box access, beam search, and semantic equivalence.

### gemini-3.8-flash · survey / comparison (UQ)

- Delivery: `completed` · assignment source: `narrative_fallback` · local checks: `pass`
- Elapsed: 57.7 s · max concurrent drawing requests: 3
- Panels: created ['p4'], repaired ['p1', 'p3'], simplified ['p2']
- Planning reduced: panel planning fell back to independent narrative briefs: panel_plan.title needs 1-80 characters; panel_plan.shared_facts.brier_score_equation.exact_text[0] must be copied from the approved fact text in the same notation; panel_plan.shared_facts.bsdetector_hybrid_equation.exact_text[0] must be copied from the approved fact text in the same notation; fallback omitted narrative relationships to keep panels independent
- Original drawing defects for p2: The model returned an invalid article or figure plan. Retry generation.
- Turns: 12 (planning 5, drawing 7)

| Stage | Requests | Tokens | Options |
| --- | --- | --- | --- |
| selection | 1 | in 3,525 / out 133 / total 3,658 | {"gemini_thinking_level":"low"} |
| narrative | 1 | in 17,248 / out 1,165 / total 18,413 | {"gemini_thinking_level":"low"} |
| panel_plan | 1 | in 18,399 / out 2,679 / total 21,078 | {"gemini_thinking_level":"low"} |
| panel_plan_clarify | 1 | in 20,768 / out 3,170 / total 23,938 | {"gemini_thinking_level":"low"} |
| panel_plan_simplify | 1 | in 20,236 / out 2,395 / total 22,631 | {"gemini_thinking_level":"low"} |
| drawing p3 · panel #1 | 1 | in 6,173 / out 1,088 / total 7,261 | {"gemini_thinking_level":"low"} |
| drawing p1 · panel #1 | 1 | in 6,047 / out 1,201 / total 7,248 | {"gemini_thinking_level":"low"} |
| drawing p2 · panel #1 | 1 | in 6,203 / out 2,480 / total 8,683 | {"gemini_thinking_level":"low"} |
| drawing p4 · panel #1 | 1 | in 6,134 / out 1,509 / total 7,643 | {"gemini_thinking_level":"low"} |
| drawing p3 · panel_repair #1 | 1 | in 7,391 / out 1,083 / total 8,474 | {"gemini_thinking_level":"low"} |
| drawing p1 · panel_repair #1 | 1 | in 7,293 / out 1,201 / total 8,494 | {"gemini_thinking_level":"low"} |
| drawing p2 · panel_repair #1 | 1 | in 6,268 / out 1,638 / total 7,906 | {"gemini_thinking_level":"low"} |
| **Total** | **12** | **in 125,685 / out 19,742 / total 145,427** | |

**Image check**: Strong 4-panel overview. Core question → five-part taxonomy → findings (SteerConf AUROC, VPD ECE, single-pass efficiency) → limitations with the three method-family bottlenecks. Readable at the intended scale.

### deepseek-flash · architecture

- Delivery: `completed` · assignment source: `planner` · local checks: `pass`
- Elapsed: 256.8 s · max concurrent drawing requests: 3
- Panels: created ['overview', 'decoder', 'generalization_findings'], repaired ['encoder_layer', 'attention_heads'], simplified ['position_why_limits', 'translation_benchmarks']
- Original drawing defects for position_why_limits: Outside the panel canvas: they have same dimension d_model=512 as embeddings.; Label is 381 units wide but its container /svg/rect[10] is 249 units wide. It escapes by 40.9px: they have same dimension d_model=512 as emb
- Original drawing defects for translation_benchmarks: Label is 127 units wide but its container /svg/rect[5] is 233 units wide. It escapes by 20.9px: above prior best,including ensembles. Widen ; Label is 205 units wide but its container /svg/rect[6] is 228 units wide. It escapes by 5.0px: prior training cost (table/abstract). Widen t
- Turns: 15 (planning 4, drawing 11)

| Stage | Requests | Tokens | Options |
| --- | --- | --- | --- |
| selection | 1 | in 3,161 / out 3,096 / total 6,257 / cached 2,944 | — |
| narrative | 1 | in 6,607 / out 5,920 / total 12,527 / cached 128 | — |
| panel_plan | 1 | in 8,253 / out 19,515 / total 27,768 | — |
| panel_plan_clarify | 1 | in 12,676 / out 32,687 / total 45,363 | — |
| drawing encoder_layer · panel #1 | 1 | in 5,692 / out 838 / total 6,530 | {"reasoning_effort":"low","deepseek_thinking":false} |
| drawing overview · panel #1 | 1 | in 5,459 / out 1,409 / total 6,868 | {"reasoning_effort":"low","deepseek_thinking":false} |
| drawing attention_heads · panel #1 | 1 | in 5,127 / out 1,839 / total 6,966 | {"reasoning_effort":"low","deepseek_thinking":false} |
| drawing decoder · panel #1 | 1 | in 5,639 / out 1,497 / total 7,136 | {"reasoning_effort":"low","deepseek_thinking":false} |
| drawing translation_benchmarks · panel #1 | 1 | in 5,092 / out 915 / total 6,007 | {"reasoning_effort":"low","deepseek_thinking":false} |
| drawing position_why_limits · panel #1 | 1 | in 6,110 / out 1,582 / total 7,692 | {"reasoning_effort":"low","deepseek_thinking":false} |
| drawing encoder_layer · panel_repair #1 | 1 | in 6,555 / out 816 / total 7,371 / cached 5,632 | {"reasoning_effort":"low","deepseek_thinking":false} |
| drawing generalization_findings · panel #1 | 1 | in 5,782 / out 1,474 / total 7,256 | {"reasoning_effort":"low","deepseek_thinking":false} |
| drawing attention_heads · panel_repair #1 | 1 | in 6,941 / out 1,767 / total 8,708 / cached 5,120 | {"reasoning_effort":"low","deepseek_thinking":false} |
| drawing translation_benchmarks · panel_repair #1 | 1 | in 6,096 / out 915 / total 7,011 / cached 4,992 | {"reasoning_effort":"low","deepseek_thinking":false} |
| drawing position_why_limits · panel_repair #1 | 1 | in 7,671 / out 1,673 / total 9,344 / cached 6,016 | {"reasoning_effort":"low","deepseek_thinking":false} |
| **Total** | **15** | **in 96,861 / out 75,943 / total 172,804 / cached 24,832** | |

**Image check**: 7 panels, text-heavy. Two panels are simplified fallbacks, so the mechanism is partly prose rather than diagram. Numbers and the O(n²·d) qualification are present; the overview is usable but the least visual of the five providers.

### deepseek-flash · method (PRO)

- Delivery: `completed` · assignment source: `planner` · local checks: `pass`
- Elapsed: 239.3 s · max concurrent drawing requests: 3
- Panels: created ['pro_score'], repaired ['sampling_topk', 'lower_bound', 'adaptive_k'], simplified ['entropy_target', 'evaluation', 'limitation']
- Original drawing defects for entropy_target: The declared exact display text "Input x \u2192 LLM generation distribution p(y|x)" is missing or changed in the drawing. Preserve its group
- Original drawing defects for evaluation: Label is 231 units wide but its container /svg/rect[7] is 208 units wide. It escapes by 3.0px: Improves over NLL by 3.4% onTriviaQA and SciQ
- Original drawing defects for limitation: Overlapping text: Alternative decoding strategies are left to future work. / grey-box
- Turns: 17 (planning 4, drawing 13)

| Stage | Requests | Tokens | Options |
| --- | --- | --- | --- |
| selection | 1 | in 2,294 / out 3,781 / total 6,075 / cached 128 | — |
| narrative | 1 | in 5,339 / out 4,416 / total 9,755 / cached 384 | — |
| panel_plan | 1 | in 6,675 / out 10,874 / total 17,549 / cached 512 | — |
| panel_plan_clarify | 1 | in 8,990 / out 32,483 / total 41,473 / cached 256 | — |
| drawing pro_score · panel #1 | 1 | in 5,022 / out 817 / total 5,839 | {"reasoning_effort":"low","deepseek_thinking":false} |
| drawing entropy_target · panel #1 | 1 | in 5,515 / out 1,191 / total 6,706 | {"reasoning_effort":"low","deepseek_thinking":false} |
| drawing lower_bound · panel #1 | 1 | in 5,588 / out 518 / total 6,106 | {"reasoning_effort":"low","deepseek_thinking":false} |
| drawing sampling_topk · panel #1 | 1 | in 5,542 / out 1,839 / total 7,381 | {"reasoning_effort":"low","deepseek_thinking":false} |
| drawing adaptive_k · panel #1 | 1 | in 5,644 / out 1,004 / total 6,648 | {"reasoning_effort":"low","deepseek_thinking":false} |
| drawing limitation · panel #1 | 1 | in 5,448 / out 631 / total 6,079 | {"reasoning_effort":"low","deepseek_thinking":false} |
| drawing evaluation · panel #1 | 1 | in 4,962 / out 1,316 / total 6,278 | {"reasoning_effort":"low","deepseek_thinking":false} |
| drawing lower_bound · panel_repair #1 | 1 | in 6,177 / out 590 / total 6,767 / cached 5,504 | {"reasoning_effort":"low","deepseek_thinking":false} |
| drawing entropy_target · panel_repair #1 | 1 | in 6,812 / out 1,144 / total 7,956 / cached 5,504 | {"reasoning_effort":"low","deepseek_thinking":false} |
| drawing limitation · panel_repair #1 | 1 | in 6,189 / out 641 / total 6,830 / cached 5,376 | {"reasoning_effort":"low","deepseek_thinking":false} |
| drawing sampling_topk · panel_repair #1 | 1 | in 5,601 / out 1,202 / total 6,803 / cached 5,376 | {"reasoning_effort":"low","deepseek_thinking":false} |
| drawing adaptive_k · panel_repair #1 | 1 | in 6,575 / out 949 / total 7,524 / cached 5,632 | {"reasoning_effort":"low","deepseek_thinking":false} |
| drawing evaluation · panel_repair #1 | 1 | in 6,399 / out 1,344 / total 7,743 / cached 4,864 | {"reasoning_effort":"low","deepseek_thinking":false} |
| **Total** | **17** | **in 98,772 / out 64,740 / total 163,512 / cached 33,536** | |

**Image check**: 6 panels, equation-heavy with three simplified fallbacks. The PRO formula, lower bound, K=1 case, and benchmark AUCs are all present, but the panels read as notes rather than diagrams.

### deepseek-flash · survey / comparison (UQ)

- Delivery: `completed` · assignment source: `narrative_fallback` · local checks: `pass`
- Code: `2b7afbd0c526` · dirty diff `b92513e7d6f4d469`
- Elapsed: 383.4 s · max concurrent drawing requests: 3
- Panels: created [], repaired ['p2', 'p3'], simplified ['p1', 'p4']
- Planning reduced: panel planning fell back to independent narrative briefs: panel_plan.shared_facts.example_question.exact_text[0] must be copied from the approved fact text in the same notation; panel_plan.shared_facts.explanation_multiagent_weaker.exact_text[0] must be copied from the approved fact text in the same notation; panel_plan.shared_facts.explanation_multiagent_weaker.exact_text[1] must be copied from the approved fact text in the same notation; fallback omitted narrative relationships to keep panels independent
- Original drawing defects for p1: Outside the panel canvas: With only externally observable outputs (no logits/hidden states), how do black-; Label is 1847 units wide but its container /svg/rect[6] is 438 units wide. It escapes by 613.4px: With only externally observable outputs (n
- Original drawing defects for p4: Outside the panel canvas: 
- Turns: 13 (planning 5, drawing 8)

| Stage | Requests | Tokens | Options |
| --- | --- | --- | --- |
| selection | 1 | in 3,253 / out 9,257 / total 12,510 / cached 3,072 | — |
| narrative | 1 | in 23,313 / out 5,957 / total 29,270 / cached 384 | — |
| panel_plan | 1 | in 24,541 / out 13,860 / total 38,401 / cached 512 | — |
| panel_plan_clarify | 1 | in 28,761 / out 55,187 / total 83,948 / cached 256 | — |
| panel_plan_simplify | 1 | in 28,093 / out 5,884 / total 33,977 | — |
| drawing p3 · panel #1 | 1 | in 5,594 / out 1,009 / total 6,603 | {"reasoning_effort":"low","deepseek_thinking":false} |
| drawing p2 · panel #1 | 1 | in 5,498 / out 1,117 / total 6,615 | {"reasoning_effort":"low","deepseek_thinking":false} |
| drawing p1 · panel #1 | 1 | in 5,417 / out 937 / total 6,354 | {"reasoning_effort":"low","deepseek_thinking":false} |
| drawing p4 · panel #1 | 1 | in 5,556 / out 774 / total 6,330 | {"reasoning_effort":"low","deepseek_thinking":false} |
| drawing p3 · panel_repair #1 | 1 | in 6,612 / out 958 / total 7,570 / cached 5,504 | {"reasoning_effort":"low","deepseek_thinking":false} |
| drawing p2 · panel_repair #1 | 1 | in 6,566 / out 1,238 / total 7,804 / cached 5,376 | {"reasoning_effort":"low","deepseek_thinking":false} |
| drawing p4 · panel_repair #1 | 1 | in 6,904 / out 717 / total 7,621 / cached 5,504 | {"reasoning_effort":"low","deepseek_thinking":false} |
| drawing p1 · panel_repair #1 | 1 | in 6,338 / out 982 / total 7,320 / cached 5,376 | {"reasoning_effort":"low","deepseek_thinking":false} |
| **Total** | **13** | **in 156,446 / out 97,877 / total 254,323 / cached 25,984** | |

**Image check**: 4 panels. Question → five-category taxonomy plus the unified benchmark → open/closed-ended findings → limitations. Coherent; panel 3 is dense but readable.

### openai/gpt-5.6-luna · architecture

- Delivery: `completed` · assignment source: `narrative_fallback` · local checks: `pass`
- Elapsed: 173.2 s · max concurrent drawing requests: 3
- Panels: created ['p4'], repaired ['p1', 'p3'], simplified ['p2']
- Planning reduced: panel planning fell back to independent narrative briefs: panel_plan.shared_facts.attention_equation.exact_text[0] must be copied from the approved fact text in the same notation; panel_plan.shared_facts.causal_relation.exact_text[1] must be copied from the approved fact text in the same notation; panel_plan.shared_facts.complexity.exact_text[0] must be copied from the approved fact text in the same notation; fallback omitted narrative relationships to keep panels independent
- Original drawing defects for p2: Label is 1032 units wide but its container /svg/rect[7] is 738 units wide. It escapes by 10.0px: The paper proposes the Transformer, an enco
- Turns: 12 (planning 5, drawing 7)

| Stage | Requests | Tokens | Options |
| --- | --- | --- | --- |
| selection | 1 | in 3,032 / out 660 / total 3,692 | — |
| narrative | 1 | in 5,968 / out 1,833 / total 7,801 | — |
| panel_plan | 1 | in 7,399 / out 4,425 / total 11,824 | — |
| panel_plan_clarify | 1 | in 10,911 / out 6,248 / total 17,159 | — |
| panel_plan_simplify | 1 | in 10,123 / out 3,560 / total 13,683 | — |
| drawing p1 · panel #1 | 1 | in 5,236 / out 1,750 / total 6,986 | {} |
| drawing p3 · panel #1 | 1 | in 5,485 / out 2,332 / total 7,817 | {} |
| drawing p2 · panel #1 | 1 | in 5,449 / out 2,482 / total 7,931 | {} |
| drawing p4 · panel #1 | 1 | in 5,519 / out 2,004 / total 7,523 | {} |
| drawing p3 · panel_repair #1 | 1 | in 7,055 / out 2,025 / total 9,080 | {} |
| drawing p1 · panel_repair #1 | 1 | in 5,326 / out 1,888 / total 7,214 | {} |
| drawing p2 · panel_repair #1 | 1 | in 7,551 / out 2,582 / total 10,133 | {} |
| **Total** | **12** | **in 79,054 / out 31,789 / total 110,843** | |

**Image check**: Wide 4-panel overview with a useful qualification panel (neighborhood attention, O(n/r), “future work, not established”). The finding panel states 41.0 BLEU on English-to-French; the paper reports 41.8. The narrative itself said 41.0, so the earliest source is the narrative, not the drawing, and no display check can catch a wrong planner-supplied number.

### openai/gpt-5.6-luna · method (PRO)

- Delivery: `completed` · assignment source: `narrative_fallback` · local checks: `pass`
- Code: `2b7afbd0c526` · dirty diff `b92513e7d6f4d469`
- Elapsed: 160.9 s · max concurrent drawing requests: 3
- Panels: created ['p2', 'p3'], repaired ['p1', 'p4'], simplified []
- Planning reduced: panel planning fell back to independent narrative briefs: panel_plan.shared_facts.adaptive_selection.exact_text[1] must be copied from the approved fact text in the same notation; panel_plan.shared_facts.alpha_extremes.exact_text[2] must be copied from the approved fact text in the same notation; panel_plan.shared_facts.decoding_dependence.exact_text[1] must be copied from the approved fact text in the same notation; fallback omitted narrative relationships to keep panels independent
- Turns: 11 (planning 5, drawing 6)

| Stage | Requests | Tokens | Options |
| --- | --- | --- | --- |
| selection | 1 | in 2,186 / out 530 / total 2,716 | — |
| narrative | 1 | in 4,546 / out 1,641 / total 6,187 | — |
| panel_plan | 1 | in 5,698 / out 3,662 / total 9,360 | — |
| panel_plan_clarify | 1 | in 8,528 / out 4,946 / total 13,474 | — |
| panel_plan_simplify | 1 | in 7,930 / out 3,215 / total 11,145 | — |
| drawing p3 · panel #1 | 1 | in 5,479 / out 1,601 / total 7,080 | {} |
| drawing p1 · panel #1 | 1 | in 5,236 / out 1,780 / total 7,016 | {} |
| drawing p2 · panel #1 | 1 | in 5,344 / out 2,068 / total 7,412 | {} |
| drawing p1 · panel_repair #1 | 1 | in 6,680 / out 1,602 / total 8,282 | {} |
| drawing p4 · panel #1 | 1 | in 5,411 / out 2,196 / total 7,607 | {} |
| drawing p4 · panel_repair #1 | 1 | in 7,046 / out 1,863 / total 8,909 | {} |
| **Total** | **11** | **in 64,084 / out 25,104 / total 89,188** | |

**Image check**: 4 panels. The brief put the measured results in a statement with no exact_text, and the drawing changed them: 3.3 %→3.1 %, 6.5 %→0.5 %, 0.819→0.841, 0.806→0.816. This is a real fidelity gap: numbers inside statements are not protected by the numeric omission check, which only covers value items and declared exact text.

### openai/gpt-5.6-luna · survey / comparison (UQ)

- Delivery: `completed` · assignment source: `narrative_fallback` · local checks: `pass`
- Code: `2b7afbd0c526` · dirty diff `b92513e7d6f4d469`
- Elapsed: 146.3 s · max concurrent drawing requests: 3
- Panels: created ['p2'], repaired ['p1', 'p3'], simplified ['p4']
- Planning reduced: panel planning fell back to independent narrative briefs: panel_plan.shared_facts.benchmark_scope.exact_text[0] must be copied from the approved fact text in the same notation; panel_plan.shared_facts.benchmark_scope.exact_text[1] must be copied from the approved fact text in the same notation; panel_plan.shared_facts.benchmark_scope.exact_text[2] must be copied from the approved fact text in the same notation; fallback omitted narrative relationships to keep panels independent
- Original drawing defects for p4: Overlapping text: five samples when repeated sampling is required / GPT-5.1correctness judge foropen-ended QA
- Turns: 12 (planning 5, drawing 7)

| Stage | Requests | Tokens | Options |
| --- | --- | --- | --- |
| selection | 1 | in 3,127 / out 1,037 / total 4,164 | — |
| narrative | 1 | in 5,730 / out 1,453 / total 7,183 | — |
| panel_plan | 1 | in 6,901 / out 3,752 / total 10,653 | — |
| panel_plan_clarify | 1 | in 9,454 / out 4,097 / total 13,551 | — |
| panel_plan_simplify | 1 | in 8,692 / out 2,588 / total 11,280 | — |
| drawing p3 · panel #1 | 1 | in 5,476 / out 2,250 / total 7,726 | {} |
| drawing p1 · panel #1 | 1 | in 5,260 / out 2,353 / total 7,613 | {} |
| drawing p2 · panel #1 | 1 | in 5,359 / out 2,700 / total 8,059 | {} |
| drawing p4 · panel #1 | 1 | in 5,486 / out 2,064 / total 7,550 | {} |
| drawing p1 · panel_repair #1 | 1 | in 7,250 / out 2,540 / total 9,790 | {} |
| drawing p3 · panel_repair #1 | 1 | in 7,325 / out 2,701 / total 10,026 | {} |
| drawing p4 · panel_repair #1 | 1 | in 7,009 / out 1,868 / total 8,877 | {} |
| **Total** | **12** | **in 77,069 / out 29,403 / total 106,472** | |

**Image check**: 3 dense panels in two columns. Covers the taxonomy, benchmark scope, and the “no single method dominates” finding, but the layout is cramped at the intended scale.

### openai/gpt-5.6-terra · architecture

- Delivery: `completed` · assignment source: `narrative_fallback` · local checks: `pass`
- Code: `2b7afbd0c526` · dirty diff `b92513e7d6f4d469`
- Elapsed: 129.3 s · max concurrent drawing requests: 3
- Panels: created ['p2', 'p3', 'p4'], repaired ['p1'], simplified []
- Planning reduced: panel planning fell back to independent narrative briefs: panel_plan.shared_facts.full_attention_cost.exact_text[0] must be copied from the approved fact text in the same notation; panel_plan.shared_facts.model_dimension.exact_text[0] must be copied from the approved fact text in the same notation; panel_plan.shared_facts.self_attention.exact_text[0] must be copied from the approved fact text in the same notation; fallback omitted narrative relationships to keep panels independent
- Turns: 10 (planning 5, drawing 5)

| Stage | Requests | Tokens | Options |
| --- | --- | --- | --- |
| selection | 1 | in 3,032 / out 328 / total 3,360 | — |
| narrative | 1 | in 6,813 / out 1,267 / total 8,080 | — |
| panel_plan | 1 | in 8,037 / out 3,089 / total 11,126 | — |
| panel_plan_clarify | 1 | in 10,467 / out 4,206 / total 14,673 | — |
| panel_plan_simplify | 1 | in 9,894 / out 3,341 / total 13,235 | — |
| drawing p3 · panel #1 | 1 | in 5,395 / out 1,574 / total 6,969 | {} |
| drawing p1 · panel #1 | 1 | in 5,233 / out 1,760 / total 6,993 | {} |
| drawing p2 · panel #1 | 1 | in 5,317 / out 1,861 / total 7,178 | {} |
| drawing p1 · panel_repair #1 | 1 | in 6,858 / out 1,656 / total 8,514 | {} |
| drawing p4 · panel #1 | 1 | in 5,312 / out 2,021 / total 7,333 | {} |
| **Total** | **10** | **in 66,358 / out 21,103 / total 87,461** | |

**Image check**: 4 panels. Question → encoder/decoder stacks → 28.4/27.3/41.8 BLEU finding → O(n²·d) limitation with the restricted-attention future work. Answers match the paper; the mechanism panel is diagrammatic and readable.

### openai/gpt-5.6-terra · method (PRO)

- Delivery: `completed` · assignment source: `narrative_fallback` · local checks: `pass`
- Code: `2b7afbd0c526` · dirty diff `00e02a5953880333`
- Elapsed: 135.1 s · max concurrent drawing requests: 3
- Panels: created ['p1', 'p4'], repaired ['p3'], simplified ['p2']
- Planning reduced: panel planning fell back to independent narrative briefs: panel_plan.shared_facts.adaptive_threshold.exact_text[0] must be copied from the approved fact text in the same notation; panel_plan.shared_facts.adaptive_threshold.exact_text[1] must be copied from the approved fact text in the same notation; panel_plan.shared_facts.adaptive_threshold.exact_text[2] must be copied from the approved fact text in the same notation; fallback omitted narrative relationships to keep panels independent
- Original drawing defects for p2: Label is 79 units wide but its container /svg/rect[15] is 61 units wide. It escapes by 9.2px: response 2. Widen the container by about 18 un
- Turns: 11 (planning 5, drawing 6)

| Stage | Requests | Tokens | Options |
| --- | --- | --- | --- |
| selection | 1 | in 2,186 / out 288 / total 2,474 / cached 2,183 | — |
| narrative | 1 | in 4,711 / out 1,007 / total 5,718 | — |
| panel_plan | 1 | in 5,839 / out 3,559 / total 9,398 | — |
| panel_plan_clarify | 1 | in 8,564 / out 3,879 / total 12,443 | — |
| panel_plan_simplify | 1 | in 7,776 / out 3,076 / total 10,852 | — |
| drawing p1 · panel #1 | 1 | in 5,242 / out 1,341 / total 6,583 | {} |
| drawing p2 · panel #1 | 1 | in 5,263 / out 1,767 / total 7,030 | {} |
| drawing p3 · panel #1 | 1 | in 5,344 / out 2,588 / total 7,932 | {} |
| drawing p2 · panel_repair #1 | 1 | in 5,327 / out 1,889 / total 7,216 | {} |
| drawing p4 · panel #1 | 1 | in 5,303 / out 2,516 / total 7,819 | {} |
| drawing p3 · panel_repair #1 | 1 | in 7,721 / out 2,935 / total 10,656 | {} |
| **Total** | **11** | **in 63,276 / out 24,845 / total 88,121 / cached 2,183** | |

**Image check**: 4 panels. The mechanism panel is a simplified fallback, but the finding panel is clean: 11 of 15 settings, 0.739 / 0.715 / 0.709, 2.4 % improvement. Limitations cover grey-box access, no QA semantics, beam search, and decoding.

### openai/gpt-5.6-terra · survey / comparison (UQ)

- Delivery: `completed` · assignment source: `narrative_fallback` · local checks: `pass`
- Code: `2b7afbd0c526` · dirty diff `b92513e7d6f4d469`
- Elapsed: 143.0 s · max concurrent drawing requests: 3
- Panels: created [], repaired ['p1', 'p2'], simplified ['p3', 'p4']
- Planning reduced: panel planning fell back to independent narrative briefs: panel_plan.shared_facts.calibration_equation.exact_text[0] must be copied from the approved fact text in the same notation; panel_plan.shared_facts.cot_sampling.exact_text[0] must be copied from the approved fact text in the same notation; panel_plan.shared_facts.cot_sampling.exact_text[1] must be copied from the approved fact text in the same notation; fallback omitted narrative relationships to keep panels independent
- Original drawing defects for p3: Label is 233 units wide but its container /svg/rect[13] is 659 units wide. It escapes by 5.7px: longer bar = generally higher AUROC. Widen t; Overlapping text: strong across metrics / best
- Original drawing defects for p4: Unsupported attribute on text: aria-label.
- Turns: 13 (planning 5, drawing 8)

| Stage | Requests | Tokens | Options |
| --- | --- | --- | --- |
| selection | 1 | in 3,127 / out 527 / total 3,654 | — |
| narrative | 1 | in 7,512 / out 1,115 / total 8,627 | — |
| panel_plan | 1 | in 8,674 / out 2,667 / total 11,341 | — |
| panel_plan_clarify | 1 | in 11,718 / out 4,195 / total 15,913 | — |
| panel_plan_simplify | 1 | in 10,934 / out 2,640 / total 13,574 | — |
| drawing p1 · panel #1 | 1 | in 5,245 / out 1,602 / total 6,847 | {} |
| drawing p2 · panel #1 | 1 | in 5,314 / out 2,185 / total 7,499 | {} |
| drawing p3 · panel #1 | 1 | in 5,428 / out 2,002 / total 7,430 | {} |
| drawing p2 · panel_repair #1 | 1 | in 7,314 / out 2,041 / total 9,355 | {} |
| drawing p4 · panel #1 | 1 | in 5,399 / out 2,356 / total 7,755 | {} |
| drawing p1 · panel_repair #1 | 1 | in 6,595 / out 2,047 / total 8,642 | {} |
| drawing p4 · panel_repair #1 | 1 | in 5,454 / out 1,978 / total 7,432 | {} |
| drawing p3 · panel_repair #1 | 1 | in 5,483 / out 2,979 / total 8,462 | {} |
| **Total** | **13** | **in 88,197 / out 28,334 / total 116,531** | |

**Image check**: 3 panels. Panels 1–2 are repaired drawings and read well; panels 3–4 are simplified fallbacks and the finding text is garbled (“PRO evaluated QA”, “13 and UP”, a repeated “On closed-ended QA”). The defect is in the approved brief text, not the fallback.

### openai/gpt-5.6-sol · architecture

- **Stopped**: stopped by the operator after ~11.5 min; the selection request never returned.

### openai/gpt-5.6-sol · method (PRO)

- **Stopped**: stopped by the operator after ~11.5 min; the selection request never returned.

### openai/gpt-5.6-sol · survey / comparison (UQ)

- Delivery: `completed` · assignment source: `narrative_fallback` · local checks: `pass`
- Code: `2b7afbd0c526` · dirty diff `b92513e7d6f4d469`
- Elapsed: 377.0 s · max concurrent drawing requests: 3
- Panels: created ['p2', 'p3'], repaired ['p4'], simplified ['p1']
- Planning reduced: panel planning fell back to independent narrative briefs: panel_plan.shared_facts.benchmark_scope.exact_text[0] must be copied from the approved fact text in the same notation; panel_plan.shared_facts.benchmark_scope.exact_text[1] must be copied from the approved fact text in the same notation; panel_plan.shared_facts.benchmark_scope.exact_text[2] must be copied from the approved fact text in the same notation; fallback omitted narrative relationships to keep panels independent
- Original drawing defects for p1: Outside the panel canvas: confidence matches accuracy; Label is 166 units wide but its container /svg/rect[11] is 148 units wide. It escapes by 10.0px: observable outputs. Widen the container by ; Label is 184 units wide but its container /svg/rect[12] is 91 units wide. It escapes by 28.2px: confidence matches accuracy. Widen the conta
- Turns: 11 (planning 5, drawing 6)

| Stage | Requests | Tokens | Options |
| --- | --- | --- | --- |
| selection | 1 | in 3,127 / out 1,177 / total 4,304 | — |
| narrative | 1 | in 20,199 / out 1,537 / total 21,736 | — |
| panel_plan | 1 | in 21,539 / out 4,471 / total 26,010 | — |
| panel_plan_clarify | 1 | in 25,142 / out 8,437 / total 33,579 | — |
| panel_plan_simplify | 1 | in 24,342 / out 4,710 / total 29,052 | — |
| drawing p3 · panel #1 | 1 | in 5,401 / out 2,797 / total 8,198 | {} |
| drawing p2 · panel #1 | 1 | in 5,323 / out 2,846 / total 8,169 | {} |
| drawing p1 · panel #1 | 1 | in 5,254 / out 3,266 / total 8,520 | {} |
| drawing p1 · panel_repair #1 | 1 | in 5,309 / out 2,897 / total 8,206 | {} |
| drawing p4 · panel #1 | 1 | in 5,420 / out 4,163 / total 9,583 | {} |
| drawing p4 · panel_repair #1 | 1 | in 5,475 / out 3,018 / total 8,493 | {} |
| **Total** | **11** | **in 126,531 / out 39,319 / total 165,850** | |

**Image check**: 4 panels. Unified formulation → evidence families → method-task fit (SteerConf/VPD/T3/UP, NLI vs embedding) → benchmark scope, metric caveats, and semantic comparison limits. The strongest survey overview of the run set.

## Notes and caveats

- The Sol architecture and Sol method runs were stopped by the operator after hanging at the first selection request for about 11.5 minutes; both left a run directory in `running` state with no model events. Sol survey completed in 377 s.
- The bold-measurement fallback fix was made after the first DeepSeek survey attempt failed; the successful re-run is what appears here.
- The invalid supplemental-evidence fix was made after the first Terra method attempt crashed; the successful re-run (with the fix) is what appears here. Terra architecture, Terra survey, and all three Luna runs used the wrapping fix but not the supplemental-evidence fix.
- A full live matrix would add Sol architecture and Sol method with a larger per-request timeout or a smaller selection prompt.
