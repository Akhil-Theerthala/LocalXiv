# Overview efficiency implementation

The selective Overview workflow is implemented in the source checkout. Import no longer triggers model reading; the application builds a local source map, lets the model select evidence, retrieves only the selected IDs, accepts a grounded narrative, authors a structured scene, and reviews the exact rendered candidate. Focused, wider, UI, extension, native-render, and EPUB checks pass.

Fresh live Attention runs did not produce an approved Overview. Gemini and DeepSeek remained over the page-height and reading-size gates, Luna repeated an invalid repair, and GLM exceeded the diagnostic deadline during narrative planning. The method and survey trials were therefore not run. Groq was excluded from further live work at the user's request. This report does not claim release readiness or general model compliance.

## Scope and starting state

This work changes the repository checkout only. It did not modify `/Applications/LocalXiv.app`, send a document, install, commit, push, publish, or release. `.env` was preserved and its values were never written to traces or this report.

The starting tracked diff contained 344 insertions and 56 deletions. The recorded starting status was:

```text
 M CONTEXT.md
 M docs/development.md
 M papers/HTMLSnapshot.swift
 M papers/agent_overviews.py
 M papers/ai.py
 M papers/explanation.py
 M papers/reading.py
 M tests/test_agent_overviews.py
 M tests/test_ai.py
 M tests/test_library.py
?? .env
?? docs/adr/
?? docs/verification/2026-09-12-live-structured-overviews.md
?? docs/verification/2026-09-12-overview-efficiency-audit.md
?? docs/verification/2026-09-12-structured-overview-and-reading.md
?? docs/workflow_plan.md
?? papers/overview-examples.json
?? papers/overview_scene.py
?? papers/prototypes/structured_overview.py
?? tests/test_overview_scene.py
?? tests/test_reading_bibliography.py
```

Before changing workflow behavior, `tests.test_agent_overviews tests.test_ai` ran 38 tests. The restricted sandbox produced one loopback `PermissionError`; normal macOS execution passed all 38 with one opt-in Keychain skip in 1.042 seconds.

## Implemented boundaries

| Boundary | Result |
| --- | --- |
| Import and reading | Import queues only an enabled automatic Overview. A legacy `reading` job builds local orientation without credentials or a provider. `prepare_reading`, `shared_reading`, and reading batches are removed. |
| Orientation and retrieval | `reading-v5-selective` keeps the original paper identity, extracts an honest abstract and complete section/page map, excludes bibliography evidence, preserves appendices, and loads only selected safe local images. Large maps use explicit paging. |
| Staged generation | The normal path is selection → narrative → author → review. The accepted plan and digest precede drawing. Supplemental evidence and narrative revision remain explicit exceptional paths. |
| Structured scenes | Per-kind closed schemas and local validation share one field definition. Lane titles/captions are legal, connector limits are advertised, independent errors are aggregated, and unknown fields are rejected. |
| Counts and layout | Authored visible strings are counted once before compilation. Numeric and Latin tokens stay intact, CJK can break legally, and insufficient width yields a measured `layout_fit` issue. |
| Repair state | Atomic `generation_context.json` checkpoints retain selection, evidence, accepted narrative, candidate digest, issues, decisions, and progress. Figure repair requires the current digest and exact issue IDs. |
| Failure behavior | Malformed tool JSON receives one in-stage correction. Repeated content, cycles, unchanged mechanical failures, and unchanged tool actions stop with the draft retained. Provider failures remain terminal. |
| Compatibility | Blog remains independent, may adapt a valid saved Overview without copying it, and uses broader selective retrieval. Existing generations and exports remain readable. |
| Diagnostics | One sanitized trace distinguishes model requests from local retrieval/render operations and records stage, usage, elapsed time, attachments, digest, and issue codes without request bodies or private reasoning. |

The implementation uses the existing modules and runtime. It adds no embedding service, vector store, orchestration framework, provider switch, or production request cap.

## Offline and artifact verification

`tests/fixtures/overview_efficiency.json` contains seven sanitized regressions: cross-kind flow fields, lane title/caption, connector length, a one-panel connected row, trailing JSON, authored-word counting, and the `512` wrap failure.

The final commands and results were:

