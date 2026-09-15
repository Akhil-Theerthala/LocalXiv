# Blog workflow update implementation plan

> **For agentic workers:** Use `superpowers:executing-plans` to implement this plan task by task. Use `superpowers:subagent-driven-development` only if delegation is requested for implementation. Steps use checkboxes for tracking.

**Goal:** Deliver readable, grounded Blogs using Overview's directed reading and panel-authoring structure, aiming for usable focused figures within two or three attempts and allowing four before coherent omission.

**Architecture:** Keep the existing Blog prose and review coordinator in `papers/agent_overviews.py`. Reuse `papers/reading.py` and the individual drawing functions in `papers/panel_authoring.py`, with one small `papers/blog_figures.py` module owning Blog figure state and omission edits. Render figures at article width and publish only accepted assets after final article review.

**Tech stack:** Existing Python, standard-library XML/JSON, provider adapter and smolagents prose stages, native Swift/WebKit renderer, current reader/export code. No new dependency.

**Spec:** [Agreed Blog design](../specs/2026-09-14-blog-workflow-update-design.md), plus Blog definitions in [CONTEXT.md](../../../CONTEXT.md).

## Global constraints

- This document is a plan. Do not implement, call paid providers, commit, install, or publish as part of writing it.
- Preserve the existing worktree changes in `papers/html_figures.py`, `papers/overview_workflow.py`, `papers/edge_align.py`, `papers/mixed_fit.py`, and related tests/reports. Recheck the checkout before implementation; do not overwrite or stage unrelated work.
- Keep the existing prose generator, language preference, and length keys `short`, `medium`, `large`, with maxima 1000, 1400, and 2600 words respectively.
- Use abstract-directed selective reading with bibliography filtering at every provider boundary. General background may explain concepts but cannot establish paper-specific claims.
- Keep zero to three planned figures. Each has one focused visual purpose, a detailed brief, a broad layout idea, relevant SVG examples, and a stable ID. The drawing author supplies SVG; the application owns the surrounding article and assets.
- Target usable figures within two or three attempts, ideally one. Allow at most four drawing requests per figure over the whole run: creation plus up to three corrections. No counter reset after review or omission.
- Check new figures at 640px displayed width with a 14px minimum label size. Preserve SVG safety and native geometry checks.
- After four unsuccessful attempts, omit the figure and clean its dependent article text. Omission is recovery, not the figure-generation success criterion. Never use Overview's text-panel fallback.
- Successful figures and unaffected prose survive repairs unchanged. Final output contains no dangling generated-figure references.
- Preserve saved Blog and Overview compatibility and the existing atomic generation save boundary.

## Current code and smallest change

| Area | Current code | Planned responsibility |
| --- | --- | --- |
| Entry point | `papers/ai.py::generate_overview` | Keep Blog dispatch to `agent_overviews.generate`; Overview dispatch is unchanged. |
| Reading | `papers/reading.py` | Reuse current orientation, bibliography filter, and retrieval without a new reading service. |
| Blog coordination | `papers/agent_overviews.py::generate` | Author prose/briefs, dispatch drawings, route targeted repairs, clean omissions, review and assemble. |
| Contracts | `papers/explanation.py` | Add Blog brief/draft validation and drawing-assignment projection; preserve legacy contracts for saved references. |
| Drawing | `papers/panel_authoring.py` | Reuse guides, requests, source validation and exact-value checks; add a small Blog purpose option. |
| Figure lifecycle | New `papers/blog_figures.py` | Count attempts, retain accepted/omitted outcomes, invoke drawing/checking, and apply exact cleanup edits. |
| Rendering | `papers/html_figures.py`, `papers/HTMLSnapshot.swift` | Add `blog` mode using panel safety and measurements at actual article width. |
| Delivery | `papers/exports.py`, `app/static/app.js`, existing library save path | Verify sparse stable IDs, no missing asset requests, captions, SVG download, and export compatibility; edit only where tests expose an assumption. |

