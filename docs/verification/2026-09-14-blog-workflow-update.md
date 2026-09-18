# Blog workflow update verification

Status: historical. The model-drawn SVG path this report verifies was deleted by the [figure library consolidation](../superpowers/specs/2026-09-18-figure-library-consolidation-design.md); the code is at commit 9abae74.

Date: 2026-09-14
Plan: Blog workflow update (plan removed; in git history)
Design: [Agreed Blog design](../superpowers/specs/2026-09-14-blog-workflow-update-design.md)
Status: offline implementation and verification complete. No live provider call was made or is
claimed here; the pilot needs explicit authorization and a spend ceiling.

## Code identity

| Item | Value |
| --- | --- |
| Branch | `akhil/model-authored-svg-overviews` |
| HEAD at verification | `35260f3` (`Checkpoint overview rebuild and shrink-first layout refinement`) |
| Working tree vs HEAD digest | `2f14dcb0f655745e34121f7c2b36b93b61dbf28195a71dfc85d70a7a3e7a794c` (SHA-256 of `git diff HEAD --binary`) |
| New Blog lifecycle module | `papers/blog_figures.py`, SHA-256 `2963be66ca359d3c473efeef1f6cebafdb67fc2adb253546899f232d392b7c45` |
| New Blog lifecycle tests | `tests/test_blog_figures.py`, SHA-256 `bdf7485481375a8f5c35c12c8c2c06e2054d33e82ff9cbfdc5be3f157d5a7e2f` |
| Native helper | `/tmp/localxiv-blog-html-snapshot`, SHA-256 `763e5cbc9edad9c6cebe6971a08758b8aab08c2fca2a25c89b25c0fc5631614e` |
| Native rebuild | `xcrun swiftc -sdk /Library/Developer/CommandLineTools/SDKs/MacOSX15.4.sdk -O papers/HTMLSnapshot.swift -o /tmp/localxiv-blog-html-snapshot` (SDK present as documented) |
| Probe artifact | `docs/verification/artifacts/2026-09-14-blog-workflow-update/` |

`docs/development.md` documents the split Blog/Overview sequence, the four-attempt figure budget,
the 640px article width, and the updated offline test command list.

## What is implemented

- **Task 1 — reading and editorial contract.** Blog keeps `build_orientation`,
  `orientation_page`, `evidence_document`, and `retrieve_evidence`; selection requests carry the
  abstract/map, authoring sees only selected evidence, and supplemental retrieval crosses the same
  bibliography-filtered boundary. Blog prompts open with contribution and importance, explain
  context before jargon, distinguish standard background from paper evidence, and describe figures
  as visual aids. `tests/test_reading_bibliography.py` checks bibliography sentinels at the
  selection, authoring, drawing, review, omission-cleanup, and article-repair boundaries, keeps an
  in-text citation and related-work prose, and leaves the retained paper unchanged.
- **Task 2 — draft and briefs.** `BLOG_DRAFT_SCHEMA`, `validate_blog_draft`, `validate_blog_brief`,
  and `blog_figure_assignment` live in `papers/explanation.py`. A draft is cited prose plus zero to
  three briefs with layout intent, purpose, entry context, exit state, construction, content, and
  exact text. The author submits `blog-focused-svg-v1`; legacy HTML validation stays only for saved
  references. `candidate_digest` moved to `papers/explanation.py` unchanged and is re-exported by
  the Blog coordinator for existing callers.
- **Task 3 — drawing at article width.** `request_panel(..., purpose='blog')` reuses the
  assignment → examples → construction notes → output contract order with Blog purpose guidance.
  `html_figures.render(mode='blog')` uses the panel safety profile, and `captureCanvas` scales a
  Blog viewBox to 640px before measuring so `getScreenCTM()` reports the real display size. The
  saved editable SVG is self-contained with the shared marker definitions.
- **Task 4 — four attempts.** `papers/blog_figures.py` owns `new_figure_state` and
  `attempt_figure`: one provider request per attempt, `MAX_FIGURE_ATTEMPTS = 4`, increment and
  checkpoint before dispatch, checkpoint after checking, terminal omission on the fourth failure,
  provider usage recorded once per call, and article-width defects with locations and measured
  sizes in the repair prompt. Authentication raises; malformed and transport failures consume the
  budget; a local renderer failure propagates.
- **Task 5 — omission cleanup.** `remove_omitted_markers` and digest-bound `apply_text_edits` remove
  the marker and the prose that depended on the omitted drawing in one batched exact-edit request,
  with at most one validation correction. Surviving IDs stay stable (`fig1`, `fig3`). Review is
  bounded by artifact changes; an all-omitted Blog can still be delivered.
