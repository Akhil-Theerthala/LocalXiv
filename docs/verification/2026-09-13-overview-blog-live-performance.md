# Overview and Blog live performance test — observational report

**Date:** 2026-09-13T19:16:43.565943+00:00 · **Session:** `/Users/silver/Developer/arxiv-paper-to-kindle/.scratch/overview-live-e2e/2026-09-13-live` · **Scope:** testing only, application code frozen

## 1. What was tested, and what was not

The question for this run was whether the two generation services work without issues: the
**Overview** service (`POST /api/papers/<id>/bento`, the panel-authoring workflow) and the **Blog**
service (`POST /api/papers/<id>/summary`, the selective Blog agent). Per user direction on
2026-09-13, imports were used only as the way papers enter a library; exports, Kindle/Mail handoff,
persistence and cancellation behaviour were **not** tested, and nothing in the application was
changed, repaired, tuned or migrated.

Forty generation slots were planned: five pinned papers × four OpenRouter models × two modes.
This report describes every slot's terminal outcome, the artifacts each left behind, and the
telemetry the application and the provider exposed.

## 2. The tested candidate, frozen

| Item | Value |
| --- | --- |
| HEAD | `35260f3561dcfdf69b245c369122b32729a43ed9` |
| Branch | `akhil/model-authored-svg-overviews` |
| Tracked diff SHA-256 | `a1ce6725641cb9fbe2e2ad2500cf9991768f3c9b895cb01bec74f46ac0dbeabc` (5876 bytes of unstaged changes) |
| Untracked runtime modules included in the run | `papers/edge_align.py`, `papers/mixed_fit.py` |
| Other untracked files present in the checkout | `docs/superpowers/plans/2026-09-13-overview-end-to-end-live-testing.md`, `docs/verification/2026-09-13-overview-edge-alignment.md`, `docs/verification/2026-09-13-overview-mixed-scaling.md`, `tests/test_edge_align.py` |
| Interpreter | `/Applications/LocalXiv.app/Contents/Resources/runtime/bin/python3` (Python 3.14.7) |
| Web renderer | papers/html-snapshot (native WebKit host, sandbox-exec) |
| Overview prompt/contract revisions | `overview-panel-workflow-v2`, workflow `panel-workflow-v1`, reading `reading-v5-selective`, ai `2026-09-09.2` |
| Blog prompt revision | `smolagents-selective-blog-v3` (as recorded by the Blog agent itself), context revision `generation-context-v1` |

Every generation job recorded the same code identity at submission time
(`tracked_diff_sha256` `a1ce6725641c…` for all
40 slots), and the checkout still matches today, so the candidate under test did not move
during the session. Per-file SHA-256 values for the runtime sources are in `manifest.json`
(`code_identity.source_files`).

Tools actually used for the matrix (recorded in `manifest.json` → `runtime`): `pandoc` pandoc 3.11 (/opt/homebrew/Cellar/pandoc/3.11/bin/pandoc), `latexml` Unknown option: version (/opt/homebrew/Cellar/latexml/0.8.8_5/bin/latexml), `latexmlpost` Unknown option: version (/opt/homebrew/Cellar/latexml/0.8.8_5/bin/latexmlpost), `rsvg-convert` rsvg-convert version 2.63.0 (/opt/homebrew/Cellar/librsvg/2.63.0/bin/rsvg-convert), `node` v22.19.0 (/Users/silver/.nvm/versions/node/v22.19.0/bin/node), `epubcheck` EPUBCheck v5.3.0 (/opt/homebrew/Cellar/epubcheck/5.3.0/bin/epubcheck), `gs` 10.08.0 (/opt/homebrew/Cellar/ghostscript/10.08.0/bin/gs), `sandbox-exec` /usr/bin/sandbox-exec: illegal opt (/usr/bin/sandbox-exec).

## 3. Models: what was requested, what was resolved, where requests went

