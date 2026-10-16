# Parser audit: root causes from the 100-paper corpus run

This file lists the causes of parser failures and content loss in the full tier of the parser corpus (100 papers). Each issue has its papers, its mechanism, its trigger in the source, a fix direction, and a check. Use it to fix the parser in a later session. The earlier audit is `docs/parser-audit-2026-09-25.md`. This file does not repeat its structural analysis.

## Work from this file

1. Read "Baseline" and "Decisions for the user" before you change code.
2. Pick an issue from "Issue index". Fix it at its root, in the function the issue names. Find code by function name first. The line numbers are hints.
3. Check the fix with the corpus on the issue's papers only:

   ```sh
   python3 tools/robustness/corpus.py run --tier full --ids <paper ids> --base <baseline commit>
   ```

   The issue is done when the run reports `fixed <key>` for the issue's finding on every listed paper, the issue's "Check" line is true, and no paper in the run has a new finding.
4. Before you merge, run the gate tier as `tools/robustness/README.md` says.

The corpus is the only check for parser changes. Run it only when you change the parser, and give it `--ids` while you work on one issue.

## Baseline

- Run directory: `.verification/parser-corpus/runs/9a411c3e884e/`. It holds `report.md`, `report.json`, and one work directory for each paper, with `conversion-report.json`, `pandoc/pass-trace/`, `arxiv-html/`, `latexml/`, and `reader/`.
- Code: commit `c68c780` on `main`, plus the uncommitted removals from the 2026-10-12 cleanup (`native/host.py`, `papers/document.py`, `papers/coordinator.py`, `papers/explanation.py`, `papers/figures/`, `papers/HTMLSnapshot.swift`, `tools/overview_run.py`). None of these removals changes parser output.
- `corpus.py` names a run by a hash of the code, not by the commit. A commit that holds exactly this working tree hashes to `9a411c3e884e`. Then `--base <that commit>` reuses this run and converts nothing for the base. `--base main` at `c68c780` converts the base papers again.
- The run used `--jobs 8` with no base, so every finding in `report.md` is marked `new`. Read `new` as "found", not as "regression".
- CPU contention from `--jobs 8` can explain some timeouts: the epubcheck timeout of 2310.12815v5 and the LaTeXML timeouts at 180 s. Before you treat a timeout as a parser defect, convert the paper again alone.
- Line numbers are for this working tree. In `native/host.py`, lines after 3513 are 3 lower than at `c68c780`.
- The corpus runs the tools on `PATH`: Pandoc 3.12.1, epubcheck 5.4.0, and Homebrew LaTeXML 0.8.8 with TeX Live 2026. The app runs its bundled tools, which differ. See H3.

## Outcome

| Result | Papers |
|---|---:|
| Converted on Pandoc, the expected route | 47 |
| Converted on Pandoc with no finding | 34 |
| Fell back to arXiv HTML | 18 |
| Fell back to LaTeXML | 1 |
| No EPUB, expected Pandoc | 32 |
| No EPUB, expected (no usable source) | 2 |

51 of the 98 papers with source leave the Pandoc route. The Pandoc failures by stage are: math 18, Pandoc parse 10, validation 11, document 9, pass 3.

These 32 papers were expected on Pandoc and got no EPUB: 0706.3366v3, 1902.10664v6, 2010.15789v10, 2302.05737v3, 2305.04587v3, 2305.08212v2, 2310.12815v5, 2404.19350v1, 2405.04715v5, 2409.00966v2, 2409.02094v1, 2409.08755v3, 2409.10221v2, 2412.11900v1, 2506.15107v2, 2506.20120v1, 2507.00193v2, 2508.16499v1, 2603.16907v1, 2604.01908v3, 2604.06922v4, 2604.23859v3, 2606.21289v1, 2606.23510v1, 2606.30309v1, 2608.17487v1, 2608.29172v1, 2609.17638v1, 2609.26840v1, 2609.28841v1, cs/0204049v1, hep-th/9912286v3.

## Decisions for the user

The issues below make a whole route fail for a local defect. Each one is a policy choice, so ask the user before you change it. Each issue section gives the papers and the cost.

- D1. One equation that neither renderer can draw fails the Pandoc route. `repair_math` raises on the first rejected equation (`papers/math_fallback.py:54`), and the comment at line 77 says "All expressions must succeed". 2507.00193v2 fails on 1 of 79 equations, 2604.25385v2 on 1 of 221, and 2010.15727v4 on 2 of 93. The other choice: keep the raw TeX as visible text and record it in the conversion report.
- D2. One dangling internal link fails the Pandoc route (`validate_epub`, `native/host.py:664`). In 7 of 9 papers the dangling link marks real content loss (a table became text, or a caption or heading was lost). In 2607.26204v1 and 2508.16499v1 only the anchor is lost. The other choice: at runtime, change the link to a span as `_repair_cross_file_fragments` does (host.py:791-797), and fail only when the labelled float is missing.
- D3. Strict checks that LaTeX itself tolerates:
  - a duplicate `\bibitem` key (host.py:3572-3573, hep-th/9205063v1)
  - an unused `\graphicspath` entry outside the source tree (host.py:1243-1249, 2603.16907v1)
  - a second, translated abstract (`_validate_abstract_order`, host.py:466-470, 2609.15350v1)
  - duplicate link targets (`_normalize_structure`, `papers/document.py:222-223`, 3 papers, see P14)
- D4. The arXiv HTML route rejects a paper if any class contains `ltx_ERROR` or `ltx_missing` (`papers/document.py:631`). arXiv's own render has these spans, mostly in front matter. This check stops 10 papers (see F4).

## Issue index

Issues are grouped by the code that changes. "Papers" counts the papers in which the issue occurs. "Fails a route" counts the papers in which the issue alone is enough to fail a route. Most papers with no EPUB need fixes from more than one issue, because the Pandoc route and both fallback routes failed.

