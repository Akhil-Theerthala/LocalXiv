# Overview workflow rebuild

Status: proposed design for implementation review. This document records the current conversation; it does not authorize implementation or live provider calls.

## Purpose and authority

Build one illustrated overview for a novice who knows the paper's relevant basics and wants an intuitive understanding before reading it. Concentrate on the central contribution. Include secondary material only when it helps explain that contribution.

This design replaces the Overview requirements in `docs/workflow_plan.md`, `docs/workflow_plan_r2.md`, ADRs 0001–0003, and the amended `2026-09-13-model-authored-svg-overviews.md` plan where they conflict. Those files remain historical evidence. The checkpoint `progress_summary_1309.md` describes an earlier, unfinished implementation.

## Agreed requirements

- The overview is one image with 1–7 numbered panels.
- Image dimensions follow content; there is no fixed page size, aspect ratio, or whole-image word budget.
- Panels read left to right, then top to bottom.
- Planning owns scientific meaning, shared examples, notation, and panel handoffs.
- Each panel author receives a complete drawing assignment and builds only that panel.
- Panel authors receive relevant SVG examples and concise construction references, without the paper, planning history, or other panel briefs.
- The first panel-plan refinement clarifies; the second simplifies and removes troublesome dependencies before drawing proceeds.
- Panel generation runs concurrently; completion order never changes reading order.
- The intended structure is 1–2 narrative calls, 1–3 panel-plan calls, and one creation call plus one repair call where needed per panel.
- Those call counts describe the normal workflow, not a universal request ceiling.
- Acceptance centres on the rendered images and their fidelity to the approved drawing assignments.
- Regeneration keeps the saved overview available until a complete replacement is ready.
- Reading, conversion, Blog generation, and existing saved artifacts remain usable.
- No new runtime dependency or generic agent framework is required.

## Rebuild boundary

Replace the visual Overview coordinator, panel contracts/prompts, and fixed-page arrangement. Build the replacement beside the current implementation, route production to it once its complete path passes checks, then delete the superseded visual branches in the same implementation series. There will be one production Overview path after cutover.

Retain `Provider.complete`, local evidence orientation/retrieval, library ownership, job cancellation, export selection, and the WebKit renderer. Modify these only at the seams needed for parallel requests, free-sized SVG rendering, and the existing output contract. `agent_overviews.py` continues to support Blog; its presence is not a reason to retain obsolete Overview logic.

Do not reset the current checkout to HEAD. It contains uncommitted work across reading, UI, provider handling, and exports. Snapshot relevant source changes and inventory untracked files before implementation; leave `.env`, credentials, historical `.scratch` evidence, the installed app, and unrelated work untouched.

## Ownership and flow

1. Build the source orientation locally and retrieve evidence through the existing validated functions. Retain the current evidence-selection capability; record selection requests separately from narrative requests.
2. Narrative planning identifies the central contribution, mechanism, finding, and qualification for the target reader. A second call may correct the narrative. The narrative remains linked to retained evidence.
3. Panel planning assigns that narrative to 1–7 detailed briefs. Its first refinement checks and clarifies the initial briefs. Its final refinement simplifies unresolved connections by making the affected panels self-contained. Review and revision happen within these planner passes; there is no separate repeating draft-review agent.
4. Freeze the resulting assignments. The application resolves each brief's inherited context and shared facts before dispatch.
5. Make independent panel requests in parallel. Render each returned SVG locally. Supply an affected panel with its existing SVG and measured image defects for its repair request. A rendered PNG may accompany repair when the configured provider supports image inputs.
6. Compose completed panels in planned order, render the complete image, check placement, and persist the existing generation result shape.

The final check examines drawing and composition. It does not reopen planning or launch a scientific narrative rewrite. Runtime geometry checks cannot certify scientific correctness; source-grounded planning and independent artifact inspection have separate records.

## Panel contract

Use plain JSON objects and small validation functions. Retain the existing narrative claim fields where compatible. Replace nested groups, bridge routing, shape quotas, and passage-union coverage with the following Overview-specific contract.

`PanelPlan` contains `title`, `paper_connection`, `caption`, `shared_facts`, and ordered `panels`.

Each shared fact has a stable key, display text, source passage IDs, and a kind of `source` or `illustrative`. Illustrative numbers are explicitly identified and used consistently; they are not reported as paper results.

