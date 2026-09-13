# Model-authored SVG Overview migration

Status: **local implementation verified; live acceptance in progress**

Updated: 2026-09-13 (Asia/Kolkata)

This report records the migration described by
`docs/superpowers/plans/2026-09-13-model-authored-svg-overviews.md`. It does not
claim release, publication, or modification of the installed LocalXiv
application. Historical reports keep their own revisions and results; this
document does not rewrite them.

The earlier progress handoff at
`docs/verification/2026-09-13-svg-overview-migration-progress.md` is folded into
this report and remains as the historical record of the first implementation
round.

## 1. Repository state and boundaries

- Branch: `akhil/model-authored-svg-overviews`
- Starting commit: `864db006982bedc337bff705e9da33a736418d6e`
- The branch was created inside the existing checkout because the migration
  depends on substantial uncommitted work already present there. No reset,
  stash, or repository-wide cleanup was performed.
- The starting tree already contained tracked and untracked work in the
  application, reading pipeline, provider integration, tests, and
  documentation. Those changes remain uncommitted and mixed in the same
  checkout; they are preserved rather than attributed wholesale to this
  migration.
- `.env` was neither opened nor copied. Provider secrets and private model
  reasoning were not written to repository fixtures or reports.
- `/Applications/LocalXiv.app` was used only as an installed Python runtime that
  can read existing Keychain credentials. The installed app was not modified.
- Nothing was sent to Kindle or another person. Nothing was pushed, published,
  released, or installed.
- Live model calls were authorized by the user on 2026-09-13 for DeepSeek and
  Gemini Flash, including the retained test papers and their generated figures.
  No other provider was called.
- `main` was never modified.

## 2. Production path

### 2.1 One direct-SVG authoring path

- `papers/explanation.py` defines a one-figure Overview envelope with the fixed
  ID `fig1`, empty prose `text`, and a model-authored `svg` string. New Overview
  submissions reject `html` and `scene`; Blog keeps its separate HTML contract.
- `papers/agent_overviews.py` runs selection, narrative planning, SVG
  authoring, native rendering, evidence review, whole-figure repair, checkpoint
  persistence, and saved-generation reuse without importing a scene compiler.
  The active prompt revision is recorded in `PROMPT_REVISION` and in every
  generation's provenance.
- The authoring prompt states the explanatory depth, the first-draft canvas, the
  reading-scale arithmetic, and the per-paper-type guidance. It also carries a
  teaching-quality section derived from the supplied references: one running
  example, progressive zoom, a consistent visual vocabulary, values named with
  their tensor or condition, a takeaway sentence per step, and a closing finding
  with its qualification.
- Blog preferences and legacy Blog authoring remain independent.

### 2.2 Supported SVG boundary

`papers/html_figures.py` implements the `overview-svg-v1` profile:

- One SVG root, standard namespace or namespace-free input, normalized
  consistently.
- `g`, `rect`, `circle`, `ellipse`, `line`, `polyline`, `polygon`, `path`,
  `text`, `tspan`, `title`, `desc`, `defs`, and `marker` only.
- Per-element attribute validation with finite-number, paint, path-command, and
  affine-transform checks. Bounded token consumption, arity, arc flags, and
  radii are verified.
- Duplicate-ID, unresolved-reference, wrong-marker-type, unknown-namespace,
  DTD/entity/processing-instruction, and resource-bearing-value rejection.
- Scripts, events, animation, foreign HTML, images, external fonts and
  stylesheets, arbitrary CSS, links, `use`, filters, masks, and clipping paths
  are rejected before WebKit sees the document.
- Bounds: 60,000 Unicode characters, 500 elements, 12,000 characters per
  attribute, viewBox width 100–2000 and height 80–2000, source font size 16–80,
  and `SVG_MAX_VISIBLE_WORDS = 600` over visible SVG text only.
- Normalization materializes the standalone font family, root font size, and
  fill so the digest describes the displayed figure.

`normalize_svg` and `svg_visible_text` are the two shared entry points used by
authoring, validation, word accounting, review, and export. The display contract is
ratio-based rather than pixel-based. The application owns the physical size of an
authored figure: the standalone SVG is fitted into the space the heading and caption
leave, so the model may compose near-square or portrait figures (height/width 0.75–1.33)
without pushing the page past its limit, and it keeps `font_size/viewBox_width` at or
above `0.035 × height/width`. The native checks measure the physical result, so no
particular canvas size is required or rewarded.

