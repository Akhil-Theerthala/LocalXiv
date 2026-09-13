# Overview call and repair audit

This audit replays the saved live submissions against local validators and examines recorded provider calls. It makes no new paid API calls and does not change the production generation flow. Its purpose is to identify what to remove before another model trial.

## What the structured renderer actually removed

The application owns SVG coordinates, arrow routing, fonts and wrapping. Models still select scene rows, panel types, relative widths, connections and content. We therefore removed drawing-code authoring, but did not remove structure selection. No controlled before/after experiment established a latency improvement over raw SVG.

The renderer can turn valid scene data into a static page. Most observed failures happened before native rendering, because the content contract was unclear or a plan/scene exceeded its bounds. Some layouts then passed native checks while failing the intended narrative.

## Measured waste

The corrected Attention runs reused reading notes, so their counts isolate planning/authoring costs from whole-paper reading.

| Evidence | Observation | Implication |
| --- | --- | --- |
| Gemini, corrected Attention | 30 requests: 2 planning, 27 authoring, 1 review. Tools included 13 `diagram_reference` calls and 12 candidate submissions. | Fresh repair sessions repeatedly pay to reload the same reference. |
| Gemini candidate replay | Of 12 submissions, 7 failed the visible-word limit, 2 failed connector-label length, 1 omitted branches, and 2 passed local content checks. Those two then reached native layout/review checks. | Most repair traffic was mechanical, before substantive review. |
| Luna, corrected Attention | Eight candidate submissions. Seven included unsupported fields on a flow panel; one failed a one-panel connected-row check first. No candidate reached native rendering. | The provider schema exposes all panel fields, while the application accepts only those belonging to the chosen kind. |
| DeepSeek, corrected Attention | Fourteen submission calls. Six had malformed JSON with trailing data; four were rejected for lane titles/captions; two failed connector-label length; two passed local content checks. | Protocol/contract issues consumed most attempts before scientific review. |
| Repeated plan output | The plan averaged 58.8% of Gemini's and 71.4% of DeepSeek's parseable candidate JSON by character count. Luna's average was 29.0%, alongside large irrelevant scene fields. | Every visual repair unnecessarily regenerates a substantial already-approved plan. These are character ratios, not token or cost ratios. |
| Initial Luna planning | 25 submitted plans: 24 failed the visual-focus length limit, one failed relationship count. | Previously unstated limits caused a long loop. The last iteration already added those limits to the schema and prompt. |
| Word counting | A Gemini candidate with 189 authored words counted as 206 after SVG wrapping; another with 182 counted as 199. The hidden SVG title also contributes two words. | The model is asked to satisfy a word count that changes after rendering. These examples were already too long, but the reported overage was inflated. |

DeepSeek's final review failed on the explicit JSON instruction requirement, already corrected in the previous iteration. Its isolated review retry then rejected the explanation. Gemini's final PRO candidate passed provider review but omitted the coastline question and the beginner explanation of surprise. Reducing mechanical retries must not weaken those substantive checks.

## Reading costs

Attention was divided into three reading batches followed by a synthesis call. PRO had four batches and a synthesis. Each later batch included earlier notes; planning, authoring and every fresh repair then received the collected notes again.

| Initial Attention run | Reading calls | Recorded reading time | Recorded input tokens | Recorded output tokens |
| --- | ---: | ---: | ---: | ---: |
| Gemini | 4 | 33.9 s | 28,889 | 6,389 |
| Luna | 4 | 52.4 s | 24,695 | 5,585 |
| DeepSeek | 4 | 82.2 s | 20,385 | 19,313 |
| GLM | 4 | 487.4 s | 27,811 | 62,812 |

Output counts are provider-reported completion usage and can include reasoning. They should not be interpreted as visible note lengths. GLM's longest reading response took 329.7 seconds. Groq's later rate-limit experiment showed a reading request requiring 8,660 tokens against its 8,000-token account limit.

Selective reading will remove a real cost. It will not by itself repair the panel contract or stop repeated layout-reference calls.

## Proposed reading flow

Build the initial orientation locally, without an LLM call:

- Actual abstract text, retaining passage IDs. Do not assume every passage assigned to the Abstract chapter is abstract prose: the retained Attention chapter also contains a permission statement and author notes.
- All section/subsection titles and retrievable IDs, including appendices. Do not omit appendices merely because they follow references.
- Figure/table locations with short captions and IDs. Load original image content only when selected.
- Retrieval size information so a selection can avoid account-size problems. For PDFs with weak structure, state that the index is page-based instead of inventing headings.

