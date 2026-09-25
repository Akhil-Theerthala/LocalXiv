# Parser corpus test

The parser corpus test converts about 100 frozen arXiv papers of different templates through the real conversion path. For each paper, it reports what went wrong and which part of the parser caused it. It implements the corpus gate that `docs/parser-audit-2026-09-25.md` recommends.

## What the test must answer

A developer changes the parser and runs one command. The command must answer three questions for every paper in the corpus:

1. Did the paper convert on the expected route? Pandoc is expected unless the manifest says otherwise.
2. Is the content complete? The test checks Content retention for text, equations, tables, figures, and references against the paper's own source.
3. Is the content correct? The test compares the output with a reviewed baseline and applies checks that need no baseline.

For every "no", the report names the stage, the pass or tool, the source file and line, and a short excerpt. A developer must be able to open the file and line without rerunning anything.

"Correct" in this test means two things. The output has no unreviewed change from a reviewed baseline, and no source item is missing from the output. It does not mean "matches the PDF". The first baseline is only as good as its review.

## What the test keeps from `tools/robustness/`

The 2026-09-08 robustness evaluation (`docs/superpowers/specs/2026-09-08-parser-robustness-design.md`) is a statistical sample with a development and a held-out split. The corpus test has a different purpose. It is a regression gate, so it gets its own manifest. It does not append to `docs/verification/robustness-sample.json`.

The corpus test keeps these parts:

- `sample.py` paced downloads, hash records, and resume.
- The `evaluate.py` pattern. It copies the converter into a frozen stage, fingerprints it, and refuses to mix results from two code revisions.
- `integrity.snapshot` as the base of the regression snapshot.
- `audit.source_inventory` and `audit.reader_inventory` as the completeness check.

The corpus test changes these parts:

- `integrity.compare` returns whole lists today. It must return the changed items only, with `difflib` on each list.
- `evaluate.failure_group` sorts errors with regular expressions into six groups. Pass attribution replaces it.
- The dev and holdout split goes away. Every corpus paper runs every time.
- `audit.source_inventory` returns counts and texts without positions. It must also record the source file and line of each heading, caption, display equation, table, and note, so that a missing item can point at its source.

## The corpus

### Manifest

`docs/verification/parser-corpus.json` is tracked. Sources live in `.verification/parser-corpus/inputs/`, outside git. Each entry has these fields:

| Field | Meaning |
|---|---|
| `id` | arXiv identifier with version, for example `2303.10665v2` |
| `template` | the root `\documentclass` or `\documentstyle` name, for example `revtex4-2` |
| `style` | the venue or journal style package, if any, for example `neurips_2024` |
| `traits` | detected source features from the trait list below |
| `reason` | why this paper is in the corpus: a template quota, a trait quota, or an audit risk number |
| `expected_route` | `pandoc`, `arxiv-html`, `latexml`, or `pdf` |
| `source_sha256` | hash of the downloaded source |
| `html_available` | whether arXiv HTML existed for this version at freeze time |
| `tier` | `gate` or `full` |

A paper stays in the corpus after it fails. Nobody replaces a failing paper with an easier one.

### Template quotas

The corpus fills these quotas. The counts add to about 100. A paper counts toward one template and toward any number of traits.

The quotas are targets. Some names are style files, not classes, and some are rare on arXiv. Discovery records every shortfall. A group with less than half of its quota is a finding in the freeze report.

| Group | Templates | Papers |
|---|---|---|
| Machine learning venues | `neurips`, `iclr`, `icml`, `jmlr2e`, `tmlr`, `colm`, `pmlr` (CoRL) | 9 |
| Language and vision venues | `acl`, `cvpr`, `llncs` (ECCV), `aaai`, `ijcai` | 7 |
| ACM and IEEE | `acmart` (sigconf, acmsmall, manuscript), `sig-alternate`, `IEEEtran` (conference, journal, compsoc), `ieeeconf`, `spconf` (ICASSP), `interspeech` | 10 |
| Other CS publishers | `lipics`, `eptcs`, `usenix`, `svjour3`, `sn-jnl`, `elsarticle`, `siamart` | 8 |
| Mathematics | `amsart`, `amsproc`, `amsbook`, plain `article` with heavy theorems, `imsart`, `smfart`, a `tikz-cd` or `xy` paper | 10 |
| Physics and astronomy | `revtex4-1` (PRL), `revtex4-2` (PRD), `aastex631`, `mnras`, `aa`, `JHEP` (`jheppub`), `iopart`, `PoS`, `quantumarticle`, `SciPost`, `emulateapj`, `jcappub` | 14 |
| Life and social sciences | PLOS, eLife, Frontiers, MDPI, Copernicus, `apa7` (psychology), `apa6`, `econometrica`, `jasa`, `achemso` (chemistry), `jss` | 12 |
| Long documents and teaching | `report` thesis, `book`, `memoir`, `scrartcl`, `scrbook`, lecture notes on `article`, `beamer` slides, `tufte-handout`, a survey over 100 pages, a tutorial with `minted`, exercise sheets | 14 |
| Other languages | `ctexart` (Chinese), French `babel`, German `babel`, Russian with Cyrillic | 4 |
| No usable source | a PDF-only submission | 2 |

