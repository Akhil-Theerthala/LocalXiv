# Highlight anchor spike (2026-10-19)

The script is `anchors_spike.py`. It and the full output (`results.txt`, `results.json`) are in `.scratch/anchor-spike-2026-10-19/` in the main checkout, which git ignores. `papers/anchors.py` is the search that the app and `tools/robustness/corpus.py compare` use.

## Method

- Quotes: one quote of 6 to 15 whole words from the middle of each passage with 40 or more characters. Also one quote around a formula when the passage has one. A ` $tex$ ` formula counts as one word. Prefix and suffix: 32 characters each.
- Exact search: href, ID, section (nearest index), whole Paper (context, then distance).
- Fuzzy step: in each passage, difflib puts a window at the longest common substring, trims it to the matching blocks, and takes `ratio()` (`autojunk=False`). The section comes first, then the whole Paper.
- Direction: `revision.json` has no date. So the spike used the `base_revision` in `report.json`, then the `document.json` time. Self-check: 6bff→cde8 has 19 Papers, 4 with changed text, and 0 route changes. 9de5→dc91 has 16, 10, and 5.

## Results (% of quotes; moved = 100 − found − not found)

| Pair, route | Quotes | Same ID | Other ID | Not found 0.6 | 0.7 | 0.8 | 0.85 | 0.9 |
|---|---|---|---|---|---|---|---|---|
| 6bff→cde8, same | 7983 | 92.2 | 7.8 | 0 | 0 | 0 | 0 | 0 |
| 9de5→dc91, same | 4191 | 89.0 | 9.7 | 0 | 0 | 0 | 0 | 0.2 |
| 9de5→dc91, changed | 1165 | 9.2 | 44.4 | 0.7 | 0.9 | 3.2 | 5.2 | 10.6 |
| dc91→9de5, same | 4195 | 88.9 | 9.7 | 0 | 0 | 0.1 | 0.1 | 0.3 |
| dc91→9de5, changed | 965 | 10.7 | 42.5 | 4.2 | 7.3 | 11.0 | 13.7 | 20.0 |
| Other 34 pairs, same | 135366 | 97.8 | 2.2 | 0 | 0 | 0 | 0 | 0 |
| Other 34 pairs, changed | 1923 | 5.1 | 53.6 | 1.0 | 1.3 | 3.0 | 4.6 | 8.5 |

In the 4 changed Papers of 6bff→cde8, only 1.7% of quotes keep their ID, but all quotes are found. The other pairs repeat a few changes (2603.22797v1 changes route in 8 pairs). So this table counts each distinct text change once:

| Route | Quotes | Found exact | Moved 0.85 | Not found 0.8 | Not found 0.85 |
|---|---|---|---|---|---|
| pandoc→pandoc | 4310 | 97.4 | 2.4 | 0.1 | 0.1 |
| arxiv-html→pandoc | 1522 | 56.9 | 38.4 | 2.9 | 4.7 |
| pandoc→arxiv-html | 1358 | 54.7 | 34.4 | 8.7 | 11.0 |

No arxiv-html→arxiv-html Paper changed its text, so that route has no data.

## False positives

1850 quotes of a Paper A searched in an unrelated Paper B (37 pairs). Exact hits: 0. Fuzzy match rate (%):

| Quotes | 0.6 | 0.7 | 0.8 | 0.85 | 0.9 |
|---|---|---|---|---|---|
| All (1850) | 4.0 | 0.5 | 0.16 | 0 | 0 |
| 6–9 words (770) | 9.1 | 1.2 | 0.26 | 0 | 0 |
| 10–15 words (1080) | 0.4 | 0.1 | 0.09 | 0 | 0 |

Worst: 0.840, "there exists $A\in G'$ such that for any" against "there exists $p \geq 0$ such that for any".

## Recommended threshold: 0.85

- At 0.85, 0 of 1850 quotes match falsely. At 0.8, 3 do, all on stock phrases.
- At 0.8, only 2.0 more points of quotes are moved on a route change (38.5% against 36.5%).
- Samples: in the 0.8 to 0.85 band, 1 of 8 is in the wrong place. In the 0.85 to 0.9 band, 8 of 8 are correct. Below 0.7, matches go to wrong passages (Author note to Acknowledgment, 0.667).
- A Highlight in the wrong place hides the error. A not-found Highlight shows it, and the reader can place it again.

## Per-route gate (at 0.85, with a reviewed allow-list)

- Same route: each not-found quote must be on the allow-list. Today: 5 of 4310.
- Changed route: today's not-found rates are arxiv-html→pandoc 4.7% and pandoc→arxiv-html 11.0%. Most are display equations that the two routes write in different TeX.

## Timing (budget: 50 Highlights of one Paper in less than 1 s)

- Plain difflib on every passage fails: 30.5 s for 50 missed quotes in 2305.08212v2 (1203 passages).
- Pre-filter: the passages with one of the 3 rarest quote words, top 10 by IDF overlap, plus the passages with the old href and ID. Worst case for 50 missed quotes: 625 ms. For the 50 slowest real quotes: 884 ms (math_9912218v2, 9de5→dc91), or 701 ms with a normalized exact step first. In that Paper, all 418 quotes take 2303 ms, about 5.5 ms each, so 50 typical Highlights take about 0.3 s.
- The pre-filter loses 6 of 1610 moved matches (0.4%, all pairs).
- Median per quote: exact 1 µs, pre-filter fuzzy 9 ms.

## Surprises

1. A normalized exact step (NFKC, case fold, letters and digits only) finds 720 of 1382 distinct exact misses, with 0 false hits. Most differences are formula spaces and braces (`m_{0}` against `m_0`). Add this step before the fuzzy step.
2. 4.0% of exact hits (all pairs) are in another section. For 345 of these 380, the heading changed ("2 Optimization…" to "3 Optimization…", "3.1" to "III-A"). arXiv HTML also gives "Lemma 3." as a section. So the section is only a hint, as the ID is.
3. 91% of exact hits at another ID keep their full context. One short quote matched exactly in another theorem. Rank exact hits by context.
4. The misses show defects in Pandoc-route text: `$${\bf Q}^{+}_L$$` and `$$$\begin{equation}…$$$`, `\label{…}` in formulas, "(equation)" for equation numbers, "Theorem [PLM-follows-ray]", and picture coordinates such as "(60.33,40.00)" as text.
5. Exact search finds 75.1% of formula quotes and 93.5% of other quotes.
6. Only 1 miss crosses a passage boundary.
7. The plan says 89.2% are found for 9de5→dc91. This spike measures 88.9%.
