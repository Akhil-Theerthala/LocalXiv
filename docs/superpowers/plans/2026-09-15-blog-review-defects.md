# Two Blog review defects: implementation plan

Status: implementation is present in the September 15 local checkpoint. The audit passed 48 focused tests and reproduced two remaining cases. Work is parked; see the [checkpoint record](../../verification/2026-09-15-blog-checkpoint.md). The checklist below preserves the original acceptance criteria and does not certify completion.

**Goal:** retain unresolved findings and prevent repairs to the wrong figure.
**Approach:** amend the existing Blog review loop and its scripted tests. Keep the current coordinator and budgets.
**Scope source:** the September 15 audit discussion and the [agreed Blog design](../specs/2026-09-14-blog-workflow-update-design.md).

## Subagent instructions

Use this as the task prompt when implementation is authorized:

> Fix only the two defects below. Read this plan and the cited code before editing. Use Ponytail, the Zen of Python, and PEP 8. Work in `papers/agent_overviews.py` and `tests/test_agent_overviews.py`. You may change `papers/explanation.py` and `tests/test_explanation.py` only if the Blog review response needs a schema change; preserve the existing shared/Overview contract. Do not create a generic review framework or split modules. Do not delegate further. Preserve all pre-existing changes. If another defect is found, record it in the handoff without fixing it. Do not change authoring/style prompts, source selection, provider/model settings, figure geometry, drawing budgets, prose budgets, exports, UI, README, packaging, or architecture. Review-prompt and response-validation changes necessary for these two defects are in scope. No paid calls, installs, commits, pushes, or releases. Stop when the regression checks below pass and report the exact changed files and remaining limitations.

## 1. Keep findings until their resolution is verified

**Where:** `review_blog()`, the verdict loop, `cleanup_article()`, and `_prose_no_progress()` in `papers/agent_overviews.py`.

**Evidence:** post-fix Terra/LoRA, reviews 2–5. The merge-equation defect disappeared from review 4 without an edit fixing it, then returned after the last prose correction. Records: `.scratch/blog-live-e2e/2026-09-14-blog-pilot-rerun/results/gpt-terra/2106.09685v2/run/`.

- [ ] Add a scripted regression: report a prose defect alongside a drawing defect, repair the drawing, then omit the prose defect from the next verdict. Approval must remain blocked and the prose defect must still reach the repair task.
- [ ] Keep a small per-run collection of open findings with stable application-owned IDs. Supply it to subsequent reviews. A finding disappears only after explicit, validated resolution against the current candidate; absence from a new response is not resolution. Preserve it through existing checkpoints and failure diagnostics.
- [ ] Have review responses distinguish new findings from resolutions of supplied IDs. Reject unknown resolution IDs. Require a resolution explanation tied to current text or the affected figure; reject stale candidate identity and contradictory approval. A reworded finding must not silently reset its correction history.
- [ ] Preserve the existing correction ceilings and source checks. Do not reopen omitted figures. Resolve an omitted drawing's visual defect through omission, but keep any resulting prose-continuity issue open until cleanup is reviewed. Old saved generations must remain readable without the new review fields.

## 2. Bind a figure finding to the figure it describes

**Where:** review image labeling, Blog review-response validation, `_figure_issue_target()`, and the drawing dispatch branch in `papers/agent_overviews.py`.

**Evidence:** post-fix Terra/Mamba labels HBM/SRAM findings as `fig1`, although those labels belong to `fig2`. The coordinator repairs and omits the selective-copying figure. Records: `.scratch/blog-live-e2e/2026-09-14-blog-pilot-rerun/results/gpt-terra/2312.00752v2/run/`.

- [ ] Add a regression with `fig1` containing selective-copying labels and `fig2` containing HBM/SRAM labels. A finding naming `fig1` while quoting `fig2` must not dispatch a draw, alter a brief, or consume either figure's drawing budget.
- [ ] Label each review image with its stable ID and title. Require a figure finding to include a verbatim identifying label or relation endpoints from that figure's visible content. Validate that anchor against the named figure before dispatch. Normalize whitespace only as necessary; do not use broad fuzzy matching or guess another target from the message.
- [ ] Use the existing bounded review protocol-correction allowance to clarify a mismatched or ambiguous target. Return a concrete validation error naming the mismatch. If it remains unresolved, retain the draft and fail clearly. Never silently drop the finding or remap it to another figure or to prose.
- [ ] Verify that a correctly attributed `fig2` finding repairs only `fig2`; `fig1`, its source, and its attempt count remain unchanged. Cover sparse surviving IDs and an omitted target. Ambiguous shared labels need more identifying context within the same protocol budget.

## Verification and stop condition

Use the existing scripted provider and mocked renderer. These checks need no network or native renderer:

```sh
.venv/bin/python -m unittest tests.test_agent_overviews tests.test_explanation
.venv/bin/python -m unittest tests.test_blog_figures.LifecycleTests tests.test_blog_figures.TextEditTests tests.test_reading_bibliography
git diff --check
```

Also cover explicit valid resolution, unknown/stale resolution rejection, unchanged four-draw and two-prose-correction ceilings, and no fifth draw after semantic review. Record the failing-before/passing-after regression results. Stop after this scope passes. Offline protocol tests establish these two behaviors, not better scientific accuracy or live model convergence.