| ID | Issue | Papers | Fails a route |
|---|---|---:|---:|
| P1 | `$` pairing in `prepare_math_compatibility` reads comments and `\\$` | 6 | 1 |
| P2 | `prepare_table_labels` pairs a commented `\begin{table*}` | 1 | 1 |
| P3 | `prepare_inline_equations` promotes math in headings and captions | 3 | 0 |
| P4 | `prepare_column_types` leaves siunitx `S[...]` options | 2 | 2 |
| P5 | `\cref` to a theorem, lemma, or equation reads "Section" | 7 | 0 |
| P6 | `_algorithmic_line_labels` takes labels in nested math | 1 | 1 |
| P7 | `prepare_unmatched_inline_groups` is too narrow and reads only the root file | 2 | 2 |
| P8 | `prepare_graphics` misses `\psfig`, `\epsfig`, `\BoxedEPSF` | 2 | 2 |
| P9 | `prepare_abstracts` misses `\abst` and `\Abstract` | 2 | 0 |
| P10 | `prepare_source_notes` drops `\institute` and `\keywords` | 3 | 0 |
| P11 | `prepare_compiled_bibliography` cannot read a biblatex `.bbl` | 1 | 1 |
| P12 | A Latin-1 `.bib` file empties every citation | 1 | 1 |
| P13 | TikZ, tikzcd, and xymatrix have no renderer | 10 | 10 |
| P14 | Duplicate link targets that are not duplicate labels | 3 | 3 |
| P15 | Figures that Pandoc empties | 1 | 1 |
| P16 | Table constructs that Pandoc turns into text | 4 | 3 |
| P17 | Labels inside constructs that Pandoc drops | 3 | 3 |
| P18 | Author constructs that Pandoc cannot parse | 9 | 9 |
| P19 | Non-math content inside math | 3 | 3 |
| P20 | Macro expansion leaks into math | 3 | 3 |
| P21 | Gaps in `_math_macros` and the `tex_math.js` stand-ins | 6 | 6 |
| P22 | Commands that Pandoc drops with their text | 4 | 1 |
| P23 | Equation numbers and the eqref text | 1 | 0 |
| P24 | Abstract detection on the fallback routes (2026-09-25 risk 8) | 19 | 0 |
| P25 | Other document-stage defects | many | 0 |
| P26 | `lstlisting` options become an HTML `style` attribute | 2 | 1 |
| F1 | LaTeXML runs with no `--includestyles` | 14 | 14 |
| F2 | LaTeXML 0.8.8 is older than the TeX Live 2026 expl3 | 11 | 11 |
| F3 | LaTeXML error handling (applies to every LaTeXML attempt) | 2 | 2 |
| F4 | arXiv HTML checks that reject a whole paper | 25 | 25 |
| F5 | The app's bundled LaTeXML has no TeX tree | 1 | 1 |
| H1 | The corpus report hides fallback causes | all | 0 |
| H2 | False positives in the retention and invariant checks | 12 | 0 |
| H3 | The corpus runs different tool versions than the app | all | n/a |
| U1 | 2409.02094v1: cause not found | 1 | 1 |

Start with P1, P2, and P3. They share one root cause: a pass reads raw TeX with a regex and does not mask comments, escapes, or context. The 2026-09-25 audit asked for one TeX reading layer. Moving these passes onto `_searchable_tex_source` and one math scanner fixes all three. Then take P13, F1, and F4, which cover the most papers with no EPUB.

## TeX passes in `native/host.py`

### P1. `$` pairing reads comments and `\\$`

- Where: `prepare_math_compatibility`, the `split_inline` regex `(?<![\\$])\$(?!\$)...` (host.py:4196-4218). It runs on `path.read_text`, not on `_searchable_tex_source`.
- Mechanism: a `$` in a `%` comment opens a match. The lookbehind takes the `$` in `\\$` (a row break, then math) and in `\$$` for an escaped dollar. After one wrong pair, the pass treats the text between formulas as a formula and writes `$\\$` at row breaks. Pandoc then cannot parse the tabular. It writes `<div class="tabular">` and drops the caption and the label.
- Papers and triggers:
  - cs/0204049v1 (no EPUB): `jmlr.tex:724` ``at$_O$ \$$_I$``. Two tables and their labels are lost.
  - 2603.22797v1: `2025-0603.tex:394` `{@{}c@{}}$H_{1}^{6}(k)$\\$+H_{1}^{10}(k)$`. A table and its caption are lost.
  - 2607.20095v1: the `$` in the comment at `main.tex:37`. A table and its caption are lost.
  - 2010.15727v4: the comment at `spigm2024_workshop.tex:821`. The pass writes 32 `$\\$`.
  - 2608.20741v1: `revised_version.tex:810`. This is a second blocker behind P18.
  - 2302.05737v3: 160 changed lines.
- Fix: run the pass on comment-masked text and pair `$` with a scanner that counts the backslashes in front of each `$` (an odd count means escaped). Change only text inside the original math span.
- Check: the `33-prepare_math_compatibility` trace of cs/0204049v1 leaves `jmlr.tex:755` and `:913` unchanged. 2603.22797v1 and 2607.20095v1 have no `div.tabular` in the reader.

### P2. `prepare_table_labels` pairs a commented `\begin{table*}`

- Where: `prepare_table_labels` (host.py:1306). `table_pattern` (host.py:1312-1315) is applied to raw text at host.py:1471.
- Mechanism: the non-greedy match starts at a commented `% \begin{table*}` that has no end. The match runs to the next live `\end{table*}` and rewrites it to `\end{table}`. The live `\begin{table*}` then has no end. This confirms 2026-09-25 risk 11.
- Papers: 2606.30309v1 (no EPUB). Trigger: `main.tex:527` `% \begin{table*}[!t]`. Pandoc fails with "expecting \end{table*}".
- Fix: find table spans on `_searchable_tex_source` and apply the edits to the original text, as the other passes do.
- Check: after the pass, 2606.30309v1 has as many `\end{table*}` as `\begin{table*}`, and it converts on Pandoc.

### P3. `prepare_inline_equations` promotes math in headings and captions

- Where: `prepare_inline_equations` (host.py:4420-4435). This confirms 2026-09-25 risk 3.
- Mechanism: any `$a=b$` after a colon becomes `\[...\]`, also inside `\section` and `\caption` arguments.
- Papers: 2404.01305v1 (`main.tex:669` `\section{The Second case: $m_1=m_2=m_3$}`, also :889, :1831, :1966), 2507.00193v2 (captions at `v3.tex:981-1010`), 2606.08910v1 (`sample701.tex:351`), and about 10 `\item ...: $x=y$` cases.
- Fix: skip matches inside the arguments of sectioning commands, `\caption`, and `\item` lines.
- Check: the `<h1>` elements of 2404.01305v1 hold inline math, and its `display-math-inline` finding is fixed.

### P4. `prepare_column_types` leaves siunitx `S[...]` options

