# LocalXiv bundle size audit

Implementation follow-up: [final reduced build and repository review](lean-release-2026-09-09.md).

Audited 2026-09-09. Checkout and installed `/Applications/LocalXiv.app` both identify commit `d05af4c47972292d693a552ae3bf853d47770e5f`, v0.0.3 build 7. The checkout was clean before this report. This audit changes no application or packaging code.

## Measured contents

Sizes below are MiB of regular-file contents, excluding symlinks, measured recursively with `stat().st_size`. Allocated disk usage differs because of filesystem blocks. The complete app contains 1,093.5 MiB; `du` reports approximately 1.1 GiB. Existing DMGs under `dist` range from 516.2 to 549.1 MiB, but those identify older versions. No matching v0.0.3 DMG was found there, and no new DMG was built.

| Component | MiB | Why it is present |
| --- | ---: | --- |
| OpenJDK | 380.3 | Runs EPUBCheck after exports |
| Pandoc | 265.0 | Source conversion, citation processing, overview Markdown conversion |
| Ghostscript | 127.1 | Rasterizes PDF, EPS and PS graphics |
| Shared native libraries | 121.3 | Includes 53.5 MiB of Node libraries and about 36 MiB ICU, plus image, TLS and other dependencies |
| Python installation | 73.3 | Local service and conversion workers |
| JavaScript packages | 61.5 | MathJax, XML parsing, overview diagrams and transitive dependencies |
| EPUBCheck | 34.6 | Validates exported EPUBs |
| librsvg | 12.2 | Equation, cover and figure rasterization |
| LaTeXML | 10.6 | Alternative TeX conversion engine |

The remaining files include signatures, notices, certificates, assets and app code. The native launcher occupies about 160 KiB on disk. The `app`, `papers` and `native` directories together contain about 0.83 MiB of regular files. The UI uses system WKWebView, not a bundled browser. Node's tiny launcher is misleading in isolation: its implementation lives in the shared library directory.

## Root cause

`app/macos/bundle_runtime.py:72-79` copies entire Homebrew formula installations. It then discovers native dependencies from every copied Mach-O file, including tools the app never calls. This ships development materials and can expand the dependency set unnecessarily.

`app/macos/build-release.py:97-99` copies all of `node_modules`. Production npm dependencies include optional product capabilities, source trees and alternate browser bundles. `npm ci --omit=dev` alone does not remove these.

## Reductions, in recommended order

### 1. Replace the full JDK with a runtime built for EPUBCheck

Measured experiment: `jlink` produced a 46.8 MiB runtime, compared with 380.3 MiB for the shipped OpenJDK tree. Gross reduction: **333.5 MiB**. Packaging will still need any native libraries required by that runtime.

The current JDK includes an approximately 82 MiB `jmods` directory, 52 MiB `lib/src.zip`, demos, developer commands and modules beyond those needed by EPUBCheck. Prefer a generated runtime to a long manual deletion list.

The experiment used the locally installed Homebrew JDK:

```sh
jlink --add-modules java.base,java.compiler,java.desktop,java.security.jgss,java.sql,jdk.unsupported,jdk.xml.dom \
  --strip-debug --no-header-files --no-man-pages --compress=zip-6 \
  --output /private/tmp/localxiv-audit-jre-20260909
```

Module selection came from `jdeps --ignore-missing-deps --multi-release base --print-module-deps`, with EPUBCheck's dependency jars on the classpath. It emitted split-package warnings. This is a tested starting point, not proof that reflective loading and every document type are covered.

With reads from `/opt/homebrew` and `/usr/local` denied, the reduced runtime ran the installed EPUBCheck jar successfully:

- A Pandoc-generated EPUB with math passed with no warnings or errors, exit 0.
- A copy with an invalid mimetype failed with `PKG-007`, exit 1.

Logs are in `/private/tmp/localxiv-audit-jre-20260909-tests`. The sandbox test required execution outside Codex's nested sandbox, which initially refused `sandbox_apply`.

Keep EPUBCheck. `papers/document.py:340-350` requires it, and deleting it would remove a real export validation step. Before shipping, relocate and sign the reduced runtime, then check both EPUB profiles, image validation, overview exports and the conversion corpus under the application sandbox.

### 2. Package the Ghostscript executable the app uses

The app calls `gs`. The vendor tree also includes PCL/XPS executables and `libgpcl6`, `libgpdl`, `libgxps`, `libgs`, plus their small launcher programs. All regular files in Ghostscript's `lib` and all `bin` files except `gs` total **80.2 MiB**.

`otool -L` shows that the shipped `gs` does not link to those four Ghostscript libraries. It does link to image libraries, Tesseract and Leptonica, so these cannot simply be deleted even though LocalXiv does not expose OCR.