### 2.3 Native measurement

`papers/HTMLSnapshot.swift` measures the real WebKit page:

- Complete-page height, diagram viewport, available diagram height, reading
  scale, and every text run with its effective transform.
- The compact overview page fits an authored figure into the space left by the
  heading and caption, so the page-height limit holds structurally while the model
  keeps freedom over shape. The reading-scale policy itself is unchanged; a fitted
  figure that becomes too small still fails the displayed-text floor, and the
  failure reports the diagram height that was actually available.
- Displayed font sizes against the 14 px floor, text-to-text collisions, text
  and drawing overflow beyond the page and SVG viewport, and stroke/marker
  extents.
- A **container-overflow check**: the smallest plausible rectangle whose
  interior contains a label's centre must contain the whole label. This was
  added after independent inspection found encoder/decoder labels escaping their
  boxes in a candidate that the earlier measurement accepted.
- Small-text findings now name the required source font size, and an aggregated
  `layout_fit` diagnostic explains a uniform small-text cascade once as a
  composition problem (viewBox width, reading scale, required scale factor)
  instead of repeating dozens of per-label messages.
- Container-overflow findings state the label's width in user units, the
  container element path and width, and the number of units to add or the wrap
  needed. Repair prompts order the unresolved geometry issues by severity so the
  widest overflow is visible first.
- Page-height failures report the actual available diagram height.
- Tightly stacked lines of text are not treated as collisions; only substantial
  overlap in both axes is an error, and uncertain shape/connector intersections
  remain visual-review findings.

### 2.4 Repair, stopping, and progress

- Repairs receive the accepted narrative, the exact current SVG, the current
  candidate digest, the unresolved issues with measured actual/limit values, the
  last repair decisions, and only the passages the accepted plan and figure
  cite. The rendered candidate is attached when the provider supports vision.
- A validation or native-render failure keeps every unresolved semantic finding
  active, so the next repair receives semantics and geometry together instead of
  losing the review verdict to a geometry regression. Shell-metadata failures
  name the exact field, measured count, and limit (for example
  `figures[0].caption has 54 words; the limit is 45`), and a visible passage ID
  reports its exact location.
- Figure repair replaces the complete figure atomically and preserves the
  accepted narrative unless an explicit narrative revision is validated.
- Semantic review issues stay active across mechanical repairs. Approval binds
  to the digest of the exact rendered candidate.
- The two-corrections-without-progress stop rule is preserved, including
  figure-level matching so renaming a label cannot reset a failure.
- Provider truncation (`finish_reason=length`) is classified at
  `Provider.complete` and never enters the geometry-repair path.
- No global production request ceiling was added. Substantive repairs can
  continue beyond ten requests.

### 2.5 Persistence, source download, and old data

- New accepted figures persist the reviewed normalized source as
  `fig1.source.svg` next to the complete-page HTML, compatibility SVG, PNG, and
  PDF assets.
- `papers/exports.py` resolves `svg_source` through the existing containment,
  existence, suffix, and symlink protections (`extension="svg"` with an explicit
  field, so the metadata key and suffix are not confused).
- `app/static/app.js` labels the source control **Download SVG** and preserves
  the legacy HTML and Excalidraw fallbacks for older generations.
- Old scene and HTML generations are read from their stored assets. Scene
  metadata is inert; eligible Blog reference reuse validates the stored source
  format, document identity, retained passages, reading revision, and approval
  without importing the deleted compiler.
- Migration is lazy and read-compatible: no library rewriting, no deleted
  generations, no cache clearing.

### 2.6 Removed obsolete machinery

- `papers/overview_scene.py`
- `papers/overview-examples.json`
- `papers/prototypes/structured_overview.py`
- `tests/test_overview_scene.py`
- The scene-only `--measure-text` native mode.

This active-source search returns no matches:

```sh
rg -n 'overview_scene|SCENE_SCHEMA|overview-examples|STRUCTURED_AUTHORING|overview-scene|--measure-text' papers app tests tools
```

Remaining mentions are historical reports, the superseded ADR, or plan text.
`papers/prototypes/parallel_scene.py` is unrelated and was retained.

## 3. Preserved behavior