- Where: `prepare_column_types` counts `S` as a custom column with no argument (host.py:4519). `_standardize_column_spec` writes `c` (host.py:4487) and leaves the `[...]` option.
- Mechanism: Pandoc cannot parse `c[table-format=7.8]`. The tabular becomes text, and its caption and label are lost. Pandoc also rejects the original `S[...]`.
- Papers: 2605.00564v1 (`arXive.tex:407`), 2609.28678v1 (`article.tex:521`, `:772`, `:850`). Both were rescued by arXiv HTML.
- Fix: in `_standardize_column_spec`, also remove a `[...]` option after a replaced column letter.
- Check: both papers convert on Pandoc, with `<table id="tab:Fitted_param">` and `<table id="tab:simulation">`.

### P5. `\cref` to a theorem, lemma, or equation reads "Section"

- Where: `prepare_typed_references_and_algorithms`. The `kinds` dict (host.py:2659) has no theorem-like, `multline`, or `eqnarray` entry, so the code falls back to "Section" (host.py:2681). This is 2026-09-25 risk 1b. Risk 1a is fixed in `3fb8f14`.
- Papers: 2602.24195v1 (`arxiv.tex:392` `\cref{lem:app:QasH2}` for a label in `\begin{lemma}`), 2609.17638v1 (`thm:`, `lemma:`, `eq:`), 2609.30242v1 (`conj:`, `d:`), 2405.04715v5 (`cond:`), 2302.05737v3 (`prop:`), 2609.28678v1 (`ass:`), 2409.02094v1 (`tab:examples`).
- Fix: take the kind from the environment that holds the `\label`, including the environments declared with `\newtheorem` in the paper.
- Check: in 2602.24195v1 the reference reads "Lemma", not "Section".

### P6. `_algorithmic_line_labels` takes labels in nested math

- Where: `_algorithmic_line_labels` (host.py:2633-2654). `prepare_typed_references_and_algorithms` (host.py:2749-2750) then writes `\hypertarget{key}{}` inside the `align`.
- Papers: 2609.17638v1 (no EPUB). Trigger: `sections/lecture4.tex:3114-3116`, `\State{...\begin{align}\label{eq:4:5:theta_update}`. MathJax rejects `\hypertarget` in 5 equations.
- Fix: skip a `\label` inside `equation`, `align`, `gather`, and their starred forms.
- Check: the `09-` trace keeps the `\label` in those environments.

### P7. `prepare_unmatched_inline_groups` is too narrow

- Where: the retry for "unexpected \end" in `convert_source` (host.py:4783-4788) runs `prepare_unmatched_inline_groups` (host.py:2873) on the root file only. The pass removes only the shape in `_UNMATCHED_INLINE_GROUP` (host.py:2864), `{\textbf{\textit{`.
- Papers (both no EPUB):
  - 2409.00966v2: `main.tex:1285` `{\begin{proof}`, never closed.
  - 2506.15107v2: `contents/l2.tex:282` `Fig. \ref{frenchcwresult} {shows how`, never closed, in an `\include`d file.
- Fix: remove, or close before `\end{document}`, any `{` that is still open at the end of the body. Walk the included files too.
- Check: both papers convert on Pandoc.

### P8. `prepare_graphics` misses `\psfig`, `\epsfig`, and `\BoxedEPSF`

- Where: the command pattern in `prepare_graphics` (host.py:1236) matches only `\includegraphics` and `\epsfbox`.
- Papers:
  - math/9201280v1: `branched-plm.tex:458` `\centerline{\psfig{figure=PLM-fig.ps,height=1.5in}}`. Pandoc skips it, and `build_document` reports "A figure lost its content". arXiv HTML rescued the paper.
  - hep-th/9912286v3 (no EPUB): `thesis.tex:468-469` `$$ \BoxedEPSF{plot.eps scaled 500}`. The command is inside display math, so MathJax rejects it.
- Fix: rewrite `\psfig{figure=X,...}`, `\epsfig{file=X,...}`, and `\BoxedEPSF{X scaled N}` to `\includegraphics{X}`, and send them through the existing EPS-to-PNG step. Unwrap a `$$...$$` that holds only a graphic.
- Check: math/9201280v1 converts on Pandoc.

### P9. `prepare_abstracts` misses `\abst` and `\Abstract`

- Where: `prepare_abstracts` matches only `\abstract` and the `abstract` environment (host.py:1534). `prepare_latex_209_front_matter` handles `\abst`, `\inst`, and `\recdate` only under `\documentstyle` (host.py:1558).
- Papers: 2609.14007v1 (jpsj2, `71978_arxiv_final.tex:58` `\abst{`), math/0505527v1 (JSS, `zoo.tex:20` `\Abstract{`). Pandoc drops the command and its text, so the reader has no abstract.
- Fix: handle `\abst` and `\Abstract` in `prepare_abstracts` for every class. Move the `\inst` and `\recdate` handling out of the `\documentstyle` gate.
- Check: the passages contain "We analyze how an arbitrary observation mask" (2609.14007v1) and "zoo is an R package" (math/0505527v1).

### P10. `prepare_source_notes` drops `\institute` and `\keywords`

- Where: `prepare_source_notes` collects only affiliation, affil, contribution, correspondence, and email (host.py:4070, :4115).
- Papers: 2603.22797v1 (`2025-0603.tex:44` `\institute{`), 2603.02944v2 (`Main.tex:105` `\institute{`, `Main.tex:135` `\keywords{`), 2609.06740v1 (ctex `\author{...\\ \small \textit{Sanya University...}}`; the regex at host.py:4054 misses it; this one is likely, not confirmed).
- Fix: add `\institute` (split at `\and`) and `\keywords` to `prepare_source_notes`.
- Check: "Tongren University" and the keywords show in the abstract chapter of 2603.02944v2.

### P11. `prepare_compiled_bibliography` cannot read a biblatex `.bbl`

- Where: host.py:3577-3583 raises "This Biber bibliography needs its source .bib database" when the `.bbl` has `\entry` records and no `.bib` is in the archive.
- Papers: 2506.20120v1 (no EPUB). `Exp1240-Chambert-Loir.bbl` has 49 `\entry` records with all the data.
- Fix: in `prepare_compiled_bibliography`, convert `\entry` blocks (`\name{author}`, `\field{title}`, `\field{year}`, `\field{journaltitle}`, `\verb{doi}`) to a generated `.bib` for citeproc.
- Check: 2506.20120v1 converts on Pandoc with linked citations.