| Check | Result |
| --- | --- |
| Focused Python suites | 86 passed, 1 opt-in skip, 6.584 s |
| Wider Python regression | 57 passed, 37.561 s |
| App UI JavaScript | Passed |
| Extension JavaScript | 63/63 passed |
| Python compilation | Passed |
| `git diff --check` | Passed |

The native WebKit renderer must run outside the restricted sandbox. An attempted sandbox run timed out in the renderer; the same focused suite passed under normal macOS execution.

The production compiler rendered and human-inspected all three reference explanations at a 640 px reading width:

| Example | Type | Native size | Minimum label | Native issues | Human check |
| --- | --- | ---: | ---: | ---: | --- |
| D | Architecture | 960 × 959 | 14 px | 0 | `512` remains intact; arrows, grouping, order, and caption are clear. |
| E | Survey | 960 × 930 | 14 px | 0 | The four-family comparison and synthesis remain readable. |
| F | Method | 960 × 774 | 14 px | 0 | The question, retained candidates, arithmetic, and interpretation remain connected. |

Artifacts: [review page](../../.scratch/overview-efficiency-implementation/examples/index.html), [native manifest](../../.scratch/overview-efficiency-implementation/examples/manifest.json), and [Kindle EPUB](../../.scratch/overview-efficiency-implementation/examples/bento.epub). The EPUB is 377,685 bytes; EPUBCheck 3.3 reported zero fatal errors, errors, warnings, or infos for both generated profiles. No delivery was attempted.

## Live contract gate

The four retained providers below accepted the exported structured tool contract. These were minimal schema requests, not generation-quality approvals.

| Provider/model | Contract result | Elapsed | Reported total tokens |
| --- | --- | ---: | ---: |
| Gemini `gemini-3.8-flash` | Passed | 3.276 s | 2,491 |
| OpenRouter `openai/gpt-5.6-luna` | Passed | 4.644 s | 1,685 |
| DeepSeek `deepseek-flash` | Passed | 1.491 s | 3,017 |
| OpenRouter `z-ai/glm-5.3-flash` | Passed | 1.736 s | 2,751 |
| Groq `openai/gpt-oss-120b` | Excluded from further work | — | — |

Groq had already exposed an outer `candidate` wrapper mismatch. A narrow provider-boundary adapter flattened that wrapper for the request and restored it locally; one isolated retry accepted the schema. The user then asked to ignore Groq, so this result is not counted as a full provider gate and no further Groq request was run. Raw gate records are in [schema-gates.json](../../.scratch/overview-efficiency-implementation/live/schema-gates.json) and [groq-boundary-retry/schema-gates.json](../../.scratch/overview-efficiency-implementation/live/groq-boundary-retry/schema-gates.json).

## Fresh Attention architecture gate

The final run used paper `1706.03762v7`, no reading-note cache, `smolagents-selective-staged-v1`, `reading-v5-selective`, `overview-scene-v2`, vision where supported, and the configured provider/model pair. Counts below are completed HTTP model requests. The trial ceiling is diagnostic only; production has no fixed request limit.

| Provider | Completed requests by stage | Local retrieval | Reported usage | Elapsed | Outcome |
| --- | --- | --- | --- | ---: | --- |
| Gemini | 1 selection, 3 narrative, 1 author, 7 repair | 44 passages, 3 images | 171,473 prompt; 13,772 completion; 187,615 total | 80.14 s | Failed after 12 completed requests. Final draft was 960 × 1,173 and did not reach review. |
| Luna | 1 selection, 1 narrative, 1 author, 3 repair | 53 passages, 3 images | 93,873 prompt; 7,260 completion; 101,133 total | 78.62 s | Stopped on an unchanged repair. The 456-word, single-panel-connected candidate never rendered. |
| DeepSeek | 1 selection, 5 narrative, 1 author, 5 repair | 79 passages, 4 images; two later reads added nothing | 193,878 prompt; 55,666 completion; 249,544 total | 251.33 s | Failed after 12 completed requests. Final draft was 960 × 1,087 and did not reach review. |
| GLM | 1 selection, 1 completed narrative; a second narrative request was cancelled | 71 passages, 3 images | 13,706 prompt; 91,494 completion; 105,200 total for completed requests | More than 791 s | Incomplete. Its first narrative response took 641.605 s, so the case exceeded the plan's 600-second deadline before authoring. |
| Groq | Not run to an architecture outcome | — | — | — | Excluded at the user's request. One selection request completed before cancellation and is not treated as a result. |