Use `gs`, its required resources/fonts and its actual native dependency closure as the packaging roots. The 80.2 MiB is a candidate reduction based on file and link inspection; a trimmed Ghostscript package was not run. Validate PDF/EPS/PS figures, font handling and both conversion engines before accepting it. Keep notices and required resources.

### 3. Omit Python's test suite

The shipped `lib/python3.14/test` contains **32.3 MiB**. LocalXiv does not need CPython's own test suite in its installed app. Other development files, IDLE and ensurepip are smaller secondary candidates.

Keep Python's standard library and extension modules needed for SSL, SQLite, compression, ctypes and subprocesses. Do not replace bundled Python with an assumed system interpreter. Verify startup, import and both conversion engines after pruning.

### 4. Ship only the MathJax distributions used by the app

MathJax contains **32.7 MiB** of regular files. LocalXiv uses server-side `js/` modules in `papers/math.js` and `papers/tex_math.js`; the UI serves `es5/tex-svg.js` from `app/server.py:462-463`.

The TypeScript source, build components and other `es5` contents total **25.4 MiB**. Keep `js/`, the browser `tex-svg.js` bundle and any resources it actually loads, package metadata and licenses. Verify browser math and server rendering before adopting the selection. Do not infer that all MathJax dependencies are unused from a single equation test.

### 5. Exclude Excalidrawer's unused MCP and PNG dependency branches

`papers/overview_render.mjs` requests SVG only. The installed Excalidrawer package also declares an MCP server and PNG renderer, bringing in the MCP SDK, Zod, Hono, validation packages, resvg and font conversion dependencies.

A temporary package containing only Excalidrawer, with none of its declared dependencies, successfully ran LocalXiv's actual `overview_render.mjs`. It generated a ten-element SVG with zero renderer warnings. Source inspection found the MCP imports in `src/mcp.mjs` and the dynamic resvg import in the PNG path. The embedded SVG font remains necessary.

Comparing the lockfile package graph against MathJax/XML dependencies plus Excalidrawer identifies **95 installed package directories totaling 20.7 MiB** as candidates for omission. This includes Zod at 5.5 MiB, the MCP SDK at 4.1 MiB and native resvg at 3.4 MiB. This graph estimate assumes the current flat installation and does not replace full rendering checks.

Prefer selecting runtime files at packaging time while retaining the reproducible development install. Exercise all diagram layouts, long labels and non-ASCII text before shipping.

## Combined size target

The five candidates total approximately **492 MiB**, giving a provisional app-content size around **601 MiB**. A practical first target is **600–650 MiB**, roughly 40–45% below the measured file contents. This is an estimate, not a rebuilt release result. The Java and SVG experiments establish useful feasibility; they do not establish full feature equivalence.

Compressed DMG savings cannot be inferred by subtracting these numbers. Source archives, text and executable code compress differently. Build and measure the resulting DMG after changes.

Pandoc remains the largest unresolved item after Java is reduced. Its executable alone is 263.4 MiB. Running `strip -S` on a temporary copy saved **zero bytes**. A different build may be smaller, but no alternative binary was measured. Replacing Pandoc or removing LaTeXML would affect conversion and citation behavior, so neither belongs in the first packaging pass.

## Runtime efficiency findings

These are code-based opportunities, not measured latency or battery improvements.

- `app/static/app.js:706` polls every two seconds. `/api/state` returns every paper record and the full job history, and `papers/library.py:76` and `:135` load every corresponding JSON record. Saved paper records include document data, so polling grows with the library. Return lightweight list records, bound completed job history, slow polling when idle or hidden, and avoid overlapping refreshes. Existing signature checks already avoid some DOM redraws, but not transport and JSON work.
- `papers/convert.py:108` uses `int(elapsed) % 5 == 0` for process-memory checks. Several output-driven loop iterations can fall in the same second and repeatedly launch `ps`; other iterations can miss that second. Use a monotonic next-check deadline while preserving the aggregate memory limit.
- `papers/document.py:243-288` already batches MathJax rendering and caches repeated equations and PNG bytes. Preserve that. Each distinct equation still invokes `rsvg-convert`; measure this on equation-heavy papers before adding a batch renderer or replacing rasterizers.

## Repository storage and release guardrails

`du` measured about 14 GiB in `dist` and 31 GiB in `.verification`. These directories are not selected by the release builder and do not explain the app's installed size. They are separate local-storage candidates. No files were deleted.

Add a release size inventory with totals for the app, each runtime component, npm packages and the final DMG. Set budgets after the first verified reduced build so a dependency update cannot silently reintroduce a full JDK or extra executables. Apply pruning before dependency traversal and final signing. Verify relocation with Homebrew blocked, the existing release smoke checks, and representative plus holdout papers with equations, references and PDF/EPS/PS graphics.

No app rebuild, installation, publication or full conversion-corpus run was performed during this audit.