### P12. A Latin-1 `.bib` file empties every citation

- Where: no pass converts `.bib` files to UTF-8. `prepare_bibtex_string_delimiters` (host.py:3513) keeps the bytes with `surrogateescape`. Pandoc exits with code 92 ("UTF-8 decoding error"). `run_pandoc` (host.py:4775-4779) then retries without `--bibliography` and `--citeproc` and does not report it. All 41 citations come out empty, and host.py:982 raises "Pandoc emitted an empty citation", which names the wrong stage. This confirms part of 2026-09-25 risk 5.
- Papers: 2608.29172v1 (no EPUB). Trigger: `egbib.bib:271` `G\xf6sta`.
- Fix: decode `.bib` files as UTF-8, with cp1252 as the fallback, and write UTF-8. When the paper has citations, make `run_pandoc` raise "the bibliography cannot be read" and not retry without it.
- Check: 2608.29172v1 converts on Pandoc with linked citations.

### P13. TikZ, tikzcd, and xymatrix have no renderer

- Where: no pass renders TikZ in the Pandoc route. Only `prepare_forest_diagrams` (host.py:2022) renders a drawing to an image. Pandoc skips a `tikzpicture`. In math, MathJax rejects tikzcd, xymatrix, and `\tikz` (`papers/tex_math.js:1` rejects unknown commands by design).
- Papers in figures (all rescued by arXiv HTML): 2601.20893v1 (`author_version.tex:219`, pgfplots), 2604.09129v1 (`proceeding-pisa-2024-Vanhove_final.tex:749`), 2607.26832v2 (`main.tex:78`). `build_document` reports "A figure lost its content".
- Papers in math. The numbers in brackets are rejected equations of all equations sent to MathJax:
  - 2409.08755v3 (15/17, no EPUB): `Squelettes-accessibles.tex:423-424` `\[ \begin{tikzcd}`.
  - 2412.11900v1 (14/17, no EPUB).
  - 2609.30242v1 (16/48, rescued by arXiv HTML).
  - 2010.15789v10 (1, no EPUB; see also P19).
  - 2305.08212v2 (157/186, no EPUB): `main.tex:258` `$$\xymatrix{`.
  - 2609.17638v1 (3, no EPUB): `sections/lecture2.tex:448` `\tikz[baseline=(C.base)...]{`.
  - 2604.06922v4 (20, no EPUB): `SciPostPhysCodeb.tex:856` `\diagram`, which wraps `tikzpicture` in `cqmacros.sty`.
- Fix: extend `prepare_forest_diagrams` to `tikzpicture`, `tikzcd`, `\xymatrix`, and `\tikz`. Render them with TeX to an image, and replace the whole equation when the drawing is in math.
- Check: 2305.08212v2 and 2409.08755v3 convert on Pandoc. The three figure papers convert on Pandoc with an image in each figure.

## Constructs that Pandoc cannot handle

For each issue below, Pandoc fails on, or drops, a construct that is in the original source. No pass changes the construct. The fix is a new rule in the named pass, or a new pass next to it.

### P14. Duplicate link targets that are not duplicate labels

`_normalize_structure` raises at `papers/document.py:222-223`. In all three papers every route failed. None of them has a duplicate `\label` in the TeX that LaTeX reads. See D3.

- 2310.12815v5: Pandoc copies a shared table caption and id onto each grid. The shared-caption grouping (document.py:179) would handle it, but `build_document` adds a table to `table_groups` (document.py:589) only when the body has exactly one `\label`. This body has three: two sub-labels and the outer label (`6_evaluation.tex:214`, `:228`, `:242`). `prepare_subfloats` removed the `\subfloat` wrappers and left the three labels. Fix: accept a body with grids + 1 labels, keyed on the label outside every tabular. Check: the paper converts on Pandoc with the warning "Preserved a shared caption".
- 2604.23859v3 (Quarto output): `content_en.tex:1156` `\protect\hypertarget{exm-fail-safe-nan-en}{}\label{exm-fail-safe-nan-en}`. The `div` gets the id from `\label`, and an empty `span` inside it gets the same id. The marker test at document.py:158 needs `data-label` equal to the id. Fix: treat an empty `span` with only an id as a marker.
- 2606.23510v1: `papers/math_fallback.py:59` runs `re.findall` for `\label` over raw TeX with comments. It finds `Berm06` twice: once in `%\label{Berm06}` (line 343) and once live (line 378). Fix: remove comments and duplicates before the scan.
- Three `\label` scanners disagree on comments and duplicates: document.py:545, math_fallback.py:59, and host.py:697. Use one shared helper.

### P15. Figures that Pandoc empties

- 2102.04217v4: `\centering{ \includegraphics[...]{...} }` (`02_Related.tex:59-60`, also `07_RQ4.tex:24`, `:33`, `999_Appendix.tex:6`, `:224`, `08_Conclusion.tex:12`). Pandoc takes the braced group as an argument of `\centering` and drops the image. Fix: in `prepare_graphics` or a new pass, remove `\centering` when `{` follows it. Check: the paper converts on Pandoc with 6 more `<img>` elements.
- Pandoc logs a skipped construct as `[INFO] Skipped` only with `--verbose`, and the pipeline does not pass that option. The only signal is the late figure check at document.py:621-630, which is correct.

### P16. Table constructs that Pandoc turns into text

When Pandoc cannot parse a tabular, it writes `<div class="tabular">` and drops the caption and the label. P1 and P4 also cause this.

- 2609.26840v1 (no EPUB): `\multicolumn{8}{@{}l}{$d = 2$}` in `best_known_gh.tex:11`, `best_known_le.tex:11`, `:52`. Fix: remove `@{...}` and `!{...}` from the second argument of `\multicolumn` in `prepare_column_types` or `prepare_table_rules_and_checks`.
- 2607.26204v1 and 2508.16499v1 (the second has no EPUB): a float with more than one `\label`. Pandoc gives every table in the float the last label and drops the others. Triggers: `98a-chain-address.tex:12` plus a stray `\label{tab:heuristic1}`; `table/RQ2/memory_and_results.tex:3-6`, which inputs two tables that each have a caption and a label. Fix: keep one label per caption. Move each extra label after `\end{table}`, and split a float that holds several caption and tabular pairs.
- 2609.27200v1: `\addlinespace` before a `\multicolumn` row (`OptimalTest_arXiv.tex:3472-3473`). Pandoc writes an empty row and drops the "Panel B" cell. Fix: remove `\addlinespace[...]` in `prepare_table_rules_and_checks`.
- Detection: report `class="tabular"` in Pandoc output, or a source `\label` with no id in the output, and name the label. That error is more useful than "EPUB link fragment is missing".

