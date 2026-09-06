# Local paper library and reliable EPUB conversion

Status: Approved on 2026-09-05. The user authorized the recommended implementation decisions without intermediate approval requests.

This design covers a local macOS application for importing arXiv and alphaXiv paper links, reading papers, generating technical summaries, asking questions, and sending selected artifacts to Kindle. Conversion reliability is the first implementation milestone.

## Usage

Launch Papers to Kindle from macOS. On first launch, choose an API provider, model, and API key. Save the key in macOS Keychain. Offer a clear option to skip AI setup and use conversion alone. Configure the Kindle address once under delivery settings.

Paste a paper link. The app resolves its exact arXiv version, downloads its source, and shows import progress. After conversion, the paper opens with three views: Overview, Paper, and Chat. Overview contains a technical blog-style summary generated from the full available paper. Paper contains the original content and section navigation. Chat answers questions with links to supporting passages.

Offer separate actions to send the paper, the overview, or both. A saved automatic-send preference can send the paper after conversion passes validation. Summary failure must not prevent reading or sending a valid paper. The app must distinguish an EPUB saved locally, a message handed to Mail, and delivery confirmed by the user. Mail success alone cannot establish arrival on Kindle.

## Current behavior and evidence

The inspected checkout is on `main` at `d4cf564`. Existing uncommitted edits in `README.md`, `install.sh`, `native/host.py`, and `tests/test_host.py` predate this work and remain untouched.

- `native/host.py:55`, `parse_arxiv_url`, currently accepts trusted HTTPS abstract-page URLs. AlphaXiv supplies the identifier; arXiv supplies the source.
- `native/host.py:3265`, `convert_source`, applies source normalizers and invokes Pandoc with `--from=latex`, `--to=epub3`, and `--mathml`. There is no independent converter fallback.
- `native/host.py:3123`, `prepare_inline_equations`, promotes a subset of colon-introduced inline equations to display math. This is not a general inline-math rendering solution.
- `native/host.py:2897`, `prepare_compiled_bibliography`, retains author-date labels from compiled bibliographies. `native/host.py:904`, `_finalize_epub`, inserts those labels into citation links.
- The BibTeX path enables `--citeproc` without choosing a numeric CSL style. A temporary fixture reproduced `(Matlin and Buho 2025)` with the installed Pandoc. A compiled-bibliography fixture retained `Matlin et al.(2025)` as its label.
- The earlier citation design explicitly preserved compiled labels to repair empty citations. Numeric citations change that presentation requirement, while retaining complete bibliography entries and working links.
- `native/host.py:3526`, `process_request`, couples acquisition, conversion, persistence, and optional Mail delivery. Source files disappear with its temporary directory. Chat requires retained document content and stable passage identifiers.

Pandoc is installed. LaTeXML and Docker were not found on the current executable search path. No claim about LaTeXML conversion success or actual Kindle rendering has been verified in this investigation.

## Product boundary

Support arXiv identifiers reached through valid arXiv and alphaXiv paper links, including abstract, PDF, HTML, versioned, and legacy identifier forms where the host supports them. Normalize query parameters without trusting arbitrary domains or redirect destinations. Pin an unversioned request to a specific version before storing any generated artifact.

Do not promise faithful EPUB conversion for every paper. Some submissions have no TeX source. Some source archives depend on unsupported packages or incomplete assets. arXiv itself documents that not every paper can be converted to HTML.

A supported link must produce an import result, including an actionable unsupported-source result when necessary. It must never produce a success message for known missing content. An original PDF remains available as a separately labeled fallback. PDF extraction is not silently substituted for source conversion.

Preserve wording, section and appendix order, figures, captions, tables, equations, footnotes, references, and cross-references. Preserve semantic structure rather than printed page geometry. Generated explanation is a separate artifact and cannot overwrite original paper content.

## Architecture choice

