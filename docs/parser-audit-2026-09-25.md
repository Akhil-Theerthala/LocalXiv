# Parser audit: why a fix for one template breaks another

Audited on 2026-09-25 at `main` (`1f7151f`). Three read-only reviews covered the TeX rewrite passes in `native/host.py`, the routes and tree passes in `papers/`, and the verification harness in `tools/robustness/`. Claims marked "probe" were reproduced on synthetic input. The others cite code.

## The short answer

A fix for template A breaks template B for four structural reasons. No check before merge would notice the break.

1. **Almost every pass runs on every paper.** `convert_source` (`native/host.py:4797`) runs 39 TeX rewrite passes in a fixed order on every Pandoc conversion. Eleven run unconditionally, and about ten more trigger on a textual pattern that many templates match. Several were written for one paper or one venue: `prepare_prompt_blocks` (`mymessagebox`), `prepare_measured_inline_boxes`, `prepare_inline_font_commands`, and the IEEE, AASTeX, IJCAI, and CVPR branches inside `prepare_source_notes` (`native/host.py:4232-4283`). All of them run on every paper.
2. **Most passes edit raw TeX with regular expressions.** Thirteen passes never mask comments or verbatim, so they also rewrite commented-out code and code listings. There are five separate comment strippers and four separate inline-math regexes. Thirteen passes read files with `errors="replace"`, so a Latin-1 source loses its accented letters (probe).
3. **Passes depend on each other through the order and through shared markers.** The `% arxiv-kindle-abstract-end` marker is written by `prepare_abstracts` and read by two later passes. `prepare_source_notes` pairs a footnote text with the last mark before it, so any pass that moves text earlier changes the pairing. The footnote regression below, from today, came from exactly this.
4. **A failing pass changes the route, and each route has a different output shape.** A `ConversionError` in any Pandoc pass sends the paper to arXiv HTML, then LaTeXML (`papers/convert.py:39-77`). Those routes draw display equations as table cells, keep a different abstract markup, and cite differently. The reader, Paper orientation, and the Overview and Blog evidence then see a different document for the same kind of paper.

Verification does not close the gap. The robustness harness in `tools/robustness/` has a stratified 76-paper sample and a per-paper content snapshot (`integrity.py`). It ran once, by hand, on 2026-09-08. The downloaded corpus is not on this machine. The test suite is not in git, and no CI job, hook, or written rule requires a corpus run before a parser change merges.

## Regressions found in today's changes, and fixed

Today's Paper reader work (`9c4c757`) was merged after unit tests on one paper only. The audit found four faults in it. Each is fixed on `main` with a test that fails on the earlier code.

- **Title footnotes swapped.** Moving pre-title `\footnotetext` after the abstract made an author note and an abstract note trade places (probe). Title footnotes now go to the start of the abstract again. Only notice blocks such as a license move to the end. Fixed in `cf31e2c`.
- **Wrong equation numbers without a warning.** The numbering pass read only `*.tex` and missed per-chapter classes, REVTeX appendices, `\counterwithin`, `\@addtoreset`, and theorems that share the equation counter. It now also reads the paper's `.sty` and `.cls` files and turns itself off for all of these. A `\tag` written in TeX no longer shows raw TeX. Fixed in `0fe9b44`.
- **Brackets stretched too widely.** The pass stretched floor and set brackets, inline math, and fractions inside superscripts, on every route. It now acts only on round and square brackets in display math, around a fraction or array directly inside them. It still overrides Pandoc's `stretchy="false"` on purpose. This is a readability choice: TeX and the PDF draw these brackets at text size. Fixed in `0fe9b44`.
- **Shrunk display equations on LaTeXML and arXiv HTML papers.** The inline-fraction CSS also hit display equations that those routes draw as inline math in table cells. The rule now skips math in a table cell. Fixed in `0fe9b44`.

## Open risks, most severe first

These faults existed before today. None is fixed.