### P17. Labels inside constructs that Pandoc drops

Pandoc drops the label together with a caption or heading. `prepare_wrapfigures` (host.py:3326) maps only `wrapfigure` and `wraptable`.

- 2305.04587v3 (elife, no EPUB): a `table` float with no tabular drops its `\caption*` and `\label` (`rsabsence.tex:585-597`). The Box 1 caption is lost. Fix: rewrite a `table` float that holds no tabular as `figure`.
- 2607.17725v1 (acmart, rescued): `teaserfigure` keeps the image and drops the caption and the label (`FastVEM.tex:69-82`). Fix: map `teaserfigure` to `figure*`.
- 0706.3366v3 (copernicus, no EPUB): `\conclusions[...\label{sec5}]` and `\introduction` (`draft9.tex:635-636`). The heading text and the label are lost. Fix: map `\introduction[x]` and `\conclusions[x]` to `\section{x}`, with "Introduction" and "Conclusions" as defaults.

### P18. Author constructs that Pandoc cannot parse

All nine papers got no EPUB.

| Paper | Trigger | Fix |
|---|---|---|
| 2110.05216v4 (spconf) | `\renewcommand\maketitle` with `\global\@topnum\z@` (`egpaper.tex:116-131`). Pandoc expands it at `\maketitle`. | Remove redefinitions of `\maketitle` and `\@maketitle`, next to `prepare_title_formats` (host.py:3104). |
| 2404.19350v1 (acmsmall) | `\newenvironment{mlirblock}{\VerbatimEnvironment\begin{minted}...}` (`main.tex:45-51`), 66 uses. | Rewrite each use of a verbatim wrapper environment into the wrapped environment, and remove the definition. |
| 2606.21289v1 (IEEEtran) | `\textit{\begin{itemize}...\end{itemize}}` (`cai_fewshot.tex:302`). | Unwrap a font command around a block environment, next to `prepare_inline_font_commands` (host.py:3265). |
| 2608.17487v1 (elsarticle) | `\cite{chen2022dped,simonyan2014two,,yang2026unipet}` (`arxiv_pr.tex:522`). | Remove empty keys in `prepare_redundant_citation_groups` (host.py:2105). |
| 2608.20741v1 (revtex) | `\def\proof`, `\def\endproof`, and `\QEDclosed` = `\mbox{\rule[0pt]{1.3ex}{1.3ex}}` (`revised_version.tex:165-168`). | Remove paper definitions of `\proof` and `\endproof`, near `prepare_qed_marks` (host.py:3219). Add `mbox` to `prepare_reflowable_boxes` (host.py:2997). P1 is the second blocker. |
| 2609.28841v1 (article) | `\DeclareMathOperator*{\vec1}{\vect}` (`revision_26.tex:85`), never used. | Remove declarations whose name is not `\[A-Za-z]+` in `prepare_package_math` (host.py:4262). |
| 2604.25385v2 (jcap) | `\def\ba#1\ea{\begin{align}#1\end{align}}` (`main-4.tex:146`). Pandoc writes the body as a formula and drops every use. arXiv HTML rescued this paper. | Expand macros with delimited parameters at their uses, and remove the definition. Check: 4 more display equations in the EPUB. |
| 2409.10221v2 (jss) | `Sinput` and `Soutput` from `jss.cls:203` (`\DefineVerbatimEnvironment`). The `$` in R code opens math (`article.tex:1101`). | Rewrite every `\DefineVerbatimEnvironment` name to `verbatim`, next to `prepare_alltt_blocks`. |
| 2507.00193v2 (siamart) | `\item [(ii)]` inside `subequations` (`v3.tex:228-233`). | Unwrap a `subequations` body that holds non-math content, and keep its `\label` on the first equation. |

### P19. Non-math content inside math

`prepare_math_compatibility` (host.py:4220-4238) lifts only `$...$` and `\emph` out of `\text`.

- 2010.15789v10 (no EPUB): `\text{(by \cite[Section 12.24]{Rudin} ...)}` (`virtual_morse-bott...tex:1824`), 11 equations. Fix: move the citation out of the formula.
- 2604.06922v4 (no EPUB): `\begin{align} \raisebox{-0.5\height}{\includegraphics[...]}` (`SciPostPhysCodeb.tex:492-493`), 8 equations. Fix: write a display equation that holds only a graphic as an image paragraph, and keep its `\label`.
- 2010.15727v4 (rescued): `tabular` inside `eqnarray` (`spigm2024_workshop.tex:2301-2303`). Fix: rewrite `tabular` to `array` inside math.

### P20. Macro expansion leaks into math

Pandoc expands the paper's macros before `repair_math` sees the TeX, so `_math_macros` (host.py:4567) does not take part. All three papers got no EPUB.

- 1902.10664v6: `\DeclareMathOperator*{\E}{\mathds{E}}` (`tmlr.tex:191`) after `\sideset` (`:798`) gives an unbraced `\mathop`, 11 equations. Also `\ifthenelse` (6) and `\scalerel` (2).
- 2302.05737v3: `\newcommand{\var}[2][]{\ifthenelse{\equal{#2}{}}...}` (`preamble.tex:177-178`), 17 equations.
- 2405.04715v5: `\newcommand*{\centernot}{\mathpalette\@centernot...}` (`tptstyle.sty:38-39`), 9 of 15 equations.
- Fix: a new pass that removes paper definitions of commands MathJax knows when the definition uses `@` internals, adds braces around the third argument of `\sideset`, and resolves `\ifthenelse{\equal{#n}{}}{A}{B}` at each call.
- Check: 2405.04715v5 converts on Pandoc. 1902.10664v6 has no `\mathop` or `\ifthenelse` rejection.

### P21. Gaps in `_math_macros` and the `tex_math.js` stand-ins

- The stand-ins in `papers/tex_math.js` assume math mode. `textsc` becomes `\text{#1}` (line 17) and `emph` becomes `\textit{#1}` (line 24), so `\text` ends up in text mode, where MathJax rejects it. `\textunderscore` exists only in math mode.
  - 2603.12597v1: `\( R \gets \text{\feynman}(S) \)` (`sections/2_methodology.tex:164`).
  - 2602.24195v1: `$\text{top\textunderscore p}=0.9$` (`arxiv.tex:1558`).
  - 2609.17638v1: `\emph{\text{L}}` (`sections/lecture5.tex:1332`).
  - Fix: `textsc` to `\textrm{#1}`, `textunderscore` to `'\_'`, and `text` to `\textrm{#1}`. These two lines fix 2602.24195v1 and 2603.12597v1 completely. Both were rescued by arXiv HTML in this run.
