# Workflow revision 2: geometry sizing and Blog preferences

> **Superseded for Overview execution:** the [Overview workflow rebuild]
> (superpowers/specs/2026-09-13-overview-workflow-rebuild-design.md) removes the page-fit geometry
> this plan introduced. Blog preferences and measured-repair principles remain active.

> **Superseded for Overview geometry:** The model-authored SVG migration in
> [the 2026-09-13 plan](superpowers/plans/2026-09-13-model-authored-svg-overviews.md) removes the
> scene compiler. Blog preferences and the general measured-repair principles remain active.

> **Implementation status:** The original advisory did not authorize geometry execution. The subsequent request to implement this plan did. The geometry work is complete, with local verification recorded in [the implementation report](verification/2026-09-12-workflow-r2-geometry.md). No live provider calls were made.

**Goal:** Fit explanatory content by measuring and resizing its containers before asking the model to rewrite it.

**Architecture:** Keep the existing structured scene and renderer. Measure nested content from the inside out, allocate available width from the outside in, and use the same dimensions for measurement and drawing. Return a content/composition repair only when the measured scene cannot fit without changing meaning or violating readability.

**Tech stack:** Existing Python scene compiler, native WebKit text measurements, SVG output, and unittest. No new layout framework, model stage, dependency, or settings screen.

**Spec:** This advisory supplements [workflow_plan.md](workflow_plan.md), especially its geometry and repair requirements, and preserves [the accepted authoring boundary](adr/0001-structured-visual-authoring.md). The user's clarification in this conversation supersedes the earlier blanket objection to production output limits: provider-specific output-token allowances and request timeouts are intentional. Preserve them; do not replace them with a single allowance or remove them as part of this work.

## Scope and status

| Work | Status |
| --- | --- |
| Pass Blog writing style and requested length through all generation stages | Implemented in this revision; scripted verification recorded below |
| Replace the Blog planning instruction to fit within Overview scope | Implemented in this revision |
| Correct nested geometry measurement and resize containers | Implemented and locally verified |
| Make geometry failures measurable and stable across repairs | Implemented and locally verified |
| Change provider limits, run live comparisons, install, publish, or release | Outside this request |

Provider-specific allowances accommodate the user's expectations about inference speed and token use across providers. They are configuration choices, not measured guarantees about an entire class of models. Diagnostic trial budgets remain separate. This revision does not change `papers/ai.py` or approve another trial.

## Constraints

- Preserve all authored text, numeric values, citations, node IDs, grouping, connector endpoints, arrow direction, and reading order during local resizing. Resizing must not turn a comparison into a computation or change which output feeds which input.
- Models continue to choose content, panel kinds, rows, relative weights, and relationships. Code owns physical dimensions and routing. Do not ask models for coordinates or replace the scene contract with HTML/SVG authoring.
- Preserve the 960 px complete Overview height limit and the 14 px minimum label size at 640 px display width. Do not fit by shrinking text, scaling a tall SVG until text becomes too small, cropping, or hiding overflow.
- Preserve the 180 authored-word limit, the separate 12/30/45-word title/connection/caption limits, 1–4 rows, 1–3 panels per row, at most 7 panels, and weights of 0.5–2. Geometry repair cannot excuse invalid content.
- Keep words, decimals, signs, dimensions, and identifiers intact. Preserve the existing legal CJK wrapping behavior. Count authored words before wrapping.
- Do not automatically move panels between rows or change orientation of a connected flow. That would change model-authored composition. If the existing arrangement is infeasible, report the measured constraint and let the author choose a new arrangement.
- Preserve source filtering, local conversion, saved artifacts, cancellation, and exact-candidate review. A failed layout must not replace an approved generation.
- Use saved local failures first. No paid request is needed to implement or verify these geometry changes.
- Preserve the existing working-tree changes and `.env`. No reset, broad staging, commit, installation, or publication belongs to this advisory.

## What the saved failures establish

The current renderer already grows panel widths from estimated minimums and distributes remaining row space using weights. The problem is incomplete measurement inside those panels, not universally fixed-size boxes.

