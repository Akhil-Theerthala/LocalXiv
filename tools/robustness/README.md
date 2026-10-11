# Parser corpus test

`corpus.py` is the regression gate for parser changes. It converts a frozen set of arXiv papers of many templates and reports what broke and why. The design is in `docs/superpowers/specs/2026-09-25-parser-corpus-test-design.md`. The manifest is `docs/verification/parser-corpus.json`. Sources, runs, and reports are in `.verification/parser-corpus`.

Run each command from the repository root.

## Check a parser change

To build the corpus on a new machine, download the frozen sources:

```sh
python3 tools/robustness/corpus.py fetch
```

To check a parser change, convert the gate tier and compare it with `main`:

```sh
python3 tools/robustness/corpus.py run --tier gate --base main
```

The command exits with code 1 if a paper has a new failure, a new Content retention loss, a new invariant failure, or a changed output item that is not in `docs/verification/parser-corpus-allow.json`. The report is `.verification/parser-corpus/runs/<revision>/report.md`. Use `--tier full` before a release.

## Find the cause of a failure

To find the pass behind a failure, run `corpus.py explain ID`. It converts again once for each pass that changed the source, with that pass skipped. To get a small fixture, run `corpus.py reduce ID`. It shrinks the failing file while Pandoc or the failing pass still gives the same error.

## Rebuild the corpus

To rebuild the corpus, run `corpus.py discover`, then `corpus.py freeze`. A freeze replaces the manifest, so record the reason in the commit.

## What each file does

- `corpus.py` has the commands above.
- `audit.py` finds Content retention loss. It takes 10-word anchors that are in both the TeX source and the PDF text, and looks for each anchor in the reader output. It reads the PDF text with Ghostscript. A missing anchor is a candidate for review, not proof of loss.
- `integrity.py` makes a content snapshot of the reader XHTML: prose, headings, tables, MathML, images, links, and broken links. Unless `--base` is empty, `corpus.py run` compares the snapshots of the two revisions item by item.
