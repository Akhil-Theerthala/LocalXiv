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