- **Task 6 — delivery.** Published `figures` contain accepted figures only; omission diagnostics
  stay in provenance and run artifacts. `result['text']` is the citation-cleaned form of the final
  `cited_text`. Blog figures now expose their editable SVG source in the reader's Share dialog, the
  same way free-sized Overviews do; legacy Overview sources keep their old behavior.

## Checks run

| Check | Command | Result |
| --- | --- | --- |
| Focused integration | `LOCALXIV_HTML_RENDERER=/tmp/localxiv-blog-html-snapshot .venv/bin/python -m unittest tests.test_reading tests.test_reading_bibliography tests.test_explanation tests.test_blog_figures tests.test_agent_overviews tests.test_svg_figures tests.test_exports tests.test_app tests.test_overview_workflow` | 231 tests, OK |
| Native figure checks | `LOCALXIV_HTML_RENDERER=/tmp/localxiv-blog-html-snapshot .venv/bin/python -m unittest tests.test_figure_readability tests.test_panel_authoring tests.test_panel_guides` | 86 tests, OK |
| Blog fixture replay | `LOCALXIV_HTML_RENDERER=/tmp/localxiv-blog-html-snapshot .venv/bin/python -m unittest tests.test_blog_figures` | 19 tests, OK |
| Reader UI | `node tests/test_app_ui.js` | passed |
| Offline suite | `LOCALXIV_HTML_RENDERER=/tmp/localxiv-blog-html-snapshot .venv/bin/python -m unittest discover -s tests` | 567 tests, OK, 1 skipped |
| Whitespace | `git diff --check` | clean |

No native check was skipped: the helper was rebuilt from the current Swift source and passed to the
suites that gate on it. The single full-suite skip is the unrelated opt-in Keychain test
(`tests.test_ai.KeychainSmokeTest`, "Opt-in test creates and removes one fake Keychain item"). Some
failure-path subprocesses print `Error while generating output:` on stderr; the owning tests pass.

## Rendered dimensions

The probe in `docs/verification/artifacts/2026-09-14-blog-workflow-update/` ran the real coordinator
with a scripted provider and the native helper. It planned three figures, drew `fig1` on the first
attempt, exhausted `fig2` with four malformed responses, and accepted `fig3` on its second attempt
after a measured readability failure.

| Figure | Outcome | Attempts | Canvas | Displayed label |
| --- | --- | --- | --- | --- |
| `fig1` | accepted | 1 | 640 × 240 | `/svg/text[1]` = 18px, "Two paths, one output" |
| `fig2` | omitted | 4 | — | — |
| `fig3` first attempt | rejected | — | 640 × 240 | 11px (< 14px minimum) |
| `fig3` accepted | accepted | 2 | 640 × 240 | `/svg/text[1]` = 18px, "Step by step" |

The `fig3` repair prompt received the measured defect, not a generic failure string:

```
- /svg/text[1]: Small text in the panel canvas (11.0 units; minimum 14): Step by step.
  Raise its source font size from 11 to at least 14 units, or use fewer labels.
  (measured 11; limit 14)
```

The helper renders Blog PNGs at 4× the displayed width (2560 × 960 for a 640 × 240 canvas); the
accepted compatibility SVG carries `width="640" height="240"` and the editable source keeps the
authored `viewBox="0 0 640 240"` plus the shared arrow markers. Provider calls: 3 authoring,
1 `fig1` drawing, 4 `fig2` drawings, 2 `fig3` drawings, 1 cleanup, 1 review = 12, matching the
usage records.

## Artifact inspection

The probe article covers an operation (two paths added), a comparison (ranking across two
settings), and a worked example (3 + 0.5 = 3.5). The delivered, cleaned article is:

```markdown
The paper compares a frozen baseline with a small learned update [p00001].

An input reaches a frozen path and a trainable path, and their outputs are added [p00001]. Adding the two outputs gives the layer output [p00001].

{{figure:fig1}}

The two methods rank differently in the two evaluated settings [p00002].

For the toy input the frozen path returns 3 and the update returns 0.5, so the layer output is 3.5 [p00003]. The third drawing traces that computation step by step [p00003].

{{figure:fig3}}

Only two datasets were tested [p00004].
```