Each `PanelBrief` contains:

| Field | Meaning |
| --- | --- |
| `id`, `title` | Stable safe ID and visible panel title |
| `purpose` | The one idea this panel explains |
| `covers` | Narrative claim keys assigned to this panel |
| `entry_from` | IDs of earlier panels whose endpoint it builds on; empty for independent panels |
| `exit_state` | What this panel establishes for the reader |
| `shared_fact_ids` | Canonical facts, example values, or notation used here |
| `content` | Ordered items containing `text`, `passages`, and `kind` |
| `construction` | Reference family: `flow`, `mapping`, `comparison`, `calculation`, or `chart` |

Validate count, safe unique IDs, earlier-only dependencies, known narrative claim keys, known passage/fact IDs, and required content. Every narrative claim selected for the overview has a panel owner. A citation copied to unrelated metadata does not satisfy claim ownership. Scientific support and explanatory completeness are planner-review responsibilities, not claims made by structural validation.

Build a `PanelAssignment` with `id`, `title`, `purpose`, `entry_context`, `content`, `exit_state`, `shared_facts`, and `construction`. `entry_context` is resolved from the referenced earlier `exit_state` values. Resolve canonical shared facts into their exact display content. Remove evidence IDs and source text from the author-facing projection while retaining their mapping in provenance.

Panel authors may choose wording, geometry, and visual composition within that assignment. Exact names, equations, numerical values, and required connections remain fixed. They cannot request narrative changes or revise another panel.

## Authoring guide

Keep one short common drawing guide, a concise SVG construction reference, and small complete SVG examples. Load the relevant example into the request; do not ask the panel author to browse. The user's three examples are preserved in [reference inputs](2026-09-13-panel-svg-reference-inputs.md).

Adapt the examples into self-contained SVG with explicit font and paint attributes. Preserve their teaching patterns: separate opposing flows, map multiple facts into fewer objects, and track an object across a change of state. Add a small calculation example and a labelled chart example so networking layouts do not become the default for every paper.

