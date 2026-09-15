# Blog live pilot results (rebuilt workflow)

Date: 2026-09-14 · Session: `/Users/silver/Developer/arxiv-paper-to-kindle/.scratch/blog-live-e2e/2026-09-14-blog-pilot-rerun`

Three OpenRouter models generated Blogs for two retained matrix papers from the previous live session. Fixed settings: casual language, medium length, vision review on. Every accepted Blog was exported to PDF. Test instrumentation only; no application code, prompt, or validator changed for this run.

## Session

| Item | Value |
| --- | --- |
| HEAD | `35260f3561dc` |
| Tracked diff SHA-256 | `0a3bffe7ab51ebf9806070c71b986d5fd7297332928626a0d235c9dc8279f6be` |
| Endpoint | `https://openrouter.ai/api/v1` |
| Spend ceiling | $10.00 |
| Session spend | $3.1314 |
| Articles accepted | 2 of 6 |
| PDFs exported | 2 |
| Model | `google/gemini-3.8-flash` (gemini-3.8-flash) |
| Model | `openai/gpt-5.6-luna` (gpt-luna) |
| Model | `openai/gpt-5.6-terra` (gpt-terra) |

## Outcomes by model and paper

| Model | Paper | Status | Approved | Figures (id:status/attempts) | Omitted | Verdicts | Provider calls | Cost | Wall | PDF |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gemini-3.8-flash | 2106.09685v2 (LoRA) | ready | True | fig1:accepted/2 | — | 1 | 8 | $0.1586 | 361s | 194 kB |
| gemini-3.8-flash | 2312.00752v2 (Mamba) | ready | True | fig1:accepted/3, fig2:accepted/3 | — | 1 | 13 | $0.4138 | 480s | 301 kB |
| gpt-luna | 2106.09685v2 (LoRA) | failed | None | fig1:omitted/4 | — | — | — | $0.1451 | 360s | — |
| gpt-luna | 2312.00752v2 (Mamba) | failed | None | fig1:pending/2, fig2:accepted/2 | — | — | — | $0.0564 | 225s | — |
| gpt-terra | 2106.09685v2 (LoRA) | failed | None | fig1:omitted/4 | — | — | — | $0.5899 | 285s | — |
| gpt-terra | 2312.00752v2 (Mamba) | failed | None | fig1:omitted/4, fig2:accepted/3 | — | — | — | $1.7676 | 450s | — |

## Figure completion against the four-attempt budget

Denominator: all 9 planned figures across accepted and failed articles.

| Attempt | Accepted on this attempt | Cumulative accepted | Cumulative share |
| --- | --- | --- | --- |
| 1 | 0 | 0 | 0.0% |
| 2 | 2 | 2 | 22.2% |
| 3 | 3 | 5 | 55.6% |
| 4 | 0 | 5 | 55.6% |

Status counts: accepted 5, omitted 3, pending 1.

Target from the plan: usable figures within two or three attempts. A higher article delivery rate obtained by omitting figures does not establish that target.

## Previous workflow comparison

The 2026-09-13 session ran the same three models on the same two papers with the previous Blog workflow.

| Model | Paper | New status | New figures | Old status | Old error |
| --- | --- | --- | --- | --- | --- |
| gemini-3.8-flash | 2106.09685v2 | ready | fig1:accepted/2 | failed | SVG text must be 16–80px. Use fewer labels instead of shrinking text. It did not improve after two corrections |
| gemini-3.8-flash | 2312.00752v2 | ready | fig1:accepted/3, fig2:accepted/3 | failed | Error while generating output:
Provider request failed with HTTP status 400. |
| gpt-luna | 2106.09685v2 | failed | fig1:omitted/4 | failed | The example shows x entering W₀ and BA and then writes W₀x + BAx, but it never explains the low-rank compositi |
| gpt-luna | 2312.00752v2 | failed | fig1:pending/2, fig2:accepted/2 | failed | Place each figure marker exactly once and omit unknown markers. It did not improve after two corrections. |
| gpt-terra | 2106.09685v2 | failed | fig1:omitted/4 | failed | Error while generating output:
Provider request failed or returned an invalid response. Check connectivity and |
| gpt-terra | 2312.00752v2 | failed | fig1:omitted/4, fig2:accepted/3 | failed | Error while generating output:
Provider request failed or returned an invalid response. Check connectivity and |

