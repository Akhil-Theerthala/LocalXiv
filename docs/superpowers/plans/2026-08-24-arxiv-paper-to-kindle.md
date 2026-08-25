# arXiv Paper to Kindle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a macOS Chrome extension that turns the active arXiv paper's source into a validated EPUB and sends it to a saved Kindle address.

**Architecture:** A Manifest V3 popup passes the active arXiv URL and saved Kindle address to a Python native-messaging host. The host securely downloads and extracts source, delegates LaTeX conversion to Pandoc, validates the EPUB, saves it to Downloads, and sends it through the configured macOS Mail account.

**Tech Stack:** Chrome Extension Manifest V3, browser JavaScript, Python 3 standard library, Pandoc CLI, macOS `osascript`/Mail.

## Global Constraints

- macOS and Google Chrome only for version 1.
- No hosted service, daemon, custom TeX parser, SMTP password, or non-Pandoc Python dependency.
- Preserve source order, section hierarchy, text, citations, figures, tables, and local cross-reference links; fail on detected omissions or broken links.
- Keep downloaded/extracted source temporary; retain the final EPUB under `~/Downloads/Arxiv to Kindle/`.
- Generate a text-only SVG cover containing title, authors, and arXiv ID.
- Never print non-protocol data to stdout from the native host.

---

## File map

- `native/host.py`: validation, secure extraction, root selection, metadata/cover generation, Pandoc invocation, EPUB validation, Mail delivery, native-messaging framing.
- `tests/test_host.py`: standard-library unit and fixture integration tests for every non-trivial host behavior.
- `extension/manifest.json`: permissions and popup registration.
- `extension/popup.html`: accessible first-use/send UI.
- `extension/popup.js`: active-tab lookup, local address persistence, and one native-host request.
- `extension/popup.css`: compact popup presentation.
- `install.sh`: user-scoped native-host registration.
- `README.md`: installation, Amazon approved-sender prerequisite, use, fidelity boundary, and recovery path.

### Task 1: Source boundary and archive safety

**Files:**
- Create: `tests/test_host.py`
- Create: `native/host.py`

**Interfaces:**
- Produces: `parse_arxiv_url(url: str) -> str`, `safe_extract(archive: Path, destination: Path) -> None`, `find_root_tex(source_dir: Path) -> Path`.
- Consumes: Python standard library only.

- [ ] **Step 1: Write failing tests**

Add literal cases for modern/versioned/legacy arXiv URLs and rejection of PDF, non-arXiv, query-confused, and traversal-like URLs. Build tar fixtures in a temporary directory and assert traversal/symlink/expanded-size violations raise `ConversionError`. Write two TeX roots and assert the root including the child wins; assert an unresolved tie fails.

```python
def test_parse_arxiv_url_accepts_modern_and_legacy(self):
    self.assertEqual(parse_arxiv_url("https://arxiv.org/abs/2401.01234v2"), "2401.01234v2")
    self.assertEqual(parse_arxiv_url("https://arxiv.org/abs/hep-th/9901001"), "hep-th/9901001")

def test_tar_traversal_is_rejected(self):
    archive = self.make_tar({"../escape.tex": b"bad"})
    with self.assertRaises(ConversionError):
        safe_extract(archive, self.root / "out")
```

- [ ] **Step 2: Run tests and verify RED**

Run: `python3 -m unittest -v tests.test_host`

Expected: import failure because `native.host` does not exist.

- [ ] **Step 3: Implement the minimum boundary**

Use `urllib.parse.urlsplit`, full-match ID regexes, `tarfile`, resolved-path containment, member/file-count and expanded-byte ceilings, and explicit rejection of links/devices. Root candidates must contain both `\\documentclass` and `\\begin{document}`; score included children below includers and reject equal top scores.

- [ ] **Step 4: Run tests and verify GREEN**

Run: `python3 -m unittest -v tests.test_host`

Expected: all Task 1 tests pass.

### Task 2: Deterministic EPUB conversion and validation

**Files:**
- Modify: `tests/test_host.py`
- Modify: `native/host.py`

**Interfaces:**
- Produces: `extract_metadata(tex: str, arxiv_id: str) -> PaperMetadata`, `write_cover(metadata: PaperMetadata, path: Path) -> None`, `convert_source(source_dir: Path, arxiv_id: str, output: Path, pandoc: str | None = None) -> PaperMetadata`, `validate_epub(path: Path) -> None`.
- Consumes: Task 1 root selection and Pandoc executable.

- [ ] **Step 1: Write failing metadata, cover, and EPUB tests**

Assert nested-brace title/author extraction, TeX command cleanup, XML escaping in the SVG, EPUB `mimetype` placement/content, nonempty spine, and resolution of local `href`/`src` fragment targets. Include a broken-link EPUB fixture that must raise `ConversionError`.

```python
def test_cover_escapes_metadata(self):
    write_cover(PaperMetadata("A & B", "X < Y", "2401.01234"), self.root / "cover.svg")
    cover = (self.root / "cover.svg").read_text()
    self.assertIn("A &amp; B", cover)
    self.assertIn("X &lt; Y", cover)

def test_validate_epub_rejects_missing_fragment(self):
    epub = self.make_epub(href="chapter.xhtml#missing", chapter_id="present")
    with self.assertRaises(ConversionError):
        validate_epub(epub)
```

- [ ] **Step 2: Run the new tests and verify RED**

Run: `python3 -m unittest -v tests.test_host`

Expected: import failure for the new conversion functions.