The construction reference covers `svg`/`viewBox`, basic shapes, `line`/`polyline`/`path`, text alignment and explicit `tspan` lines, groups, and fill/stroke/type attributes. Credit the [W3Schools SVG reference](https://www.w3schools.com/graphics/svg_reference.asp); write concise original notes and verify the examples in LocalXiv's renderer. Include only constructs the production profile supports.

Prompt order: drawing assignment, relevant complete example, applicable construction notes, output contract. Keep instructions positive and specific. Remove whole-paper narrative advice, page fitting, repeated ratio rules, and unrelated stages from panel prompts.

## Rendering and arrangement

The application owns the HTML wrapper and shared visual style. The model returns only `{"panel_id": "p1", "svg": "<svg ...>...</svg>"}`. Use direct structured provider requests, without a tool-calling conversation for drawing a single panel.

Native measurements include transformed paths, strokes, marker extents, text/tspans, and actual font metrics. Check each drawing against its own SVG canvas. The existing Python attribute scan is not an authoritative boundary check. Safe-SVG validation remains a trust-boundary check; attribute choices are not aesthetic acceptance criteria.

Use a shared body size of 18 drawing units as the initial implementation default, with a 14-unit minimum for secondary labels at 100% viewing scale. The example suite must establish whether that default reads well. The viewer's fit-to-window zoom does not change acceptance. Superscripts need contextual measurement rather than a blanket rejection of every smaller run.

Retain each panel's internal geometry. Use a simple row arrangement with at most three panels per row; choose among one, two, and three columns using measured unused row area, with fewer rows as a tie-break. This is an application default, not a constraint sent to the model. Do not reorder panels or scale them down to satisfy a page aspect target. Apply only uniform type-normalising scale where necessary, preserving title/body hierarchy.

Use small gutters and a number band per panel. Start with no nested group frames and no duplicated panel headings. Titles are inside the authored panel. Store every panel rectangle in composed-image coordinates for click-to-focus.

Extend the renderer with explicit panel and composed-image modes. Width and height come from the content, replacing the 960px wrapper, the 640px reading-scale check, and the 6000px height rejection for this path. Preserve the legacy rendering mode for Blog and saved formats. Resource protection is based on finite geometry, bounded input bytes/elements, and measured raster allocation, not an editorial page budget. Handle a large export with tiled rasterisation at the same scale rather than shrinking its text; record tested size coverage and practical resource limits.

## Parallel execution

Use the standard-library `ThreadPoolExecutor` for model requests. Start with a maximum of three in-flight panel requests, bounded by the actual panel count. This is a conservative application default, not a claimed provider limit. Keep native WebKit rendering sequential initially; network authoring still overlaps.

The coordinator owns result order, progress, cancellation, usage aggregation, and shared artifact writes. Request workers receive immutable assignments and return response/usage/diagnostics. They never share mutable conversation history or write the common trace. Deliver callbacks and usage persistence from the coordinator, including completed paid requests whose candidate is rejected.

Process completed requests as they arrive; schedule a panel's repair without waiting for unrelated panels. A geometry failure does not cancel successful sibling panels. On user cancellation, stop scheduling, cancel unstarted futures, drain already-running requests within existing timeouts, and prevent publication. Retain request accounting and diagnostics without allowing late results to replace a cancelled job.

## Recovery and proposed implementation defaults

The agreed semantic recovery is clarify, then simplify. The simplification pass removes unresolved dependencies and gives each affected panel sufficient source-supported content to stand alone. It is not another polish loop.

Recommended recovery after a panel's drawing repair still fails: render the approved panel content in a simple application-owned text/equation panel with measured wrapping and the same typography. Preserve its title, necessary facts, and place in the story. Mark this as simplified in provenance. This is a proposed implementation default for plan approval; the user has not separately selected its visual design.

For malformed planner output after simplification, construct independent briefs from the last structurally valid, source-linked narrative. Use its existing claims, without inventing connections or new findings. When no usable narrative exists, retain the original paper and any saved overview, show a plain recovery message, and allow retry. Authentication loss, unavailable services, missing source text, and renderer crashes cannot honestly be turned into a successful new overview. Keep those distinct from recoverable planning/drawing failures.

## Calls and review records

For N panels and R repaired panels, the intended core count is `narrative + panel_planning + N + R`. At N=7 and R=7, the upper normal allocation is 19, not 14. Selection, transport retries, and any explicitly added image-review calls are recorded separately. The new default path adds no model call solely to announce completion or conduct a whole-image scientific review.

Keep structured local checks, planner review decisions, and human/live evaluation results distinct. Do not fabricate the old `reviews[-1].approved` scientific-review record to make Blog reuse accept a new generation. New Overview artifacts may be used as drawing references only when their source identity, assets, accepted planner record, and local checks match; Blog still grounds its claims in the paper and runs its own review. Legacy reviewed artifacts retain their existing handling.

## Viewing and persistence

Extend the existing figure dialog. Initially fit the image to the viewport; click a panel to focus it; support pan/zoom, keyboard controls, Escape, and a visible Fit image button. Keep text descriptions and keyboard-accessible panel targets. Old figures without rectangle metadata retain whole-image enlargement.

Preserve generation keys `text`, `explanation`, `plan`, `figures`, `evidence`, and `provenance`. Preserve figure asset keys `html`, `svg`, `png`, `pdf`, `svg_source` and compatibility with export selectors. Add composed dimensions and ordered panel rectangles. PNG/PDF and editable SVG depict the same complete overview. Update EPUB packaging only where it assumes fixed dimensions.

Store the accepted panel plan, per-panel source/render/checks, arrangement, composed source/image, call trace, and recovery decisions under the existing per-run artifact directory. Publish a complete generation atomically through the existing library save boundary. Never remove the previous saved generation merely because a replacement started.

## Completion evidence

Validate 1, 4, and 7 panels; mixed aspect ratios; long labels; equations; branching connections; transformed paths; repair; simplification; out-of-order completion; cancellation; and unchanged prior-generation availability. Demonstrate a composed image larger than 960px in each dimension without reduced text size.

Human inspection of rendered outputs must establish that a novice can follow the central contribution and that the exact brief content survived drawing. Native geometry checks and reference SVGs alone do not establish this. Use the already-retained architecture, methodology, and survey/comparison papers for a later authorized live pilot. Record complete delivered images, simplified panels, scientific defects, requests, and elapsed time. No success claim rests solely on model self-review or a green mocked suite.

Implementation follows [the rebuild plan](../plans/2026-09-13-overview-workflow-rebuild.md).
