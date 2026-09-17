# Blog live pilot: three models, two papers, PDFs

Date: 2026-09-14
Session: `.scratch/blog-live-e2e/2026-09-14-blog-pilot/`
Plan: Blog workflow update (plan removed; in git history)
Spec: [Agreed Blog design](../superpowers/specs/2026-09-14-blog-workflow-update-design.md)

Status: live pilot executed with explicit user authorization under a $10 ceiling. The prior
40-job matrix had already used $10.53 of the OpenRouter account. This session ran Blogs only.
A post-fix re-run of the full matrix followed the same day and confirmed the budget fix live, then
found and fixed a second defect (`\bm` broke PDF export): see
[Blog live pilot re-run](2026-09-14-blog-live-pilot-rerun.md).

## Scope and settings

| Item | Value |
| --- | --- |
| Models (OpenRouter) | `google/gemini-3.8-flash`, `openai/gpt-5.6-luna`, `openai/gpt-5.6-terra` |
| Papers | `2106.09685v2` (LoRA), `2312.00752v2` (Mamba), retained from the 2026-09-13 matrix |
| Mode | Blog only (`POST /api/papers/<id>/summary`) |
| Fixed settings | casual language, medium length, `overview_vision` on |
| Libraries | isolated per-model clones of the retained matrix libraries; the real library untouched |
| PDF export | `POST /api/papers/<id>/export` with `kind=overview`, `profile=pdf` |
| Ceiling | $10.00 |
| Actual spend | $1.8738 (OpenRouter account-usage delta) |

The session predates the budget fix below. Its captured code identity is HEAD `35260f3561dc`
with tracked diff SHA-256 `2f14dcb0f655745e34121f7c2b36b93b61dbf28195a71dfc85d70a7a3e7a794c`.
The fix changes only the exhausted-figure review path, so the delivered articles and PDFs are
unaffected; the overspend it caused is counted and reported here.

## Results

Two of six Blogs were delivered and exported to PDF. The rebuilt workflow delivered articles for
models where the previous workflow delivered none: in the 2026-09-13 matrix all 15 Blog jobs across
these three models failed.