| Design | Ownership and trade-off | Decision |
| --- | --- | --- |
| Extend the Chrome popup | Chrome owns interaction and job visibility. Reuses all current UI, but a popup is awkward for sustained reading and chat. | Keep as an optional import entry point. |
| Local web app with a macOS launcher | One local Python service owns the library and jobs. The browser owns presentation. Reuses conversion and Mail code with no hosted application account. | Recommended. |
| Native Swift application | Swift owns the UI and application lifecycle, with a separate conversion worker. Requires another application stack before conversion quality improves. | Defer until native integration justifies the maintenance cost. |

The local app uses the existing journal palette. Its main layout has a library sidebar, a readable document column, and an optional chat pane. First-use setup and dependency errors live in the app, rather than requiring users to inspect Chrome native-messaging configuration.

Use Python, SQLite, and ordinary HTML, CSS, and JavaScript initially. A launcher starts the service on loopback and opens the local page. SQLite holds records and job states. Per-paper directories hold immutable source archives, normalized documents, PDFs, EPUBs, and generation records. Avoid a vector database for a personal collection until measured retrieval failures justify one.

## Core data and ownership

Use ordered XHTML documents and their asset manifest as the canonical reading artifact. Do not invent a second document language that has to model every possible scientific table. A derived passage index supports AI retrieval without becoming the source of truth.

| Record | Important fields | Owner |
| --- | --- | --- |
| PaperVersion | arXiv identifier, resolved version, title, authors, original URL, source digest | Acquisition |
| PaperDocument | paper version, ordered XHTML paths, asset manifest, reference map, passage index, converter version | Conversion |
| Passage | stable identifier, section path, document anchor, text, linked equation and figure identifiers | Document indexing |
| ConversionReport | converter attempts, diagnostics, missing-content findings, checks completed | Conversion validation |
| Artifact | identifier, paper version, kind, path, content digest, validation state | Library |
| Generation | paper version, source digest, model, prompt revision, passages used, text, usage when reported | AI generation |
| Job | identifier, operation, paper version, state, progress, result identifier, error | Job worker |
| DeliveryAttempt | artifact identifier, recipient, requested time, Mail outcome | Delivery |
| ProviderSettings | provider, endpoint, model, Keychain reference | Settings |

Conversion job states are queued, downloading, converting, validating, ready, failed, interrupted, or cancelled. Generation and delivery have separate jobs. A failed summary cannot change a ready paper into a failed conversion.

One worker processes conversion jobs initially. Each job gets an isolated working directory. SQLite transactions reserve work and publish results. Artifacts move into the library atomically only after checks finish. Duplicate imports of the same pinned version reuse artifacts only when the source digest and conversion settings match. A restart marks unfinished jobs interrupted and permits an explicit retry.

Do not automatically retry ambiguous Mail submissions. A retry after a connection failure can send the same book twice.

## Interfaces and module map

The application calls these proposed contracts:

```text
	import_paper(url) -> JobId
	get_job(job_id) -> JobStatus
	get_paper(paper_version) -> PaperView
	generate_overview(paper_version) -> JobId
	ask(paper_version, conversation_id, question) -> AnswerWithEvidence
	export_epub(artifact_id, reading_profile) -> JobId
	send_to_kindle(artifact_id) -> DeliveryAttemptId
```

Proposed Python module ownership:

- `papers/acquire.py` owns URL normalization, version resolution, downloads, and safe archive extraction.
- `papers/convert.py` owns converter selection and conversion attempts in separate source copies.
- `papers/document.py` owns ordered XHTML, citation normalization, passage indexing, and EPUB checks.
- `papers/library.py` owns SQLite and artifact persistence.
- `papers/ai.py` owns provider requests, evidence selection, summaries, and grounded answers.
- `papers/delivery.py` owns the existing Mail integration.
- `app/server.py` owns HTTP validation, session protection, and job dispatch. `app/static/` owns presentation.
- `native/host.py` becomes a compatibility adapter as callers migrate. Move existing code only when a new caller needs its boundary.

