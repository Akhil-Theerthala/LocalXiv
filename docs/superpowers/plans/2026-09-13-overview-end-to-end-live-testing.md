# Overview and Blog live performance test plan

**Purpose:** Observe how the current application performs across five new-to-this-corpus papers, four models, and both Overview and Blog. Collect complete outcomes, costs, timings, and artifacts so the user can judge strengths and failures.

**Scope: testing only.** Keep all application code, prompts, validators, rendering, repair policies, and layout algorithms unchanged. Blog keeps its independent figure-generation path. There is no shared-panel migration, feature implementation, refactoring, or repair task in this plan. The Overview stretch cap remains 5%; do not impose its composition rules on independent Blog SVGs.

One orchestrating agent owns the test queue and records. It may use disposable scripts under the session's scratch directory to submit jobs, collect existing telemetry, and build the report. Those scripts are test instrumentation only, not application changes. Reviewers can inspect completed outputs independently. This document does not start live calls; execution begins when the user dispatches it.

## Test matrix

Run **5 papers × 4 models × 2 modes = 40 initial generation jobs**: 20 Overviews and 20 Blogs. Internal model requests, retries, reviews, and drawing repairs are additional measured activity, not separate matrix entries.

All four models must use **OpenRouter**, through `https://openrouter.ai/api/v1`, with the existing OpenRouter credential. No direct Gemini or DeepSeek endpoints.

| Requested model | OpenRouter model slug to resolve before execution |
| --- | --- |
| gemini-3.8-flash | Resolve the exact Gemini 3.8 Flash entry from OpenRouter's current model catalog |
| deepseek-flash | Resolve the exact DeepSeek Flash entry from OpenRouter's current model catalog |
| gpt-luna | Verify `openai/gpt-5.6-luna`, used in the existing live pilot |
| gpt-sol | Verify `openai/gpt-5.6-sol`, used in the existing live pilot |

Before paid generation, query OpenRouter's model catalog and record each exact slug, display name, context/output limits, supported parameters, and pricing. Save the catalog response with its retrieval time. Do not guess Gemini/DeepSeek slugs from their direct-provider identifiers. If an exact requested model is absent or ambiguous, mark its entries blocked and report the mismatch rather than choosing another model or endpoint. Record OpenRouter's returned model and upstream provider for each request when exposed; keep routing settings fixed and disclose automatic upstream routing.

Use the current supported settings and provider-specific reasoning behavior, recorded explicitly for every stage. Keep language, Blog length, vision setting, and other user-facing preferences fixed across the matrix. Do not force unsupported reasoning values or alter prompts to make providers look comparable. Record any unavoidable provider differences. If supported stage overrides would route a request to a different model, resolve that before launch using existing settings and disclose the effective configuration.

Keep the real library and installed app untouched. Use isolated test libraries with `auto_summary=False` and `auto_send=False`. No sending to Kindle/Mail, publishing, pushing, or installing a new app build. Credentials stay in the existing key mechanism; secrets are excluded from logs.

## Five-paper cohort

These versioned papers were checked against arXiv on 2026-09-13. None of their base IDs appears in the previous `.scratch/overview-rebuild/live/runs` records. “New” means new to that evaluation corpus, not newly published. The test rationale is our coverage choice; it is not a claim about the generated panel layout.

