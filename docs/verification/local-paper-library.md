# Local paper library verification

Date: 2026-09-06. This report covers the local implementation and the exact artifacts in the linked corpus reports. It does not establish support for every TeX template, live-provider summary quality, or rendering on a physical Kindle.

The original browser launcher described in this report has since been replaced with a native macOS window. See [native window verification](native-window.md) for the implementation and checks.

## Delivered workflow

The macOS launcher opens a loopback web application. It accepts arXiv and alphaXiv links, pins an arXiv version, retains the downloaded TeX and original PDF, and builds a local reader plus two EPUB profiles. The Kindle profile draws inline and display equations as images; the semantic profile retains MathML. Citations use linked numbers while narrative references retain their author text.

The app stores papers, jobs, passages, overviews, and chat in a local library. First-use settings accept an OpenAI-compatible provider endpoint, model, and API key. Keys use macOS Keychain. A user can skip AI setup. Overview generation reads section evidence notes, drafts a technical explanation, then checks and edits the draft against those notes. Chat links answers to retained passages. The app and generated overview exports display compact citation numbers, keeping internal passage identifiers in saved provenance. Both operations keep model, source identity, citations, and reported usage. An existing overview opens without another generation request.

Paper, overview, and combined exports are separate choices. Each choice supports the selected reading profile. Sending uses macOS Mail and records the recipient, exact artifact hash, requested time, and handoff outcome. An uncertain Mail outcome does not trigger an automatic resend. A successful handoff is not confirmation of arrival on Kindle.

## Corpus and method

The [corpus manifest](corpus.json) records 16 pinned arXiv source/PDF pairs spanning 2015 through 2026. [Discovery notes](corpus-discovery.md) explain the title matches and source provenance. The supplied Ji, Joshi, and Hedström starting points are included. An exact arXiv match for Li, Kuang, and Botelho's AIED paper was not verified; its author PDF is retained separately and excluded from the source-conversion denominator.

The [conversion results](conversion-results.json) record engine, time, equation and passage counts, attempted fallbacks, and SHA-256 hashes for both EPUB profiles. `python3 -m tests.verify_corpus --force` rebuilds the retained sources. `--ids` selects exact versions. Each conversion runs in its own sandboxed process and every published profile passes local resource/link validation and EPUBCheck. The corpus runner independently runs EPUBCheck on the resulting files.

The [content audit](content-audit.md) compares source, retained PDF, reader, and semantic EPUB. It checks scientific structure, figures, captions, tables, equations, bibliography items, and sampled prose anchors. Counts are heuristics, and review flags require investigation. The audit has already exposed missing content in EPUBs that passed package validation; neither a successful converter exit nor EPUBCheck alone is a fidelity guarantee.

Pandoc remains first because it handles most of this corpus after the measured repairs. LaTeXML runs independently on a fresh source copy when the Pandoc candidate fails. The [LaTeXML investigation](latexml-runtime.md) records why an untested engine swap would not solve arbitrary template problems.

## Verified results

The latest retained artifacts pass conversion and EPUBCheck for all 16 papers, producing 32 validated EPUBs. Thirteen papers used Pandoc; three used LaTeXML after Pandoc failed. The builds contain 4,841 inline/display math instances in total; this count does not establish mathematical equivalence to the PDF. All 16 papers were rebuilt after the final content repairs using conversion revision `4885826715d23aea4e74a52a912611dfd25029a71d63007b6a74f66a6e30686e`. Each JSON record retains its build revision and artifact hashes; these are measured cases, not a universal success-rate estimate.

