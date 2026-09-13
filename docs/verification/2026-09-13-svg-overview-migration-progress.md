# Model-authored SVG Overview migration — progress handoff

Status: **local implementation verified; full live acceptance incomplete**

Updated: 2026-09-13 (Asia/Kolkata)

This is a handoff of work completed while implementing
`docs/superpowers/plans/2026-09-13-model-authored-svg-overviews.md`. It records
observed results, failed runs, and remaining gates. It does not claim release,
publication, or modification of the installed LocalXiv application.

## Repository state and boundaries

- Branch: `akhil/model-authored-svg-overviews`
- Starting and current commit: `864db006982bedc337bff705e9da33a736418d6e`
- The branch was created in the existing checkout because the plan depends on
  substantial uncommitted work already present there. No reset or broad cleanup
  was performed.
- The starting tree already contained tracked and untracked work in the app,
  reading pipeline, provider integration, tests, and documentation. The changes
  remain uncommitted and mixed in the same checkout; use the starting-state notes
  in `docs/verification/2026-09-13-svg-overview-migration.md` before attributing
  individual files to this migration.
- `.env` was not opened or copied. Provider secrets and private model reasoning
  were not written to repository fixtures or reports.
- `/Applications/LocalXiv.app` was used only as an installed Python runtime that
  could read existing Keychain credentials. The installed app was not changed.
- Nothing was sent to Kindle or another person. Nothing was committed, pushed,
  published, released, or installed.

## Production implementation completed

### One direct-SVG Overview path

- `papers/explanation.py` now defines a one-figure Overview envelope with fixed
  ID `fig1`, empty prose text, and model-authored `svg`. New Overview submissions
  reject `html` and `scene`; Blog retains its separate HTML contract.
- `papers/agent_overviews.py` now runs selection, narrative planning, SVG
  authoring, native rendering, evidence review, whole-figure repair, checkpoint
  persistence, and saved-generation reuse without importing a scene compiler.
- The active prompt revision is `smolagents-selective-svg-v3`. It states the
  explanatory depth, advises a roughly 912 by 600 first draft, distinguishes
  architecture/method/survey explanations, carries unresolved issues into
  repairs, and treats 600 visible SVG words as an extreme ceiling rather than a
  target.
- Blog preferences and legacy Blog authoring remain independent. New SVG
  references require an owned `.source.svg`; eligible old HTML/scene generations
  remain inert, readable compatibility data and do not require the deleted
  compiler.

### Supported SVG boundary and genuine source export

- `papers/html_figures.py` contains the `overview-svg-v1` profile, standalone SVG
  parsing and normalization, per-element/attribute validation, bounded path and
  affine-transform syntax, namespace/resource checks, local marker validation,
  visible-text extraction, and the 60,000-character, 500-element, 12,000-character
  attribute, source-font, viewBox, and 600-visible-word limits.
- Unsupported scripts, events, links, images, external resources, arbitrary CSS,
  foreign HTML, animation, filters, masks, clipping paths, DTDs, entity
  declarations, processing instructions, invalid numbers, malformed geometry,
  duplicate IDs, and unresolved/wrong-type marker references fail before WebKit.
- New accepted figures persist the exact normalized model source as
  `fig1.source.svg` alongside the complete-page HTML/SVG/PNG/PDF assets. The
  standalone source has local font/color defaults and remains text plus vector
  geometry rather than a raster image in an SVG wrapper.
- `papers/exports.py` resolves `svg_source` through the existing containment,
  existence, suffix, and symlink protections.
- `app/static/app.js` exposes the new source as **Download SVG** while preserving
  legacy HTML and Excalidraw source fallbacks.

### Native checks and repair evidence

- `papers/HTMLSnapshot.swift` now returns structured `issue_details`, complete
  page and diagram bounds, effective reading scale, transformed text sizes,
  text-overlap/out-of-bounds findings, and conservative stroke/arrow-marker
  extents. Its unused scene-only `--measure-text` mode was removed.
- `papers/agent_overviews.py` keeps native issues structured, preserves semantic
  issues across mechanical repair, ties approval to the rendered candidate
  digest, distinguishes provider truncation from geometry defects, retains the
  last valid draft on malformed replacement, and stops repeated non-progress or
  cycles without adding a production request ceiling.
- The native checker does not prove that every label is comfortably contained by
  a decorative box. Independent inspection found such a miss in the live Gemini
  Attention output described below. Model approval and zero native issues are
  therefore insufficient for visual acceptance.

### Obsolete production machinery removed