The harness used a 12-request/1,200-second guard while mechanical fixes were being frozen; this was broader than the plan's 10-request/600-second diagnostic bound. Gemini and DeepSeek are therefore reported as failures at 12 requests, not as compliant 10-request trials. GLM was manually stopped once its completed narrative request had already crossed 600 seconds. No production limits changed.

The live matrix stopped at its architecture gate:

| Paper type | Gemini | Luna | DeepSeek | GLM | Groq |
| --- | --- | --- | --- | --- | --- |
| Architecture / Attention | Failed | Failed | Failed | Incomplete | Excluded |
| Method / PRO | Not run after gate failure | Not run after gate failure | Not run after gate failure | Not run after gate failure | Excluded |
| Survey / UQ | Not run after gate failure | Not run after gate failure | Not run after gate failure | Not run after gate failure | Excluded |

No bibliography passage ID appeared in any recorded provider context.

## Human inspection and repair audit

Gemini's final draft is structured and readable at full size, but native checks found a 1,173 px page and 12.4 px labels at 640 px reading width. It also says scaling by `1/√d_k` “prevents small gradients”; the paper makes the narrower claim that scaling counters large dot products that push softmax into regions with extremely small gradients. The closing claim that constant sequential depth enables both fast training and top BLEU also compresses association into causation. The draft is not scientifically approved. [Gemini PNG](../../.scratch/structured-live-2026-09-12/selective-implementation-final-attention/gemini/1706.03762v7/reader/overview-figures/1e4f614809324a83a0cdc003f9a933c7/fig1.png)

Gemini recorded seven repair decisions. They corrected measured issues in sequence, but one width repair introduced unsupported `scene.title`, word and width failures alternated, and the final edit exposed the unresolved height failure. Claims such as “well below” the word limit were not trusted: application validation measured 194 and later 185 words and kept repairing.

DeepSeek's final draft is source-aligned and clearer than Gemini's at full size. It distinguishes recurrence, one-query attention, eight heads, encoder/decoder reuse, illustrative weights, and the 28.4 BLEU finding. Native checks still found a 1,087 px page and 13.4 px labels at 640 px, so it is not deliverable. [DeepSeek PNG](../../.scratch/structured-live-2026-09-12/selective-implementation-final-attention/deepseek/1706.03762v7/reader/overview-figures/8d0b4cf1e8b34b18837738054d8f66c7/fig1.png)

DeepSeek recorded five repair decisions. Recomposition first traded height for a measured width failure; redistribution fixed width but left a 1,281 px page; the final focused trim improved height to 1,087 px. One repair requested already-present evidence for a layout problem and retrieved nothing new, exactly the unnecessary-read behavior the trace is meant to expose.

Luna never produced a native artifact. The application aggregated both defects—`connect=true` on a one-panel row and 456 authored words against 180—and stopped after the model repeated an unchanged invalid tool action. GLM selected 12 sections, 7 direct passages, and all 6 figures, expanding to 71 of 84 retained passages; this was not selective enough for the task even before its narrative delay.

Full sanitized traces, saved contexts, decisions, and failed drafts are under [selective-implementation-final-attention](../../.scratch/structured-live-2026-09-12/selective-implementation-final-attention/).

## Remaining limits

- No live model produced an approved Overview, so live narrative, renderer, reviewer, and persistence acceptance is still open.
- The models selected 44–79 of 84 retained Attention passages. The workflow prevents automatic whole-paper reading, but this single run does not establish lower live token use. A general hard selection cap was not added because it could remove necessary evidence; the trace makes over-selection measurable.
- The live sample is one architecture paper per attempted provider. It does not establish latency percentiles, provider rankings, the three-paper matrix, or release readiness.
- PDF bibliography filtering remains marker- and extraction-order-dependent. Missing or unsupported original images are reported rather than treated as visually inspected.
- The broader frozen 100-plus-paper, per-content-type semantic-retention and layout gate remains outside this implementation evidence.

The source implementation is complete at the requested workflow boundary. The failed live gate is retained as evidence rather than weakened to make a provider pass.
