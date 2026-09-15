# Public code cleanup: architecture plan

Status: audit and plan only. README was rewritten separately; this plan does not include another README rewrite. No source cleanup has been applied.

**Goal:** make the code and its maintained documentation easier to understand without changing product behavior or delaying v0.0.11 for a broad rewrite.
**Approach:** clarify existing ownership, remove only proven dead code, and expand compressed Python into readable control flow. Separate mechanical cleanup from structural changes.
**Scope source:** the September 15 request for public-repository cleanup under the Zen of Python and PEP 8. The [two-defect plan](2026-09-15-blog-review-defects.md) owns functional Blog changes.

## Baseline and public visibility

Verified through GitHub on September 15: public `main` is `864db006982bedc337bff705e9da33a736418d6e`, and v0.0.10 is the latest listed public prerelease. The local branch is `akhil/model-authored-svg-overviews`, HEAD `35260f3`, with substantial uncommitted work. Recheck these identities before execution.

Review both the published tree and the complete candidate, including untracked files. The larger Overview coordinator, arrangement code, and new Blog lifecycle belong to the pending candidate, not public v0.0.10. `git diff` alone omits untracked files such as `papers/blog_figures.py`.

GitHub visitors see committed files and history; hiding a file with `.gitignore` does not remove tracked content. The release source archive uses `git archive` of the release commit. The app builder separately copies `app/`, `papers/`, and `native/`. Check all three inventories before deleting or moving a file.

## Audit findings and proposed treatment

Line counts describe this checkout, not quality thresholds.

| Area | Evidence and consequence | Treatment |
| --- | --- | --- |
| Blog coordinator | `papers/agent_overviews.py`, 1,478 lines, includes legacy figure admission, checkpoint I/O, model adapters, prompts, and a large nested `generate()` function. | Fix the two workflow defects first. Expand compressed code in touched functions. Defer module extraction until after release. |
| Overview coordinator | `papers/overview_workflow.py`, 1,556 lines, owns run storage, evidence, planning, dispatch, fitting, and completion. | Document stage ownership. Retain `arrangement.py`, `edge_align.py`, and `mixed_fit.py` as separate geometry modules. |
| Provider boundary | `papers/ai.py:Provider.complete()` repeats hostname parsing, compresses tool-schema branches, and ends with a broad exception translation. Shared `_sources` and `_evidence` helpers are imported across modules. | Expand branches first. Later separate evidence formatting from HTTP transport and narrow exception translation with regression evidence. Keep provider wire behavior exact. |
| Shared contracts | `papers/explanation.py` owns schemas and validation, but some tests import `candidate_digest` through `agent_overviews`; app/export tests import result-key constants from the Overview coordinator. | Migrate digest imports to their existing owner. Later move genuinely shared result-key constants into `explanation.py` without changing their values. |
| Test dependencies | `test_explanation`, `test_reading_bibliography`, `test_app`, and other suites import fixtures/builders from `test_agent_overviews` or `test_overview_workflow`. | Move shared builders into one small support module, updating all callers together. Do not create a fixture framework. |
| Converter | `native/host.py`, 5,083 lines, serves the extension and desktop worker. `papers/worker.py` replaces two host functions inside its isolated process. | Preserve this boundary before release. Explain the substitutions; defer any injected-function redesign until both callers have regression coverage. |
| Application service | `app/server.py`, 608 lines, deliberately owns one durable job worker, cancellation, and HTTP handlers. | Keep its current structure. Improve names and control-flow formatting only where needed. Do not add service/repository/controller layers. |
| Maintained developer docs | `docs/development.md` refers to deleted `papers/prototypes/parallel_scene.py`, describes one-scene Overview authoring alongside the newer panel workflow, and overstates uniform review behavior. | Rewrite current architecture descriptions from actual call paths. Preserve dated reports as history instead of retroactively editing their observations. |
| Deletion candidates | `_native_issue_messages()` and `_native_issues()` in `agent_overviews.py` have no production callers in the current search; their remaining external callers are tests. No runtime references to `papers/diagram-guides/` were found. | Recheck imports, dynamic loads, packaging, and attribution before removing these helpers/resources and tests that exercise only the retired path. Keep `_update_no_progress()`, which narrative planning still calls. |
| Active legacy guidance | Blog authoring still reads `papers/diagram-style.md`, which contains the old 960px-to-640px drawing advice. | Keep this file during behavior-preserving cleanup. Reconciling active prompt guidance is a separate behavioral change, outside the two-defect handoff. |
| Repository artifacts | Runtime sample, regression fixtures, vendored resources, historical verification data, and local pilot dumps have different purposes. `.venv` is a symlink to `.scratch/overview-agent-env` and is not matched by `.venv/`. | Use a root `.venv` ignore entry that covers the symlink. Classify artifacts by consumer and reproducibility value. Keep runtime sample assets and licenses. Do not blanket-delete evidence. |
| Release checks | `.github/workflows/macos-build.yml` names selected suites; the new `test_blog_figures`, `test_edge_align`, and `test_svg_figures` suites are absent from its explicit test lists. | Add applicable offline coverage to the correct pre-renderer or post-build step. Do not execute native fixture tests before a matching helper exists. |