The current Blog already imports `build_orientation`, `evidence_document`, `orientation_page`, and `retrieve_evidence`. Its main fault boundary is later: `compile_candidate`, `render_candidate`, and the Blog repair loop operate on complete prose-plus-HTML candidates. Keep reading and prose, replace that drawing boundary. Do not call `overview_workflow.build_panels`: it retries internally and substitutes `simple_panel`, both incompatible with this Blog omission policy.

## Task 1: Lock down reading and the Blog editorial contract

**Files:** Modify `papers/agent_overviews.py` prompts; extend `tests/test_reading_bibliography.py`, `tests/test_reading.py`, and `tests/test_agent_overviews.py`. `papers/reading.py` changes only if a failing case exposes a shared defect.

**Interfaces:** Keep `build_orientation(document)`, `orientation_page(orientation, offset=0, limit=100)`, and `retrieve_evidence(document, orientation, selection, *, vision)`. Initial and supplemental source requests retain the existing `SELECTION_SCHEMA`.

- [x] Extend the existing both-modes bibliography test to inspect selection, authoring, semantic repair, omission cleanup, and review messages. Include bibliography sentinels, an in-text citation, related-work prose, and an appendix after the bibliography.
- [x] Add a scripted Blog source-selection case with an identified abstract, an unrelated section, and a necessary appendix. Assert the selection request carries the abstract/map, subsequent authoring receives only selected evidence, and supplemental retrieval includes the appendix without bibliography material. Cover missing/ambiguous abstract and paged source maps using existing reading fixtures.

Use the actual provider boundary, following the existing test pattern:

```python
payload = json.dumps([call.args for call in provider.complete.call_args_list])
self.assertNotIn('BIBLIOGRAPHY_SENTINEL', payload)
self.assertNotIn('ONLY_BIBLIOGRAPHY', payload)
self.assertEqual(before, document)
```

- [x] Run `.venv/bin/python -m unittest tests.test_reading tests.test_reading_bibliography tests.test_agent_overviews`. Existing reuse tests may already pass; do not invent a failing production change where behavior is already correct.
- [x] Update Blog-specific prompts to open with contribution and importance, explain context before jargon, honor depth preferences, distinguish standard background from paper evidence, and describe figures as visual aids. Do not apply the Overview requirement to place the whole explanation inside panels to Blog review.
- [x] Re-run the focused tests. Preserve source digests, coverage metadata, selected-image behavior, existing reference-admission checks, and original paper content.

## Task 2: Separate the article draft from drawing briefs

**Files:** Modify `papers/explanation.py` and Blog paths in `papers/agent_overviews.py`; extend `tests/test_explanation.py` and `tests/test_agent_overviews.py`.

**Interfaces:** Add `BLOG_DRAFT_SCHEMA`, `validate_blog_draft(draft, document, length) -> dict`, and `blog_figure_assignment(brief) -> dict` in `papers/explanation.py`. The draft retains `plan` and `text`; its `figures` are briefs, not SVG or HTML. A brief has these exact fields:

```python
brief = {
    'id': 'fig1',
    'title': 'Two paths, one output',
    'paper_connection': 'Show how the two contributions combine.',
    'caption': 'The frozen path and learned update add to one output.',
    'illustrative': False,
    'passages': ['p00001'],
    'purpose': 'What happens when an input enters the adapted layer?',
    'entry_context': ['The prose has introduced the frozen weights.'],
    'exit_state': 'The reader can trace the base output and the update.',
    'construction': 'flow',
    'layout_intent': 'Input at left; frozen and trainable paths stacked in the middle; addition and output at right.',
    'content': [
        {'text': 'Input reaches both paths, whose outputs are added.',
         'kind': 'connection', 'passages': ['p00001']},
    ],
    'exact_text': ['W₀x', 'BAx'],
    'illustrative_values': [],
}
```

