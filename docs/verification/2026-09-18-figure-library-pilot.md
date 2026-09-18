# Figure library pilot

Live runs on 2026-09-18 with deepseek-flash through `tools/overview_run.py`, on the branch `figure-library-consolidation` at commit `14c581f`. The Blog runs used Attention and Uncertainty Profiles because LoRA and Mamba are not in this library. The first Blog attempt found two prompt defects (the panel request never said "JSON", which DeepSeek's `json_object` mode rejects with HTTP 400; the author cited passages in parentheses and wrote exact text in LaTeX) and one provider artefact (an echoed `"type": "json_object"` key); commits `5f1c8aa` and `14c581f` fixed them and the tables below are the runs after those fixes.

## Overview runs

| Paper | Requests | Tokens | Seconds | Density | Panels | Native checks |
| --- | --- | --- | --- | --- | --- | --- |
| Attention Is All You Need | 5 | 62,872 | 119 | 63.1 | 3 | passed |
| Probabilities Are All You Need | 4 | 31,792 | 84 | 54.4 | 3 | passed |
| A Systematic Evaluation of Black-Box Uncertainty Estimation | 3 | 52,725 | 109 | 59.7 | 4 | passed |

## Blog runs

| Paper | Delivered | Verdicts | Requests | Tokens | Seconds | Words |
| --- | --- | --- | --- | --- | --- | --- |
| Attention Is All You Need | yes | 5 | 24 | 391,122 | 616 | 1,356 |
| Uncertainty Profiles for LLMs | no: `article_cleanup` exact edits exceeded the 1,400-word limit after the fig3 omission | 6 | 29 | 526,441 | 916 | not delivered |

## Blog figures

"First acceptance" counts the requests until the panel first passed validation, coverage, layout, and the native checks. "Final" is the state when the run ended; a review finding on an accepted figure spends a Scene correction from the same one-plus-three budget.

| Paper | Figure | First acceptance | Final status | Requests | Corrections | Panel density | Last problem |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Attention | fig1 | 1 correction (an invented node kind) | omitted after review | 4 | 3 | 104.2 | an arrow cannot reach its target |
| Attention | fig2 | 0 corrections | accepted | 1 | 0 | 83.4 | |
| Attention | fig3 | 0 corrections | omitted after review | 4 | 3 | 70.0 | an edge label of 29 characters (limit 28) |
| Uncertainty Profiles | fig1 | 1 correction (layout) | omitted after review | 4 | 3 | 62.1 | a fourth review finding with no request left |
| Uncertainty Profiles | fig2 | 0 corrections | accepted | 2 | 1 | 49.8 | |
| Uncertainty Profiles | fig3 | 1 correction (`notes` inside the body) | omitted after review | 4 | 3 | 90.0 | an arrow cannot reach its target |

## Acceptance

- Every Overview reached density 40 and passed the native checks: three of three, densities 54.4 to 63.1.
- Blog figures first accepted with zero corrections: 3 of 6; with one correction: 3 of 6; with two or three: 0 of 6. Every planned figure was drawn within one correction.
- Blog figures accepted at the end of the run: 2 of 6. The other four were accepted first and then omitted when review findings spent the remaining corrections; the failing corrections were one-character limit overshoots, an unroutable arrow, and a fourth finding on an exhausted budget.
- Blogs delivered: 1 of 2. The Attention Blog is a recovered article (two omissions). The Uncertainty Profiles run failed in article cleanup, not in drawing.
- Panel densities of a single 640-unit panel: 49.8 to 104.2, every one above the page floor of 40. The panel floor open item can adopt 40.

## Open

- A review finding on an accepted figure restarts the panel from the brief, and the first redraw fails a limit by one character often enough to spend the budget. Two options: keep the accepted panel when the redraw fails, or let a review correction run the edited panel through validation before the request is counted.
- The article word limit rejects exact edits that repair a review finding by adding a sentence. The cleanup stage needs room, or the reviewer needs the word budget.
- The reviewer's word-count findings quote a 750 to 1,250 range the prompt never states; the length preference text should name the number the validator uses.
