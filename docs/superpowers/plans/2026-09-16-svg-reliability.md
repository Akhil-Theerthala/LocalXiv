# SVG reliability and explanatory continuity

## Authority and goal
The user authorized a revamp to reduce unnecessary failures and latency without returning to slow, fragile whole-document SVG authoring, then requested continuous subagent-driven execution. Keep parallel panel drawing and holistic planning. This plan is the scoped implementation specification; earlier workflow specs describe the baseline.

## Global Constraints
- Work only in this isolated worktree. Leave the original checkout's reader-layout.css modification untouched.
- No paid provider calls, credentials access, installs to the user's app, pushes, or merges. Local native renderer builds and offline tests are permitted. Commit only task-owned files.
- Preserve safe-SVG validation, evidence-reference validation, exact scientific values and notation, cancellation, previous-generation availability, and exported artifact compatibility.
- No unbounded retry loop, no whole-document model repair, no new dependency. Existing successful requests must not need extra provider calls.
- Text fallback remains available and explicitly recorded as reduced output. Shape counts cannot certify explanatory quality and must not become a new hard failure gate.
- Write regression tests first and record failing then passing commands. Use the real renderer for the final offline integration tests; scripted provider output does not establish live-model quality or latency.

## Task 1: Preserve the best explanation through planning recovery
Files: papers/explanation.py, papers/overview_workflow.py, tests/test_explanation.py, tests/test_overview_workflow.py.

Fix narrative recovery to retain a valid visual_focus (including valid ordered string lists) instead of always replacing it with the contribution. Malformed optional relationships (including non-list containers) must not crash recovery. Retain valid source-linked relationships; preserve resource protection; provenance must truthfully identify whether focus was preserved or derived.

Repair panel planning within the existing draft/clarify/simplify request allocation. When draft and clarification are invalid, the last structural diagnostics currently disappear before simplification. Carry the latest candidate and its exact validation messages into correction. Separate a structural correction from semantic simplification: the correction prompt must preserve all valid panels, content, handoffs and shared facts, changing only reported defects, rather than instructing dependency removal. A malformed clarification must still preserve a valid issue-free draft. Never silently remove mismatched exact_text, unknown source references, or conflicting science to make validation pass. Align documented prompt field limits with validators to prevent avoidable round trips (notably shared fact text length).

Tests: valid focus survives optional relationship rejection; missing focus still derives a fallback; malformed relationships cannot crash; resource limit still enforced; invalid exact_text is corrected through bounded planner responses while original panel order/content/handoffs survive; latest diagnostics reach correction; unchanged semantic issues still require reduction; no extra calls on ordinary success.

## Task 2: Make independently drawn panels carry a coherent visual story
Files: papers/explanation.py, papers/overview_workflow.py, papers/panel_authoring.py, papers/panel-guides/authoring.md, relevant tests.

Reuse Blog's optional layout_intent for Overview briefs, validation and assignment projection. It describes the visual inference (same object before/after, contrasting paths, operations on concrete examples), not rigid coordinates. Existing saved briefs without it must remain valid. Include a short shared story context derived from the accepted narrative for every Overview author via an optional argument to panel_assignments; no extra provider call. Preserve Blog's existing contract. Relevant drawing evidence remains planner-owned; no unrestricted source retrieval by workers.

Update Overview planning and authoring guidance to prioritize the central mechanism/comparison, use the same example and semantic encodings across panels, distinguish relationships shown by geometry from sentences in boxes, and retain secondary findings/qualifications without forcing extra panels. Construction families choose reference examples, not mandatory templates. Keep exact text protection and the existing SVG safety subset. No shape-count rejection. Bump prompt revision and avoid unsupported claims about drawing reasoning quality; do not silently raise provider cost by changing reasoning policy.

Tests: layout intent and shared story reach actual author request payload; old plans still validate/project unchanged when no new context is supplied; Blog requests unchanged in structure; shared context survives a local repair; no added provider requests.

## Task 3: Verify integrated recovery and document limits
Files: tests/test_overview_workflow.py and/or a focused integration test; docs/verification/2026-09-16-svg-reliability.md; current workflow docs as needed.

Build/use the native renderer locally. Add an offline end-to-end regression exercising real planning, parallel panel requests, native checks, composition and exports with only the provider scripted: inject a recoverable planner contract defect, then a drawing defect repaired locally; assert completed image assets, retained relationships/shared story, no unnecessary text fallback, bounded calls, valid checks, truthful provenance. Reuse existing integration harness where possible. Preserve failure/cancellation tests and test fallback remains usable. Run relevant Python suites and any directly affected UI/export tests. Record exact commands, totals/skips and evidence limitations. Do not claim generated images are scientifically reviewed merely because checks pass.

Finish with independent whole-branch review. Do not merge or push.