- Reading, bibliography filtering, selective evidence retrieval, and local
  import/conversion without AI credentials are unchanged. `evidence_document`
  removes reference-list content before any model call; measured on the live
  papers, the Transformer source dropped 40 of 124 passages and the survey
  dropped 88 of 208, with no reference headings or numbered citation entries
  left in the model-facing passages or source map.
- Blog language and length preferences reach every Blog stage, including repair
  and review. Blog can use an accepted Overview as a reference but must adapt
  its own HTML figure.
- Existing safe path handling, provider credential handling, signed reasoning
  history, and source-as-untrusted-data rules are unchanged.
- Complete-page PNG, PDF, compatibility SVG, and local Kindle/EPUB exports are
  retained.

One focused provider change was made for the live deadline: for DeepSeek only,
authoring and repair requests send the documented `thinking: disabled` toggle
(`https://api-docs.deepseek.com/guides/thinking_mode/`) because the default
high-effort reasoning spent 30k+ reasoning tokens per figure request and pushed
complete runs past the diagnostic wall clock. The toggle is scoped by hostname,
preserved for review, and covered by a request-serialization test. It is not a
reasoning-history or credential change.

One further local normalization was added after a DeepSeek run stalled on it:
`font-family` values composed only of local sans-serif families (`Arial`,
`Helvetica`, `Helvetica Neue`, `sans-serif`, `system-ui`, `Liberation Sans`,
`Nimbus Sans`) are accepted and canonicalised to `Arial, sans-serif`; any other
family is still rejected. This preserves the profile's no-external-font rule
while removing a spelling trap that consumed a run.

## 4. Reference-image notes

Three supplied images were inspected as untrusted visual references, not as
paper evidence or layouts to reproduce.

- `codex-clipboard-6df391a9-47d5-4d18-9c86-d9000965b3e8.png`: a multi-level
  architecture explanation. Useful traits: title hierarchy, restrained semantic
  colour, short explanations beside mechanisms, generous whitespace, clear
  arrows, and a progression from a concrete operation to the whole architecture.
- `codex-clipboard-e15186b7-12ba-41d3-8ea1-8b86cfd5f2c9.png`: a survey or
  comparison composition. It separates model signals, method families, and
  downstream use without pretending the methods form one pipeline, annotates
  each family locally, and closes with the synthesis and its limit.
- `codex-clipboard-15f55eef-f6dc-44f5-b092-913d2a18a603.png`: a worked method.
  It carries one example through scoring, filtering, and interpretation, defines
  quantities near first use, labels discarded information, and places the
  baseline comparison beside the result.

The shared guidance derived from them is deliberately general: a clear reading
start, explanations beside their objects, whitespace and contrast, connectors
through open space, and a supported finding with its qualification. No
reference coordinates, panel counts, aspect ratios, wording, or paper-type
templates were encoded.

## 5. Direct regression fixtures

Three deliberately different synthetic fixtures exercise architecture, worked
method, and comparison layouts. They are labelled synthetic and make no paper
claims. Each has editable SVG source plus complete-page HTML, SVG, PNG, PDF, and
checks JSON under
`docs/verification/artifacts/2026-09-13-svg-overviews/reader/overview-figures/`.

| Fixture | Artifact directory | Page | Smallest displayed label | Native issues |
| --- | --- | ---: | ---: | ---: |
| Architecture | `e20da24b6eb84bda9a2348a2a6f01da2` | 960 x 693 | 15.200 px | 0 |
| Method | `b9bc3584b03b4a7eb1428cc790088840` | 960 x 621 | 15.200 px | 0 |
| Comparison | `3d74893345d44ff99a05106569b75b79` | 960 x 662 | 15.200 px | 0 |

The comparison and method fixtures were tightened after the new
container-overflow check found labels escaping their boxes; the current
revisions pass with no native issue.

Representative local EPUBs and their logs:

- `docs/verification/artifacts/2026-09-13-svg-overviews/architecture.epub`
- `docs/verification/artifacts/2026-09-13-svg-overviews/method.epub`
- `docs/verification/artifacts/2026-09-13-svg-overviews/comparison.epub`

Each EPUBCheck log reports 0 fatals, 0 errors, 0 warnings, and 0 infos.

## 6. Local verification

Baseline before migration: 87 focused tests passed outside the restricted
loopback sandbox, 1 pre-existing skip, 0 failures; `node tests/test_app_ui.js`
passed.

Current state (prompt revision `smolagents-selective-svg-v6`):