Dependencies point from the web and extension adapters to paper operations. Conversion has no knowledge of HTTP, API keys, or Mail. AI generation reads PaperDocument and cannot edit it. Delivery accepts an existing validated artifact and never triggers implicit reconversion.

## Conversion flow and bypassing Pandoc

1. Resolve the exact paper version and retain the original archive and PDF when available.
2. Extract a fresh working copy. Preserve the untouched archive for retry and diagnosis.
3. Use LaTeXML as the proposed primary source converter. It can emit structured HTML and EPUB directly, bypassing Pandoc's LaTeX reader. Preserve LaTeXML's ordered documents and links for shared postprocessing.
4. Keep the current Pandoc route as a compatibility fallback on a separate fresh source copy. Do not feed already modified sources from one engine into another.
5. Normalize citation presentation and prepare the reader and Kindle math profiles from the selected candidate.
6. Validate the document and EPUB, then publish the artifact and conversion report together.

Engine order remains subject to a measured comparison on the regression corpus before becoming the default. Compare preserved content and rendered output, not just converter exit codes. If both candidates have detected omissions, retain diagnostics and report failure.

An optional future route can consume arXiv's HTML for the exact same version. This is derived from TeX and avoids local package installation, but availability and conversion quality vary. It is not the default in this proposal because the requested workflow converts downloaded source locally.

LaTeXML is not a universal TeX implementation. A second engine reduces dependence on one parser; it does not justify suppressing unknown-command warnings or missing figures.

## Citations and equations

Both bibliography routes use compact linked numeric citations, such as `[12, 13]`. Preserve complete reference entries and their source order; assign numbers against that order. For BibTeX without a compiled ordering, use the selected numeric CSL ordering consistently. Never derive reference numbers from archive order or raw citation text.

Preserve narrative citation semantics: `Matlin et al. [12] show ...` must not become `[12] show ...`. Preserve citation prefixes, page locators, suffixes, and punctuation. Each key in a multi-citation must resolve independently. Citation transformations operate on parsed citation structure before author-date rendering loses those distinctions.

The browser reader uses semantic math with a bundled renderer. The Kindle export offers a compatibility profile with tightly cropped equation images, relative dimensions, and explicit baseline offsets for inline formulas. Keep source TeX and accessible descriptions in the document data. Display equations retain numbering and anchors. Never rasterize whole paragraphs merely to fix one formula.

Keep a semantic MathML EPUB profile too. Amazon documents MathML support, so the design must not assume that all MathML is unsupported. The reported issues require a rendered comparison on the target Kindle. Image equations trade selectable math and perfect font scaling for predictable drawing; high-resolution output alone does not prove readable inline layout.

Wide equations and tables need checks at larger font sizes. Never silently remove columns, change formulas, or shrink an entire table until it is unreadable. A candidate that cannot render acceptably must expose the affected location for review.

## Overview and chat

The default overview is a roughly 1,000 to 1,500 word technical explanation, adjusted when a paper warrants less. Open with the problem and concrete contribution. Explain the mechanism, the strongest experiments, the actual comparison, and the limits of what the results establish. Define necessary notation where it first appears. Use a worked example only when the paper supports it, or label an invented example explicitly.

Build the overview from section-level evidence notes covering the available full paper, then draft and edit for plain language. Keep an evidence record of numerical results, experimental settings, and section anchors. The final pass checks numbers and references against that record. A style pass applies the user's Technical Writing and Unslop rules without changing technical meaning. Prompts cannot guarantee factual correctness; evaluation must include human checks against the original paper.

A local skill installed in Codex is not automatically available to another provider's API. The application must carry its own versioned writing prompts and validators. Excalidraw diagrams are optional, separately labeled explanations. Add one when it clarifies the method, not as decoration or an unverified reproduction of a paper figure.

Chat retrieves relevant passages and neighboring context using the section index and SQLite full-text search. Include associated equations, captions, and table headers. A question about the whole paper uses broader section coverage. Detect context overflow and request bounded section analysis rather than silently truncating the paper. Display links to supporting passages, and say when the available material cannot answer the question. Validate that cited anchors exist; anchor validity alone does not prove that an answer is supported.

