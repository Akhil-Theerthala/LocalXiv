# Blog workflow refactor: progress

**Status (2026-09-14):** implemented in the source checkout, verified offline with the native
renderer, and exercised in two live pilots (3 models × 2 papers, Blogs only). Two real defects were
found live and fixed. Everything is uncommitted; no release, publish, or install was performed.

**Goal:** deliver readable, grounded Blogs using Overview's directed reading and the individual
drawing machinery, aiming for usable focused figures within two or three attempts and allowing four
before coherent omission.

**Spec:** [Agreed Blog design](superpowers/specs/2026-09-14-blog-workflow-update-design.md)
**Plan:** [Blog workflow update](superpowers/plans/2026-09-14-blog-workflow-update.md) (all 36 items
checked)
**Offline verification:** [Blog workflow update verification](verification/2026-09-14-blog-workflow-update.md)
**Live pilots:** [pilot 1](verification/2026-09-14-blog-live-pilot.md) ·
[post-fix re-run](verification/2026-09-14-blog-live-pilot-rerun.md)

## Status at a glance

| Workstream | Status |
| --- | --- |
| Directed reading with bibliography filtering at every Blog boundary | Implemented, tested |
| Blog draft/brief contract (`BLOG_DRAFT_SCHEMA`, layout intent, exact text) | Implemented, tested |
| Drawing at the real 640 px article width, panel safety profile | Implemented, native-checked |
| Four-attempt figure lifecycle with checkpointed budget | Implemented, live-confirmed |
| Omission cleanup with digest-bound exact text edits | Implemented, live-confirmed |
| Bounded review, brief correction, no-progress handling | Implemented, live-exercised |
| Delivery: sparse figure IDs, no-figure Blogs, PDF/EPUB/SVG export | Implemented, tested |
| Live pilot (3 models × 2 papers) | Run twice; 2 of 6 Blogs delivered each time |
| Defects found live | 2, both fixed with regression tests |
| Blog delivery rate / review convergence | Open: models fail the bounded review on substantive findings |

## Code identity

| Item | Value |
| --- | --- |
| Branch | `akhil/model-authored-svg-overviews` |
| HEAD | `35260f3` |
| Working tree vs HEAD | SHA-256 `512136f1ebd7ed04e86841c53796d22a60d3a9c639de1fd64130a45f4328148e` (`git diff HEAD --binary`) |
| Offline suite | 569 tests, OK, 1 unrelated skip (opt-in Keychain) |
| Native helper | `/tmp/localxiv-blog-html-snapshot` built from `papers/HTMLSnapshot.swift` with the documented `MacOSX15.4.sdk` |

## What changed

| Area | Files | Responsibility |
| --- | --- | --- |
| Contracts | `papers/explanation.py` | `BLOG_DRAFT_SCHEMA`, `BLOG_BRIEF_SCHEMA`, `validate_blog_draft`, `validate_blog_brief`, `blog_figure_assignment`, `candidate_digest` moved here unchanged |
| Coordinator | `papers/agent_overviews.py` | Blog prompts and editorial rules, draft submission, figure dispatch, review loop, brief correction, omission cleanup, bounded verdicts, exhausted-figure guard, provenance |
| Figure lifecycle | `papers/blog_figures.py` (new) | `new_figure_state`, `attempt_figure` (one request per attempt, `MAX_FIGURE_ATTEMPTS = 4`, checkpoint before dispatch), `check_blog_figure`, `remove_omitted_markers`, `apply_text_edits` |
| Drawing | `papers/panel_authoring.py` | `purpose='blog'` request guidance; Blog omits article/evidence/siblings |
| Rendering | `papers/html_figures.py`, `papers/HTMLSnapshot.swift` | `mode='blog'`: panel safety profile, viewBox scaled to 640 px before `getScreenCTM()` measurement |
| Delivery | `papers/exports.py` | `pdf_math_macros`: `\bm` → `\boldsymbol` for the LaTeX PDF path |
| Reader UI | `app/static/app.js` | Blog figures expose their editable SVG source in the Share dialog |
| Tests | `tests/test_blog_figures.py` (new), `tests/fixtures/blog-figures/`, plus extensions to `test_agent_overviews`, `test_explanation`, `test_reading_bibliography`, `test_panel_authoring`, `test_svg_figures`, `test_figure_readability`, `test_exports`, `test_app`, `test_app_ui.js` | lifecycle, edit arithmetic, bibliography boundaries, native width cases, delivery/compatibility |
| Docs | `CONTEXT.md`, `docs/development.md` | Blog/Overview sequence, four-attempt budget, 640 px width, updated test commands |