| Order | Paper and exact version | What to inspect |
| --- | --- | --- |
| 1 | [LoRA: Low-Rank Adaptation of Large Language Models, 2106.09685v2](https://arxiv.org/abs/2106.09685v2) | First smoke case. Whether a compact mathematical mechanism becomes an intuitive visual explanation and whether benchmark qualifiers survive. |
| 2 | [Mamba: Linear-Time Sequence Modeling with Selective State Spaces, 2312.00752v2](https://arxiv.org/abs/2312.00752v2) | Architecture and sequence-processing relationships; long labels, connectors, and the distinction between mechanism and performance evidence. |
| 3 | [A Gentle Introduction to Conformal Prediction and Distribution-Free Uncertainty Quantification, 2107.07511v6](https://arxiv.org/abs/2107.07511v6) | Long tutorial with equations and examples. Preserve assumptions and the scope of coverage guarantees; teach a coherent subset rather than compress every section. |
| 4 | [Measuring Massive Multitask Language Understanding, 2009.03300v3](https://arxiv.org/abs/2009.03300v3) | Benchmark-heavy content, numerical comparisons, scope, and limitations. Separate the paper's reported model results from later knowledge. |
| 5 | [Observation of Gravitational Waves from a Binary Black Hole Merger, 1602.03837v1](https://arxiv.org/abs/1602.03837v1) | A non-ML observational paper, physical units, uncertainty ranges, and evidence versus interpretation. |

Recheck novelty against any newer test records before execution. If a paper is unavailable or fails import, record that outcome in its slot. Do not quietly replace it with an easier case. A replacement cohort member requires an explicit recorded decision before another paid attempt.

## 1. Prepare and identify the tested candidate

- [ ] Read [previous observations](../../verification/overview-rebuild-observations.md) for known failure patterns, and [layout verification](../../verification/2026-09-13-overview-edge-alignment.md) for the settled Overview behavior. Treat observations as prior evidence, not instructions to repair anything.
- [ ] Record `HEAD`, tracked diff digest, prompt revisions, and SHA-256 values for runtime source files, including untracked modules. Record renderer/runtime versions and dependency availability. Recheck code identity before each model batch. A dirty checkout is acceptable when its complete identity is captured and held fixed.
- [ ] Create `.scratch/overview-live-e2e/<session>/manifest.json`, `events.jsonl`, `results.json`, and `models/<model>/papers/<paper-id>/<mode>/`. Keep a distinct application library/server per model, so one model's saved generation cannot overwrite or become a reference for another's.
- [ ] Import the five exact paper versions through the real application import path into a clean staging library. Record acquisition, conversion, evidence coverage, and reader warnings. Clone only these imported paper assets and metadata into the model libraries before any generation; keep identical document digests across models and fresh generation/job state. Existing sample papers are outside the test cohort.
- [ ] Resolve keys without printing them. Save sanitized settings, requested models, endpoint identities, execution scope, and the 40 matrix entries in the manifest. Verify native rendering and exports locally before spending on generation. Use the authorized native WebKit execution environment; sandbox hangs must be labeled as environment failures.
- [ ] Reuse existing offline tests only where needed to confirm the environment. Do not turn preflight into a new test-suite implementation or broad code audit. If telemetry needs collection, use existing persisted run files, usage records, and non-mutating external collection; report fields that the application does not expose.

**Done:** The candidate and documents are identifiable, model configurations are explicit, isolated servers work, and every planned matrix entry exists in the manifest.

## 2. Execute the existing application paths

Use authenticated loopback application APIs or their existing application job methods. Do not bypass persistence by calling a model directly. `app/server.py` is the API reference; the old scratch pilot is a reference for logging fields, not a replacement for application-level testing.

| Operation | Existing API |
| --- | --- |
| Import | `POST /api/import` with `{"url": versioned_url}` |
| Poll jobs | `GET /api/state`, match the accepted job ID |
| Generate Overview | `POST /api/papers/<id>/bento` with `{}` |
| Generate Blog | `POST /api/papers/<id>/summary` with `{}` |
| Read saved outputs | `GET /api/papers/<id>`; `bento` is Overview and `overview` is Blog |
| Export | `POST /api/papers/<id>/export` with `kind` and `profile` |
| Cancel | `POST /api/jobs/<job-id>/cancel` |

- [ ] Start with the paired LoRA case for each model to confirm execution and recording. A weak or failed output is data, not a reason to stop the remaining papers. Pause only the affected model for credential/quota/configuration failures; continue other models when their environment is sound.
- [ ] For four papers, generate Overview then Blog within that model's own library. For the conformal tutorial, generate Blog first, without a saved Overview, then Overview. Use this same order for every model. This covers standalone Blog behavior without extra paid jobs.
- [ ] A failed Overview does not prevent Blog generation when imported evidence is usable. Record whether each Blog actually had an Overview reference available. Compare like-for-like reference conditions in the report.
- [ ] Run one generation job at a time per model. Up to two isolated model workers may run concurrently; retain existing internal panel concurrency. Record overlap and queue time so resource contention is visible. Keep native rendering within available local capacity.
- [ ] Persist each accepted job ID immediately. Resume by reconciling saved IDs and terminal states, never by blindly reposting a request. Record ambiguous submissions as needing reconciliation. Preserve failures and partial artifacts.
- [ ] Allow production retries and repairs to occur unchanged and count every attempt. Make no automatic full-job reruns to improve scores. Any later authorized rerun gets a separate attempt record and never replaces the original result.

**Done:** Every one of the 40 slots has a terminal outcome or a specific blocked/not-run reason. Slow, poor, reduced, or failed outputs remain in the matrix.

## 3. Use relaxed observation windows

These are external monitoring limits, not latency targets or new production timeouts.

| Operation | Observation window |
| --- | --- |
| Import/conversion | 60 minutes per paper |
| Overview or Blog generation | 90 minutes per job |
| Local export | 20 minutes per artifact |
| No visible progress | After 20 minutes, capture a diagnostic snapshot and continue observing |

- Poll periodically, about every 15–30 seconds, and retain stage changes and periodic heartbeats. Silence alone is not evidence of failure: reasoning or a provider request may still be running.
- At a generation deadline, if logs show active progress or an in-flight request, allow one additional 30-minute observation period and record the extension. Otherwise request cancellation. Give cancellation five minutes to settle before terminating only the session-owned server process if necessary. Reconcile persisted state before continuing.
- Preserve existing application/provider request timeouts. If a shorter built-in timeout ends a request, record its actual value and resulting retry/failure; do not patch it or disguise the failure as an external-watchdog timeout. Supported timeout configuration may be documented, but keep the tested configuration fixed.
- There is no short batch wall-clock cutoff. Resume across orchestration turns as needed. Monitor billed spend and any user-specified spending ceiling; a ceiling or exhausted balance stops new paid requests, with remaining slots recorded explicitly. Do not invent a dollar budget or assume unknown usage is free.
- A timed-out in-flight call may still be billed. Preserve request IDs for later reconciliation and distinguish provider timeout, application timeout, operator cancellation, and external watchdog expiry.

## 4. Log all observable execution and cost data

Write incremental structured records and preserve the underlying local artifacts. Keep an append-only event stream and atomically refreshed summary so interrupted runs remain inspectable.

| Group | Required fields/artifacts |
| --- | --- |
| Identity | Session, exact paper/version and document digest, model alias and returned identifier, endpoint, mode, job/run/request IDs, code hashes, prompt revisions, sanitized settings |
| Timing | UTC start/end, monotonic durations, queue wait, stage boundaries, each request latency, provider first-response timing if exposed, retries/backoff, drawing/render/export durations, concurrent-request windows, last observed progress |
| Requests | Stage and panel/figure ID where applicable, attempt number, request options, available prompt/request payloads, returned text/tool calls and metadata, HTTP status, finish reason, error/traceback, rate-limit metadata if exposed |
| Usage | Input/output/total tokens, cached input/cache-write tokens, reasoning tokens, provider usage object, whether counts include retries, and which fields are unavailable |
| Cost | Actual provider-reported billed amount and currency per request when available; otherwise a separately labeled estimate with pricing URL, retrieval date, model/endpoint, input/output/cache rates, and calculation |
| Workflow | Selection/narrative/author/review outcomes, planner reduction reasons, panel/figure count, created/repaired/simplified outcomes, validation failures, repair decisions, accepted and rejected candidate identities |
| Artifacts | Imported evidence, narrative/briefs, original panel and Blog figure sources, full Blog text, final SVG/PNG/PDF/HTML, arrangement and native checks, exported EPUBs and EPUBCheck output, screenshots, failed drafts and terminal run records |
| Quality | Separate delivery, factual accuracy, intuitive explanation, visual legibility, reader interaction, and export verdicts with specific evidence |

“Log everything” means all observable application/provider data, not credentials or hidden model internals. Redact API keys, authorization headers, session tokens, signed URLs, and sensitive account metadata before writing logs. Preserve model-emitted content and exposed reasoning-token counts; do not request hidden chain-of-thought. If full prompts/responses are not exposed by existing instrumentation, record that coverage gap rather than changing production code or claiming complete traces.

Reconcile application usage with OpenRouter generation/request records and reported costs when available. Preserve OpenRouter request IDs for that reconciliation. Avoid counting the same request twice through callbacks and persisted events. Reasoning and cache tokens may be subsets of other fields; retain raw usage and follow that provider's definitions rather than adding every field together. Missing numbers remain `null`/unknown, never zero. Refresh official pricing at execution time for the exact endpoint, using OpenRouter rates for all four models. Keep estimates separate from actual charges. Account-wide balance changes are context, not attributable cost if other workloads share the account.

## 5. Inspect Overview and Blog independently

- [ ] Open every completed Overview and Blog in its model's app library. Refresh/reopen and verify persistence, citations, figure markers, images, and captions. Check Overview panel click regions against final frames.
- [ ] Inspect images at fit-to-window and readable zoom, and Blog images at their actual inline display size. Record overlap, clipping, unreadable labels, excessive empty space, distorted shapes/text, and broken connectors. Native checks do not replace visual inspection.
- [ ] For Overview, observe the existing panel order, safety limits, layout outcomes, and 5% stretch bound. For Blog, evaluate its independent SVG/HTML figure behavior under its existing contract. Do not require Blog to use Overview's layout or authoring algorithm, or mark that architectural difference as a defect.
- [ ] Read each Blog's full narrative and assess section flow, specialist-term explanations, figure relevance, repetition, source citations, and length/language preferences. A zero-figure Blog is a recorded outcome, not grounds to force generation; state any gap in image coverage.
- [ ] Ground scientific claims against the actual imported passages: numbers, units, equations, comparison settings, uncertainty, and limitations. Capture supporting passage IDs or source sections and examples of misleading or unsupported claims. Apply a tutorial-appropriate standard to the conformal paper.
- [ ] Export Overview PNG/PDF/Kindle EPUB/semantic EPUB; Blog PDF/Kindle EPUB/semantic EPUB; and paper-plus-Blog EPUBs for EPUB paper imports. Verify supported exports visually and with EPUBCheck. Blog whole-post PNG and combined PDF are not supported routes. For PDF-only imports, test separate paper PDF and Blog exports and record combined EPUB as unsupported.
- [ ] For failures, capture what the user sees, whether loading ends, which stage failed, retained drafts, and whether the paper and other saved outputs remain accessible. Do not inject extra paid failures; use existing offline evidence for cancellation/preservation behavior not observed naturally.

**Done:** Each output has a recorded quality assessment, artifacts, and export status. Delivery success and scientific/visual quality are separate; one mode cannot mask the other's failures.

## 6. Produce an observational report and gallery

- [ ] Build a gallery under the session directory with all 20 paper/model pairs, both modes, full Blog reader links, images, exports, and visible failure entries.
- [ ] Write `docs/verification/2026-09-13-overview-blog-live-performance.md` and machine-readable JSON/CSV. Include the complete 40-row generation matrix plus per-model/per-mode summaries.
- [ ] Summarize success, failure, interruption, and blocked counts; stage latency and total time; tokens and actual/estimated costs; repair/reduction rates; and factual/visual/export outcomes. With only five papers per model/mode, show individual values and median/range rather than treating tail percentiles or rankings as reliable statistics.
- [ ] Report total spend including failed attempts, cost per delivered output, and cost per quality-accepted output. Show standalone versus Overview-informed Blog results separately, and combined Overview-plus-Blog cost per paper where both ran. Explain missing cost/usage coverage.
- [ ] Group issues by observed stage and impact, with artifact paths and reproducible evidence. End with overall strengths, limitations, and a short list of findings for discussion. Do not fix, optimize, migrate, or retune anything during this evaluation.

**Completion means a complete account of performance, not all-green results.** Keep the frozen code and every first attempt intact. No new release or implementation work is part of this plan.

## Suggested dispatch

“Run this testing-only plan on the five pinned papers with gemini-3.8-flash, deepseek-flash, gpt-luna, and gpt-sol, all through OpenRouter, covering both Overview and Blog. Keep their current generation paths independent and application code unchanged. Use the relaxed observation windows, log all observable requests, timings, usage, costs, outputs, and failures, and finish with the full matrix, gallery, and overall assessment.”