The example is a contract fixture; real briefs must cite the retrieved paper. Reuse the existing construction/kind enums, metadata bounds, and passage validation. Require a nonempty `layout_intent` within the existing 1200-character plan-text bound; it describes composition and reading order, leaving exact geometry to the SVG author. Require supporting evidence per brief, while allowing an explicitly illustrative content item to lack source citations. A brief need not cover every narrative claim.

- [x] Write tests rejecting markup in the draft, unknown evidence IDs, duplicate IDs, unknown constructions, and mismatched markers. Accept zero figures and sparse ordered IDs such as `fig1`, `fig3` after omission. Initially allocate `fig1` through `fig3`; never reuse an omitted ID in the same run.
- [x] Test the author-facing projection:

```python
assignment = blog_figure_assignment(brief)
self.assertEqual('fig1', assignment['id'])
self.assertEqual(brief['exact_text'], assignment['exact_text'])
self.assertEqual(brief['layout_intent'], assignment['layout_intent'])
self.assertNotIn('passages', json.dumps(assignment))
self.assertNotIn('p00001', json.dumps(assignment))
```

- [x] Implement validation using the existing plan/citation/length helpers. Preserve the old HTML validator for legacy references, but remove it from new Blog authoring and repair acceptance. Project into the current panel assignment keys: `id`, `title`, `purpose`, `entry_context`, `exit_state`, `construction`, `content`, `exact_text`, `illustrative_values`, and `shared_facts={}`, plus `layout_intent`. Remove passage IDs from projected content; evidence remains on the saved brief. Teach the shared `assignment_block` to include optional layout intent, so existing Overview assignments remain valid.
- [x] Move the existing `candidate_digest(value)` implementation unchanged to `papers/explanation.py` and import it into `papers/agent_overviews.py`, preserving the existing imported symbol for callers. New figure/edit helpers import it from `explanation`, avoiding a circular import back into the Blog coordinator. Assert the digest of existing fixture candidates is unchanged.
- [x] Switch the new Blog author submission to `BLOG_DRAFT_SCHEMA` without changing the prose text format or adding a second prose-generation stage. Checkpoint the article digest and briefs before drawing. Use `blog-focused-svg-v1` for the new prompt/schema identity; reject incompatible old in-progress contexts while retaining saved artifact readers.
- [x] Run `.venv/bin/python -m unittest tests.test_explanation tests.test_agent_overviews tests.test_reading_bibliography` and resolve new-path regressions without loosening legacy validation.

## Task 3: Reuse panel drawing at the actual Blog width

**Files:** Modify `papers/panel_authoring.py`, `papers/html_figures.py`, `papers/HTMLSnapshot.swift`; create `papers/blog_figures.py`; extend `tests/test_panel_authoring.py`, `tests/test_svg_figures.py`, and `tests/test_figure_readability.py`.

**Interfaces:** Add keyword `purpose='overview'` to `panel_messages` and `request_panel`; accept only `overview` and `blog`. Add `mode='blog'` to `html_figures.render`. Add `check_blog_figure(source, directory, figure_id) -> dict` in `papers/blog_figures.py`, returning the existing `check_panel` result shape: `source`, `assets`, `checks`, `labels`.

- [x] Test the same request order used by Overview panels: one detailed assignment with layout intent, one or two complete relevant SVG examples, construction notes, common drawing guidance, and output contract. Include Blog visual-purpose/640px guidance, but no article, source evidence, sibling briefs, or whole-Overview composition requirements. Preserve `{"panel_id": "fig1", "svg": "<svg>...</svg>"}` as the response shape; only the SVG is authored content. Keep Overview prompt regression tests.
- [x] Extend render-mode validation to map `blog` to the panel SVG safety profile and shared markers. Keep source SVG, PNG, PDF, compatibility SVG and HTML asset keys. Make the saved editable SVG self-contained with the same shared marker definitions as the render.
- [x] In `captureCanvas`, apply Blog dimensions before collecting native measurements. Preserve the authored viewBox and its geometry:

```javascript
// After reading the viewBox dimensions; only for Blog mode.
if (mode === 'blog') {
  height = height * 640 / width;
  width = 640;
}
```

Pass the mode into the evaluated JavaScript from the existing Swift argument. The current `getScreenCTM()` measurements then include the actual display scale. Retain existing resource ceilings and report unsupported dimensions explicitly. No 960px wrapper, caption padding, or height-based shrink is applied to new Blog drawings.

- [x] Add native cases: a 640-unit drawing with 18-unit text passes; a 960-unit drawing with 18-unit text fails at 12px; a 960-unit drawing with 24-unit text passes at 16px. Include transformed text, clipping, overlap, and shared arrow markers. Check zero bibliography/passages in visible labels separately.
- [x] Rebuild to a temporary helper and run native checks:

```sh
xcrun swiftc -sdk /Library/Developer/CommandLineTools/SDKs/MacOSX15.4.sdk -O papers/HTMLSnapshot.swift -o /tmp/localxiv-blog-html-snapshot
LOCALXIV_HTML_RENDERER=/tmp/localxiv-blog-html-snapshot .venv/bin/python -m unittest tests.test_figure_readability tests.test_panel_authoring tests.test_panel_guides
```

If the documented SDK is unavailable, use the installed compatible SDK and record it. Inspect the representative renderings at 640px; compilation and issue counts alone do not establish readable output.

## Task 4: Make focused repairs converge within four drawing requests

**Files:** Implement lifecycle in `papers/blog_figures.py`; integrate with `papers/agent_overviews.py`; create `tests/test_blog_figures.py` and extend `tests/test_agent_overviews.py`.

**Interfaces:** `new_figure_state(brief) -> dict` creates a record containing `id`, `brief`, `attempts=0`, `status='pending'`, `checked=None`, `issues=[]`, and `history=[]`. `attempt_figure(provider, state, directory, *, issues=(), image=None, options=None, checkpoint=None) -> dict` returns the updated state after at most one provider drawing request. When supplied, `checkpoint(state)` persists state before dispatch and after checking; production always supplies it. Status is `pending`, `accepted`, or `omitted`; omitted is terminal, and an accepted state without new issues is returned unchanged. Provider usage must be returned through the existing per-run accounting, once per call.

- [x] Add tests for success on each of attempts one through four, four failures, and a locally accepted drawing later rejected by semantic review. Verify generation stops at the first accepted result, the total call count never exceeds four, and successful sibling assets remain unchanged.

```python
state = new_figure_state(brief)
for _ in range(4):
    state = attempt_figure(provider, state, directory)
self.assertEqual(4, state['attempts'])
self.assertEqual('omitted', state['status'])
state = attempt_figure(provider, state, directory)
self.assertEqual(4, provider.complete.call_count)
```

Use four scripted invalid responses for this case. Other cases return complete fixture SVGs and mocked native measurements, with separate native coverage from Task 3. Assert that a failed second attempt remains pending, not omitted, and that a fourth-attempt success is retained.

- [x] Implement direct calls to `request_panel(..., purpose='blog')` and `check_blog_figure`, followed by `missing_value_details`. Use one `MAX_FIGURE_ATTEMPTS = 4` constant in `papers/blog_figures.py`; increment and checkpoint attempts before dispatch so a later review cannot restore the budget. Pass the previous source, every current defect with measured location/size, the unchanged detailed assignment/layout/examples, and an optional rendered image for that figure's correction. Confirm article-width measurements reach the repair prompt, not just a generic failure string.
- [x] Replay retained problematic SVGs through local checking and retain representative regression fixtures for undersized text, out-of-bounds labels, and contract mismatches. Pair each with a hand-corrected version to verify the reported defects and accepted correction. These checks validate feedback quality, not model convergence. The later live pilot measures actual completion by attempts two and three.
- [x] Count malformed responses and transport retries inside the ceiling. Propagate authentication failure, cancellation, and local renderer failure. Do not import `build_panels`, `_author_once`, or `simple_panel` from the Overview workflow. Start sequentially; concurrency is not required to fix the failure boundary.
- [x] Route review findings about drawing execution to the affected stable ID. A scientific error in an assignment requires a supported brief correction before consuming any remaining drawing attempt. It never receives a fresh ID or budget. If no attempt remains, omit and clean the article.
- [x] Persist per-figure source/checks/history and aggregate provider usage. Keep accepted article text byte-for-byte unchanged during geometry-only attempts.
- [x] Run `.venv/bin/python -m unittest tests.test_blog_figures tests.test_panel_authoring tests.test_agent_overviews`.