| Component | Current behavior | Recorded consequence | Required behavior |
| --- | --- | --- | --- |
| Flow steps | Equal subdivision; panel minimum uses the largest individual bar label without fully accounting for subdivision among bars | `The` needed 37.9 px but received 24.9 px; a later `0.1` needed 30.6 px but received 25.7 px | Measure the complete bar group, include its containing step padding, and allocate sufficient step width |
| Lane connector | Fixed 110-unit gutter; label receives half the gutter minus 10, then the wrapper reserves another 3 units | `Memory` needed 79.4 px but received 42 px | Grow the gutter from the measured label and reserve its height in the connected blocks |
| Complete scene | Width and height failures appear in sequence | DeepSeek changed from 1,328 px tall to an overwide row, then 1,281 px tall and finally 1,087 px tall | Measure all row requirements before drawing and report independent feasible-to-measure failures together |

The final Gemini draft is 1,173 px tall; the final DeepSeek draft is 1,087 px tall. Correcting the local width calculations does not prove either complete draft will meet 960 px. A scene can still contain too much content for its chosen arrangement.

Evidence is retained in:

- [Gemini repair context](../.scratch/structured-live-2026-09-12/selective-implementation-final-attention/gemini/1706.03762v7/reader/overview-figures/133c47da4a8d4f4c9dffb43f00100b25/generation_context.json)
- [DeepSeek repair context](../.scratch/structured-live-2026-09-12/selective-implementation-final-attention/deepseek/1706.03762v7/reader/overview-figures/eae99b98da4649b2b29b73abfa1de07e/generation_context.json)
- [Recorded outcomes](verification/2026-09-12-overview-efficiency-implementation.md)

## File responsibilities

| File | Responsibility |
| --- | --- |
| `papers/overview_scene.py` | Correct minimum widths, allocate nested space, measure heights, and draw from those measurements |
| `tests/test_overview_scene.py` | Minimal geometry regressions and content-preservation assertions |
| `tests/fixtures/overview_efficiency.json` | Sanitized saved failure inputs with provenance, only if existing fixtures cannot express them |
| `papers/agent_overviews.py` | Preserve structured layout measurements in issues; distinguish mechanical improvement from mere edits |
| `tests/test_agent_overviews.py` | Prove avoidable layout problems need no provider repair; verify genuine repeated failures stop |
| `papers/html_figures.py`, `papers/HTMLSnapshot.swift` | Existing complete-page and export gates; modify only for a demonstrated defect unavailable to the Python compiler |

Keep `compose(scene) -> str`, `validate_scene(scene)`, `_measure(scene)`, and `visible_scene_fields(scene)` compatible. Add only small internal helpers needed to share calculations. Do not create a parallel renderer or persistent layout cache.

## Task 1: Freeze narrow, reproducible geometry failures

- [x] Extract the flow-bar and connector cases from the saved drafts. Retain source paths and original failure messages, not provider credentials or reasoning. Do not overwrite the live traces.
- [x] Add a focused flow case with three labeled bars inside one of two steps. Include both word labels and decimal labels, and a two-panel row with spare space in its neighbour. Verify that a feasible row can render without changing the scene.
- [x] Add a lane case with the legal two-word label `Memory K,V`, for both connector directions and unequal source/target step heights. Verify label clearance and unchanged endpoints.
- [x] Add an infeasible row whose true minimum widths exceed available space. It must report the required and available width rather than shrink or truncate.

Use this assertion pattern with the existing `measure_fixture` helper in `tests/test_agent_overviews.py`. Build the scene from the retained case, then test the complete compiler rather than an unrelated helper:

```python
before = copy.deepcopy(scene)
with patch('papers.overview_scene._measure', side_effect=measure_fixture):
    svg = overview_scene.compose(scene)
self.assertEqual(before, scene)
labels = [''.join(node.itertext()) for node in ET.fromstring(svg).iter()
          if node.tag.split('}')[-1] == 'text']
self.assertIn('0.1', labels)
self.assertIn('512', labels)  # Include this dimension in the fixture.
```

Scripted font metrics establish arithmetic and preservation. They do not establish real-font fit. Native checks in Task 5 must use the saved wording and actual font measurements.

## Task 2: Measure nested components before allocating rows