The following scene-authoring files were removed after callers migrated:

- `papers/overview_scene.py`
- `papers/overview-examples.json`
- `papers/prototypes/structured_overview.py`
- `tests/test_overview_scene.py`

This active-source search returns no matches:

```sh
rg -n 'overview_scene|SCENE_SCHEMA|overview-examples|STRUCTURED_AUTHORING|overview-scene|--measure-text' papers app tests tools
```

Remaining mentions are historical records, the superseded ADR, or migration-plan
text. `papers/prototypes/parallel_scene.py` is unrelated and was retained.

## Documentation completed

- Added `docs/adr/0002-model-authored-svg-overviews.md`.
- Marked ADR 0001 superseded without rewriting its historical decision.
- Updated current development and diagram guidance, including
  `docs/development.md`, `papers/diagram-style.md`, and
  `papers/diagram-guides/architecture.md`.
- Added supersession notices to older active plans while preserving their old
  results and terminology as historical evidence.
- The fuller migration report at
  `docs/verification/2026-09-13-svg-overview-migration.md` still needs its final
  implementation/test/live tables folded in from this handoff.

## Reference-image review

All three supplied images were inspected as untrusted visual references, not as
paper evidence or layouts to reproduce.

- The Attention reference uses a dominant title and lead, restrained semantic
  color, open connector routing, and a progression from a concrete operation to
  parallel heads to the full architecture.
- The uncertainty-family reference keeps parallel families distinct rather than
  inventing one algorithmic pipeline. It places short explanations beside each
  family and ends with a bounded synthesis.
- The PRO reference carries one concrete example through scoring, filtering, and
  interpretation; it defines quantities close to first use and places the
  baseline comparison beside the result.

The shared runtime guidance derived from them is limited to a clear reading
start, local explanations, whitespace and contrast, connectors through open
space, and a supported finding with its qualification. No reference coordinates,
panel count, aspect ratio, wording, or paper-type template was encoded.

## Direct regression artifacts

Three deliberately different synthetic fixtures exercise architecture, worked
method, and comparison layouts. They are labelled synthetic and make no paper
claims. Each has editable SVG source plus complete-page HTML, SVG, PNG, PDF, and
checks JSON under:

`docs/verification/artifacts/2026-09-13-svg-overviews/reader/overview-figures/`

| Fixture | Artifact directory | Page | Diagram | Smallest displayed label | Native issues |
| --- | --- | ---: | ---: | ---: | ---: |
| Architecture | `e20da24b6eb84bda9a2348a2a6f01da2` | 960 x 693 | 912 x 476.719 | 15.200 px | 0 |
| Method | `b9bc3584b03b4a7eb1428cc790088840` | 960 x 621 | 912 x 404.172 | 15.200 px | 0 |
| Comparison | `3d74893345d44ff99a05106569b75b79` | 960 x 662 | 912 x 445.625 | 15.200 px | 0 |

All use the existing 640/960 reading scale of two thirds, stay below the 960 px
page-height limit, and exceed the 14 px displayed-label floor. The complete pages
and standalone sources were opened and visually inspected after native checks;
an earlier fixture revision with visible spacing problems was corrected instead
of being accepted from metrics alone.

Representative local EPUBs and their logs are in
`docs/verification/artifacts/2026-09-13-svg-overviews/`:

- `architecture.epub` / `architecture.epubcheck.log`
- `method.epub` / `method.epubcheck.log`
- `comparison.epub` / `comparison.epubcheck.log`

Each EPUBCheck log reports 0 fatals, 0 errors, 0 warnings, and 0 infos.

## Local verification

### Baseline

Before migration, the required focused Python baseline passed outside the
restricted loopback sandbox: 87 tests, 1 pre-existing skip, 0 failures. The UI
JavaScript baseline also passed. The restricted run's only error was the sandbox
denying a loopback HTTP contract test.

### Current results

- Rebuilt `papers/html-snapshot` successfully with the Command Line Tools 15.4
  SDK and a writable module cache:

  ```sh
  xcrun swiftc \
    -sdk /Library/Developer/CommandLineTools/SDKs/MacOSX15.4.sdk \
    -module-cache-path /private/tmp/localxiv-swift-module-cache \
    -O papers/HTMLSnapshot.swift -o papers/html-snapshot
  ```

  The default SDK invocation first failed because the compiler and selected SDK
  versions did not match; sandboxed module-cache writes also failed. These were
  build-environment problems, not accepted native-test skips.