## Task 5: Remove failed figures and repair only dependent prose

**Files:** Add cleanup helpers in `papers/blog_figures.py`; integrate with Blog review/checkpoints in `papers/agent_overviews.py`; extend `tests/test_blog_figures.py` and `tests/test_agent_overviews.py`.

**Interfaces:** `remove_omitted_markers(text, omitted_ids) -> str` removes exact generated markers. `apply_text_edits(text, edits, *, base_digest) -> str` accepts `edits=[{'old': str, 'new': str}]`, bound to `candidate_digest(text)`. The cleanup provider response is `{'base_digest': str, 'edits': [...]}`. Edits have unique nonempty old strings that occur exactly once in the current text, with nonoverlapping source spans. Empty replacements are allowed. Apply spans in reverse position order so replacements cannot match other replacement output.

- [x] Test exact edit application, stale digest, repeated old text, overlapping edits, and preservation outside changed spans:

```python
text = 'Opening stays.\n\nFollow the blue branch below.\n\nEnding stays.'
edits = [{'old': 'Follow the blue branch below.',
          'new': 'The input follows two paths whose outputs are added.'}]
result = apply_text_edits(text, edits, base_digest=candidate_digest(text))
self.assertEqual('Opening stays.\n\nThe input follows two paths whose outputs are added.\n\nEnding stays.', result)
```

- [x] Batch current omitted IDs, remove their markers and asset entries, then request exact prose edits using the full current text for context, omitted briefs, surviving IDs, and filtered evidence. The prompt must remove captions embedded in prose, visual walkthroughs and indirect references anywhere in the article; retain essential mechanisms and citations; and forbid new figure markers or drawing requests.
- [x] Validate the response before application, then validate resulting citations, length and marker/asset equality. Reject restoration of any omitted ID. Preserve successful figure IDs even when the list becomes `fig1`, `fig3`. Do not indiscriminately remove references to original-paper figures.
- [x] Run final semantic review on the cleaned article and accepted renderings. Require no dangling visual references, no omitted explanatory step, and no new unsupported claim. Return targeted text edits for article issues and stable figure IDs for drawing issues. Preserve all active issues until a new review resolves them; an omission alone is not scientific approval.
- [x] Bound assembled review by the available work: one initial verdict, at most one new verdict per figure attempt or omission change, and at most two prose-only corrections. Derive a hard verdict ceiling of `1 + (MAX_FIGURE_ATTEMPTS + 1) * len(planned_figures) + 2`, while reviewing only when the artifact changes. Allow one cleanup response plus one validation correction per newly omitted batch; omit each stable ID at most once. A reviewer may request one batched evidence supplement per verdict. Retain no-progress checks for prose; repeated figure findings must produce focused feedback and remain eligible for the four-attempt budget. If the budget ends without approval, retain a failed draft and the old saved Blog; do not deliver unreviewed text or make a fifth drawing call. Record this as an article/review failure separately from expected figure omission.
- [x] Cover first/middle/last figure omission, multiple omissions in one cleanup, all figures omitted, a late omission after semantic review, surviving source-paper references, unsupported cleanup claims, and cleanup-provider failure. Assert the all-omitted coherent article can reach successful delivery with `figures=[]`.
- [x] Run `.venv/bin/python -m unittest tests.test_blog_figures tests.test_agent_overviews tests.test_reading_bibliography`.