The first provider integration uses a documented OpenAI-compatible chat endpoint with configurable endpoint and model. Compatibility is explicitly tested per provider, rather than assumed for every API. Provider-specific integrations can implement the same small request contract later. Keys stay in Keychain and reach the provider only from the backend. Show that selected paper content is sent to the configured provider. Conversion and local reading remain available without a key.

Save the overview as a distinct generated artifact with paper version, generation date, model, and links to the original. Export it to its own EPUB, or combine it with the paper only when the user chooses that action. Cached overviews reopen without another API call.

## Runtime boundaries

The service binds to loopback only. Validate Host and Origin and require a session token for application API access. Serve sanitized paper content in an isolated reader frame. Downloaded HTML, generated text, TeX, and paper instructions are untrusted content, never application commands.

Conversion workers have no API keys, Mail access, or general home-directory access. Source processing needs an OS-enforced sandbox or restricted container with no network, bounded CPU time and memory, and an explicit output directory. A subprocess, temporary directory, or `--no-shell-escape` alone does not provide that boundary. Packaging this boundary is a first-milestone engineering check, not a claim that the existing host already enforces it.

Provider requests have timeouts and bounded output. Errors redact credentials. A failed request preserves existing artifacts. Display reported usage when available; do not invent a currency estimate for arbitrary endpoints.

## Implementation sequence and acceptance

1. **Prove conversion.** Capture versioned source fixtures for the previously troublesome papers, add numeric-citation checks, and compare LaTeXML with the current engine. Include narrative citations, locators, complex inline math, custom macros, figures, appendices, and both bibliography formats. Verify safe worker execution before processing arbitrary source with the new engine.
2. **Prove exported reading.** Inspect generated XHTML and packaged EPUBs. Run EPUBCheck and existing link and structure checks. Render representative paragraphs at narrow widths and multiple font sizes. Compare with the source PDF. A user-controlled Send-to-Kindle check on the target device is required before claiming the reported device problem is resolved.
3. **Build the local library.** Add persistence, import jobs, setup, reader, launcher, progress, and restart recovery. Reuse the validated conversion and Mail operations. Verify duplicate imports, cancellation, partial failure, and offline reopening.
4. **Add AI reading.** Implement Keychain-backed provider setup, section evidence notes, overview generation, chat, source links, caching, and separate overview export. Test with fixed provider responses and then a user-configured live provider. Record which checks used mocks and which used a real API.
5. **Package and retain extension access.** Verify installation and launch from a clean macOS user environment. Connect the extension to shared operations without changing its existing anthology ordering contract.

The known-paper corpus starts with `2505.07309`, `2504.18346`, `2410.20199`, `2510.13290`, and `2606.19868`. Resolve and record their actual versions during acquisition. Report downloaded, unavailable, attempted, passed, and failed papers separately. Historical success is not a fresh regression result.

Acceptance requires no detected omitted sections, captions, equations, bibliography entries, or broken local links on the tested corpus. Inventory checks detect many failures but do not prove semantic equivalence for arbitrary TeX. Report conversion coverage with its corpus and versions instead of claiming support for all papers.

## External evidence

- [arXiv HTML availability and conversion limitations](https://info.arxiv.org/about/accessible_HTML.html) explains missing HTML, extensible TeX, and expected reflow differences.
- [LaTeXML usage](https://math.nist.gov/~BMiller/LaTeXML/manual/usage/) documents source conversion, math postprocessing, and direct EPUB output.
- [Pandoc citation rendering](https://www.pandoc.org/demo/example2.html) documents the author-date default and explicit CSL selection.
- [Amazon reflowable text guidelines](https://kdp.amazon.com/en_US/help/topic/GH4DRT75GWWAGBTU) covers relative sizing and MathML. KDP guidance does not establish identical Send-to-Kindle behavior on the user's device.