- Full Python suite with the rebuilt helper:

  ```sh
  LOCALXIV_HTML_RENDERER=/Users/silver/Developer/arxiv-paper-to-kindle/papers/html-snapshot \
    .scratch/overview-agent-env/bin/python3 -m unittest discover -s tests
  ```

  Result: **355 tests in 70.574 seconds; OK; 1 pre-existing skip**.

- Focused native module:

  ```sh
  LOCALXIV_HTML_RENDERER=/Users/silver/Developer/arxiv-paper-to-kindle/papers/html-snapshot \
    .scratch/overview-agent-env/bin/python3 -m unittest tests.test_figure_readability
  ```

  Result: **4 tests in 2.511 seconds; OK**. A preceding command named a nonexistent
  `NativeSVGReadabilityTests` class and produced a loader error; the module-level
  command above is the corrected product verification.

- `node tests/test_app_ui.js`: passed.
- `node tests/test_extension.js`: 63 tests passed, 0 failed, 0 skipped.
- `git diff --check`: passed.
- A focused integrated migration run before the full suite passed 103 tests with
  1 pre-existing skip.

Coverage added or migrated includes namespace handling; active content and
resource rejection; paths, transforms, markers, arrowhead bounds, tspans,
displayed sizes and page fit; exact 600/601 visible-word boundaries; atomic
repair and digest binding; persistent semantic issues; cycles, repeated lookup,
malformed responses and provider truncation; old scene/HTML/missing-source reuse;
safe `.source.svg` export; UI fallback behavior; and architecture/method/comparison
fixtures through the real native renderer.

> **Scratch cleanup (2026-09-13):** the `svg-overview-live-2026-09-13` run directory was
> deleted as superseded single-document scratch. The results below remain the record;
> the paths no longer resolve.

## Authorized live evaluation

The live runner is local and ignored under
`.scratch/svg-overview-live-2026-09-13/`. It uses fresh copies of retained papers,
the installed runtime only for Keychain ACL compatibility, source-repository
imports, the rebuilt native helper, a process-group wall deadline, and an HTTP
request counter. No secret values are printed.

### Frozen final matrix

- Prompt: `smolagents-selective-svg-v3`
- SVG profile: `overview-svg-v1`
- Vision: enabled
- Per-run diagnostic limits: 20 HTTP requests, 600 seconds
- Providers: Gemini `gemini-3.8-flash`; DeepSeek `deepseek-flash`
- Papers:
  - architecture: `1706.03762v7`, source digest
    `2e7a7d9ee2520d22eb23dae0cb148e167be02a30d6cb3f11b1c67723194339c6`
  - method: `2511.07694v1`, source digest
    `9c7541e76397b5a50c0f01378f42df045f8d8ec55692e4eaffbd0a21d1261a81`
  - survey/comparison: `2606.19868v1`, source digest
    `af1650f011dc455e3998c909d4c7a1b7ca29d96611a411b4641cca5725648d4b`
- Required runs: two independent generations for every provider/paper pair.

The frozen manifest is `.scratch/svg-overview-live-2026-09-13/manifest.json`.
Per-run summaries retain provider-reported prompt/completion/total usage; traces,
checkpoints, failures, rendered drafts, and reviews remain beside each paper copy.

### Pilot results that produced v3

| Revision | Provider / paper | Result | Requests | Time | Finding |
| --- | --- | --- | ---: | ---: | --- |
| v1 | Gemini / architecture | failed | 10/10 completed | 184.777 s | Portrait 640 x 760 SVG produced 10.2 px displayed text and stopped after non-progress. |
| v2 | Gemini / architecture | failed | 20/20 completed | 250.517 s | Reached local-valid renders and semantic review, but exhausted the ceiling with missing token-level behavior, missing bridges, and malformed/double-escaped repair submissions. |

The resulting v3 additions were global fit guidance, batched evidence reads,
explicit JSON/XML quoting guidance, and concrete Transformer-operation/bridge
requirements. Pilot failures are not counted as final-matrix successes.

### Frozen v3 results completed before this handoff

