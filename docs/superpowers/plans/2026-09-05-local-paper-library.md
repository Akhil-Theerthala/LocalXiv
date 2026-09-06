# Local paper library implementation plan

> **For agentic workers:** Use subagent-driven-development for independent modules and review the integrated result. The user approved recommended decisions for this run.

**Goal:** Deliver a local macOS paper reader with source-to-EPUB conversion, compact citations, Kindle equation compatibility, grounded summaries and chat, and Kindle delivery.

**Architecture:** A loopback Python service owns SQLite jobs and a disk library. Conversion runs in an isolated subprocess. AI reads retained passages and cannot edit paper content. Existing native-host behavior remains available while the local app adds shared conversion operations.

**Tech stack:** Python standard library, SQLite FTS5, vanilla HTML/CSS/JavaScript, Pandoc, LaTeXML, bundled MathJax and a local image renderer, macOS Keychain and Mail.

## Global constraints

- Preserve existing uncommitted changes. Work on a new local branch; do not publish or send test email.
- Keep original source archives immutable and pin paper versions.
- Retain original content and reading order. Generated overviews are separate artifacts.
- Test failure and content contracts, not only successful subprocess exits.
- No plaintext key persistence. No AI credentials or network in conversion workers.
- No approval pauses for ordinary implementation or reversible verification.

## Task 1: Conversion and document representation

Files: `papers/acquire.py`, `papers/convert.py`, `papers/document.py`, `papers/worker.py`, `papers/math.js`, converter assets, `tests/test_papers.py`.

- [x] Write failing URL tests for versioned and legacy abstract, PDF, and HTML URLs, rejecting untrusted hosts and malformed identifiers.
- [x] Implement source acquisition with exact-version metadata, retained source and PDF, and bounded verified downloads.
- [x] Write citation fixtures exercising both bibliography formats, narrative citations, multi-citations, and locators. Example contract: rendered `Prior work [1, 2]` has two resolvable reference links and `Matlin [1] argues` retains its subject.
- [x] Implement source-to-structured-document conversion through LaTeXML and the existing engine, on fresh per-engine source copies. Build ordered reader XHTML and passages from EPUB spine order.
- [x] Implement Kindle equation rendering from preserved MathML with image dimensions and inline baselines. Retain semantic EPUB.
- [x] Validate worker isolation, packaged EPUB, links, and math assets. Compare representative versioned papers across engines and record actual outcomes.

Document interchange contract used by later tasks:

```python
	# document.json, beside paper.epub, semantic.epub, reader/, source, and original.pdf
	{
		"title": "Paper title", "authors": "Authors", "arxiv_id": "2505.07309v1",
		"source_digest": "sha256", "converter": "latexml",
		"chapters": [{"title": "Introduction", "path": "reader/ch01.xhtml"}],
		"passages": [{"id": "p00001", "section": "Introduction", "text": "...", "href": "reader/ch01.xhtml#p00001"}],
		"report": {"attempts": [], "checks": []}
	}
	# acquire(url, destination: Path) -> dict with arxiv_id, title, authors, source_digest
	# convert_paper(directory: Path, metadata: dict, progress: Callable[[str], None]) -> dict above
```

## Task 2: Library, jobs, and API generation

Files: `papers/library.py`, `papers/ai.py`, `papers/settings.py`, `tests/test_library.py`, `tests/test_ai.py`.

- [x] Write failing persistence tests for restarting jobs, duplicate reservation, artifact registration, FTS passage retrieval, and settings redaction.
- [x] Implement SQLite records and FTS5 passage storage, using independent connections and transactions.
- [x] Write provider tests against a local fake HTTP server for request shape, bounded responses, invalid keys, timeout, citation validation, and full-document summary coverage.
- [x] Implement Keychain-backed keys and a configurable OpenAI-compatible API client.
- [x] Implement section evidence notes, edited technical overview, saved provenance, grounded chat, and retrieval of adjacent passages. Never truncate full-paper summary input silently.

Public interfaces:

```python
	Library(root: Path)
	Library.list_papers() -> list[dict]
	Library.get_paper(paper_id: str) -> dict | None
	Library.save_paper(paper_id: str, document: dict, directory: str) -> dict
	Library.create_job(kind: str, payload: dict) -> dict  # id, kind, payload, state, progress, result, error
	Library.update_job(job_id: str, **fields) -> dict
	Library.get_job(job_id: str) -> dict | None
	Library.list_jobs() -> list[dict]
	Library.passages(paper_id: str, query: str = "") -> list[dict]
	Library.get_settings() -> dict
	Library.save_settings(values: dict) -> dict
	Library.save_generation(paper_id: str, kind: str, value: dict) -> dict
	Library.get_generation(paper_id: str, kind: str) -> dict | None
	Library.add_message(paper_id: str, role: str, content: str, sources: list) -> dict
	Library.messages(paper_id: str) -> list[dict]
	Provider(settings: dict, key: str)
	generate_overview(provider, document: dict, progress: Callable[[str], None]) -> dict
	answer_question(provider, question: str, passages: list[dict], history: list[dict]) -> dict
	get_key(endpoint: str) -> str
	set_key(endpoint: str, key: str) -> None
```

## Task 3: Local application and packaging

Files: `app/server.py`, `app/static/`, `launch.command`, `install-app.sh`, `tests/test_app.py`.

- [x] Write HTTP boundary tests for session, Origin, Host, traversal, malformed JSON, and job lifecycle.
- [x] Implement loopback service and a single job worker. Route import, summary, chat, export, and send as independent operations.
- [x] Build the journal-style library, first-use settings, Overview/Paper/Chat views, accessible progress and errors, retry/cancel actions, and downloadable artifacts.
- [x] Package a macOS launcher that locates Python, starts or reuses the local app, and opens its authenticated page. Install application files separately from library data.
- [x] Add generated-summary EPUB and optional combined export using existing anthology validation.
- [x] Inspect actual browser rendering at narrow and desktop widths, test keyboard interaction, and exercise the live local service.

## Task 4: Integration and evidence

- [x] Run Python, Node, shell, EPUBCheck, and rendered artifact checks appropriate to the changes.
- [x] Review new code for source fidelity, job isolation, key handling, and UI correctness. Resolve actionable findings.
- [x] Record exact tested papers, versions, conversion engines, failures, and rendered evidence in `docs/verification/local-paper-library.md`.
- [x] Update README with setup, launch, dependencies, provider configuration, artifacts, and honest limitations.
- [x] Audit every approved design requirement. Live provider and physical Kindle checks remain explicitly unverified until real credentials and device evidence are available.

## Execution log

- Design approved. Initial checkout contains four pre-existing modified files. No application code existed at start.

- Implementation and local verification completed on 2026-09-06. See `docs/verification/local-paper-library.md` for exact tested versions, runtime versions, installed workflow and limits.
- Pandoc remains first after corpus measurements; LaTeXML independently handles three fallback cases. Browser-native MathML serves the reader; bundled MathJax draws Kindle equation images.
- The application and existing native extension helper were installed locally. Ji and the critical review are ready in the installed library after real arXiv/alphaXiv imports.
- Live-provider factual quality and physical Kindle delivery/rendering are explicitly unverified, as required by the acceptance boundary. No real provider or Mail call was used for tests.

- Final build: 16 pinned papers, 32 EPUBCheck-passing EPUBs, one converter revision. Final suite: 189 Python tests passed, one optional Keychain test skipped, and 64 JavaScript tests passed. All 108 historical text-audit candidates were resolved against the final artifact hashes. Rendered checks confirmed recovered table symbols, algorithm structure, equation images, and readable reference links.