| First arXiv year | Paper | Pinned version | Engine | EPUB profiles |
| --- | --- | --- | --- | --- |
| 2025 | Calibrating Verbal Uncertainty as a Linear Feature to Reduce Hallucinations | [2503.14477v2](https://arxiv.org/abs/2503.14477v2) | pandoc | Both pass |
| 2025 | Calibration Across Layers: Understanding Calibration Evolution in LLMs | [2511.00280v1](https://arxiv.org/abs/2511.00280v1) | pandoc | Both pass |
| 2025 | To Steer or Not to Steer? Mechanistic Error Reduction with Abstention for Language Models | [2510.13290v1](https://arxiv.org/abs/2510.13290v1) | pandoc | Both pass |
| 2015 | Dropout as a Bayesian Approximation: Representing Model Uncertainty in Deep Learning | [1506.02142v6](https://arxiv.org/abs/1506.02142v6) | pandoc | Both pass |
| 2016 | Simple and Scalable Predictive Uncertainty Estimation using Deep Ensembles | [1612.01474v3](https://arxiv.org/abs/1612.01474v3) | latexml | Both pass |
| 2017 | On Calibration of Modern Neural Networks | [1706.04599v2](https://arxiv.org/abs/1706.04599v2) | latexml | Both pass |
| 2021 | A Gentle Introduction to Conformal Prediction and Distribution-Free Uncertainty Quantification | [2107.07511v6](https://arxiv.org/abs/2107.07511v6) | pandoc | Both pass |
| 2022 | Teaching Models to Express Their Uncertainty in Words | [2205.14334v2](https://arxiv.org/abs/2205.14334v2) | pandoc | Both pass |
| 2022 | Language Models (Mostly) Know What They Know | [2207.05221v4](https://arxiv.org/abs/2207.05221v4) | pandoc | Both pass |
| 2023 | Semantic Uncertainty: Linguistic Invariances for Uncertainty Estimation in Natural Language Generation | [2302.09664v3](https://arxiv.org/abs/2302.09664v3) | pandoc | Both pass |
| 2024 | Semantic Entropy Probes: Robust and Cheap Hallucination Detection in LLMs | [2406.15927v1](https://arxiv.org/abs/2406.15927v1) | pandoc | Both pass |
| 2026 | Uncertainty quantification for expectation-calibrated predictions | [2608.26703v1](https://arxiv.org/abs/2608.26703v1) | latexml | Both pass |
| 2025 | Uncertainty Profiles for LLMs: Uncertainty Source Decomposition and Adaptive Model-Metric Selection | [2505.07309v1](https://arxiv.org/abs/2505.07309v1) | pandoc | Both pass |
| 2025 | Comparing Uncertainty Measurement and Mitigation Methods for Large Language Models: A Systematic Review | [2504.18346v4](https://arxiv.org/abs/2504.18346v4) | pandoc | Both pass |
| 2024 | Rethinking the Uncertainty: A Critical Review and Analysis in the Era of Large Language Models | [2410.20199v1](https://arxiv.org/abs/2410.20199v1) | pandoc | Both pass |
| 2026 | A Systematic Evaluation of Black-Box Uncertainty Estimation Methods for Large Language Models | [2606.19868v1](https://arxiv.org/abs/2606.19868v1) | pandoc | Both pass |

The final Python suite ran 190 tests: 189 passed and one optional Keychain smoke test was skipped. The opt-in fake-credential Keychain roundtrip had passed separately earlier in this session. All 64 JavaScript tests passed. Shell syntax, Python compilation, and `git diff --check` passed.

Runtime versions were Python 3.14.7, Pandoc 3.11, LaTeXML 0.8.8, librsvg 2.62.3, Ghostscript 10.07.1, Node 22.19.0, and EPUBCheck 5.3.0. MathJax is pinned by the package lock.

The 2026 expectation-calibrated paper contains 1,252 converted equations. Its LaTeXML stage exceeded a 90-second limit under concurrent verification load. A bounded 180-second stage passed; the final full conversion took 149.2 seconds; the parent still enforces its overall runtime, CPU, and memory limits.

Repairs confirmed by the corpus include inline math compatibility, numeric citation links, custom table grids and captions, graphic search paths, print-layout boxes, source root selection, preamble abstracts, table footnotes and return links, author notes, complete bibliography titles and venues, bold paragraph labels, boxed prompt examples, and algorithm captions, conditions, comments, and return statements. A rendered table check also recovered five missing checkmarks and removed leaked print-rule ranges; a regression checks their exact cells. Raw equation keys become readable live links without inventing source equation numbers. The final audit finds 9,426 of 9,494 exact source/PDF text anchors in the reader. All 108 historical review candidates were adjudicated against the final artifacts; the 68 remaining exact-match differences are explained by formatting or retained metadata. No unresolved candidate remains within that review. All 71 checked bibliography fragments are retained. These checks do not establish exhaustive equation or table-cell equivalence.

AlphaXiv overview routes were verified against a live [overview page for the critical review](https://www.alphaxiv.org/overview/2410.20199v1). Both the app and extension now normalize those links to their arXiv identifier.

## Application checks

- Python tests exercise URL trust, version handling, archive safety, real conversion, compact citations, equation images, links, source preservation, jobs, cancellation, duplicate imports, cache invalidation, HTTP session/Origin/Host checks, file traversal, Keychain interfaces, provider failures, and evidence references.
- API tests use a local fake provider or mocked responses. They check bounded requests, context overflow, unfinished output, unknown citations, provenance, and redaction. Real Pandoc/MathJax/librsvg/EPUBCheck runs validate overview and combined exports. Mail is mocked; no verification email was sent.
- JavaScript tests cover the extension lifecycle, local import handoff, safe prose rendering, evidence navigation, selected export/send profiles, and reported usage. Shell syntax, Python compilation, and whitespace checks cover the shipped entry points.
- A temporary installation and reinstallation tested paths containing spaces and library preservation. The actual application was installed under `~/Applications/Papers to Kindle.app`, with runtime and library in separate directories under `~/Library/Application Support/PapersToKindle`.
- The installed loopback service reported all required tools available. Importing Ji's `2503.14477v2` through its alphaXiv URL reached `Imported` and left the paper in the installed library. Reimporting Ji through arXiv refreshed the same paper-version record. The installed artifact retains the abstract, affiliations, contribution statement, and AUROC caveat. Importing the critical review through its alphaXiv overview URL also reached `Imported`, leaving two readable papers in the installed library. Both papers were refreshed through the final installed service and reached `ready` again. The runtime files match the checkout. No model or provider key was configured, and automatic email was disabled.
- In the test library, importing Joshi's exact paper through alphaXiv and arXiv reached the same paper-version record. Chromium displayed the original reader, chapter navigation, semantic math, images, and compact references.

## Rendered checks and limits

The app was inspected at desktop and narrow widths. A fresh Joshi Kindle EPUB was extracted for a Chromium preview. Inline formulas stayed beside their text, display equations were visible, and a numeric citation opened the correct bibliography target. The final equation images use opaque white backgrounds and the compatibility profile requests a light page canvas. This fixed the observed black-on-dark browser preview. The browser reader uses native MathML; bundled MathJax draws the exported equation images. A final Chromium inspection of the rebuilt Semantic Uncertainty EPUB confirmed all five comparison-table checkmarks in their correct columns, the restored nested algorithm, readable equation links, and visible inline/display equations.

The Codex in-app browser blocked standalone XHTML in this session; Chromium displayed the same local files. The application keeps its paper-content sandbox and does not weaken it to accommodate that preview limitation.

Remaining external checks are explicit:

- Enter a provider key and assess a real overview and chat answers against the paper. The tests do not establish factual quality, model availability, or universal provider compatibility.
- Send a chosen EPUB through the user's configured Mail account and inspect it on the actual Kindle. Confirm arrival, inline baseline behavior, large-font equations, wide tables, and the device's theme behavior.
- A clean macOS account may show first-use Keychain or Mail permission prompts that the current installation checks do not reproduce.

Source archives, PDFs, diagnostic logs, and artifact hashes remain available for reproducing a reported failure. Unsupported or detected incomplete conversions expose the original PDF and diagnostics instead of a ready EPUB.