| Model | Paper | Status | Figures (status/attempts) | Provider calls | Cost | Wall | PDF |
| --- | --- | --- | --- | --- | --- | --- | --- |
| gemini-3.8-flash | LoRA | ready, approved | `fig1` accepted/4, `fig2` accepted/1 | 10 | $0.3446 | 571 s | [476 kB](artifacts/2026-09-14-blog-live-pilot/gemini-3.8-flash-LoRA-2106.09685v2.pdf) |
| gemini-3.8-flash | Mamba | failed at narrative planning | 0 planned | — | $0.0951 | 150 s | — |
| gpt-luna | LoRA | failed at review | `fig1` omitted/4, `fig2` accepted/1, `fig3` omitted/4 | 11+ | $0.1863 | 541 s | — |
| gpt-luna | Mamba | failed at review | `fig1` omitted/4, `fig2` omitted/4 | 11+ | $0.1246 | 466 s | — |
| gpt-terra | LoRA | failed at review | `fig1` omitted/**6** | 11+ | $0.8199 | 436 s | — |
| gpt-terra | Mamba | ready, approved | none planned (prose-only Blog) | 8 | $0.3033 | 135 s | [34 kB](artifacts/2026-09-14-blog-live-pilot/gpt-terra-Mamba-2312.00752v2.pdf) |

Figure outcome against the four-attempt budget, with all 8 planned figures as the denominator:

| Attempt | Accepted on this attempt | Cumulative accepted | Cumulative share |
| --- | --- | --- | --- |
| 1 | 2 | 2 | 25.0% |
| 2 | 0 | 2 | 25.0% |
| 3 | 0 | 2 | 25.0% |
| 4 | 1 | 3 | 37.5% |

Final counts: 3 accepted, 5 omitted, 0 pending. The plan's target is usable figures within two or
three attempts; this sample does not meet it. A higher delivery rate obtained by omission does not
establish that target, so retention and omission are reported separately above.

The gemini/LoRA article shows the intended recovery path working: `fig1` failed three drawing
attempts and was accepted on the fourth after measured repair feedback. The terra/Mamba article is
a legitimate prose-only Blog: the author planned zero figures, one article correction was applied,
and the second verdict approved it.

## Defect found: the review path could exceed the four-attempt ceiling

`gpt-terra` / `2106.09685v2` made **six** drawing requests for `fig1`. The saved run state shows
attempts 1–6: rejected (12.8 px), accepted, rejected by review (13.7 px), accepted, accepted,
accepted. The coordinator reset an accepted figure to pending for every review finding without
checking the remaining budget, so findings after the fourth attempt started a fifth and sixth draw.
The plan requires at most four drawing requests per stable ID "over the whole run: creation plus up
to three corrections. No counter reset after review or omission," and "if no attempt remains, omit
and clean the article."

The offline suite did not catch this because no test combined a review finding with a figure that
had already spent all four attempts.

### Fix

`papers/agent_overviews.py` now checks the budget before redrawing a reviewed figure:

```python
if state['attempts'] >= MAX_FIGURE_ATTEMPTS:
    # No drawing request remains: a review finding on an exhausted figure omits it
    # and cleans the article instead of resetting the counter with a fifth draw.
    state['status'] = 'omitted'
    state['issues'] = copy.deepcopy(target_issues)
    figure_states[index] = state
    omitted[target] = state
    cleanup_omitted([target])
    persist_figures()
    continue
```

The review finding is retained on the omitted state for diagnostics, the marker is removed, and the
prose that depended on the figure is cleaned in the same batched exact-edit request as any other
omission. A figure with remaining attempts keeps the existing behavior: one supported brief
correction when the finding is scientific, then the next drawing attempt.

Regression test:
`tests/test_agent_overviews.py::AgentTests.test_a_review_finding_on_an_exhausted_figure_omits_without_a_fifth_draw`.
It was confirmed to fail on the pre-fix code (the scripted fifth draw errors) and to pass after the
fix, with exactly four drawing requests, an omitted `fig1`, a cleaned article, and an approved final
verdict. The [post-fix re-run](2026-09-14-blog-live-pilot-rerun.md) then reproduced this path live
twice on gpt-terra and showed a maximum of four drawing requests across the session.

Post-fix checks: `LOCALXIV_HTML_RENDERER=/tmp/localxiv-blog-html-snapshot .venv/bin/python -m
unittest discover -s tests` → 568 tests, OK, 1 unrelated skip; `git diff --check` clean. Post-fix
tracked diff SHA-256: `0a3bffe7ab51ebf9806070c71b986d5fd7297332928626a0d235c9dc8279f6be`.

## Why the four articles failed

None of the failures were transport or provider-outage failures; every stage reached a decision.

- **gemini-3.8-flash / Mamba.** The planner wrote `plan.visual_focus` at 1235 characters against the
  1200-character bound and repeated the same over-length text after two corrections, so the
  coordinator raised "did not improve after two corrections". The model could not shorten an
  otherwise usable plan field.
- **gpt-luna / LoRA, gpt-luna / Mamba, gpt-terra / LoRA.** The bounded review stopped each article
  after two prose corrections while the reviewer still reported unresolved findings. The findings
  were substantively correct, not noise: the articles repeated `h = W₀x + BAx` while the paper
  scales the update by α/r; they wrote "validation loss peaked at r = 16" (wrong direction for a
  loss metric); they described figure connectors in ways that suggested activation merging; and
  some carried corrupted control-character artifacts in math. With the policy's two-correction
  bound and no-progress check, the correct outcome is to retain the draft and the previous saved
  Blog rather than publish prose the reviewer rejected.

This matches the previous matrix: luna/LoRA failed there for the same class of scientific error.
The rebuilt workflow gets materially further (figures drawn, checked, repaired, omissions cleaned)
but does not by itself make the models converge on these two papers.

## Deliverables

| Artifact | Path |
| --- | --- |
| LoRA Blog PDF (gemini-3.8-flash) | `docs/verification/artifacts/2026-09-14-blog-live-pilot/gemini-3.8-flash-LoRA-2106.09685v2.pdf` |
| Mamba Blog PDF (gpt-terra, prose-only) | `docs/verification/artifacts/2026-09-14-blog-live-pilot/gpt-terra-Mamba-2312.00752v2.pdf` |
| Full pilot report | `docs/verification/artifacts/2026-09-14-blog-live-pilot/report.md` |
| First pages / embedded figure | `gemini-LoRA-page1.png`, `gemini-LoRA-page2-figure.png`, `terra-Mamba-page-1.png` beside the PDFs |
| Raw session | `.scratch/blog-live-e2e/2026-09-14-blog-pilot/` (results.json, events.jsonl, logs, run artifacts) |

The gemini/LoRA PDF is four pages: cited prose with typeset equations plus two native-checked SVG
figures at 640 px canvas width (fig1 640×600, fig2 640×450), both with no open geometry issues.
The terra/Mamba PDF is prose-only, as planned by the author.

## Limitations

- Two papers and three models give a small sample; per-model retention differences are indicative,
  not established.
- Four of six articles failed the bounded review policy on this sample, so the figure-acceptance
  denominator includes figures from articles that were never delivered.
- The session ran on the pre-fix identity for the exhausted-figure path; only terra/LoRA exercised
  it. The fix is verified offline, not live.
- Vision review was enabled and its findings appear above, but this report does not independently
  re-verify each reviewer finding against the paper.
- No provider failure, cancellation, or authentication error occurred, so those live paths remain
  covered only by offline tests.

## Follow-up

A rerun of the two failed gpt-luna articles and the gemini/Mamba article after model or prompt
adjustments would need a new session record and budget; nothing was retried automatically here.