```sh
xcrun swiftc -sdk /Library/Developer/CommandLineTools/SDKs/MacOSX15.4.sdk \
  -module-cache-path /private/tmp/localxiv-swift-module-cache \
  -O papers/HTMLSnapshot.swift -o papers/html-snapshot
LOCALXIV_HTML_RENDERER="$PWD/papers/html-snapshot" \
  .scratch/overview-agent-env/bin/python -m unittest discover -s tests
```

Result: **360 tests, OK, 1 pre-existing skip** (the Keychain smoke test). The
default-SDK build fails on this machine because compiler and SDK versions differ;
the Command Line Tools 15.4 SDK above is the working invocation. A sandboxed
module cache also fails, which is a build-environment limitation rather than a
skipped product test.

JavaScript checks:

```sh
node tests/test_app_ui.js          # passed
node tests/test_extension.js       # 63 passed, 0 failed, 0 skipped
git diff --check                   # passed
```

Coverage added or migrated includes namespace handling; active-content and
resource rejection; paths, transforms, markers and arrowhead bounds; tspans;
displayed sizes, container overflow and page fit; the aggregated small-text
composition diagnostic; exact 600/601 visible-word boundaries; atomic repair and
digest binding; persistent semantic issues; cycles, repeated lookup, malformed
responses and provider truncation; DeepSeek thinking-toggle serialization; old
scene/HTML/missing-source reuse; safe `.source.svg` export; UI fallback
behavior; and architecture/method/comparison fixtures through the real native
renderer.

## 7. Live evaluation

### 7.1 Runner

The live runner lives under `.scratch/svg-overview-live-v4/` (ignored). It uses
fresh copies of retained papers, the installed runtime only for Keychain ACL
compatibility, source-repository imports, the rebuilt native helper, a
process-group wall deadline, an HTTP request counter, and a provider retry with
backoff for 429/5xx responses. No secret values are printed. Cases run
sequentially with a per-provider cooldown.

Each run is bounded by the plan's diagnostic ceiling: 20 HTTP model requests and
600 seconds per generation. These limits bound the experiment only; they are not
written into production settings.

### 7.2 Frozen v3 matrix (historical)

Frozen inputs: prompt `smolagents-selective-svg-v3`, profile `overview-svg-v1`,
vision enabled, Gemini `gemini-3.8-flash`, DeepSeek `deepseek-flash`, papers
`1706.03762v7` (architecture), `2511.07694v1` (method), `2606.19868v1`
(survey/comparison), two runs per provider and paper.

| Provider | Class / run | Requests | Time | Outcome |
| --- | --- | ---: | ---: | --- |
| Gemini | architecture / 1 | 10 | 111.1 s | Internally accepted, independently rejected: labels overflowing and colliding; missing token-level example and bridges. |
| Gemini | architecture / 2 | 20 | 340.3 s | Request ceiling; reviewer had caught reversed stack flow, cramped labels, missing bridges. |
| Gemini | method / 1 | 16 | 201.1 s | Provider HTTP 429. |
| Gemini | method / 2 | 10 | 93.9 s | Provider HTTP 429. |
| Gemini | survey / 1 | 1 | 1.0 s | Provider HTTP 429. |
| Gemini | survey / 2 | 1 | 1.0 s | Provider HTTP 429. |
| DeepSeek | architecture / 1 | 9 | 129.0 s | `plan.visual_focus` outside its 1–1200 character contract after two corrections. |
| DeepSeek | architecture / 2 | 7 | 53.0 s | Same repeated plan-contract failure. |
| DeepSeek | method / 1 | 14 | 540.3 s | Non-progress on undefined probabilities and summation bounds. |
| DeepSeek | method / 2 | 14 | 350.4 s | Non-progress on a claim missing the paper's qualification. |
| DeepSeek | survey / 1 | 17 | 600 s deadline | Interrupted; no summary. Latest review still found a false flat comparison, stage arrows implying a pipeline, and undefined terms. |
| DeepSeek | survey / 2 | — | — | Not started. |

First-attempt workflow acceptance was Gemini 1/6 and DeepSeek 0/5 started
cases; independent acceptance was Gemini 0/6 and DeepSeek 0/5. The v3 matrix
does not pass and remains in the record.

### 7.3 v4–v5 pilots and fixes

Pilots on the architecture paper produced these recorded defects, each of which
was answered with a bounded local change rather than a model instruction alone:

| Finding | Response |
| --- | --- |
| Native checks accepted a figure whose encoder/decoder labels escaped their boxes. | Added the container-overflow check; verified against the accepted-bad artifact (4 labels flagged) and the three fixtures (clean). |
| Tightly stacked lines were reported as collisions; a run stopped on an unfixable overlap. | Overlap now requires substantial overlap in both axes; a regression test covers stacked heading/support lines. |
| Per-label "text too small" messages repeated dozens of times without an actionable size. | Each finding now names the required source font size; a `layout_fit` diagnostic explains a uniform cascade once with the viewBox width, reading scale, and required scale factor. |
| The model authored a 1400 x 900 viewBox and 21-unit labels, shrinking every label below the floor. | The fit guidance now states the reading-scale arithmetic explicitly and ends the authoring prompt with a pre-submission arithmetic check. |
| DeepSeek exceeded its plan-text contract twice. | Validation now reports the actual character count and the required reduction; DeepSeek passed the plan stage in later pilots. |
| Repair requests carried the full evidence set and re-attached paper figures. | Repairs receive only the plan and figure passages and the current rendered candidate, downscaled to a bounded payload. |
| DeepSeek spent 30k+ reasoning tokens per figure request (120–150 s each) and hit the 600 s wall. | Official-documentation `thinking: disabled` toggle for DeepSeek authoring and repair, with a request-serialization test; review keeps thinking. |

Pilot outcomes were mixed and are not counted as acceptance: one Gemini run
passed internal review (10 requests, 119 s), while others failed on a
too-dense composition, a label collision, or the wall clock. Each failure
produced a concrete local fix above.

### 7.4 Frozen v6 matrix

Frozen inputs are recorded in `.scratch/svg-overview-live-v4/manifest.json`:
prompt revision `smolagents-selective-svg-v6`, profile `overview-svg-v1`, vision
enabled, request limit 20, wall limit 600 s, the same three papers with their
source digests, and two runs per provider and paper.

<!-- v6 matrix results -->

## 8. Independent visual acceptance

Each generated artifact is inspected independently of the authoring model:
locally by opening the complete page at the reading size and enlargement, and
with the authorized Gemini Flash vision model as a second description where
useful. The authoring model's own approval is never treated as sufficient; the
v3 record already contains a case where it approved a figure with visibly
overflowing labels.

<!-- independent acceptance results -->

## 9. Documentation and decisions

- Added `docs/adr/0002-model-authored-svg-overviews.md` and marked ADR 0001
  superseded without rewriting its history.
- Updated `docs/development.md`, `papers/diagram-style.md`,
  `papers/diagram-guides/architecture.md`, `README.md`, and `CONTEXT.md` to
  describe the SVG production path.
- Added supersession notices to older active plans while preserving their
  results and terminology as historical evidence.

## 10. Remaining gates

Implementation status is **local implementation verified**. The strict
completion requirements of the plan remain open until:

1. Every provider in the frozen v6 matrix passes all six of its runs with
   independent factual and visual acceptance.
2. The representative artifacts are inspected and linked from this report.

<!-- remaining gates results -->
### Modular wiring status (applied)

The panel pipeline is wired into `generate()` and the orchestration tests were migrated: the visual
happy path is now selection, narrative, draft, draft review, one panel per leaf, review, and the
repair branch re-authors only the panels that own the issues. 376 tests pass (1 skip).
`PROMPT_REVISION` is `smolagents-panel-svg-v1`; the live manifest records the modular architecture's
own 30-request ceiling and the composed-page label measurement the native checker now performs.

Retired tests and the coverage that replaced them:

| Retired | Kept by |
| --- | --- |
| `test_author_can_handoff_a_narrative_defect_before_drawing` | `test_blog_can_explicitly_revise_narrative_before_and_after_authoring` (Blog only; the visual path returns to the draft, not to a handoff) |
| `test_render_geometry_failure_keeps_the_semantic_issue_for_the_next_repair` | `test_geometry_failure_does_not_erase_an_active_semantic_issue` |
| `test_structural_issue_skips_review_and_repairs_saved_candidate` | `test_malformed_panel_receives_feedback_inside_its_own_stage` and `test_alternating_layout_failures_stop_in_the_agent_loop` (native failures still skip review) |
| `test_mismatched_author_plan_digest_gets_one_focused_correction` | `test_mismatched_draft_plan_digest_gets_one_focused_correction` |
| `test_figure_repair_is_atomic_and_review_binds_each_digest` | `test_metadata_repair_is_reviewed_as_a_new_digest` |

