# Blog live pilot results (rebuilt workflow)

Date: 2026-09-14 · Session: `/Users/silver/Developer/arxiv-paper-to-kindle/.scratch/blog-live-e2e/2026-09-14-blog-pilot`

Three OpenRouter models generated Blogs for two retained matrix papers from the previous live session. Fixed settings: casual language, medium length, vision review on. Every accepted Blog was exported to PDF. Test instrumentation only; no application code, prompt, or validator changed for this run.

## Session

| Item | Value |
| --- | --- |
| HEAD | `35260f3561dc` |
| Tracked diff SHA-256 | `2f14dcb0f655745e34121f7c2b36b93b61dbf28195a71dfc85d70a7a3e7a794c` |
| Endpoint | `https://openrouter.ai/api/v1` |
| Spend ceiling | $10.00 |
| Session spend | $1.8738 |
| Articles accepted | 2 of 6 |
| PDFs exported | 2 |
| Model | `google/gemini-3.8-flash` (gemini-3.8-flash) |
| Model | `openai/gpt-5.6-luna` (gpt-luna) |
| Model | `openai/gpt-5.6-terra` (gpt-terra) |

## Outcomes by model and paper

| Model | Paper | Status | Approved | Figures (id:status/attempts) | Omitted | Verdicts | Provider calls | Cost | Wall | PDF |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gemini-3.8-flash | 2106.09685v2 (LoRA) | ready | True | fig1:accepted/4, fig2:accepted/1 | — | 2 | 10 | $0.3446 | 570s | 476 kB |
| gemini-3.8-flash | 2312.00752v2 (Mamba) | failed | None | — | — | — | — | $0.0951 | 150s | — |
| gpt-luna | 2106.09685v2 (LoRA) | failed | None | fig1:omitted/4, fig2:accepted/1, fig3:omitted/4 | — | — | — | $0.1863 | 540s | — |
| gpt-luna | 2312.00752v2 (Mamba) | failed | None | fig1:omitted/4, fig2:omitted/4 | — | — | — | $0.1246 | 465s | — |
| gpt-terra | 2106.09685v2 (LoRA) | failed | None | fig1:omitted/6 | — | — | — | $0.8199 | 435s | — |
| gpt-terra | 2312.00752v2 (Mamba) | ready | True | — | — | 2 | 8 | $0.3033 | 135s | 34 kB |

## Figure completion against the four-attempt budget

Denominator: all 8 planned figures across accepted and failed articles.

| Attempt | Accepted on this attempt | Cumulative accepted | Cumulative share |
| --- | --- | --- | --- |
| 1 | 2 | 2 | 25.0% |
| 2 | 0 | 2 | 25.0% |
| 3 | 0 | 2 | 25.0% |
| 4 | 1 | 3 | 37.5% |

Status counts: accepted 3, omitted 5, pending 0.

Target from the plan: usable figures within two or three attempts. A higher article delivery rate obtained by omitting figures does not establish that target.

**Budget violation observed:** the following figures made more than four drawing requests: gpt-terra/2106.09685v2 fig1: 6 attempts. The review-triggered redraw path did not check remaining budget, so a finding on a figure that already spent four attempts started another draw. Fixed offline after this session; see the live pilot verification document.

## Previous workflow comparison

The 2026-09-13 session ran the same three models on the same two papers with the previous Blog workflow.

| Model | Paper | New status | New figures | Old status | Old error |
| --- | --- | --- | --- | --- | --- |
| gemini-3.8-flash | 2106.09685v2 | ready | fig1:accepted/4, fig2:accepted/1 | failed | SVG text must be 16–80px. Use fewer labels instead of shrinking text. It did not improve after two corrections |
| gemini-3.8-flash | 2312.00752v2 | failed | — | failed | Error while generating output:
Provider request failed with HTTP status 400. |
| gpt-luna | 2106.09685v2 | failed | fig1:omitted/4, fig2:accepted/1, fig3:omitted/4 | failed | The example shows x entering W₀ and BA and then writes W₀x + BAx, but it never explains the low-rank compositi |
| gpt-luna | 2312.00752v2 | failed | fig1:omitted/4, fig2:omitted/4 | failed | Place each figure marker exactly once and omit unknown markers. It did not improve after two corrections. |
| gpt-terra | 2106.09685v2 | failed | fig1:omitted/6 | failed | Error while generating output:
Provider request failed or returned an invalid response. Check connectivity and |
| gpt-terra | 2312.00752v2 | ready | — | failed | Error while generating output:
Provider request failed or returned an invalid response. Check connectivity and |