- [ ] **Step 3: Implement cover, Pandoc command, and validator**

Generate SVG with `html.escape`. Invoke Pandoc from the source root with `--from=latex`, `--to=epub3`, `--standalone`, `--toc`, `--mathml`, `--number-sections`, `--resource-path`, `--epub-cover-image`, and `--metadata=identifier:arXiv:<id>`. Add every `.bib` via `--bibliography` plus `--citeproc`; retry once without bibliography/citeproc on failure. Parse `META-INF/container.xml` and the OPF spine, then parse every packaged XHTML/SVG document and resolve all nonexternal local links and fragments.

- [ ] **Step 4: Run tests and fixture conversion**

Run: `python3 -m unittest -v tests.test_host`

Expected: all tests pass; skip the Pandoc integration test only when Pandoc is not installed.

### Task 3: Download, durable output, protocol, and Mail handoff

**Files:**
- Modify: `tests/test_host.py`
- Modify: `native/host.py`

**Interfaces:**
- Produces: `process_request(message: dict) -> dict`, `read_message(stream) -> dict | None`, `write_message(stream, value: dict) -> None`, `send_with_mail(epub: Path, recipient: str, title: str) -> None`, `main() -> int`.
- Consumes: Task 1 URL/source functions and Task 2 conversion/validation functions.

- [ ] **Step 1: Write failing protocol and request-validation tests**

Round-trip Unicode JSON through length-prefixed `BytesIO`; reject payloads above 4 MiB, invalid messages, and non-Kindle-shaped email addresses before any network call. Test download/extract/convert orchestration with a local `file:` fixture archive and `send=False`, asserting the final EPUB survives outside the temporary directory.

```python
def test_native_message_round_trip(self):
    stream = io.BytesIO()
    write_message(stream, {"title": "λ paper"})
    stream.seek(0)
    self.assertEqual(read_message(stream), {"title": "λ paper"})
```

- [ ] **Step 2: Run tests and verify RED**

Run: `python3 -m unittest -v tests.test_host`

Expected: import failure for protocol/request functions.

- [ ] **Step 3: Implement orchestration and Mail send**

Download with `urllib.request` using a descriptive user agent and compressed-size ceiling. Use `TemporaryDirectory`, copy the validated EPUB atomically into the Downloads folder, and pass recipient/subject/path as `argv` to a constant AppleScript program so paper metadata cannot become AppleScript source. Return `{ok, message, epub_path}`; catch `ConversionError` at the protocol boundary.

- [ ] **Step 4: Run all Python tests**

Run: `python3 -m unittest -v`

Expected: all tests pass.

### Task 4: Thin Chrome UI and user-scoped installer

**Files:**
- Create: `extension/manifest.json`
- Create: `extension/popup.html`
- Create: `extension/popup.js`
- Create: `extension/popup.css`
- Create: `install.sh`

**Interfaces:**
- Chrome request: `{url: string, kindle_email: string, send: true}` to native host `com.arxiv_to_kindle.host`.
- Native response: `{ok: boolean, message: string, epub_path?: string}`.

- [ ] **Step 1: Create the minimal Manifest V3 popup**

Declare only `activeTab`, `storage`, and `nativeMessaging`. The popup loads the saved address, retrieves the active tab, disables Send off an arXiv `/abs/` URL, saves edited addresses locally, prevents duplicate clicks, and displays the native response. Keep all executable JavaScript in `popup.js` for extension CSP compliance.

- [ ] **Step 2: Create and exercise the installer**

`install.sh <extension-id>` validates a 32-character `[a-p]` ID, checks Python 3 and a Pandoc executable in PATH/Homebrew locations, copies `native/host.py` to `~/Library/Application Support/ArxivToKindle/`, marks it executable, and writes `~/Library/Application Support/Google/Chrome/NativeMessagingHosts/com.arxiv_to_kindle.host.json` with one exact `allowed_origins` entry.

Run: `bash -n install.sh && ./install.sh invalid-id`

Expected: shell syntax passes; invalid ID exits nonzero without installing.

### Task 5: End-to-end documentation and verification

**Files:**
- Create: `README.md`
- Modify: `tests/test_host.py` only if live behavior reveals a reproducible bug, with a failing regression test first.

**Interfaces:**
- Documents the actual files and commands produced by Tasks 1–4.

- [ ] **Step 1: Write installation and use instructions**

Document Pandoc installation, Chrome unpacked-extension loading, ID-based host registration, adding the Mail sender to Amazon's approved list, saving the Kindle address, and clicking Send. Explain that the EPUB is retained for manual upload at `https://www.amazon.com/sendtokindle` if Mail/Amazon delivery fails.

- [ ] **Step 2: Run static and unit verification**

Run: `python3 -m py_compile native/host.py tests/test_host.py && python3 -m unittest -v && bash -n install.sh && python3 -m json.tool extension/manifest.json`

Expected: zero exit status for every command.

- [ ] **Step 3: Run a bounded live conversion**

Run: `python3 native/host.py --convert-only https://arxiv.org/abs/<small-public-test-id>`

Expected: a validated EPUB path in Downloads; inspect its OPF/navigation/content ordering and confirm there are no unresolved local links. Do not invoke Mail during this check.

- [ ] **Step 4: Final workspace audit**

Run: `rg --files | sort` and `rg -n 'TBD|TODO|FIXME|PLACEHOLDER|password|secret' .`

Expected: only the planned files are present; no placeholders or credentials exist.