The cleanup removed both `{{figure:fig2}}` and the walkthrough that pointed at it ("The second
drawing shows which method wins in each setting"), while replacing the operation walkthrough with a
direct prose statement. The surviving mechanism, worked example, and citations are unchanged. The
review digest bound to the cleaned article equals `candidate_digest(result['cited_text'])`
(`19d919b0d7e739c69199f97d1c7c26be6687b24236929777fc4096f3670528a8`), the final review reports
`figure_ids = ['fig1', 'fig3']`, and the delivered `text` carries no passage IDs.

Reader and export checks against the same generation:

| Check | Result |
| --- | --- |
| Blog EPUB (`overview.epub`) | `fig1.svg` and `fig3.svg` packaged; no `fig2` name, marker, caption, or walkthrough anywhere |
| Blog PDF (`blog.pdf`, 58,259 bytes) | both surviving captions present; ≥ 2 image XObjects; no `fig2` text or marker |
| Exported XHTML | parses cleanly; keeps "Adding the two outputs" and "layer output is 3.5" |
| Sparse-ID rendering (`tests/test_app_ui.js`) | `fig1.svg` and `fig3.svg` requested; `fig2` never requested; captions rendered |
| Legacy Blog viewing (`tests/test_app_ui.js`) | a saved figure without new metadata still renders and enlarges |
| Legacy Blog export (`tests/test_exports.py`) | a figure with only `svg` still packages; caption kept; no marker |
| Editable SVG download (`tests/test_app_ui.js`) | Blog Share dialog offers "Download SVG" for the first surviving source; a legacy Blog without one stays hidden |
| No-figure Blog (`tests/test_app.py`) | real generation path saves `figures: []`, no markers, review digest matches the delivered text |
| Cleanup failure (`tests/test_app.py`) | provider failure leaves the previous saved Blog and marks the job failed |
| Cancellation (`tests/test_app.py`) | existing test keeps the previous Blog generation |
| Overview regression | all `tests.test_overview_workflow` and native panel suites pass unchanged |

Rendered survivors inspected at 640px are kept as `fig1.png` and `fig3.png` beside the probe output.
Their geometry is scripted-minimal by design: these artifacts establish the width, label size,
export, and cleanup pipeline, not model-authored visual quality.

## Live pilot (2026-09-14)

A first authorized live pilot ran after the offline verification: three OpenRouter models × two
retained matrix papers, Blogs only, $10 ceiling, PDF export per accepted Blog. It delivered 2 of 6
articles for $1.87 and found one real defect: the review-triggered redraw path could exceed the
four-attempt ceiling. `papers/agent_overviews.py` now omits a reviewed figure with no remaining
attempts instead of redrawing it, with the regression test
`tests/test_agent_overviews.py::AgentTests.test_a_review_finding_on_an_exhausted_figure_omits_without_a_fifth_draw`.
A post-fix re-run of the full matrix (2 of 6 delivered, $3.13) confirmed the budget behavior live —
the exhausted-figure path ran twice with a maximum of four drawing requests — and exposed a second
defect: a Blog using `\bm` failed PDF export until `papers/exports.py` normalized it to
`\boldsymbol` for the LaTeX pipeline. The full offline suite passes at 569 tests. Full results,
delivered PDFs, and failure analysis: [Blog live pilot](2026-09-14-blog-live-pilot.md) and
[post-fix re-run](2026-09-14-blog-live-pilot-rerun.md).

## Unresolved limitations

- No live provider call: scripted tests and the probe say nothing about live figure completion rates
  or model-authored visual and scientific quality.
- The probe disabled vision review. The vision path (rendered PNGs in review) is covered only by
  unit tests with mocked responses.
- Failed attempts retain their run directories under `reader/overview-figures/<run>/` for
  diagnostics even after a later attempt is accepted or the figure is omitted; they are never
  referenced by the delivered article.
- Acceptance is at the 640px article width. Smaller phone viewports are not claimed to be equally
  readable.
- The Share dialog exposes the editable SVG of the first surviving Blog figure only; a Blog with
  several figures has no per-figure source links.
- A flaky transport consumes the same four-attempt budget as a malformed drawing, by design.
- Blog PDF export needs MacTeX and XeLaTeX; the PDF test skips where they are unavailable.

## Later live pilot

Run only with explicit provider-call authorization and a spend ceiling, reusing retained papers
from the existing matrix (`docs/verification/2026-09-13-overview-blog-live-matrix.json`).

For every paper, report:

- article outcome: accepted, or article/review failure with its recorded failure kind;
- figures: planned, accepted, repaired, omitted;
- first-attempt acceptance and cumulative acceptance by attempts two, three, and four, with all
  planned figures as the denominator;
- semantic-review failures, provider failures, total provider requests, usage, cost, and wall time
  per accepted article;
- for omitted figures, the attempt count and final defect codes.

The target is a usable figure within two or three attempts. A higher article delivery rate obtained
by omitting figures does not establish that target; report retention and omission rates alongside
delivery. Inspect the rendered figures and cleaned articles for visual explanation quality, not only
local geometry acceptance, and record representative accepted, repaired, and omitted cases here.
