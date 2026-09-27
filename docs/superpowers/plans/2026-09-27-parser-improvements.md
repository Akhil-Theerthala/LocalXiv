# Parser improvements from the first corpus run

The first full run of the parser corpus test (`tools/robustness/corpus.py`, revision `27c304a39be7`, 2026-09-27) converted 27 of the 98 papers with TeX source on the Pandoc route. arXiv HTML saved 35 more, LaTeXML saved 1, and 35 papers produced no EPUB. This plan orders the fixes by the number of corpus papers that each can move to the Pandoc route.

Every step ends with a corpus run against the previous commit:

```bash
python3 tools/robustness/corpus.py run --tier full --base <previous commit>
```

A step is done when its target papers take the Pandoc route or reach a later failure, and no other paper changes. A paper that reaches a later failure counts as progress, because its next cause is now visible.

## Failures by stage

| Stage | Papers | Where the cause is |
|---|---:|---|
| `math` | 25 | Both equation renderers reject an expression that Pandoc left unrendered |
| `validate` | 17 | `validate_epub` and `_finalize_epub` reject links, citations, or the abstract order |
| `pandoc` | 17 | Pandoc cannot read the TeX. Pass blame puts every located line on the author, none on a pass |
| `document` | 6 | `papers/document.py` rejects the converted structure |
| `pass` | 6 | A `prepare_*` pass raises |

## Step 1. Give the equation fallback what LaTeX has

`repair_math` sends each unrendered expression to `papers/tex_math.js` alone. MathJax then knows none of the paper's macros and none of the packages that MathJax does not load. A replay of all 1,620 unrendered expressions in the 25 papers found 459 that fail. Their errors:

| Error | Expressions | Fix |
|---|---:|---|
| `\xymatrix`, `tikzcd`, `tikzpicture` | 217 | None in this plan. MathJax cannot draw diagrams, and the app ships no TeX. These papers keep their fallback route |
| `\dv`, `\qand`, `\qfor`, `\Tr` | 93 | Load MathJax's `physics` package when the paper loads `physics` |
| `\ensuremath` | 58 | Define it as its argument |
| Paper macros such as `\mathbold`, `\Tilde`, `\klxy`, `\Bbbb`, `\bold`, `\widebar` | about 70 | Send the paper's `\newcommand`, `\renewcommand`, `\providecommand`, `\DeclareMathOperator`, and simple `\def` definitions from its `.tex`, `.sty`, and `.cls` files |
| Package commands such as `\mathds`, `\uuline`, `\varoint`, `\mathlarger`, `\emph`, `\AA`, `\l`, `\-`, `\qed` | about 36 | Define each as its MathJax equivalent |

`\cite`, `\includegraphics`, `\item`, and `\footnote` inside math show that Pandoc put non-math content in a math span. This plan leaves them.

## Step 2. Work around Pandoc's `\qed` output

Pandoc 3.11 writes a bare `\qed` outside a `proof` environment as the bytes `07 30` and `◻`. The BEL character makes the XHTML invalid, so `repair_math` fails with `not well-formed`. This affects 2405.04715v5 and 2409.08755v3. A pass rewrites a bare `\qed` that the paper does not redefine to `\ensuremath{\square}`.

## Step 3. Support the `algpseudocode` commands

`prepare_typed_references_and_algorithms` raises on `\Procedure` (2607.26832v2, 2609.17638v1) and on an algorithm with two captions or labels (2206.05096v3). This is audit risk #1.

## Step 4. Validation failures

The 17 papers split into these causes. Each needs its own look, so each gets a reduced fixture from `corpus.py reduce` or a manual reduction first:

- A link to a missing fragment, 8 papers.
- A citation key that the bibliography step cannot find, 3 papers.
- An email address or a plain word treated as a link target, 2 papers.
- A missing compiled bibliography, an empty citation, invalid XML, and the abstract order, 1 paper each.

## Step 5. Pandoc parse failures

Pass blame puts all 11 located lines on the author. Examples are `\DeclareMathOperator*{\vec1}{\vect}`, `\global\@topnum\z@`, and `\BoxedEPS`. The 6 other papers end with an unclosed environment (`minted`, `table*`). Each needs its own pass or a reduced fixture, so this step starts after steps 1 to 4.

## Out of scope

- Diagrams in math need a TeX installation, which the app does not ship.
- The 35 papers with no EPUB also fail on arXiv HTML and LaTeXML. Their Pandoc fixes come from the steps above.

## Results on 2026-09-27

The full corpus run at `27a7d7a` (revision `799fdc5c259e`), compared with the branch point `parser-corpus-test`:

| Route | Before | After |
|---|---:|---:|
| Pandoc | 27 | 47 |
| arXiv HTML | 35 | 19 |
| LaTeXML | 1 | 1 |
| No EPUB | 37 | 33 |

Twenty papers moved to the Pandoc route, and none moved away. Four of them had no EPUB before. No paper that kept its route changed: the run found no snapshot change and no new retention or invariant finding. 17 of the 20 moved papers have no finding at all. Their source anchor coverage is 0.948 to 1.0.

The fixes, in commit order:

1. The equation fallback gets the paper's macros, MathJax's `physics` package, and stand-ins for commands MathJax lacks. It retries without the paper's macros, so a macro that MathJax cannot run never breaks an expression.
2. `prepare_qed_marks` works around Pandoc's BEL character for `\qed`.
3. `algpseudocode` procedures, calls, loops, and line labels.
4. `\subfigure` panels, a redefined `figure` or `table`, and minipages that declare a float type.
5. Braced graphics stems, a comment line inside `\includegraphics`, bare and missing `\input` files, and titlesec layout commands.
6. Citations: Citeproc's anchors for keys with `+`, `&`, or `@`, citations to missing entries (LaTeX prints `?`), natbib's `(author?)`, and citations in the table of contents.
7. Bibliographies: imsart's structured markup and keywords, and the internal preambles of apsrev (REVTeX) and mnras.
8. Links: Pandoc's `id_` prefix for labels that start with a digit, labels of fallback-rendered equations, `\href` and `\url` before a line break, a scheme-less `\href`, and non-web schemes.

The retention audit also stopped reporting `\href` URLs and TeX accents as lost.

## What remains

51 papers are still off the Pandoc route: 18 at `math`, 11 at `validate`, 10 at `pandoc`, 9 at `document`, and 3 at `pass`. Seven of them fail on diagrams or figure macros inside math (`tikzcd`, `\xymatrix`, `\tikz`, `\includegraphics`, `\BoxedEPSF`), which this plan leaves out of scope. The rest are mostly one paper per cause. Examples are an unclosed group before `\end{document}`, TikZ figures, a label inside a custom box, `\ifthenelse` in math, and a missing Biber database. The report at `.verification/parser-corpus/runs/799fdc5c259e/report.md` names the line for each.

Known limits of the new fixes:

- An equation reference in a paper with per-section equation numbers shows "equation" instead of its number, because `document.py` does not number such equations. 2404.01305v1 shows this.
- The MNRAS bibliography prints no journal names, because `\aap`, `\apj`, and the other journal macros come from `mnras.cls`.