- `_math_macros` (host.py:4567-4602) reads `\newcommand`, `\DeclareMathOperator`, `\def`, and `\let` only.
  - math/9912218v2: `\newfont{\Bbbb}{msbm7 ...}` (`main.tex:95`). Fix: map an msbm or msam `\newfont` to `\Bbb`.
  - 2302.05737v3 (`\klxy`), 2609.17638v1 (`\ceil`): `\DeclarePairedDelimiter[X]`. Fix: translate to `\left...\right` macros.
  - `tex_math.js` has no `\slash` (hep-th/9912286v3), `\underbar`, or `\theequation` (2302.05737v3). Fix: `slash: '/'`, `underbar` to `\underline`, `theequation: ''`.
- Check: math/9912218v2 converts on Pandoc.

### P22. Commands that Pandoc drops with their text

- math/0505527v1: `\code`, `\proglang`, and `\pkg` are defined only in the shipped `Z.cls` (lines 26-28). Pandoc drops them and their arguments: the reader has "time series, in package , but". This causes 210 missing anchors. Fix: copy simple `\let` and `\newcommand` text macros from local `.cls` and `.sty` files into the TeX that Pandoc reads.
- 2603.02944v2: a `filecontents*` block before `\documentclass` (`Main.tex:23`) shows as PostScript text in `ch001.xhtml`. Fix: remove `filecontents` and `filecontents*` in an early pass.
- 2604.01908v3 (no EPUB): `\section*{\color{scipostdeepblue}{Abstract}}` (`main-v5.tex:50`). Pandoc writes an empty `<h1>`. `_package` (document.py:333-335) writes an empty nav anchor, and epubcheck rejects it (document.py:404). The `require_abstract` regex (host.py:4727) misses this form too. Fix: remove `\color` and `\textcolor` wrappers in sectioning arguments. Never write an empty nav label.
- 2603.02944v2, 2607.21091v1: `--number-sections` (host.py:4744) ignores `secnumdepth`, so headings read "6.0.0.1". The text is kept. This one is likely, not confirmed.

### P26. `lstlisting` options become an HTML `style` attribute

Found after the corpus run, in a paper the user imported in the app. The paper is not in the corpus.

- Mechanism: Pandoc turns each `lstlisting` option into an attribute. `style=clmactstyle` becomes `style="clmactstyle"` on the code block. That value is not CSS, so epubcheck fails with CSS-008 ("Premature end of grammar"), and `papers/document.py:404` fails the route. No pass in `native/host.py` changes listing options. A snippet with `\begin{lstlisting}[style=foo,language=Python]` gives `<div class="sourceCode" style="foo" data-language="Python">`.
- Pandoc also ignores `escapeinside` and `moredelim`, so the delimiters show as text: `!open(...)!`, `@LEDGER TOP:@`, and `(*\textemdash{}*)`.
- Papers:
  - 2609.37725v1 ("Context Language Models", not in the corpus, no EPUB). `figures/clm_examples.tex:8-28` defines `\lstdefinestyle{clmactstyle}` with `escapeinside={(*}{*)}` and `moredelim=[is][\color{...}]` for `@`, `~`, and `!`. Lines 48, 57, and 69 use `\begin{lstlisting}[style=clmactstyle]`. There are 8 such blocks in `ch005.xhtml`. The arXiv HTML route failed with "An embedded code download disagrees with its printed listing" (F4). The cause is likely the same `escapeinside`, as in 2409.02094v1. The LaTeXML route failed on F5.
  - 2409.02094v1 (U1) also uses `[style=...]`. This defect will show after U1 is fixed.
- Fix: add a pass, or extend the pass that protects literal environments (`_PROTECTED_LITERAL_ENVIRONMENT`, host.py:1650), that keeps `language` and removes the other options from `lstlisting`. Read `escapeinside`, `escapechar`, and `moredelim` from `\lstset` and `\lstdefinestyle`, and remove those delimiters from the listing body. Keep the text between them.
- Check: 2609.37725v1 converts on Pandoc, its code blocks have no `style` attribute, and the listing text has no `!`, `@`, or `(*` delimiters.

## Document stage: `papers/document.py` and `papers/reading.py`

### P23. Equation numbers and the eqref text

- Where: `_equation_numbers` stops on `\numberwithin` (document.py:534-538). `_readable_internal_reference_labels` then writes the word "equation" as the link text (document.py:426, :464).
- Papers: 2404.01305v1. `main.tex:11` `\numberwithin{equation}{section}` and `main.tex:284` `system~\eqref{2_15}`. The reader reads "we will use system equation".
- Fix: support `\numberwithin{equation}{section}` by resetting the counter in each section.
- Check: `ch003.xhtml` shows "(2.15)".

### P24. Abstract detection on the fallback routes

- Where: `_markers` (`papers/reading.py:101-106`) splits on `[^A-Za-z0-9_-]`, so `ltx_abstract` stays one token. The test at reading.py:132 looks for `abstract`. This confirms 2026-09-25 risk 8.
- Papers: all 19 papers that converted on arXiv HTML or LaTeXML get `abstract_status` "unavailable". The 42 checked Pandoc papers get "identified".
- Also: the local LaTeXML `<abstract>` has no heading, so its passage takes the title as its section (document.py:637-645, math/9912218v2).
- Fix: treat a token that ends in `abstract` as an abstract marker. Give the LaTeXML abstract an "Abstract" section.
- Check: `reading.build_orientation` on the `document.json` of math/9912218v2 returns "identified".

### P25. Other document-stage defects

- 2026-09-25 risks 9 and 10 are still open. On the fallback routes each display equation is an `ltx_eqn_table`. Paper orientation counts them as tables (reading.py:199, document.py:646): hep-th/9205063v1 has 351, 2609.30242v1 236, 2604.25385v2 202. The reader CSS rule `table{display:block;...font-size:.85em}` (`app/static/appearance.js:71`) shrinks them.
- The EPUB `<title>` keeps raw TeX from the arXiv metadata title, for example "CCH$^+$ ion ($^3\Pi$)" in 2605.00564v1.
- 2026-09-25 risks 12 and 13: `prepare_compiled_bibliography` is still not idempotent, but `papers/worker.py:161-172` extracts the source again for each attempt, so the risk does not occur. Nothing reads `conversion_revision` (`papers/convert.py:127`). The corpus does not exercise either one.