Preserved deliberately: the Overview panel workflow, saved Blog/Overview compatibility, the atomic
generation save boundary, and all pre-existing worktree changes (`papers/html_figures.py`,
`papers/overview_workflow.py`, `papers/edge_align.py`, `papers/mixed_fit.py`).

## Behavior in one paragraph

One authoring stage returns cited Markdown plus zero to three drawing briefs. Each brief carries one
visual idea, purpose, entry context, exit state, construction family, layout intent, supporting
passages, and exact text. The application draws each brief through `request_panel(purpose='blog')`,
checks it at 640 px with the native renderer, and repairs with measured defects until accepted or
out of budget (four drawing requests per stable ID). A fourth failure omits the figure permanently
and rewrites only the prose that depended on it, in one digest-bound exact-edit request. Review is
bounded by artifact changes; an exhausted figure hit by a review finding is omitted rather than
redrawn. Accepted Blogs publish sparse stable IDs (`fig1`, `fig3`) and export to EPUB/PDF plus
editable SVG.

## Offline verification

| Check | Result |
| --- | --- |
| Focused integration (reading, briefs, figures, exports, app) | 231 tests OK |
| Native figure/panel suites | 86 tests OK |
| Blog fixture replay (undersized text, out-of-bounds, contract mismatch) | 19 tests OK |
| Reader UI (`node tests/test_app_ui.js`) | passed |
| Full offline suite | 569 tests OK, 1 unrelated skip |
| `git diff --check` | clean |
| Probed end-to-end artifact | operation/comparison/worked-example article, one omitted drawing, cleaned prose, EPUB/PDF exports, 640×240 canvases with 18 px labels |

Reproducible probe: `docs/verification/artifacts/2026-09-14-blog-workflow-update/probe.py`. Its
outputs (article, result JSON, rendered PNGs, EPUB, PDF) sit beside it.

## Live pilots

Same scope for both sessions: OpenRouter, casual language, medium length, vision review on, LoRA
(`2106.09685v2`) and Mamba (`2312.00752v2`) from the retained 2026-09-13 matrix, isolated per-model
libraries, $10 ceiling each.

| Session | Code identity | Delivered | Planned figures | Accepted | Spend |
| --- | --- | --- | --- | --- | --- |
| Pilot 1 (pre-fix) | `2f14dcb0…` | 2/6 (gemini/LoRA, terra/Mamba) | 8 | 3 | $1.8738 |
| Pilot 2 (post-fix) | `0a3bffe7…` | 2/6 (gemini/LoRA, gemini/Mamba) | 9 | 5 | $3.1314 |

Figure completion with all planned figures as the denominator:

| Attempt | Pilot 1 cumulative | Pilot 2 cumulative |
| --- | --- | --- |
| 1 | 2 (25.0%) | 0 (0.0%) |
| 2 | 2 (25.0%) | 2 (22.2%) |
| 3 | 2 (25.0%) | 5 (55.6%) |
| 4 | 3 (37.5%) | 5 (55.6%) |

The target — usable figures within two or three attempts — held for 5 of 9 planned figures in the
post-fix session and for 2 of 8 before it. Delivery rate stayed 2 of 6, and the composition changed
between sessions, so no model ranking follows from two papers.

Delivered PDFs:

| Session | Model | Paper | Path |
| --- | --- | --- | --- |
| Pilot 1 | gemini-3.8-flash | LoRA | `docs/verification/artifacts/2026-09-14-blog-live-pilot/gemini-3.8-flash-LoRA-2106.09685v2.pdf` |
| Pilot 1 | gpt-terra | Mamba | `docs/verification/artifacts/2026-09-14-blog-live-pilot/gpt-terra-Mamba-2312.00752v2.pdf` |
| Pilot 2 | gemini-3.8-flash | LoRA | `docs/verification/artifacts/2026-09-14-blog-live-pilot-rerun/gemini-3.8-flash-LoRA-2106.09685v2.pdf` |
| Pilot 2 | gemini-3.8-flash | Mamba | `docs/verification/artifacts/2026-09-14-blog-live-pilot-rerun/gemini-3.8-flash-Mamba-2312.00752v2.pdf` |

Raw sessions with full records: `.scratch/blog-live-e2e/2026-09-14-blog-pilot/` and
`.scratch/blog-live-e2e/2026-09-14-blog-pilot-rerun/` (`results.json`, `events.jsonl`, `manifest.json`,
per-run `failure.json` / `candidate.json` / `reviews.json` / `agent-trace.jsonl`, orchestrator log).

## Defects found live and fixed

### 1. The review path exceeded the four-attempt ceiling

Pilot 1, `gpt-terra`/LoRA: `fig1` made **six** drawing requests. A review finding reset an accepted
figure to pending without checking the remaining budget, so findings after attempt 4 started a fifth
and sixth draw.