## Failures and repairs

| Model | Paper | Failure kind | Error |
| --- | --- | --- | --- |
| gemini-3.8-flash | 2312.00752v2 | failed | plan.visual_focus has 1235 characters; the limit is 1200, so shorten it by at least 35 characters while preserving required detail It did not improve after two corrections. |
| gpt-luna | 2106.09685v2 | article_or_review | The article still has unresolved review findings after two corrections. Draft retained. |
| gpt-luna | 2312.00752v2 | article_or_review | The article still has unresolved review findings after two corrections. Draft retained. |
| gpt-terra | 2106.09685v2 | article_or_review | The article still has unresolved review findings after two corrections. Draft retained. |

## Per-article detail

### gemini-3.8-flash · 2106.09685v2 (LoRA)

- Figures: fig1:accepted/4, fig2:accepted/1
- Omitted: none
- Verdicts: 2 of ceiling 13 · prose corrections 0
- Review digest matches delivered text: True
- Article: 8548 characters (9154 display)
- Prompt/schema revision: `blog-focused-svg-v1` · SVG profile `panel-svg-v1`
- `fig1` canvas {'width': 640, 'height': 600} · 0 open issue(s)
- `fig2` canvas {'width': 640, 'height': 450} · 0 open issue(s)
- PDF: `exports/gemini-3.8-flash/2106.09685v2.pdf` (487780 bytes, valid True)

### gemini-3.8-flash · 2312.00752v2 (Mamba)

- Status: failed
- Error: plan.visual_focus has 1235 characters; the limit is 1200, so shorten it by at least 35 characters while preserving required detail It did not improve after two corrections.
- Failure kind: None · error: plan.visual_focus has 1235 characters; the limit is 1200, so shorten it by at least 35 characters while preserving required detail It did not improve after two corrections.

### gpt-luna · 2106.09685v2 (LoRA)

- Status: failed
- Error: The article still has unresolved review findings after two corrections. Draft retained.
- Failure kind: article_or_review · error: The article still has unresolved review findings after two corrections. Draft retained.

### gpt-luna · 2312.00752v2 (Mamba)

- Status: failed
- Error: The article still has unresolved review findings after two corrections. Draft retained.
- Failure kind: article_or_review · error: The article still has unresolved review findings after two corrections. Draft retained.

### gpt-terra · 2106.09685v2 (LoRA)

- Status: failed
- Error: The article still has unresolved review findings after two corrections. Draft retained.
- Failure kind: article_or_review · error: The article still has unresolved review findings after two corrections. Draft retained.

### gpt-terra · 2312.00752v2 (Mamba)

- Figures: none planned
- Omitted: none
- Verdicts: 2 of ceiling 3 · prose corrections 1
- Review digest matches delivered text: True
- Article: 8748 characters (9227 display)
- Prompt/schema revision: `blog-focused-svg-v1` · SVG profile `panel-svg-v1`
- PDF: `exports/gpt-terra/2312.00752v2.pdf` (34570 bytes, valid True)

## Artifacts

| Path | Contents |
| --- | --- |
| `/Users/silver/Developer/arxiv-paper-to-kindle/.scratch/blog-live-e2e/2026-09-14-blog-pilot/manifest.json` | scope, code identity, model resolution, ceiling |
| `/Users/silver/Developer/arxiv-paper-to-kindle/.scratch/blog-live-e2e/2026-09-14-blog-pilot/results.json` | every entry with jobs, figures, reviews, cost, timing |
| `/Users/silver/Developer/arxiv-paper-to-kindle/.scratch/blog-live-e2e/2026-09-14-blog-pilot/events.jsonl` | append-only submit/finish/settings events |
| `/Users/silver/Developer/arxiv-paper-to-kindle/.scratch/blog-live-e2e/2026-09-14-blog-pilot/exports/<model>/<paper>.pdf` | exported Blog PDFs |
| `/Users/silver/Developer/arxiv-paper-to-kindle/.scratch/blog-live-e2e/2026-09-14-blog-pilot/results/<model>/<paper>/` | saved generation and run metadata |
| `/Users/silver/Developer/arxiv-paper-to-kindle/.scratch/blog-live-e2e/2026-09-14-blog-pilot/logs/pilot.log` | orchestrator log |

