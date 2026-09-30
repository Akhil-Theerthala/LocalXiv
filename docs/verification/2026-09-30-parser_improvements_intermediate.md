# Parser improvements: intermediate report

State on 2026-09-30, when the branches `parser-corpus-test` and `parser-improvements` merged into `main`. This report says what was built, what changed for papers, and what is still open. The details are in these files:

- Design of the test: `docs/superpowers/specs/2026-09-25-parser-corpus-test-design.md`
- Plan and fix list: `docs/superpowers/plans/2026-09-27-parser-improvements.md`
- Frozen corpus: `docs/verification/parser-corpus.json`
- Runner and its commands: `tools/robustness/corpus.py`, `tools/robustness/README.md`

## Summary

On a frozen corpus of 100 arXiv papers with 68 templates, the Pandoc route now converts 47 of the 98 papers with TeX source. Before this work it converted 27. No paper moved away from the Pandoc route, and no paper that kept its route changed its output. The number of papers with no EPUB fell from 37 to 33. That count includes the two PDF-only papers, which have no EPUB by design.

| Route | 2026-09-27, before | After the fixes |
|---|---:|---:|
| Pandoc | 27 | 47 |
| arXiv HTML | 35 | 19 |
| LaTeXML | 1 | 1 |
| No EPUB | 37 | 33 |

Measured with `corpus.py run --tier full` at `27a7d7a` (run `799fdc5c259e`) against the branch point (run `27c304a39be7`). Of the 20 papers that moved to the Pandoc route, 17 have no retention or invariant finding. Their source anchor coverage is 0.948 to 1.0.

## What was built

### The parser corpus test

`tools/robustness/corpus.py` converts a frozen corpus through the app's real conversion path, compares it with a base commit, and reports each problem with its cause.

- `discover` downloads candidate sources from arXiv and records each paper's class, template, packages, and traits. `freeze` picks the corpus with seed `20260925`. `fetch` downloads the frozen papers and their arXiv HTML, and checks the source hashes.
- `run --tier gate|full --base <ref>` converts the corpus at the working tree and at the base commit, and exits with code 1 on a new failure, a new retention loss, a new invariant failure, or an output change that is not on the allow-list.
- For each failure, the report gives the stage, the pass or function that failed, the source file and line, the prepared line, and the pass that wrote it. `explain ID` converts again once for each pass with that pass skipped. `reduce ID` shrinks the failing file to a small reproducer.

The corpus has 100 papers from 68 templates. The gate tier has 25 papers: two from each template group, plus a paper for each open audit risk that those do not cover. Ten quotas are short because arXiv returned too few matching papers: PoS, Quantum, PLOS, APA (1 of 2), beamer, exercise sheets, Russian, and three audit-risk traits.

### Changes to the app for the test

- `host.convert_source` runs its passes from one table through `_PassTrace`. Each conversion report lists the passes that changed the source or raised.
- Each failed conversion attempt records `raised_at`, the function and line that raised.
- `papers/citations.py` wrote citation attributes in a random order, so two runs gave different bytes. The order is now fixed.

### Parser fixes

The plan lists every fix. In short:

1. **Equations.** The fallback renderer gets the paper's own macros, MathJax's `physics` package, and stand-ins for commands that MathJax lacks. It retries without the paper's macros, so a macro that MathJax cannot run does not break an expression.
2. **Pandoc bugs.** A bare `\qed`, a bare `\input file`, and `\href` or `\url` before a line break each stopped Pandoc 3.11. Passes rewrite them first.
3. **Algorithms.** `algpseudocode` procedures, functions, calls, loops, and line labels.
4. **Floats.** `\subfigure` panels, a redefined `figure` or `table`, and minipages with `\captionof` or `\@captype`.
5. **Inputs and layout.** An `\input` of a TeX system file that the archive lacks, a comment line inside `\includegraphics`, braced graphics names, and titlesec layout commands.
6. **Citations.** Keys with `+`, `&`, or `@`, citations to entries missing from the paper's `.bib` (shown as LaTeX shows them, with `?`), natbib's `(author?)`, and citations inside a table of contents entry.
7. **Bibliographies.** imsart's structured bibliography and keywords, and the internal preambles of apsrev (REVTeX) and mnras bibliographies.
8. **Links.** Labels that start with a digit, the labels of equations that the fallback renders, an `\href` without a scheme, and `doi:` or other non-web links.

The retention audit also stopped reporting `\href` URLs and TeX accents as lost content.

## Open issues

### Papers still off the Pandoc route

51 papers still fail on the Pandoc route. Most causes affect one paper. The report `.verification/parser-corpus/runs/799fdc5c259e/report.md` gives the line for each.

| Stage | Papers | Main causes |
|---|---:|---|
| `math` | 18 | Diagrams inside math (`tikzcd`, `\xymatrix`, `\tikz`), images or lists inside math, `\ifthenelse`, `\mathpalette`, `\cite` in math |
| `validate` | 11 | A link to a label that did not reach the output: a label in a custom box, in acmart's `teaserfigure`, in Copernicus's `\conclusions`, in a table cell with `$\\$`, or in an unused file |
| `pandoc` | 10 | Author constructs that Pandoc cannot read, such as an unclosed group before `\end{document}`, `\global\@topnum\z@`, `\DeclareMathOperator*{\vec1}`, and an unclosed `minted` or `table*` |
| `document` | 9 | TikZ figures with no image, and labels that end up on two elements |
| `pass` | 3 | A missing Biber database, a duplicate bibliography key, and a graphics path outside the archive |

Seven of the `math` papers draw diagrams or place figures inside math. Drawing them needs a TeX installation, which the app does not ship, so this work left them. arXiv HTML still covers most of them.

### Known limits of the fixes

- In a paper that numbers equations by section, an equation reference reads "equation" instead of its number, because `document.py` does not number such equations. 2404.01305v1 shows this.
- MNRAS bibliographies have empty journal names. The journal macros such as `\aap` and `\apj` are defined in `mnras.cls`, which Pandoc does not read.

### Tooling and process

- **arXiv source downloads.** `arxiv.org/src/<id>` answers HTTP 406 to Python for a source that arXiv's cache does not hold. `export.arxiv.org/src/` works. The corpus tools use the export host, but the app's `papers/acquire.py` still uses `arxiv.org`. A new import can therefore lose its TeX source. This is not fixed.
- **Gate rule.** No rule requires the gate before a parser change merges. The choice between a line in `AGENTS.md` and a pre-merge hook is open, and so is the gate size.
- **Base checkouts.** `run --base` keeps one checkout per base commit in `.verification/parser-corpus/worktrees/` and never removes it.
- **Run discipline.** A run converts with the code on disk. If the code under `native/`, `papers/`, or `app/` changes during a run, only the final revision check notices, and the run directory must be deleted. Do not edit that code while a run is going in the same checkout.
- **The test wrapper.** `tests/test_parser_corpus.py` calls the gate run. `tests/` stays untracked.