- [x] Use `_measure` once per scene. Measure each field at the font size and weight actually used to draw it. The current blanket 26 px measurement must not substitute for the distinct label/title/value styles.
- [x] Include padding, inter-item gaps, and `_wrap_lines`' 3-unit safety allowance in minimum widths. Use the same constants in measuring and drawing so the two paths cannot disagree.
- [x] Correct equal-width bar-group sizing. With `n` bars and longest indivisible label width `L`, the current `bars` drawing function needs at least `n * (L + 10 + 3)` units. A flow step containing that group also needs its 20 units of horizontal padding. Measure these requirements together, not the longest label alone.
- [x] For flow steps, compute each step's minimum from its title, text, and complete bar group. Give each step its own minimum before distributing spare space; update drawing and arrow positions to use those widths. Preserve step order and gap clearance.
- [x] Check other nested components using the same reasoning: concept groups subdivide width by group count; concept input/output pairs split their width; parallel branches already have dedicated width logic. Correct any measurement/drawing disagreement exposed by those cases without redesigning the components.

Retain the existing row allocation rule. For nested flow steps, use the same arithmetic with equal weights:

```python
remaining = available - sum(minimums)
if remaining < 0:
    # Report a structured width failure with the affected row/component path.
    raise ValueError('layout_fit: minimum content width exceeds available width')
total_weight = sum(weights)
widths = [minimum + remaining * weight / total_weight
          for minimum, weight in zip(minimums, weights)]
```

`available` excludes all gaps and outer padding. `minimums` includes the content's own padding. Row weights come from the authored panel weights; flow-step weights are all 1. Calculate these values in one helper or one shared local block, then reuse them for dry measurement and drawing. Keep the negative-width error measured and path-specific as specified in Task 4; the snippet shows allocation, not the final diagnostic format.

## Task 3: Grow connector space and then compute container heights

- [x] For lane links, derive a minimum label width from the longest unbreakable token plus the wrapper safety allowance. Under the existing routing formula, start with `label_width = max(45, minimum_token_width + 3)` and `gutter = max(110, 2 * (label_width + 10))`. Reuse the chosen gutter during lane-width allocation and drawing.
- [x] After allocating lane widths, wrap the connector label to measure its height. Increase the common lane block height if needed to contain the label and maintain clearance from the arrow route. Verify the actual existing vertical placement formula; widening the gutter alone does not prove vertical clearance.
- [x] Measure each flow step and lane block at its allocated width, then grow its height from wrapped lines and padding. Use the largest required height where a row of boxes shares a baseline. Recompute connector endpoints from final box bounds.
- [x] Use the same measured dimensions in dry layout and final drawing. Do not recompute with different subdivisions or styling after accepting the fit.
- [x] Keep panel arrangement unchanged. When larger minima cannot coexist inside the authored row, request recomposition with concrete widths. Do not squeeze neighbours below their own minima or silently change text to abbreviations.

This deliberately avoids a general constraint solver, repeated browser searches, and automatic topology changes. Start with correct minimum sizing; consider a more elaborate width/height optimizer only if saved post-fix artifacts demonstrate a remaining need.

## Task 4: Make genuine layout failures useful and stable

- [x] Measure independent rows before serializing the SVG so one narrow row does not hide another. Where width is infeasible, report width and skip height claims that require a feasible allocation.
- [x] Preserve structured details through `compile_candidate` and `render_candidate`. A width failure should identify `code: layout_fit`, `constraint: min_width`, the precise row/component path, `actual` required width, and `limit` available width. A complete-page height failure uses `constraint: max_height`, the figure path, measured height, and limit 960. Keep messages readable, but do not require downstream code to parse their numbers.
- [x] Build issue identity from constraint and affected path, not changing measurements or prose. Keep independent constraints distinct while a height change from 1,281 to 1,087 remains the same issue.
- [x] For mechanical issues, count progress only when the measured violation decreases or that issue is resolved. A title edit or additional evidence must not reset a width/height/word-budget counter. Preserve separate semantic-review handling, where changed explanatory content or evidence can matter.
- [x] Maintain the planned two-correction no-progress rule. Test unchanged and worsening heights with changed captions, improving heights, and alternating width/height failures. An unavailable measurement must not be treated as proof the old issue was resolved.
- [x] Present the failure as a space constraint, for example: `Row 1 needs 1,062 px; 800 px is available. Recompose this row or shorten the identified labels. Text has not been removed or shrunk.` Avoid demanding content edits for a width the local renderer can supply.