## Rules for every cleanup patch

- Follow [PEP 20](https://peps.python.org/pep-0020/): explicit ownership, straightforward control flow, and a clear reason for every abstraction.
- Follow [PEP 8](https://peps.python.org/pep-0008/): four-space indentation, normal operator/comma spacing, one statement per line, grouped imports, descriptive `snake_case`, and two blank lines between top-level definitions. Use 79 columns for new or cleaned Python code and 72 for comments/docstrings. Preserve literal data when wrapping would change behavior.
- Prefer guard clauses to unnecessary nesting. Do not shorten code into one-line `if`, `try`, or semicolon chains. Do not replace a readable loop with a dense comprehension.
- Keep lazy imports that isolate optional AI dependencies or intentionally avoid cycles. Do not move every import to module scope to satisfy a stylistic preference.
- Preserve prompts byte-for-byte during mechanical cleanup. They are behavior, not comments. Keep SVG/SQL/LaTeX literals, serialized keys, digests, and protocol messages unchanged.
- Retain exception catches that provide transactional rollback or intentional fallback. Narrow a catch only after reproducing the expected error paths; never remove error handling for style.
- No new runtime dependencies, general plugin framework, dependency injection framework, schema migration, provider change, UI redesign, or mass file renaming.
- Never reformat `papers/vendor/`, generated sample assets, or historical verification records. PEP 8 applies to Python, not Swift, JavaScript, or embedded languages.
- Preserve the current working tree. Use explicit file staging when publication is later authorized; do not use blanket staging that includes environments or raw pilot records.

## Phase 1: bounded cleanup before v0.0.11

### 1. Record ownership and publication inventories

**Files:** update `docs/development.md`; create `docs/architecture.md` as the short maintained code map; update `.gitignore` only for confirmed local artifacts.

- [ ] Record public main, candidate HEAD, and the pre-existing modified/untracked paths. Classify candidate files as runtime code, tests/fixtures, current docs, historical evidence, or local-only output.
- [ ] Trace `Application.execute()` to `convert_import()`, `generate_overview()`, the two generation entry points, and `Library.save_generation()`. Document who owns jobs, retained files, request budgets, and atomic saves.
- [ ] Correct the stale prototype and single-scene descriptions. Distinguish automatic layout checks, model judgments, and independent content review. Link dated reports with their tested revision and limitations.
- [ ] Keep the offline sample and its provenance. Check all asset references before proposing any sample deletion. Keep regression fixtures and public failure evidence that support reproducible claims.
- [ ] Keep raw local libraries, credentials, environments, and duplicate pilot exports out of new commits. Inspect `.venv` with `ls -ld .venv` and `git check-ignore -v .venv`; a trailing-slash rule may not match a symlink. Do not rewrite Git history.
- [ ] Recheck the deletion candidates above with `rg`, including dynamic resource loading and release manifests. Remove only confirmed unused helpers/guides and their obsolete-only tests. Preserve attribution required by retained adaptations. Run `tests.test_agent_overviews` and `tests.test_panel_authoring` after a removal; if a live caller is found, retain the code and record that caller.

**Check:** every current code-map link resolves; `rg` finds no active documentation reference to the deleted prototype. Historical reports remain unchanged. Compare the proposed tracked-file inventory with the builder's copy rules and source archive inputs.

### 2. Make touched Python readable

**Files:** first `papers/ai.py` and the functions touched by the defect fixes in `papers/agent_overviews.py`; related tests only if imports need migration. Avoid a repository-wide formatting diff.

- [ ] Expand compound statements and one-line exception branches; use descriptive temporary names. Group imports without changing optional-dependency loading.
- [ ] Migrate tests importing `candidate_digest` through `agent_overviews` to `papers.explanation`, its existing owner. Search all production callers before removing any incidental re-export.
- [ ] Do not edit prompts or change error policy in this mechanical patch. Prove Python AST equivalence for formatting-only files and compare prompt constants before/after. An AST mismatch requires review, not automatic acceptance.

Example of the intended change, taken from the provider's tool-schema handling:

```python
# Before
function=item.get('function',{});parameters=function.get('parameters',{})

# After
function = item.get('function', {})
parameters = function.get('parameters', {})
```

**Check:** `tests.test_ai`, `tests.test_agent_overviews`, and `tests.test_explanation` pass. No model request format, emitted prompt, digest, or saved-generation key changes. This is a readability pass, not a claim of repository-wide PEP 8 compliance.

### 3. Make release checks exercise the candidate

**Files:** `.github/workflows/macos-build.yml`; `docs/development.md` test instructions.

- [ ] Add the Blog lifecycle/text-edit classes and geometry algorithm suites to offline checks. Keep `BlogFigureFixtureTests` in the native-renderer step after the app build.
- [ ] Run native fixture checks with the helper built from the release candidate. Use a bounded timeout and report renderer failure rather than silently skipping or treating it as a pass.
- [ ] Run the core app, library, conversion, UI, and saved-generation compatibility suites once on the frozen candidate. Do not include paid provider calls in cleanup verification.

```sh
.venv/bin/python -m unittest tests.test_ai tests.test_agent_overviews tests.test_explanation tests.test_blog_figures.LifecycleTests tests.test_blog_figures.TextEditTests tests.test_reading_bibliography tests.test_edge_align tests.test_svg_figures
.venv/bin/python -m unittest tests.test_app tests.test_library tests.test_conversion_recovery tests.test_pdf_fallback
node tests/test_app_ui.js
node tests/test_extension.js
git diff --check
```

**Stop:** after the two-defect plan and Phase 1 pass, freeze v0.0.11. Building, installing, pushing, tagging, and publishing remain separate release actions. README download/release wording must be checked when that release is actually published.

## Phase 2: structural cleanup after the release

Do not fold these tasks into the defect subagent's assignment or the release deadline.

### 4. Remove test-suite coupling

**Files:** create `tests/overview_support.py`; migrate shared builders/constants from `tests/test_agent_overviews.py` and `tests/test_overview_workflow.py`; update their importers found with `rg`.

- [ ] Move only shared data builders and scripted provider/render helpers, with unchanged behavior. The support module must not import a `test_*` module or eagerly load smolagents.
- [ ] Update every caller in the same patch, then delete the old definitions. Keep sample fixtures independent from production prompts.

**Check:** run each affected suite independently, then full discovery. There should be no imports from those test suites solely to obtain support data.

### 5. Make shared ownership explicit

**Files:** `papers/ai.py`, `papers/explanation.py`, `papers/overview_workflow.py`, `papers/agent_overviews.py`, and their callers. Create `papers/evidence_text.py` only if it removes the existing cross-module dependency on transport helpers.

- [ ] Move `_evidence` and `_sources` into that focused module as `format_evidence` and `validate_citations`. Keep formatting and citation behavior exact. Use a transport-independent validation exception there and preserve the current `ProviderError` translation at callers where required.
- [ ] Move `GENERATION_KEYS`, `PROVENANCE_KEYS`, and `FIGURE_ASSET_KEYS` to the existing contract module. Preserve values and saved formats. Migrate callers and remove old definitions in the same patch.
- [ ] Leave model routing in `ai.generate_overview()` unchanged. Do not add a generalized workflow registry.

**Check:** provider message snapshots, citation tests, schema/digest tests, app/export compatibility, and absence of newly introduced import cycles. Keep changes to errors separate from a formatting patch.

### 6. Extract only proven independent responsibilities

**Files:** `papers/agent_overviews.py`; candidate new `papers/overview_references.py`; matching tests and documentation.

- [ ] Trace `panel_workflow_figures()`, `reusable_overview_figures()`, `validate_candidate()`, and their helpers. Move the legacy-reference admission group together only if its dependencies can remain explicit and one-way. Preserve HTML/SVG admission and old saved-generation compatibility.
- [ ] Leave the nested Blog coordinator in place unless a second extraction removes captured mutable state without introducing a larger context object or a pass-through class. File length alone is not a reason to split it.
- [ ] Leave `native/host.py`, the worker substitutions, and the geometry algorithms unchanged in this phase. A converter split needs its own extension/desktop fidelity audit. A style cleanup must not become a conversion rewrite.

**Check:** legacy HTML, legacy SVG, current panel references, stale digest rejection, missing assets, and bibliography-filtered admission. Delete old definitions after migrating callers; do not leave duplicate implementations.

## Completion evidence

For each executed task, report the problem removed, files changed, exact checks run, and remaining uncertainty. Publishable code should explain its responsibilities through names and control flow; comments should explain constraints and deliberate tradeoffs. Preserve dated evidence, record new verification separately, and make no live-generation reliability claim from offline cleanup tests.