| Provider | Class / run | Workflow status | HTTP requests started / completed / failed | Time | Provider-reported total tokens | Observed outcome |
| --- | --- | --- | ---: | ---: | ---: | --- |
| Gemini | architecture / 1 | internally accepted; independently rejected | 10 / 10 / 0 | 111.051 s | 236,873 | Native checks returned no issue, but full-page inspection found encoder/decoder labels visibly overflowing and colliding. The figure also lacked the required concrete token example and explicit bridges between attention, heads, and architecture. Its cited BLEU, attention, and complexity statements were supported; visual/explanatory acceptance failed. |
| Gemini | architecture / 2 | failed | 20 / 20 / 0 | 340.308 s | 674,197 | Hit the diagnostic request ceiling. Its reviewer had caught reversed stack flow, cramped/truncated labels, missing token-level behavior, missing inter-level bridges, and an ambiguous encoder-to-decoder K/V connection. |
| Gemini | method / 1 | failed | 16 / 15 / 1 | 201.103 s | 442,255 | Provider HTTP 429. |
| Gemini | method / 2 | failed | 10 / 9 / 1 | 93.905 s | 164,131 | Provider HTTP 429. These two Gemini method runs overlapped; same-provider concurrency was stopped afterward, but the failures remain in the denominator. |
| Gemini | survey / 1 | failed | 1 / 0 / 1 | 1.030 s | 0 | Provider HTTP 429 after the earlier method runs. |
| Gemini | survey / 2 | failed | 1 / 0 / 1 | 1.025 s | 0 | Provider HTTP 429 after a cooldown. |
| DeepSeek | architecture / 1 | failed | 9 / 9 / 0 | 128.967 s | 126,076 | `plan.visual_focus` remained outside its 1-1200 character contract after two corrections. |
| DeepSeek | architecture / 2 | failed | 7 / 7 / 0 | 52.996 s | 79,423 | Same repeated `visual_focus` contract failure. |
| DeepSeek | method / 1 | failed | 14 / 14 / 0 | 540.265 s | 444,278 | Non-progress: the PRO formula never defined sorted retained probabilities, the summation bounds, or `p*_K`. |
| DeepSeek | method / 2 | failed | 14 / 14 / 0 | 350.402 s | 335,856 | Non-progress: the figure claimed the adaptive threshold beats fixed K without the paper's average/general qualification and isolated counterexamples. |

The token totals above are provider-reported usage summed from completed requests,
not a cost estimate.

### Interrupted/incomplete final cases

- DeepSeek survey run 1 reached request 17 and a second semantic review before the
  600-second supervisor session ended with exit 124. No `summary.json` was
  emitted, so it is **not accepted and not a completed matrix result**. Its latest
  checkpoint and two rejected reviews remain at:

  `.scratch/svg-overview-live-2026-09-13/final/deepseek/2606.19868v1/run-1/paper/reader/overview-figures/1001ff55a0354916b850964de4cce48e/`

  The latest review still found: TopK presented as a flat closed-QA winner rather
  than a slight verbalization-method AUROC edge; stage arrows implying a false
  pipeline; undefined uncertainty/confidence and discrimination/calibration
  terms; and overall-average VPD/SteerConf winners presented without the
  per-setting qualification.
- DeepSeek survey run 2 was not started.

### Live acceptance judgment

- First-attempt workflow acceptance: Gemini 1/6; DeepSeek 0/5 started cases.
- Independent acceptance: Gemini 0/6; DeepSeek 0/5 started cases.
- No provider completed all six required cases.
- The **full live acceptance gate is open**. Failed cases remain in the
  denominator. The interrupted DeepSeek survey run and unstarted run prevent a
  complete matrix even apart from the recorded failures.
- These results do not support claims of end-to-end reliability, speed, or cost
  improvement. They do show that local validation and persistent semantic review
  can preserve and surface defects rather than silently approve them.

## Exact remaining work

1. Fold this handoff into the final migration report and add direct links to the
   representative artifacts.
2. Decide whether to revise the live workflow. The recorded defects point to
   bounded plan-field normalization/feedback, smaller evidence context for
   survey papers, more reliable whole-figure repair, and stronger independent
   detection of text overflowing its intended container. Any prompt or code fix
   requires a new recorded revision and a new frozen final matrix; v3 successes
   cannot be mixed with later-revision results.
3. If v3 is retained unchanged, finish DeepSeek survey run 2 only for diagnostic
   completeness; it cannot make the already-failed v3 acceptance matrix pass.
4. Re-run the focused/full verification after any new code change. The current
   local implementation is verified, but the strict plan must continue to be
   reported as incomplete until every provider's six live cases are independently
   accepted.
5. Review the mixed dirty worktree before any future commit. Preserve unrelated
   user changes and `.env`; do not publish, release, or modify the installed app
   without separate authority.

## Current status in one line

**The direct-SVG production boundary, native checks, repair persistence, source
download, backward compatibility, cleanup, documentation, and local export/test
coverage are implemented and verified; the model-authored live workflow does not
yet meet the plan's strict DeepSeek/Gemini acceptance gate.**