Use explicit field values in progress tests. The following sequence must increment the same issue counter despite changed candidate text:

```python
old = {'id': 'height-fig1', 'code': 'layout_fit', 'constraint': 'max_height',
       'path': 'figures[0]', 'actual': 1100, 'limit': 960}
new = dict(old, actual=1150)
counters = _update_no_progress(
    [old], [new], {'height-fig1': 0},
    before_candidate={'figures': [{'caption': 'First wording'}]},
    after_candidate={'figures': [{'caption': 'Different wording'}]},
)
self.assertEqual(1, counters['height-fig1'])
```

Do not implement a general repair-history framework. Correct the existing issue records and counter logic at their current boundary.

## Task 5: Verify complete artifacts and stop at the evidence boundary

- [x] Run the focused arithmetic/content regressions with scripted measurements. Verify source immutability and unchanged labels, values, topology, and citations.
- [x] Pass a feasible saved candidate through the real agent loop using scripted selection, plan, author, and approval responses. Use the real corrected compiler. Prove that it reaches review without requesting a model geometry repair. Record native rendering separately if it is mocked in this test.
- [x] Render the three existing D/E/F reference scenes and the saved minimal failures with native measurements. Inspect each complete PNG at 640 px display width, its PDF, and its local Kindle export. Check whitespace and arrow clearance as well as overlap, clipping, minimum label size, and complete-page height.
- [x] Replay the complete failed Gemini and DeepSeek candidates without modifying their authored scenes. Record which failures disappear and which remain. A genuine remaining page-height failure is a failed artifact, even if the nested sizing fix works.
- [x] Record compiler/schema revision, source candidate identity, before/after native measurements, unchanged authored content, remaining issues, and model calls avoided by the scripted path. Do not infer real latency or token savings from scripted responses.

The existing AI environment is `.scratch/overview-agent-env/bin/python`. A future geometry implementation should begin with:

```sh
.scratch/overview-agent-env/bin/python -m unittest tests.test_overview_scene.SceneTests tests.test_agent_overviews.AgentTests
```

Native checks need the existing `HTMLSnapshot.swift` executable and a functioning macOS WebKit environment. Use the repository's native test setup and retain platform errors separately from layout defects. No provider API is needed for the saved-candidate replays or local exports. Sending an export is outside this work.

Acceptance requires that feasible content fits through correct local sizing, infeasible content produces measured actionable issues, and the safety/meaning constraints above remain intact. It does not require weakening the gates to make every old draft pass.

## Blog preference fix completed with this advisory

`papers/agent_overviews.py` now builds the Blog preference instruction once from `LANGUAGES[language]` and `LENGTHS[length]`, then includes it in the shared instructions for selection, narrative planning, authoring, repair, and review. It also replaces the shared planning demand to fit within Overview scope with the requested output mode and length. Existing preference values and word-budget validation remain in place.

New Blog generations use prompt revision `smolagents-selective-blog-v2`; their saved context and final provenance agree. Existing saved generations are not rewritten.

The added regression exercises the real agent loop with scripted provider responses, including a rejected review followed by Blog repair and approval. It checks every outgoing stage for casual/short, semi-formal/medium, and formal/large preferences. It failed before the fix because preferences were absent and passed afterward. Rendering and font measurement are mocked in this check; it makes no live provider calls and does not establish prose quality or native layout acceptance.

```sh
.scratch/overview-agent-env/bin/python -m unittest \
  tests.test_agent_overviews.AgentTests.test_blog_preferences_reach_every_stage_and_survive_repair \
  tests.test_agent_overviews.AgentTests.test_both_modes_complete_after_structured_review
```

Recorded result: both targeted tests passed, including three preference subcases. The geometry implementation and its complete verification results are recorded in [the implementation report](verification/2026-09-12-workflow-r2-geometry.md).
