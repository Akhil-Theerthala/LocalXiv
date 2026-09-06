# Pinned upstream LaTeXML compatibility probe

Date: 2026-09-06. The Homebrew LaTeXML 0.8.8_5 converter stalled while loading
TeX Live 2026 `expl3-code.tex` for arXiv 2511.00280v1. A bounded probe tested the
official upstream source at commit
`ee4b3640a26d1ba359670b3304e07678d4d1e87e` without changing the system install.

Source archive:
`https://codeload.github.com/brucemiller/LaTeXML/tar.gz/ee4b3640a26d1ba359670b3304e07678d4d1e87e`

Downloaded archive SHA-256:
`63be9089d11b8735f688254d408a8e0f6061f8305840980a96ee43b5eb4617b7`

The extracted source under `.verification/upstream-latexml/LaTeXML-<commit>`
can run directly; `bin/latexml` uses the neighboring `lib` directory. The probe
used `/usr/bin/perl -I<source>/lib <source>/bin/latexml --includestyles
--destination=<run>/paper.xml <run>/source/acl_latex.tex`, with working directory
`<run>/source`. Its environment contained only:

- `PATH=/opt/homebrew/bin:/Library/TeX/texbin:/usr/bin:/bin`
- `PERL5LIB=<source>/lib:/opt/homebrew/opt/latexml/libexec/lib/perl5`
- `HOME`, `TMPDIR`, and `TEXMFOUTPUT` pointing to the isolated run directory
- `LANG=en_US.UTF-8`

The Perl dependency path supplies Homebrew dependencies; the leading upstream
path selects the tested LaTeXML code and bundled `lib/LaTeXML/Package` bindings.
Installed `/Library/Perl` modules remain available through Perl's standard paths.
The conversion ran within the deny-by-default, no-network macOS profile from
`papers.convert.sandbox_profile`, with only the run directory writable. An outer
Python process enforces a 120-second timeout and kills the conversion process
group on expiry. The reproduction script and full log are retained in
`.verification/upstream-latexml/test_runtime.py` and `run/latexml.log`.

The upstream revision still reports repeated `Unknown message 'invalid-cctab'
for module 'cctab'` errors while loading
`/usr/local/texlive/2026/texmf-dist/tex/latex/l3kernel/expl3-code.tex`. Upstream alone
therefore has not demonstrated a fix. No production runtime installer or system
package changes were made on the strength of this probe.

The unmodified source hit the 120-second timeout after 120.01 seconds. The
supervisor killed and reaped its process group. No XML result was produced.

## Immediate trigger and diagnostic result

`acl_latex.tex:15` imports `lipsum`. Its binding loads `xparse`, which loads the
installed `expl3` implementation. The source has no active `lipsum` calls. Its
three remaining mentions are comments in `sections/methodology.tex` and
`sections/limitations-ethics.tex`.

A separate diagnostic source copy omitted only this import. Pinned upstream
completed its XML conversion in 10.35 seconds, exited zero, and parsed 84
formulae. It still reported two errors because `upquote` is loaded after the
preamble. An exit status of zero does not mean a clean conversion. This test
establishes the immediate hang trigger; it is not a production repair and does
not validate rendered HTML or EPUB fidelity. The original source is unchanged.

`--preload` requests a module before conversion; the documented example
`--preload=LaTeX.pool` forces LaTeX mode. That option does not establish a way to
avoid the installed `expl3` implementation. No older TeX files were installed.

The same isolated no-`lipsum` diagnostic completed with installed Homebrew
LaTeXML 0.8.8_5 in 5.85 seconds, exited zero, parsed 84 formulae, and reported
`No obvious problems`. This single comparison gives no reason to ship the
upstream runtime. It also shows why removing an unused import and replacing the
converter must be tested separately. These timings are one run each, not a
performance benchmark. Homebrew's output is retained in
`.verification/upstream-latexml/run-homebrew-no-lipsum/paper.xml`.