Digest binding, candidate cycles, provider truncation and progress-based stopping are all still
covered, against the panel protocol instead of the retired whole-figure repair.

### Live evidence, modular pipeline

Five live runs used the frozen credentials and the 30-request ceiling. All five stopped without an
accepted figure, and every failure names the panel and the measurement that failed.

| Case | Requests | Time | Stopped on |
| --- | --- | --- | --- |
| `gemini/1706.03762v7/run-1` | 30 | 280 s | request ceiling while correcting panels |
| `gemini/2606.19868v1/run-1` | 6 | 54 s | draft coverage: `missing p00001, p00019, p00048, ...` |
| `deepseek/1706.03762v7/run-1` | 6 | 138 s | draft coverage: `missing p00016, p00054, p00064` |
| `gemini/2511.07694v1/run-1` (first) | 7 | 34 s | draft coverage: `missing p00001, p00042` |
| `gemini/2511.07694v1/run-1` (final) | 30 | 300 s | panel stage returned prose instead of a submission |

Six defects were found by these runs. Five are fixed with tests:

1. `compose_figure` could compose past the platform's 2000-unit viewBox limit and reported only
   `SVG needs viewBox="0 0 width height"`. The unit scale now respects the viewBox and source
   font-size limits, and a canvas with no valid scale fails as "cannot be composed at a readable
   label size".
2. `svg_visible_text` validated panels without their shared-marker allowance, so the first repair
   round crashed on any panel that referenced `url(#arrow)`.
3. A caption issue re-triggered the metadata repair after a native failure and resubmitted identical
   content, stopping the run as `previously rejected`. Repairs are re-armed only after the review has
   run again, and only metadata paths reach the metadata repair.
4. The draft's coverage requirement carried no measurable distance, so a draft that covered more of
   the accepted evidence still stopped after two corrections. The issue now reports the uncovered
   count and the draft prompt states the rule.
5. The panel label ratio was prompted but never enforced. The panel stage now rejects a panel whose
   smallest label is below the ratio floor for its canvas shape and returns the canvas width or font
   size that would pass.

The sixth is open: an unreadable arrangement is detected, but the panel budget that would prevent it
is not yet communicated (below).

### What the composed page looks like

`gemini/2511.07694v1/run-1` is the only run that reached composition, and it kept its artifacts:

* `.scratch/svg-overview-live-v4/modular/gemini/2511.07694v1/run-1/paper/reader/overview-figures/45818ad0efa545bc8adb912921631d15/composed.svg`
* the same directory's `composed-page.png` and `composed-page.html`, rendered with the project renderer
* `panels/{seq_prob,topk_select,pro_bound,eval_auroc}.svg`, the four accepted model-authored panels
* `arrangement.json`, `failure.json`, `agent-trace.jsonl`, and `plan.json`

The page reached exactly 960 px with all 71 labels measuring 6.8-9.5 px against the 14 px floor. The
arrangement predicted 6.7 px for the same canvas, so prediction and measurement agree: a canvas about
64 label widths wide cannot show 14 px labels in a 640 px column, and nothing told the panel authors
that budget. The panels themselves are strong: a running example (sample N=3 candidates, softmax
token probabilities, the NLL factorisation, ranking 0.82/0.12/0.01), a real bar chart with the
alpha = 0.10 cutoff, the PRO lower bound with its K=1 and K>1 cases, and an AUROC table
(0.739 / 0.715 / 0.705).

Remaining gaps, in order of value:

1. **Page budget in label units.** The draft must allocate a width and height budget per panel from
   the panel count (a 640 px column supports about 45 label widths) and state it in the panel brief,
   with the guard enforcing it. Every live failure except the protocol stall comes from this.
2. **Panel content must stay inside its viewBox.** The composed page shows one panel's text drawn over
   the bridge label below it, because content outside a panel's viewBox is not clipped.
3. **Bridges must avoid heading bands.** One bridge crosses the lower group's heading.
4. **One prose-only turn in a panel stage should be retried with a nudge** instead of failing the run.


No claim of a 99.99% success rate, speed improvement, or cost saving is made
from this small matrix.