## Failures and repairs

| Model | Paper | Failure kind | Error |
| --- | --- | --- | --- |
| gpt-luna | 2106.09685v2 | article_or_review | The article still has unresolved review findings after two corrections. Draft retained. |
| gpt-luna | 2312.00752v2 | article_or_review | The corrected drawing brief was rejected. Draft retained. |
| gpt-terra | 2106.09685v2 | article_or_review | The article still has unresolved review findings after two corrections. Draft retained. |
| gpt-terra | 2312.00752v2 | article_or_review | The article still has unresolved review findings after two corrections. Draft retained. |

## Per-article detail

### gemini-3.8-flash · 2106.09685v2 (LoRA)

- Figures: fig1:accepted/2
- Omitted: none
- Verdicts: 1 of ceiling 8 · prose corrections 0
- Review digest matches delivered text: True
- Article: 9652 characters (10534 display)
- Prompt/schema revision: `blog-focused-svg-v1` · SVG profile `panel-svg-v1`
- `fig1` canvas {'width': 640, 'height': 820} · 0 open issue(s)
- PDF: `exports/gemini-3.8-flash/2106.09685v2.pdf` (198600 bytes, valid True)

### gemini-3.8-flash · 2312.00752v2 (Mamba)

- Figures: fig1:accepted/3, fig2:accepted/3
- Omitted: none
- Verdicts: 1 of ceiling 13 · prose corrections 0
- Review digest matches delivered text: True
- Article: 8610 characters (9435 display)
- Prompt/schema revision: `blog-focused-svg-v1` · SVG profile `panel-svg-v1`
- `fig1` canvas {'width': 640, 'height': 590} · 0 open issue(s)
- `fig2` canvas {'width': 640, 'height': 560} · 0 open issue(s)
- PDF: `exports/gemini-3.8-flash/2312.00752v2.pdf` (308733 bytes, valid True)

### gpt-luna · 2106.09685v2 (LoRA)

- Status: failed
- Error: The article still has unresolved review findings after two corrections. Draft retained.
- Failure kind: article_or_review · error: The article still has unresolved review findings after two corrections. Draft retained.

### gpt-luna · 2312.00752v2 (Mamba)

- Status: failed
- Error: The corrected drawing brief was rejected. Draft retained.
- Failure kind: article_or_review · error: The corrected drawing brief was rejected. Draft retained.

### gpt-terra · 2106.09685v2 (LoRA)

- Status: failed
- Error: The article still has unresolved review findings after two corrections. Draft retained.
- Failure kind: article_or_review · error: The article still has unresolved review findings after two corrections. Draft retained.

### gpt-terra · 2312.00752v2 (Mamba)

- Status: failed
- Error: The article still has unresolved review findings after two corrections. Draft retained.
- Failure kind: article_or_review · error: The article still has unresolved review findings after two corrections. Draft retained.

## Artifacts

| Path | Contents |
| --- | --- |
| `/Users/silver/Developer/arxiv-paper-to-kindle/.scratch/blog-live-e2e/2026-09-14-blog-pilot-rerun/manifest.json` | scope, code identity, model resolution, ceiling |
| `/Users/silver/Developer/arxiv-paper-to-kindle/.scratch/blog-live-e2e/2026-09-14-blog-pilot-rerun/results.json` | every entry with jobs, figures, reviews, cost, timing |
| `/Users/silver/Developer/arxiv-paper-to-kindle/.scratch/blog-live-e2e/2026-09-14-blog-pilot-rerun/events.jsonl` | append-only submit/finish/settings events |
| `/Users/silver/Developer/arxiv-paper-to-kindle/.scratch/blog-live-e2e/2026-09-14-blog-pilot-rerun/exports/<model>/<paper>.pdf` | exported Blog PDFs |
| `/Users/silver/Developer/arxiv-paper-to-kindle/.scratch/blog-live-e2e/2026-09-14-blog-pilot-rerun/results/<model>/<paper>/` | saved generation and run metadata |
| `/Users/silver/Developer/arxiv-paper-to-kindle/.scratch/blog-live-e2e/2026-09-14-blog-pilot-rerun/logs/pilot.log` | orchestrator log |