Then use the model to select evidence according to the task:

- Architecture: mechanism and architecture sections/figures, with the specific results and limitations needed for the Overview's claims.
- Methodology: the worked problem, method, relevant figures, and supporting evaluation/qualification. Introduction and related work are optional unless needed to explain the contribution or comparison.
- Survey: taxonomy, representative methods, comparison/discussion and synthesis. Its evidence selection will span more sections than an individual method paper.
- Blog: start from the same local map but retrieve more motivation and related work when the narrative needs them, together with methods, results and relevant appendix material.

The abstract is a navigation aid and contribution summary, not sufficient evidence for detailed mechanics, numerical results or limitations. The model can request another section when the initial selection leaves a gap. Requests should retrieve several related sections/passages/figures together, not one fragment per call.

Change both entry points: `papers.ai.prepare_reading()` currently reads the whole paper, and `app.server` queues that reading after import when AI is configured. Bypassing full reading only inside Overview generation would leave the import-time cost intact. Existing full-paper notes should not be injected wholesale into a selective run simply because a cache exists. Preserve the complete retained paper and the bibliography-filtered retrieval boundary.

A successful uncomplicated path can target three model calls: choose evidence from the abstract/map; author the explanation from retrieved evidence; review the explanation. Local indexing, retrieval, validation and rendering do not need separate model calls. Additional evidence or corrections may require more calls. This is a design target, not a measured performance result.

## Repair changes in priority order

1. **Carry stable context across repairs.** Insert the relevant composition reference once, without a tool-fetch round on every restart. Keep the accepted plan and selected source evidence in application state. Ask for the changed scene/panel, not a regenerated full plan, unless new evidence actually changes the explanation.
2. **Make the tool contract match the validator.** Each panel kind should advertise only its permitted fields. Do not send one object with every kind's optional fields and reject their use later. Lane titles/captions deserve special attention: the compiler already renders these common fields, but the validator currently forbids them. Connector-label constraints should be stated in the contract rather than revealed after submission.
3. **Return useful corrections together.** Report all applicable field errors and actual authored word counts in one local validation pass. Count authored visible content, excluding hidden SVG titles and line-break fragments. Tell the model the overage and the affected panel. Do not discard unsupported fields silently when doing so could remove intended explanation.
4. **Keep geometry work in the renderer.** It should allocate enough width for numbers such as `512`, not split them into `51` and `2` and request an LLM rewrite. Layout adjustments must preserve flow direction and grouping. If content cannot fit without changing meaning, request a focused content change instead of shrinking labels.
5. **Review the story that was selected.** Check that a beginner can follow the example and transitions, that claims are supported, and that omissions do not teach the wrong process. Do not require an exhaustive architecture inside a 180-word Overview. Distinguish a missing explanation from a deliberate, clearly indicated omission.
6. **Detect lack of repair progress.** The current guard catches an identical candidate, but a changed sentence can restart the same failure indefinitely. Track whether the reported problem improves, such as fewer unsupported fields or a decreasing word overage. Stop an unproductive loop while preserving its draft.

These changes preserve composition freedom. The model chooses what story to tell and which supported relationships matter; the application exposes compatible visual blocks and handles their physical arrangement. A fixed identical page for every paper is not required.

## Verification for the next iteration

Use the saved failed scenes as an offline regression corpus first: panel-field mismatches, lane headings/captions, broken numeric labels, inflated word counts, repeated reference retrieval and unnecessary plan output. Add payload tests proving that initial context contains the abstract/map rather than body sections, selected retrieval excludes bibliography, appendices remain discoverable, and unselected images are not attached.

Only then run a small live comparison on the same papers/models. Report cold-reading calls, retrieval calls, authoring/repair calls, review calls, tokens and elapsed time separately. Independently inspect the output. A smaller call count is not a success if the scene drops the explanation the user needs.

Replay data and script: `.scratch/overview-efficiency-audit/results.json` and `.scratch/overview-efficiency-audit/audit.py`. Source traces: `.scratch/structured-live-2026-09-12/`. The replay uses current local content validators; it does not rerun native rendering or replace the recorded native/reviewer outcomes.