| # | Risk | Where | Input that triggers it |
|---|---|---|---|
| 1 | Common algorithm commands (`\Function`, `\Procedure`, `\Statex`, `\Call`) raise and push the paper off the Pandoc route. `\cref` to a theorem or `multline` label reads "Section". | `native/host.py:3155`, `:3085` | Any algpseudocode paper; `\cref{thm:x}` |
| 2 | A `\Checkmark` or `\ding` definition anywhere, or a `\ding` code outside the 14 known ones, raises. | `native/host.py:2950`, `:2991` | Tables with check marks; `\ding{110}` |
| 3 | `: $k=1$` becomes display math, also inside headings, table cells, and comments. | `native/host.py:4646` | `\section{Case 1: $k=1$}` (probe) |
| 4 | Math compatibility rewrites run inside verbatim and in prose. | `native/host.py:4374` | A code listing that contains `\vphantom` or `\notag` (probe) |
| 5 | Non-UTF-8 sources lose letters or crash. | `native/host.py:1596`, `:4785` | A Latin-1 `.tex` file (probe) |
| 6 | Unused draft `.tex` files change the conversion. A pass can raise on them, take label kinds from them, or put author notes in them. | `native/host.py:2944`, `:3070`, `:4356` | A submission with an old `draft.tex` next to `main.tex` |
| 7 | `\boxed` inside `eqnarray`, `alignat`, or a macro body gets nested `\(`. | `native/host.py:3034` | RevTeX and physics papers (probe) |
| 8 | LaTeXML and arXiv HTML papers never get an abstract. `reading.py` tests for `abstract` in a class token list, and LaTeXML writes `ltx_abstract`. | `papers/reading.py:135` | Every paper that falls back from Pandoc |
| 9 | On those routes each display equation is a table, so Paper orientation lists equations as tables. The Overview and Blog evidence selection sees them as tables too. | `papers/document.py:615`, `papers/reading.py:200-207` | Every LaTeXML or arXiv HTML paper with equations |
| 10 | The reader CSS `table{display:block;font-size:.85em}` also shrinks LaTeXML and arXiv HTML equations. | `app/static/appearance.js` | Every LaTeXML or arXiv HTML equation |
| 11 | `prepare_table_labels` un-comments a commented `\end{table}` and `\begin{table}` pair, and turns every `table*` into `table`. | `native/host.py:1602`, `:1735` | An author who commented out a split table |
| 12 | `prepare_compiled_bibliography` is not idempotent. A second run adds a second References heading. | `native/host.py:3858-3866` | A retry that runs the passes again on the same folder |
| 13 | Old Papers are never converted again. `conversion_revision` is stored but nothing reads it, so the library mixes outputs from different converter revisions. | `papers/convert.py:127` | Any library older than today |

## What would catch a cross-template regression before merge

The pieces exist. They need a frozen corpus, a finer diff, and a rule that forces the run. This plan reuses about half of the existing code.

1. **A frozen, labelled corpus.** Choose one or two papers per template and route: article, NeurIPS or ICLR, ICML, ACL, IEEEtran, acmart, LNCS, elsarticle, RevTeX, AASTeX, amsart, and `report`. Record each paper's `\documentclass` and the route it takes. Keep the source hashes in a tracked manifest under `docs/verification/`, and cache the sources outside git with a fetch command. `tools/robustness/sample.py download` already resumes and checks hashes. The current sample has no IEEEtran, elsarticle, or amsart paper.
2. **A per-paper snapshot and an item diff.** `tools/robustness/integrity.py` already snapshots paragraph text, headings, tables, MathML, images, and links from the reader XHTML. Add the abstract, equation numbers, and the figure count. Change `compare()` to report the changed items, not the whole lists. Add an allow-list file for reviewed, expected changes.
3. **One offline command.** It converts the corpus at the base commit and at the candidate, diffs the snapshots, and exits non-zero on any change not on the allow-list. At the measured median of 16 seconds a paper, a 20-paper corpus takes about 5 to 6 minutes. The full 76-paper sample took 26 minutes and belongs before a release.
4. **A rule that forces the run.** CI cannot run it while `tests/` is untracked and conversion needs macOS tools. The practical choice is a pre-merge hook or a line in `AGENTS.md`: a change under `native/host.py`, `papers/document.py`, `papers/convert.py`, `papers/worker.py`, `papers/arxiv_html.*`, `papers/math*`, `papers/reading.py`, or the reader CSS must pass the corpus diff before merge.

Two structural changes would shrink the blast radius itself:

- **Key each single-template pass to its template.** Run a pass written for one class, package, or paper only when that class or package is present. Record in the conversion report which passes changed each paper, so a snapshot diff can name the pass that caused it.
- **One TeX reading layer.** Use one masked-source helper for comments and verbatim, one byte-preserving read and write, and one inline-math scanner, and move the passes onto it. Every raw-text finding above then fixes in one place.