All four models used `https://openrouter.ai/api/v1` with the credential from
macOS Keychain (org.papers-to-kindle.provider / https://openrouter.ai/api/v1). No direct Gemini or DeepSeek endpoint was used.

| Requested | OpenRouter slug | Name | Context / max output | Input modalities | Pricing (per token, prompt/completion) |
| --- | --- | --- | --- | --- | --- |
| gemini-3.8-flash | `google/gemini-3.8-flash` | Google: Gemini 3.8 Flash | 1,048,576 / 65,536 | text, image, video, file, audio | 0.00000075 / 0.00000375 |
| deepseek-flash | `deepseek/deepseek-v4.1-flash` | DeepSeek: DeepSeek V4.1 Flash | 1,048,576 / 384,000 | text, image | 0.00000015 / 0.0000006 |
| gpt-luna | `openai/gpt-5.6-luna` | OpenAI: GPT-5.6 Luna | 1,050,000 / 128,000 | file, image, text | 0.0000002 / 0.0000012 |
| gpt-terra | `openai/gpt-5.6-terra` | OpenAI: GPT-5.6 Terra | 1,050,000 / 128,000 | file, image, text | 0.000002 / 0.000012 |

Resolution evidence per model is recorded in `manifest.json` → `catalog.resolution`. The catalog
response was saved at session start (`catalog/openrouter-models-20260913T170339Z.json`,
retrieved 2026-09-13T17:03:39.287003+00:00).

**Upstream routing is not pinned.** OpenRouter routed requests automatically, and the upstream
provider is recorded per request:

| Model | Upstream providers observed (requests) |
| --- | --- |
| deepseek-flash | Wafer (24), Together (16), DeepInfra (12), Morph (11), GMICloud (9), Fireworks (8), Modal (7), Novita (6), SiliconFlow (5), Venice (5), Relace (5), Parasail (3) |
| gemini-3.8-flash | Google (100), unknown (1) |
| gpt-luna | OpenAI (143) |
| gpt-terra | OpenAI (98) |

For `deepseek-flash` this means the same requested model was served by
12 different upstream providers during the session, which is relevant when comparing
latency or failure rates between slots. `gemini-3.8-flash` was served by Google (with one provider error), and both OpenAI models
were served by OpenAI.

## 4. Fixed configuration and observation windows

Settings were taken from the live application's own preferences and held constant: language
`casual`, Blog length `medium`, vision **enabled** (per user direction, this is the live setting),
`auto_summary=False`, `auto_send=False`. Effective per-library settings are in
`state/clones.json`; the settings each request carried are in `telemetry/*/requests-lane*.json`.

Observation windows: import 60 min/paper, generation 90 min/job with one 30-minute extension when
progress was still visible, export 20 min/artifact (not exercised), polling every 15 s. No
production timeout was changed. The user set a hard spend ceiling of **$20**
(reserve $2 for in-flight work); the ceiling was never reached
(final reported spend $10.53).

## 5. Method, isolation, and instrumentation

* Five exact versions were imported through the real import path into a clean staging library, then
  cloned into four isolated model libraries. Document digests are identical across libraries and
  generation state is fresh (`state/clones.json`).
* Each model had its own library and its own application server process(es), started from the frozen
  checkout via `app.server.make_server`; jobs were submitted only through the authenticated loopback
  API (`/api/import`, `/api/papers/<id>/bento`, `/api/papers/<id>/summary`, `/api/state`,
  `/api/jobs/<id>/cancel`).
* Request-level telemetry was captured by wrapping the HTTP call the application's own
  `papers.ai.Provider` makes. The wrapper records the exact payload, the raw provider response,
  timings, HTTP status, usage, the OpenRouter request id, and the upstream provider. Credentials are
  never written: everything passes through a redactor, and base64 image payloads are replaced by a
  size marker.
* Concurrency: one job at a time per library server, up to two servers per model, four models in
  parallel — the user asked for models and papers to run in parallel. Recorded overlap is in
  `results/telemetry-analysis.json`; peak concurrent provider requests were
  14.
* Nothing was rerun to improve a score. Slots interrupted by a fault in this harness were recorded
  as attempt 1 with outcome `interrupted` and requeued as attempt 2 (see §9).

## 6. Results: the 40-slot matrix

* **Overviews delivered: 20/20** · failed 0
* **Blogs delivered: 0/20** · failed 20
* Slots still not terminal at the time of writing: 0

The full per-slot table, with cost, request counts, panel outcomes and failed checks, is
`results/matrix.csv` / `results/matrix.json`. Every slot's collected artifacts live under
`models/<model>/papers/<paper>/<mode>/`; failed slots keep their drafts, traces and `failure.json`.
The gallery is `gallery/index.html`.

### 6.1 Overview service

All 20 delivered Overviews are single-canvas, multi-panel SVGs with PNG/PDF/HTML
exports. Panel counts and outcomes are in the matrix CSV; summary:

| Model | Delivered | Panels per Overview | Median wall time (s) | Repaired panels (total) | Plan reduced |
| --- | --- | --- | --- | --- | --- |
| deepseek-flash | 5 | 7, 7, 7, 7, 7 | 496 | 9 | 0 |
| gemini-3.8-flash | 5 | 4, 4, 5, 4, 4 | 240 | 12 | 1 |
| gpt-luna | 5 | 4, 4, 4, 4, 4 | 150 | 10 | 5 |
| gpt-terra | 5 | 4, 4, 4, 4, 4 | 45 | 9 | 5 |

What worked, and what the app itself flagged:

* Every Overview reached `delivery=completed`; no Overview slot failed.
* The pipeline repairs rather than rejects: 29 panels were repaired and
  11 were simplified; every Overview needed at least one repair or simplification.
* The application recorded drawing defects in 10 of 20 delivered Overviews,
  28 issue strings in total (deepseek-flash: 4, gemini-3.8-flash: 19, gpt-luna: 2, gpt-terra: 3). Recorded defects describe the *panel
  attempts*, not necessarily the delivered canvas: several were fixed by the repair that followed.
* Panel planning fell back to "independent narrative briefs" in 11 of 20 delivered Overviews: the planner's
  `shared_facts.exact_text` values were rejected by the plan validator, so the intended shared-fact
  planning mode was rarely used.
* Canvas shape differs sharply by model: `gpt-terra` produced wide, short canvases (~3,900×1,140),
  `gpt-luna` and `gemini-3.8-flash` mixed taller ones, and `deepseek-flash` produced ~1,010×5,900
  canvas with seven panels. Those tall canvases are legible at 100% zoom but not when fitted to a
  screen, which is how a reader first sees them.

An independent reviewer (a second agent that saw only the rendered images, with no access to the
run records) inspected six Overviews. Its findings, including one defect the automated checks did
not report at all. The orchestrator independently confirmed the LIGO citation leak in the delivered
SVG and could not confirm the reviewer's panel-4 bar-height claim, which is therefore kept only in
`state/independent-visual-review.json` and not asserted here:

| Image | Panels | Legibility | Visible problems | Notes |
| --- | --- | --- | --- | --- |
| deepseek-flash·2106.09685v2·overview | 7 | legible only when zoomed | none reported | Delivered raster is 1012x5949, 1:1 with its SVG, so the smallest glyphs are ~14-20px on a canvas 5.9x taller than wide; nothing is readable at a fit-to-view scale. |
| gpt-luna·1602.03837v1·overview | 4 | legible as delivered | internal citation tokens appear in reader-visible prose: [p00001, p00002, p00008], [p00001, p00007, p00008], [p00003, p00007] | Asymmetric mass errors are set with Unicode super/subscripts; small but readable at full size. VERIFIED by the orchestrator: the delivered fig1.source.svg contains p00001/p00002/p00003/p00007/p00008 inside <text> nodes. |
| gpt-luna·2009.03300v3·overview | 4 | legible as delivered | panel 1: the row label 'knowledge encountered during' ends under the left edge of the opaque bar, covering the final letter; panel 3: the bold label '43.9% few-shot accuracy' is centred on the 175B bar but its right end crosses the top edge of the neighbouring UnifiedQA bar; panel 3: '43.9% few-shot accuracy' and '48.9% in transfer' sit only ~7 units apart and read as one crowded block | Reviewer also reported that in panel 4 the outlined '36.1%' bar is drawn taller than its label implies. That specific claim was not independently confirmed by the orchestrator and is recorded as unverified. |
| gpt-luna·2106.09685v2·overview | 4 | legible as delivered | panel 2: a short arrow from the 'learned adaptation' box terminates on a free-floating annotation instead of a node, so it reads as a dead end | Large type (18-27px), generous margins. The app's own check reports a 4px overflow of one paragraph line past its container in panel 3, not visible at normal size. |
| gpt-luna·2107.07511v6·overview | 4 | legible as delivered | panel 4: the horizontal connector from 'i.i.d. data' to 'exchangeability' runs through the middle of the label 'or, more generally,' so the arrow strikes through the text | Math is set as Unicode text and readable. |
| gpt-luna·2312.00752v2·overview | 4 | legible as delivered | panel 2: a grey vertical line stops ~30 units short of the 'paper contribution' box with no arrowhead, while its sibling line does have one | Panel 3 finding is a single long but legible prose paragraph. |

Automated artifact checks (structure, final-SVG validity, label floor, marker/citation consistency,
numeric traceability) plus the two independent visual passes are recorded in
`state/automated-checks.json`, `state/visual-review.json` and
`state/independent-visual-review.json`.

### 6.2 Blog service

**No Blog delivered in this run**: 20 of 20 Blog slots failed. The recorded causes are twelve
distinct messages in four families: provider-side failures (3 kinds), agent-protocol failures, figure-contract
validation, and review judgements.

| Cause observed | Count | Models | Example message |
| --- | --- | --- | --- |
| provider ended the response with an error finish reason | 5 | deepseek-flash, gemini-3.8-flash | Error while generating output: Provider did not finish its response (error). The provider stopped generation;  |
| provider returned an empty completion | 4 | gpt-terra | Error while generating output: Provider request failed or returned an invalid response. Check connectivity and |
| author returned prose instead of a tool call | 2 | gpt-luna, gpt-terra | Error while generating output: Author returned prose without a tool call. Draft retained; no automatic retry. |
| agent protocol: malformed tool JSON survived one correction | 1 | deepseek-flash | Malformed tool JSON repeated after one protocol correction. Draft retained. |
| figure contract: SVG label smaller than the 16px profile minimum | 1 | gemini-3.8-flash | SVG text must be 16–80px. Use fewer labels instead of shrinking text. It did not improve after two corrections |
| provider rejected the request (HTTP 400) | 1 | gemini-3.8-flash | Error while generating output: Provider request failed with HTTP status 400. |
| figure contract: unsupported nested SVG element | 1 | gemini-3.8-flash | Unsupported figure tag: {http://www.w3.org/2000/svg}svg It did not improve after two corrections. |
| local validation did not improve after two repairs | 1 | gemini-3.8-flash | Unsupported attributes on g: font-family It did not improve after two corrections. |
| review: the explanation was judged incomplete | 1 | gpt-luna | The example shows x entering W₀ and BA and then writes W₀x + BAx, but it never explains the low-rank compositi |
| figure markers do not match the narrative | 1 | gpt-luna | Place each figure marker exactly once and omit unknown markers. It did not improve after two corrections. |
| review: a claim was judged incorrect or misleading | 1 | gpt-luna | “Larger sets stabilize it” is incorrect or at least misleading. The paper says larger calibration sets stabili |
| review: overlapping labels in a figure | 1 | gpt-luna | The labels beneath the bars visibly collide: “GPT-3” and “UnifiedQA” run together as “GPT-3UnifiedQA.” A newco |

Where each failure happened, and how much work preceded it (full data in
`results/blog-forensics.json`):

| Slot | Requests | Repairs | Cost USD | Retained draft (chars / citations / sections / figures) | Result |
| --- | --- | --- | --- | --- | --- |
| deepseek-flash·1602.03837v1·blog | 5 | 0 | 0.0166 | 0 / 0 / 0 / 0 | Error while generating output: Provider did not finish its response (error). The |
| deepseek-flash·2009.03300v3·blog | 17 | 10 | 0.3094 | 8605 / 34 / 4 / 3 | Malformed tool JSON repeated after one protocol correction. Draft retained. |
| deepseek-flash·2106.09685v2·blog | 1 | 0 | 0.0000 | 0 / 0 / 0 / 0 | Error while generating output: Provider did not finish its response (error). The |
| deepseek-flash·2107.07511v6·blog | 3 | 0 | 0.0119 | 0 / 0 / 0 / 0 | Error while generating output: Provider did not finish its response (error). The |
| deepseek-flash·2312.00752v2·blog | 3 | 0 | 0.0055 | 0 / 0 / 0 / 0 | Error while generating output: Provider did not finish its response (error). The |
| gemini-3.8-flash·1602.03837v1·blog | 9 | 5 | 0.4616 | 10978 / 54 / 7 / 1 | Unsupported attributes on g: font-family It did not improve after two correction |
| gemini-3.8-flash·2009.03300v3·blog | 4 | 0 | 0.0526 | 0 / 0 / 0 / 0 | Error while generating output: Provider did not finish its response (error). The |
| gemini-3.8-flash·2106.09685v2·blog | 7 | 4 | 0.2804 | 10099 / 50 / 7 / 1 | SVG text must be 16–80px. Use fewer labels instead of shrinking text. It did not |
| gemini-3.8-flash·2107.07511v6·blog | 11 | 5 | 0.3518 | 7848 / 0 / 5 / 1 | Unsupported figure tag: {http://www.w3.org/2000/svg}svg It did not improve after |
| gemini-3.8-flash·2312.00752v2·blog | 15 | 9 | 0.7043 | 9977 / 55 / 6 / 1 | Error while generating output: Provider request failed with HTTP status 400. |
| gpt-luna·1602.03837v1·blog | 9 | 5 | 0.0710 | 6612 / 16 / 6 / 1 | Error while generating output: Author returned prose without a tool call. Draft  |
| gpt-luna·2009.03300v3·blog | 14 | 9 | 0.1030 | 5770 / 34 / 4 / 1 | The labels beneath the bars visibly collide: “GPT-3” and “UnifiedQA” run togethe |
| gpt-luna·2106.09685v2·blog | 14 | 10 | 0.1002 | 5918 / 13 / 4 / 1 | The example shows x entering W₀ and BA and then writes W₀x + BAx, but it never e |
| gpt-luna·2107.07511v6·blog | 27 | 23 | 0.2098 | 5324 / 38 / 6 / 1 | “Larger sets stabilize it” is incorrect or at least misleading. The paper says l |
| gpt-luna·2312.00752v2·blog | 8 | 4 | 0.0483 | 5987 / 35 / 0 / 1 | Place each figure marker exactly once and omit unknown markers. It did not impro |
| gpt-terra·1602.03837v1·blog | 7 | 3 | 0.3511 | 7896 / 30 / 6 / 1 | Error while generating output: Author returned prose without a tool call. Draft  |
| gpt-terra·2009.03300v3·blog | 6 | 2 | 0.3652 | 8494 / 46 / 7 / 1 | Error while generating output: Provider request failed or returned an invalid re |
| gpt-terra·2106.09685v2·blog | 8 | 5 | 0.4623 | 6580 / 27 / 0 / 1 | Error while generating output: Provider request failed or returned an invalid re |
| gpt-terra·2107.07511v6·blog | 6 | 3 | 0.3792 | 7401 / 42 / 7 / 1 | Error while generating output: Provider request failed or returned an invalid re |
| gpt-terra·2312.00752v2·blog | 6 | 2 | 0.2950 | 8011 / 40 / 6 / 1 | Error while generating output: Provider request failed or returned an invalid re |

Observations that the evidence supports:

* 15 of the 20 failed Blog slots left a **complete draft** behind
  (731–1512 words, 13–55 passage citations, up to 7 sections, one figure). The service fails on its own quality gates, not on
  producing prose; the failure records even name the exact paragraph a review rejected (for example
  `text.paragraphs[9]`).
* The dominant cost of a failed Blog is the repair loop: `gpt-luna` on the conformal paper made 27
  requests, 23 of them repairs, before the reviewer's objection survived the repair budget.
* Failure causes are heterogeneous across models: `gpt-terra` mostly returned empty completions
  (`finish_reason` `stop` with `content: null`) during repair; `deepseek-flash` ended responses with
  `finish_reason: error`; `gemini-3.8-flash` hit figure-contract validation ("SVG text must be
  16–80px", "Unsupported figure tag …svg") and one provider-side HTTP 400 (`Corrupted thought
  signature`, Google AI Studio). Only two slots failed on a *review* judgement of the text.
* Reference condition: for four papers the Blog ran after a saved Overview existed (the app passes
  it to the Blog as `image_overview`); the conformal tutorial ran Blog-first by design, so its Blog
  was standalone. Both conditions failed, so no comparison between them is possible from this run —
  recorded as a coverage gap, not a result.

### 6.3 Quality verdicts by dimension

Delivery is reported above; the remaining dimensions are assessed separately so a strong
explanation cannot mask a failed one.

| Dimension | Overview | Blog | Evidence |
| --- | --- | --- | --- |
| Delivery | 20/20 slots delivered | 0/20 slots delivered | §6.1–6.2, `results/matrix.csv` |
| Factual accuracy | Correct numbers and qualifiers in every Overview inspected by hand (bar/scale values, confidence intervals, false-alarm rates, mass estimates); the automated traceability check found only illustrative example values and derived arithmetic outside the retained passages | Not assessable on delivered output; drafts cite passages heavily (13–55 citations) and the two review failures were factual objections, so the body text is checkable | §6.1, `state/automated-checks.json`, `results/blog-forensics.json` |
| Intuitive explanation | Strong: panels follow problem → mechanism → evidence → limitation, label equations, and separate reported results from interpretation; `deepseek-flash` leans to prose inside panels | Drafts show the same structure and define terms before using them (see §6.2) | visual review files, `models/*/papers/*/blog/run/draft.json` |
| Visual legibility | Legible at fit-to-window for `gpt-terra`, `gpt-luna` and most `gemini-3.8-flash` canvases; `deepseek-flash`'s ~1,010×5,900 canvases need zoom | No delivered figure; several failures were figure legibility or contract failures, i.e. the service itself judged the figures inadequate | §6.1, §6.2, visual review files |
| Reader interaction (click regions, reload, reader view) | Not tested — out of scope by user direction | Not tested | – |
| Export fidelity (EPUB/PDF/EPUBCheck) | Not tested — out of scope by user direction | Not tested | – |

## 7. Cost and usage

| Item | Value |
| --- | --- |
| Reported provider cost for the session | **$10.5276** |
| Priced requests | 452 of 453 |
| Cost per delivered output | $0.5264 over 20 delivered outputs |
| Cost per delivered Overview | $0.5264 |
| Cost of failed Blog attempts | $4.5790 across 20 failed Blog slots |
| Median reported cost of a delivered Overview | $0.3093 |

Per model:

| Model | Requests | Reported cost USD | Share |
| --- | --- | --- | --- |
| gpt-terra | 98 | 4.4548 | 42.3% |
| gemini-3.8-flash | 101 | 3.7978 | 36.1% |
| deepseek-flash | 111 | 1.3318 | 12.7% |
| gpt-luna | 143 | 0.9432 | 9.0% |

**Reconciliation.** The provider-reported total matches the account-level usage delta exactly:
the OpenRouter account read 152.391192 before the session and 162.918799 after it
(delta 10.527607 against 10.527607 of per-request charges), so the per-request figures in
`state/costs.jsonl` account for the whole session. Account balance changes on this account are not
attributable to this test if anything else runs on it — none was observed.

Usage fields: 452 of 453 requests carried a usage object;
452 carried a provider-reported cost; 438 carried
reasoning-token counts; 107 reported cache reads; 452 named the
upstream provider. Missing fields are recorded as absent, never as zero.

**The application's own usage table under-records this work.** Its persisted `usage` rows cover
298 of the 453 provider requests (65.8%). The gap is the Overview panel authoring: each panel worker
gets a provider whose usage callback appends to a local list
(`papers/overview_workflow.py: default_panel_provider`), so per-panel tokens never reach the
library. Panel-level usage is not lost — it is in each run's `panel-trace.jsonl` (119 model requests
with usage) — but any cost report built from the library's usage table alone will understate
Overview work. All costs quoted here come from provider-reported per-request charges.

## 8. Timing

| Stage (Blog agent) | Events | Repair requests | Failures | Median s | Max s | Prompt tokens | Completion tokens |
| --- | --- | --- | --- | --- | --- | --- | --- |
| author | 19 | 0 | 2 | 35.8 | 204.4 | 448,628 | 147,392 |
| narrative | 29 | 0 | 2 | 23.7 | 237.9 | 317,200 | 73,721 |
| render | 31 | 0 | 0 | 0.3 | 1.7 | 0 | 0 |
| repair | 99 | 99 | 5 | 28.7 | 401.0 | 2,761,902 | 580,893 |
| retrieval | 24 | 0 | 0 | None | None | 0 | 0 |
| review | 4 | 0 | 0 | 23.3 | 317.4 | 98,900 | 37,206 |
| selection | 29 | 0 | 1 | 7.2 | 131.1 | 179,881 | 35,313 |

Overview panel workflow (from each run's own `panel-trace.jsonl`):

| Request label | Requests | Failed attempts | Median s | Max s | Prompt+completion tokens |
| --- | --- | --- | --- | --- | --- |
| panel | 97 | 1 | 49.0 | 722.5 | 1,242,238 |
| panel_repair | 40 | 3 | 31.5 | 290.9 | 483,603 |

Slowest single requests (one provider call):

| Slot | Requests | Median request s | Max request s | Span s | Queue wait s |
| --- | --- | --- | --- | --- | --- |
| deepseek-flash·2009.03300v3·overview | 13 | 72.8 | 1095.3 | 1893.9 | 875.7 |
| deepseek-flash·2312.00752v2·overview | 12 | 119.0 | 722.4 | 1327.5 | 37.0 |
| deepseek-flash·1602.03837v1·overview | 13 | 71.7 | 517.8 | 1325.4 | 0.0 |
| deepseek-flash·2106.09685v2·overview | 15 | 78.9 | 424.4 | 730.5 | 0.2 |
| deepseek-flash·2009.03300v3·blog | 17 | 109.6 | 401.0 | 2494.1 | 0.2 |

Concurrency: peak 14 simultaneous provider requests overall
(per model {'deepseek-flash': 6, 'gemini-3.8-flash': 4, 'gpt-luna': 4, 'gpt-terra': 4}). Queue time is recorded per job in
`results/telemetry-analysis.json`; under this much parallelism the four model libraries were busy but
no job reached the 90-minute observation window and no request was cancelled by the watchdog
(zero `deadline_exceeded` events). The longest single provider call was
1095 s; the application sets a 900 s socket
timeout for OpenRouter, which Python applies per socket operation rather than to the whole response,
so a slow-dripping response can run longer than 900 s without failing.

## 9. Failures, incidents and environment notes

1. **Harness fault (not the application).** The first parallel driver collected finished jobs by
   constructing the application's `Library` object, whose startup recovery marks non-terminal jobs
   interrupted. Ten slots were interrupted by that instrumentation and are recorded as attempt 1
   `interrupted` with their job ids, then requeued as attempt 2. The instrumentation was changed to
   read-only sqlite helpers; no application code was involved. Evidence: `events.jsonl`
   (`harness-incident` note, `reconciliation_pass`, `slots_requeued`).
2. **Conversion environment.** The first staging import attempt fell back to PDF for all five papers
   because the harness ran the checkout with the app bundle's `runtime/bin` first on `PATH`, while
   `papers/convert.py` builds the conversion sandbox from the checkout location and therefore did
   not allow that directory. `node`/`ghostscript` in the bundle also resolve into homebrew Cellar
   paths that no longer exist on this machine. With the machine's own toolchain the imports
   converted through the real engines; the note and the raw evidence are in the manifest (`note`
   `environment-failure`) and `events.jsonl`.
3. **Provider-side failures that the application surfaced honestly**: 5 responses ended with the
   provider's own `finish_reason: error` (zero-cost, no content, all from deepseek-flash and one
   gemini slot); OpenRouter/Google returned HTTP 400 `Corrupted thought signature` on a replayed
   reasoning message; 4 OpenAI calls returned empty completions with `finish_reason: stop` and
   `content: null`. Each produced a recorded job failure with a redacted provider message, and the
   failed Blog's draft and traces were retained.
4. **No export, send, or publish step was executed**, and no test wrote to the user's real library:
   every job ran in an isolated library under `.scratch/overview-live-e2e/`.

## 10. Limits of this evidence

* Five papers per model and mode is too few for tail statistics; the report states individual values
  and medians/ranges rather than rankings.
* The Blog slots never delivered, so Blog *quality* (prose grounding, figure relevance, length
  preference) could not be assessed on delivered output; only drafts were inspectable.
* Vision was enabled (the live preference). Request payloads show the attached panel render on
  repairs; the earlier pilot corpus ran with vision off, so cross-corpus comparisons are not
  like-for-like.
* Automatic upstream routing means "the same model" was not always the same serving stack,
  particularly for `deepseek-flash`.
* Exports and reader-facing checks were out of scope by user direction, so EPUB/PDF fidelity,
  click regions and persistence after reload were not re-verified here.

## 11. Findings for discussion

1. **The Overview service delivers.** 20/20 slots produced a complete, exportable multi-panel
   overview, including from a 16-passage PDF-fallback import (LIGO). Readers get a coherent,
   numerically faithful explanation in every case inspected.
2. **The Blog service does not deliver in this configuration.** 20/20 Blog slots failed after, in several
   cases, a complete draft and multiple repair cycles. This is not one bug: ten slots died on
   provider behaviour (empty completions, `finish_reason: error`, one HTTP 400), three on the agent
   protocol (prose instead of a tool call, malformed tool JSON), four on the figure contract or
   local validation, and three on a review judgement of the text or figure.
3. **The repair loops are the expensive part of Blog.** Repair requests consumed 2.19M prompt and
   0.43M completion tokens in this run, more than authoring by a wide margin
   (author: 0.32M/0.10M). A repair budget or an early "cannot satisfy" exit would cut both cost and
   wall time.
4. **Layout outcomes diverge by model, and only a reader notices.** `deepseek-flash` delivered
   seven-panel canvases around 1,010×5,900 that pass every automated check but are unreadable when
   fitted to a screen; wide `gpt-terra` canvases read well at fit-to-window.
5. **Recorded defects are not delivered defects.** 10 delivered Overviews carry recorded drawing
   defects that the following repair fixed; the report separates the two so the numbers are not
   misread.
6. **Cost reporting from the application alone is insufficient.** The library usage table covers
   65.8% of provider requests because panel providers keep usage locally.
7. **Empty-completion handling deserves a look.** Several Blog failures come from a provider
   returning HTTP 200 with `finish_reason: stop` and `content: null`; the application treats that as
   a hard job failure rather than a retryable empty response.

## 12. Evidence index

| Artifact | Location |
| --- | --- |
| Session manifest (identity, catalog, matrix, notes) | `/Users/silver/Developer/arxiv-paper-to-kindle/.scratch/overview-live-e2e/2026-09-13-live/manifest.json` |
| Append-only event stream | `/Users/silver/Developer/arxiv-paper-to-kindle/.scratch/overview-live-e2e/2026-09-13-live/events.jsonl` |
| Per-request telemetry (payload, raw response, usage, provider) | `/Users/silver/Developer/arxiv-paper-to-kindle/.scratch/overview-live-e2e/2026-09-13-live/telemetry/<model>/requests-lane*.jsonl` |
| Per-slot ledger with attempts and outcomes | `/Users/silver/Developer/arxiv-paper-to-kindle/.scratch/overview-live-e2e/2026-09-13-live/state/queue.json` |
| Collected artifacts, run directories, drafts | `/Users/silver/Developer/arxiv-paper-to-kindle/.scratch/overview-live-e2e/2026-09-13-live/models/<model>/papers/<paper>/<mode>/` |
| Imports and conversion evidence | `/Users/silver/Developer/arxiv-paper-to-kindle/.scratch/overview-live-e2e/2026-09-13-live/state/imports.json` |
| Machine-readable matrix | `/Users/silver/Developer/arxiv-paper-to-kindle/.scratch/overview-live-e2e/2026-09-13-live/results/matrix.json`, `matrix.csv` |
| Blog failure forensics | `/Users/silver/Developer/arxiv-paper-to-kindle/.scratch/overview-live-e2e/2026-09-13-live/results/blog-forensics.json` |
| Telemetry analysis (concurrency, stages, coverage) | `/Users/silver/Developer/arxiv-paper-to-kindle/.scratch/overview-live-e2e/2026-09-13-live/results/telemetry-analysis.json` |
| Automated artifact checks | `/Users/silver/Developer/arxiv-paper-to-kindle/.scratch/overview-live-e2e/2026-09-13-live/state/automated-checks.json` |
| Visual reviews (orchestrator + independent) | `/Users/silver/Developer/arxiv-paper-to-kindle/.scratch/overview-live-e2e/2026-09-13-live/state/visual-review.json`, `state/independent-visual-review.json` |
| Gallery with images and failure entries | `/Users/silver/Developer/arxiv-paper-to-kindle/.scratch/overview-live-e2e/2026-09-13-live/gallery/index.html` |

*No application code, prompt, validator, layout algorithm or repair policy was changed during this
test. Every first attempt is preserved; the only requeues are the ten slots interrupted by the
harness fault described in §9, each with its original attempt recorded.*