### Trait quotas

Traits catch faults that no template quota finds. Each trait needs at least two papers. Some rows come from the open risks in the parser audit.

| Trait | How the discovery tool detects it | Audit risk |
|---|---|---|
| `algpseudocode` with `\Function`, `\Procedure`, or `\Statex` | package and command in masked source | #1 |
| `\cref` to a theorem or `multline` label | `\cref` target label inside a theorem or `multline` | #1 |
| `\ding` or `\Checkmark` in a table | command in masked source | #2 |
| inline math after a colon in a heading | `\section{...: $...$}` | #3 |
| code listing with `\vphantom` or `\notag` | command inside `verbatim`, `lstlisting`, or `minted` | #4 |
| non-UTF-8 source | UTF-8 decode fails on a `.tex` file | #5 |
| unused `.tex` beside the root | a second `\documentclass` file that the root never inputs | #6 |
| `\boxed` in `eqnarray` or `alignat` | environment and command together | #7 |
| commented-out table split | `%\end{table}` followed by `%\begin{table}` | #11 |
| `.bbl` only, no `.bib` | file list | |
| `biblatex` with `biber` | package | |
| `00README.json` | file list | |
| single-file source that is not a tar archive | gzip magic without tar header | |
| `\input` tree three or more levels deep | include graph | |
| EPS figures | file suffix | |
| heavy macros | more than 100 `\newcommand` or `\def` | |
| `tikz` or `pgfplots` figures | package | |
| shipped `.sty` or `.cls` files | file list | |
| `longtable` or `sidewaystable` | environment | |
| `algorithm2e` | package | |
| `siunitx` `S` columns | package and column type | |
| paper from before 2000 | arXiv identifier | |

### Discovery

The template of a paper is known only after download. The discovery tool therefore works in two phases:

1. `corpus.py discover` reads monthly arXiv listing pages through `sample_listings.py` for a spread of categories. The 2026-09-08 run found that the arXiv API returns errors 500 and 429 at deep offsets, and the listing pages do not. Discovery downloads each source at one request every three seconds, and records the template, the style package, and the traits of the root file. It stops when every quota is full or the listing budget runs out. Discovery records every candidate it downloads, so a second run resumes.
2. `corpus.py freeze` picks papers for each quota with seed `20260925`. It writes the manifest and the source hashes. After a freeze, only an explicit amendment can change the manifest.

`corpus.py fetch` downloads the frozen sources on a new machine and checks their hashes. It reuses `sample.download`.

alphaXiv items resolve to arXiv identifiers, so they need no separate corpus.

## Attribution of a failure

This section answers "what caused the error, and why can the parser not handle this paper?".

### Stages

Every failure belongs to one stage. The stage order follows the code:

| Stage | Code | Example cause |
|---|---|---|
| `acquire` | `papers/acquire.py` | arXiv has no source for this version |
| `extract` | `host.extract_source` | the archive has an unsafe path |
| `root` | `host.find_root_tex` | two equally likely root files |
| `pass` | a `prepare_*` pass in `host.convert_source` | `prepare_typed_references_and_algorithms` raises on `\Function` |
| `pandoc` | the Pandoc run | parse error at line and column in a prepared file |
| `math` | `repair_math` | neither equation renderer draws one equation |
| `validate` | `host.validate_epub` | the EPUB has no abstract |
| `route` | `papers/convert.py` | Pandoc failed, and the paper converted on arXiv HTML |
| `retention` | the completeness check | 3 of 41 source equations are not in the output |
| `invariant` | the checks that need no baseline | raw `\textbf` shows in a paragraph |
| `regression` | the snapshot diff | table 2, row 4 changed |

### Pass trace

`host.convert_source` calls 38 `prepare_*` passes in a fixed order, then `prepare_compiled_bibliography`. Today a failure names only the last message. The corpus test needs each pass to report itself.

The change to `native/host.py` has three parts:

1. Replace the 38 calls with one ordered table of `(name, function)` pairs. Each function takes `source_dir` and `root`, so the five passes that need `root` fit the same table. The loop runs each pass, hashes every `.tex`, `.sty`, `.cls`, and `.bib` file before and after, and records `{pass, changed_files, seconds}`. If a pass raises, the loop writes a last record `{pass, error}` and re-raises.
2. `prepare_compiled_bibliography` stays a separate call, because the Pandoc command needs its return value. `prepare_unmatched_inline_groups` runs only after a Pandoc failure. Both append a record to the same trace, so no edit to the source goes unrecorded.
3. When the environment variable `LOCALXIV_PASS_TRACE` names a directory, the loop also copies each changed file after each pass to `<trace>/<NN>-<pass>/<path>`.

The loop writes the record list to `legacy.pass-trace.json`. The report reads the failing pass from that file, not from the error text. `papers/worker.py` keeps the last 2000 characters of an error and `papers/convert.py` keeps the first 2000, so a pass name at the start of the text can be cut. The worker copies it into the attempt entry of `conversion-report.json`, the same way it copies `legacy.source-warnings.json` today. The record is small, so the app keeps it on for every paper. The file copies are for the corpus test only.

The audit recommends this change for the app as well. A snapshot diff can then name the passes that changed a paper.

### Pass blame for a Pandoc failure

A Pandoc parse error names a file, a line, and a column in the prepared source. That file is not the author's file, because the passes rewrote it. Pass blame finds the pass that wrote the failing line. It works like `git blame` with one commit for each pass:

1. Take the failing line from the prepared file.
2. Walk the trace copies of that file backward. Use `difflib.SequenceMatcher` to map the line to the previous version.
3. Stop at the first version where the line did not exist or was different. The pass after that version wrote the line.
4. If no pass changed the line, the author wrote it. Map it to the original file and line.

The report shows the original excerpt, the prepared excerpt, and the blamed pass. If the author wrote the line, the report says so. Pandoc cannot read that construct, and no pass handles it yet.

The Pandoc position is not always the cause. A probe with Pandoc 3.11 on 2026-09-25 gave two results:

- For an unexpected token, such as a stray `}` in an `\input` child, Pandoc names the child file and the correct line: `Error at "sec/child.tex" (line 4, column 1)`.
- For an environment that never closes, such as `\begin{itemize}` ended by `\end{enumerate}` in the child, Pandoc names the last line of the root file: `Error at "main.tex" (line 7, column 2): unexpected end of input`.

When the error is `unexpected end of input`, pass blame therefore does not blame a line. It reports the environment that Pandoc expected, and the report points to pass ablation.

### Pass ablation

Pass blame finds the pass that wrote the line. It does not find a pass that broke the input some lines earlier, for example by an unbalanced brace or an unclosed environment. For a failing paper, `corpus.py explain <id>` runs the Pandoc route again once for each pass that changed a file, with that pass skipped. The report lists each skipped pass that makes the paper convert. This result is a suspect, not a proof, because skipping a pass can expose a different failure. `explain` runs only when asked, because it costs one conversion for each pass.

### Minimal reproducer

`corpus.py reduce <id>` shrinks the failing source to a small file that fails the same way. It removes paragraphs, then lines, and keeps a removal when the stage and the first error line stay the same. The output goes to `.verification/parser-corpus/reduced/<id>.tex`. A developer copies it to `tests/fixtures/parser/` as a fast check for the fix. The real paper stays in the corpus.

## Checks for each converted paper

### Content retention

`audit.source_inventory` counts source items and anchors. `audit.reader_inventory` counts the same items in the reader output. The corpus test compares them for each kind and reports every missing item with its source file and line:

- section and subsection headings,
- display equations, with their numbers,
- figures and their captions,
- tables, with their row and column counts,
- citations and bibliography entries,
- footnotes, after `audit.reader_inventory` learns to find notes in the reader output, which it does not do today,
- the abstract,
- paragraph text anchors.

A missing anchor is a finding. It can also be a flaw in the inventory. The report says which it is only after review.

### Checks that need no baseline

These checks run on every paper, including the first run:

- No raw TeX in reader text. The check looks for a backslash command, a lone `$`, or `{` and `}` outside math and code.
- No `??` or empty reference text.
- No U+FFFD replacement character. This catches encoding loss (audit risk #5).
- Every internal link and image resolves. `integrity.snapshot` already reports these problems.
- Equation numbers rise in reading order, unless the source uses `\tag`.
- The abstract exists and is not empty on every route (audit risk #8).
- `document.json` lists equations as equations, not as tables (audit risk #9).

### Regression snapshot

The snapshot extends `integrity.snapshot` with the abstract text, the equation numbers, the figure count, and the counts from `document.json`: sections, passages, figures, tables, and equations. Each snapshot records `conversion_revision`.

The diff is per item. A changed table cell reports as "table 2, row 4, cell 3" with the old and new text. It does not print both tables.

`docs/verification/parser-corpus-allow.json` lists reviewed changes. Each entry names the paper, the snapshot key, the item, the new value, and a reason. An allowed change does not fail the run. When the reviewer accepts a new baseline, the tool removes the allow-list entries that the new baseline makes true.

## The command

```bash
python3 tools/robustness/corpus.py run --tier gate --base main
```

The command runs these steps:

1. Copy the working tree into a frozen stage, as `evaluate.py` does.
2. Find the baseline snapshots for the base commit's `conversion_revision` in `.verification/parser-corpus/baselines/`. If they are missing, check out the base commit with `git worktree add`, copy it into a second frozen stage, convert the corpus there, and store the snapshots.
3. Convert every paper in the tier through `papers.convert.convert_import` with `epub_only=True`, four papers at a time, with `LOCALXIV_PASS_TRACE` set. With `epub_only=True`, `convert_import` raises `ValueError('EPUB unavailable...')` instead of opening the PDF. For a paper whose `expected_route` is `pdf`, that raise is the expected outcome.
4. Run the checks and pass blame for each paper.
5. Write `report.json` and `report.md` to `.verification/parser-corpus/runs/<stage>/`.
6. Exit with code 1 if a paper has a new failure, a new retention loss, a new invariant failure, or a regression that is not on the allow-list. A fault that the baseline already has does not fail the run. The report lists it as known.

`tests/test_parser_corpus.py` calls this command and fails on a non-zero exit. It has no logic of its own. `tests/` stays untracked, so the durable code lives in `tools/robustness/corpus.py`.

### Tiers

| Tier | Papers | Time at the measured 16-second median, four at a time | When |
|---|---|---|---|
| `gate` | about 25, one per template group and one per audit risk | about 2 minutes | before a parser change merges |
| `full` | about 100 | about 7 minutes, more when papers fall back to LaTeXML | before a release |

The times are estimates. LaTeXML has a 180-second limit, so a paper that falls back to LaTeXML can take several minutes.

### Report

The report has three parts:

1. **Template by outcome.** One row for each template group. Columns count `converted on expected route`, `other route`, `failed`, `retention loss`, and `regression`.
2. **Failures grouped by cause.** The group key is the stage, the pass or tool, and the error text with numbers and paths removed. Each group lists its papers and templates. A developer who fixes one cause sees every template that the fix touches.
3. **One section for each paper with a finding.** The section shows the identifier, template, traits, expected and actual route, the stage, the blamed pass, the original and prepared excerpts, missing items by kind, the regression items, and the paths to the logs and the trace.

A paper entry in `report.md` looks like this:

```text
2401.01234v2  revtex4-2  traits: boxed-in-eqnarray, bbl-only
route    expected pandoc, actual latexml
stage    pandoc
error    unexpected \end{eqnarray} at sections/results.tex:212:7
blame    prepare_math_compatibility wrote this line
original \boxed{E = mc^2} \nonumber \\
prepared \(\boxed{E = mc^2}\) \nonumber \\
lost     equations 3 of 41 (results.tex:212, :218, :230)
logs     .verification/parser-corpus/runs/r12/2401.01234v2/
```

## Delivery order

Each step ends with a check that runs on real papers.

1. Add the pass table and `legacy.pass-trace.json` to `host.convert_source`. Convert the Attention sample and one corpus paper, and confirm that `document.json` and the reader XHTML files are byte-identical to the output before the change. Do not compare `paper.epub` bytes, because the ZIP file can hold timestamps.
2. Add `corpus.py discover` and `freeze`. Freeze the manifest. Confirm that every quota has its papers or is listed as short.
3. Add `corpus.py run` with the stages, pass blame, the retention check, and the checks that need no baseline. Run the gate tier and review the first report by hand.
4. Add the regression snapshot, the per-item diff, and the allow-list. Change one pass on purpose and confirm that the run fails and names that pass.
5. Add `explain` and `reduce`.
6. Add the rule to `AGENTS.md`. A change under the paths the audit lists must pass the gate tier before merge.

## Decisions for the user

- Step 1 changes `native/host.py`. The app then records which passes changed each paper. It adds one small JSON record to every conversion report.
- The gate tier runs in about 2 minutes by estimate. A smaller gate is faster and catches less.
- Step 6 makes the gate a written rule. A pre-merge hook is the stricter choice.