## Fallback routes: `papers/worker.py` and `papers/arxiv_html.*`

### F1. LaTeXML runs with no `--includestyles`

- Where: `worker.py:79` runs `latexml` with no `--includestyles`. LaTeXML then only scans a shipped `.sty` or `.cls` for dependencies, so its macros stay undefined. Each failure follows "Warning:missing_file:X Can't find binding" or "using OmniBus".
- Papers: 1902.10664v6, 2302.05737v3, 2404.19350v1, 2405.04715v5, 2409.08755v3, 2409.10221v2, 2506.15107v2, 2507.00193v2, 2604.01908v3, 2604.06922v4, 2604.23859v3, 2609.17638v1, cs/0204049v1, hep-th/9912286v3. Example: `tmlr.tex:469` `\name`, with `tmlr.sty` in the source.
- The mechanism is confirmed. That `--includestyles` fixes most of these papers is likely, not tested.
- Check: 1902.10664v6 and cs/0204049v1 write `latexml/paper.xml`.

### F2. LaTeXML 0.8.8 is older than the TeX Live 2026 expl3

- Mechanism: `expl3.sty.ltxml:20` makes LaTeXML 0.8.8 read the raw `expl3-code.tex`, including the CaseFolding loop at line 35568. tcolorbox, xparse, spath3, bookmark, babel-german, and mhchem load it.
- Papers with an error: 2508.16499v1, 2606.21289v1, 2606.23510v1, 2606.30309v1, 2608.17487v1. Papers with a timeout at 180 s: 0706.3366v3, 2305.04587v3, 2310.12815v5, 2409.02094v1. babel-french (`french3.ldf:864`, `\IfPackageLoadedTF`) fails 2412.11900v1 and 2506.20120v1.
- The location is confirmed. The version mismatch as the cause is likely.
- Fix: this is the environment, not the code. Use LaTeXML 0.8.9 or later, or a TeX tree with an l3kernel that LaTeXML supports. Tell the user. This fix affects the Mac app's bundled tools.

### F3. LaTeXML error handling

- `worker.py:51-52` raises on the first `Error:` line. The `finally` block (worker.py:63) stops LaTeXML, so every "Fatal:terminate" line in the logs comes from LocalXiv, not from LaTeXML.
- The regex `\d+ errors?\b` also matches the latexmlpost summary "1 error" when latexmlpost exits with code 0. This stops 2608.29172v1 for "No available image processing module" (overpic). Install PerlMagick, or pass `--nopictureimages`.
- 2609.28841v1: latexmlpost fails on a bare `_` in `mybib.bib`. This one is likely.
- Fix: keep recoverable errors (`Error:undefined`, image post-processing) apart from failures.

### F4. arXiv HTML checks that reject a whole paper

| Check | Where | Papers | Fix |
|---|---|---|---|
| Any `ltx_ERROR` or `ltx_missing*` class (D4) | `papers/document.py:631` | 0706.3366v3 (3), 2305.04587v3 (2), 2409.08755v3 (45), 2409.10221v2 (187), 2412.11900v1 (missing labels only), 2506.15107v2 (70), 2506.20120v1 (59), 2603.16907v1 (21), 2609.17638v1 (12), cs/0204049v1 (1) | Remove an `ltx_ERROR` span and keep its tail text, then warn. Fail only above a threshold. Report `ltx_missing_*` as unresolved references. |
| SVG has an external or active resource | `_check_svg`, `papers/arxiv_html.py:182-193` | 1902.10664v6, 2608.29172v1, 2608.17487v1 (overpic `<img src>` or `<object>`), 2604.23859v3 (tcolorbox `<a href>`) | Accept a `src` that `asset_url()` accepts, and accept `<a href>`. Keep the ban on script, iframe, embed, and `on*` attributes. |
| XHTML inside `<mtext>` | `clone()` in `papers/arxiv_html.js:79-80` | 2507.00193v2, 2405.04715v5 (MathJax rejects `span` and `a`), 2409.00966v2 (a `span` with `<p>` becomes a `div`, and epubcheck fails) | In math text, reduce the children to text and never promote to `div`. |
| Code download differs from the printed listing | `restore_listings`, `papers/arxiv_html.py:50` | 2409.02094v1 (`escapeinside`), 2508.16499v1 | Keep the printed listing and skip the restore. |
| xmldom warning stops the parse | `papers/arxiv_html.js:10` | 2604.01908v3, 2604.06922v4 (U+FFFD from mathdesign) | Stop only on errors. The glyphs are lost, so the route must still fail, with a readable message. |
| Figure lost its content | `restore_caption_groups`, `papers/arxiv_html.py:78` | 2606.30309v1 (media is still `<object>`; image and caption sit in one row) | Add `object` to the media set and accept a two-cell row. hep-th/9912286v3 is a real loss. |
| epubcheck on invalid arXiv markup | `clone()` in `papers/arxiv_html.js` | 2606.23510v1 (`rowspan` on `span`), 2606.21289v1 (raw `<Math><XMath>`), 2609.28841v1 (URL with `<`) | Remove `rowspan` and `colspan` outside cells, replace `Math` with its TeX, and encode bad URLs. |

These failures are not defects: HTTP 404 because arXiv has no HTML (2302.05737v3, 2404.19350v1, 2609.26840v1), the 30 s parse timeout on a 15 MB page (2010.15789v10, arxiv_html.py:129), and the epubcheck timeout on a 7.4 MB page (2305.08212v2).

Upstream defects in arXiv's own HTML: raw TeX from `\textcircled` in `ltx_markedasmath` (2609.30242v1, 2010.15727v4), and the English abstract is missing from 2609.15350v1.

### F5. The app's bundled LaTeXML has no TeX tree