Fix in `papers/agent_overviews.py`: when a reviewed figure has `attempts >= MAX_FIGURE_ATTEMPTS`,
mark it omitted, keep the review finding as diagnostics, run the omission cleanup, and continue.
Regression test
`tests/test_agent_overviews.py::AgentTests.test_a_review_finding_on_an_exhausted_figure_omits_without_a_fifth_draw`
(fails pre-fix, passes post-fix). The post-fix pilot reproduced the path twice on gpt-terra; both
times it emitted exactly four drawing requests and then `omission_cleanup`. Session maximum: 4.

### 2. `\bm` broke Blog PDF export

Pilot 2, gemini/Mamba: the article passed review but PDF export failed with `Undefined control
sequence. \bm`. MathJax (reader) accepts `\bm`; pandoc's Unicode math setup cannot load the `bm`
package. Fix in `papers/exports.py`: `pdf_math_macros` rewrites `\bm` → `\boldsymbol` for the PDF
text only; saved articles are unchanged. Regression test
`tests/test_exports.py::BlogSparseFigureExportTests.test_bold_math_macros_export_after_normalization`.
The affected PDF was re-exported through the application after the fix.

## PDF and delivery pipeline (why LaTeX appears)

| Output | Pipeline | LaTeX |
| --- | --- | --- |
| Reader | app Markdown renderer + bundled MathJax | math only (permissive) |
| Blog EPUB | pandoc Markdown → HTML5 + MathML | no |
| Blog PDF | pandoc → JSON AST → `--pdf-engine=xelatex` | yes |
| Overview PDF | composed SVG → PNG → `rsvg-convert --format=pdf` | no |

The model authors Markdown; pandoc emits the LaTeX that XeLaTeX typesets. `$...$` / `$$...$$`
equations are the only model-authored LaTeX. Consequences: Blog PDF export requires MacTeX/XeLaTeX
on the machine (`Blog PDF export requires XeLaTeX. Install MacTeX, then restart LocalXiv.`), and the
macro surface can differ between the reader and the PDF — the `\bm` defect was exactly that seam.
A headless-WebKit print-to-PDF path using the existing `HTMLSnapshot.swift` renderer would remove
the MacTeX dependency and make reader/PDF macros identical; it is **not implemented** and awaits a
decision.

## Known limitations and open work

- Delivery rate is 2 of 6 in both sessions. gpt-luna and gpt-terra articles fail the bounded review
  on substantive findings (missing α/r scaling in the displayed forward pass, loss-direction wording,
  figure connectors implying activation merging, symbol-definition gaps). gpt-luna/Mamba also failed
  once at brief correction. These are model-convergence issues inside the agreed policy, not
  transport failures; the policy correctly withholds unreviewed prose.
- Sample size: two papers, three models, two sessions. Per-model differences are not established.
- The first pilot's `gemini/Mamba` failed on an over-length `plan.visual_focus` (1235 > 1200 chars)
  repeated after two corrections; the second session passed it. No prompt change was made for this.
- Vision review ran but its findings were not independently re-verified against the papers.
- No live provider failure, cancellation, or authentication error occurred in either session; those
  paths remain covered only by offline tests.
- Omission diagnostics expose attempt counts and issue codes but few details of the final drawing
  defects for malformed-response omissions.
- A Blog with several figures exposes only the first figure's editable SVG in the Share dialog.
- Acceptance is at the 640 px article width; smaller phone viewports are not claimed.
- The `\bm` fix covers the demonstrated macro; other reader-valid macros XeLaTeX lacks could still
  fail PDF export.
- Everything is uncommitted, per the plan's handoff constraints.

## How to reproduce

```sh
# Offline suites
LOCALXIV_HTML_RENDERER=/tmp/localxiv-blog-html-snapshot .venv/bin/python -m unittest \
  tests.test_reading tests.test_reading_bibliography tests.test_explanation tests.test_blog_figures \
  tests.test_agent_overviews tests.test_svg_figures tests.test_exports tests.test_app tests.test_overview_workflow
LOCALXIV_HTML_RENDERER=/tmp/localxiv-blog-html-snapshot .venv/bin/python -m unittest \
  tests.test_figure_readability tests.test_panel_authoring tests.test_panel_guides
node tests/test_app_ui.js
LOCALXIV_HTML_RENDERER=/tmp/localxiv-blog-html-snapshot .venv/bin/python -m unittest discover -s tests

# Offline end-to-end artifact probe
.venv/bin/python docs/verification/artifacts/2026-09-14-blog-workflow-update/probe.py

# Live pilot (spends money; requires the OpenRouter Keychain credential and an explicit ceiling)
.venv/bin/python .scratch/blog-live-e2e/2026-09-14-blog-pilot-rerun/scripts/run_blog_pilot.py status
```