## Task 6: Verify delivery, compatibility, and honest outcome reporting

**Files:** Extend `tests/test_exports.py`, `tests/test_app.py`, `tests/test_app_ui.js`; update `docs/development.md`. Modify `papers/exports.py` or `app/static/app.js` only for demonstrated new-path incompatibilities. Write results to `docs/verification/2026-09-14-blog-workflow-update.md` during implementation.

- [x] Preserve result fields `text`, `cited_text`, `explanation`, `plan`, `figures`, `evidence`, and `provenance`. Derive clean display text from the final cited text. Set the new SVG profile revision and keep omission details only in provenance/run diagnostics.
- [x] Verify a Blog with `fig1` and `fig3` renders and exports both, makes no request for `fig2`, and contains no omitted caption, link, marker or visual walkthrough. Verify no-figure Blog delivery, legacy HTML Blog viewing/export, new editable SVG download, and unchanged Overview generation.
- [x] Confirm final review digest matches the delivered prose and surviving figure sources. Test cancellation and cleanup failure preserve the previous saved generation through the existing application boundary.
- [x] Run the focused integration checks, then the existing offline suite once the focused checks pass:

```sh
.venv/bin/python -m unittest tests.test_reading tests.test_reading_bibliography tests.test_explanation tests.test_blog_figures tests.test_agent_overviews tests.test_svg_figures tests.test_exports tests.test_app tests.test_overview_workflow
node tests/test_app_ui.js
LOCALXIV_HTML_RENDERER=/tmp/localxiv-blog-html-snapshot .venv/bin/python -m unittest tests.test_figure_readability tests.test_panel_authoring tests.test_panel_guides
.venv/bin/python -m unittest discover -s tests
git diff --check
```

- [x] Inspect reader and exported artifacts for an operation, comparison, and worked example. Include a deliberately omitted drawing and inspect the cleaned article as a whole. Record checks run, skipped native checks, render dimensions, and unresolved limitations.
- [x] Define a later live pilot using retained papers from the existing matrix. It requires explicit provider-call authorization and a spend ceiling. Report accepted articles, planned/accepted/repaired/omitted figures, semantic failures, provider failures, request counts, and cost/time per accepted article. For figures, report first-attempt acceptance and cumulative acceptance by attempts two, three, and four using all planned figures as the denominator. The desired result is usable figures within two or three attempts; a higher article delivery rate obtained by omitting figures does not establish this goal. Inspect visual explanation quality as well as local geometry acceptance.

## Completion and handoff

The implementation is locally complete when all six tasks pass their relevant checks and the verification report includes actual rendered and cleaned articles. No claim of provider reliability follows from scripted tests. Keep the implementation uncommitted unless the user requests a commit; do not publish, change the installed app, or run the paid matrix as an implicit continuation.

Plan coverage: Tasks 1–2 preserve reading and prose while establishing focused briefs with layout intent; Task 3 shares Overview's example-led SVG request structure and checks article width; Task 4 targets convergence within the four-attempt ceiling; Task 5 removes failed assets and their discussion only after that budget is exhausted; Task 6 checks final delivery, visual success, and compatibility.

Implemented and verified offline on 2026-09-14; see the [verification report](../../verification/2026-09-14-blog-workflow-update.md) for commands, artifacts, rendered dimensions, and the still-open live pilot. No provider call was made during implementation and nothing was committed.

A first authorized live pilot followed the same day (3 models × 2 papers, Blogs only, $10 ceiling): [Blog live pilot](../../verification/2026-09-14-blog-live-pilot.md). It delivered 2 of 6 articles and exposed one budget defect in the review-triggered redraw path, now fixed with a regression test. A post-fix re-run ([results](../../verification/2026-09-14-blog-live-pilot-rerun.md)) confirmed the budget behavior live and exposed a second defect (`\bm` broke Blog PDF export), also fixed and tested.