- Mechanism: `/Applications/LocalXiv.app/Contents/Resources/runtime/vendor` holds LaTeXML 0.8.8, but the runtime has no TeX tree and no `kpsewhich`. When a LaTeXML binding reads a TeX file, the file is missing. For `listings`, LaTeXML logs "Can't find configuration listings" and then `Error:undefined:\lstlanguagefiles` (listings.sty.ltxml line 1603). `worker.py:51-52` then fails the route.
- Papers: 2609.37725v1 (app import, not in the corpus). In the corpus, 2508.16499v1 loads `listings.sty.ltxml` with no such error, because TeX Live 2026 is on this Mac.
- Effect: in the shipped app, every paper that uses `listings` likely fails the LaTeXML route. Other bindings that read TeX Live files likely fail the same way. The corpus does not show this (H3).
- Fix: this is packaging, so tell the user. Bundle the TeX files that the LaTeXML bindings read, such as `listings.cfg`, or point LaTeXML at a TeX tree.
- Check: in the installed app, the LaTeXML route of 2609.37725v1 gets past `listings.sty.ltxml`.

## Diagnostics and the corpus harness

### H1. The corpus report hides fallback causes

- `cause_of` runs only for the expected route (`tools/robustness/corpus.py:798-799`). The report gives no cause for the arXiv HTML and LaTeXML failures of the 32 papers with no EPUB.
- `corpus.py:668` keeps `error[:800]`, and `:683` and `:692` keep `splitlines()[0]`. For LaTeXML, the first line is "(Loading ...)" noise. The first `Error:` line is in the stored text (`worker.py:52` keeps the last 1800 characters), so the corpus loses it, not the worker.
- Errors that `arxiv_html.retrieve()` raises have `raised_at: None`, so `stage_of` cannot give a stage.
- `papers/arxiv_html.py:131` keeps `stderr[-800:]` and `papers/document.py:284` keeps `stderr[-500:]`. Both cut off the real message.
- `signature()` groups by the first line of the error. Two causes can share one signature.
- Fix: report a cause for every attempt, and store the first diagnostic line.

### H2. False positives in the retention and invariant checks

A missing retention anchor is a candidate, not proof. In this run these findings are not parser defects:

- `audit.visible_text` (`tools/robustness/audit.py:160-166`) reads MathML tokens with spaces: "SU(2)" becomes "s u 2". This explains all anchors on math/9912218v2 and math/9201280v1, nearly all on hep-th/9205063v1, and some on 2607.21091v1 and 2609.27200v1.
- `prose()` (audit.py:47) does not map `\"{\i}`.
- audit.py:165 and `invariants` (corpus.py:731) read the `<head><title>` text.
- The `raw-math` regex (corpus.py:703) matches prices: `\$250` (2102.04217v4), `\$0.0129` (2608.00261v1).
- `??` comes from the source: `volume = {???}` in 2605.00564v1.
- Numeric citations are by design (`papers/citations.py`): 11 of 14 anchors on 2607.19007v1.
- `retention()` (corpus.py near 760) has no details for `unparsed_tabular_blocks` or the graphics count, so their count shows 0. The missing graphic of 2102.04217v4 is inside the author's `\remove{}`.
- 2404.01305v1 and 2607.24136v1 have no abstract in the source. cond-mat/9912445v1 has `{\bf Abstract}`, and its text is present.

### H3. The corpus runs different tool versions than the app

| Tool | Corpus (`PATH` on this Mac) | App bundle (`runtime/manifest.json`, v0.0.18) |
|---|---|---|
| Pandoc | 3.12.1 | 3.11 |
| epubcheck | 5.4.0 | 5.3.0 |
| LaTeXML | 0.8.8 with TeX Live 2026 | 0.8.8_5 with no TeX tree |
| Python | 3.15 | 3.14.7 |

- A corpus pass does not prove that the app converts the paper. F2 reads expl3 from TeX Live 2026, so in the app it likely fails in a different way. F5 cannot occur in the corpus on this Mac.
- Fix: run the corpus with the bundled tools first on `PATH`, or record the tool versions in each run and in `report.md`. Ask the user which environment the corpus must represent.

## Unresolved

### U1. 2409.02094v1: cause not found

- Pandoc reports "unexpected ()" at `main.tex:130:17`, just after `\begin{document}`. Snippet tests of the preamble, the body without `\input`, the `.bbl`, and the figure inputs all parse. The real error is likely in an `\input` file.
- Suspects: `prepare_local_heading_styles` removes `\usepackage{sosy-paper}` but not `\usepackage{../sosy-paper}` in `figures/output-witnesses-*.tex:2`. `prepare_math_compatibility` changed a TikZ label in `figures/output-witnesses-example-correctnes.tex:42`.
- This paper also uses `\begin{lstlisting}[style=...]`, so P26 will fail it after this cause is fixed.
- Next step: `python3 tools/robustness/corpus.py reduce 2409.02094v1`. It converts the paper many times, so tell the user before you run it.

## State of the 2026-09-25 audit

| Risk | State | Evidence |
|---|---|---|
| 1a algorithm commands raise | Fixed in `3fb8f14` | `Assert`, `Goto`, `Print`, `Switch`, and `Case` still raise (host.py:2768). No corpus paper uses them. |
| 1b `\cref` reads "Section" | Open, hit | P5 |
| 2 `\Checkmark` and `\ding` | Open, not hit | The corpus uses only `\ding{51}` and `\ding{55}`. The pass now reads masked text. |
| 3 colon rule in headings | Open, hit | P3 |
| 4 math rewrites in verbatim and comments | Open, hit in comments | P1. 87 edits fell inside comments. |
| 5 non-UTF-8 sources | Open, hit | P12. 12 passes still read with `errors="replace"`. |
| 6 unused draft `.tex` files | Open, hit, no harm seen | Passes edited unused files in 2603.05806v1, 2409.02094v1, and 2102.04217v4. |
| 7 `\boxed` in `eqnarray` | Open, not hit | |
| 8 no abstract on fallback routes | Open, hit | P24 |
| 9 equations counted as tables | Open, hit | P25 |
| 10 CSS shrinks fallback equations | Open, hit | P25 |
| 11 `prepare_table_labels` and comments | Open, hit, fails a route | P2 |
| 12 bibliography pass not idempotent | Open, not triggered | P25 |
| 13 `conversion_revision` never read | Open, not hit | P25 |

Structural state: `convert_source` runs 46 passes, plus `prepare_compiled_bibliography` and the retry pass. The audit counted 39. Only `prepare_latex_209_front_matter` is gated on the class. Three passes gate one branch on a package. `_PassTrace` now records changed files and errors for each pass. Four separate comment strippers and six inline-math regexes remain. P1, P2, and P3 come from unmasked raw-text passes, so the single TeX reading layer is still the fix with the most effect.
