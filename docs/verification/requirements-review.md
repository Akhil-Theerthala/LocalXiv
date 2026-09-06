# Final requirements review

Date: 2026-09-06. Read-only review of the approved local-library design against the current app, AI/export code, installer, and README. No provider request, Mail submission, corpus rerun, or inspection of existing keys was performed. This is a source snapshot; later fixes need their own verification.

## Findings and resolution status

| Priority | Requirement or user action | Current behavior and evidence | Consequence |
|---|---|---|---|
| Resolved | Choose a reading profile, then send the selected artifact | The Send action now passes the selected profile, matching export. | The UI test verifies that choosing both artifacts and the semantic profile posts both selections to the send endpoint without submitting Mail. |
| Resolved | Display reported provider usage when available | Overview notes now sum provider-reported totals across generation requests; chat displays its reported usage. Missing usage remains absent and partial totals are labeled. | UI tests cover total aggregation, chat display, zero usage, partial reporting, and input/output counts when no total is reported. No currency estimate is generated. |
| Resolved | Keep a delivery attempt with artifact identity, recipient, request time, and outcome | The job now stores recipient, artifact filename and SHA-256, profile, kind, requested/attempted time, and Mail outcome before the handoff. | Fake-Mail tests confirm the selected artifact and preserve an unknown outcome after a timeout without retrying. |
| Resolved | Validate the final combined export before publication | The combined candidate now passes EPUBCheck before replacing the previous export. This exposed and fixed missing EPUB 3 modification metadata in the anthology packager. | Real combined Kindle and semantic exports pass EPUBCheck. A failed-candidate test confirms the earlier valid book remains intact. |

The browser reader uses browser-native MathML rather than the bundled browser renderer described in the design. MathJax is bundled for equation-image generation. This is an implementation deviation, not evidence of a demonstrated rendering failure in the tested browser.

## Earlier review findings addressed

- Reimported content has a document digest; changed content invalidates overview/chat records and reloads an open reader once.
- Failed imports retain an accessible original PDF when available and preserve an existing ready paper after a failed retry.
- Narrow chat requests use retrieval with neighboring passages; optional conversation history is bounded. Explicit whole-paper requests fail clearly when their evidence is too large.
- Chat persists model, prompt revision, document/source identity, evidence scope and IDs, and reported usage.
- Overview/chat prose is rendered through text nodes into readable blocks. Source links resolve only to retained local evidence. Unknown HTML and unsafe links remain literal text.
- Request context/output/time limits can be edited through the settings dialog.
- The launcher, app bundle, native handoff, and server default use the same library path. Temporary installation and reinstallation previously verified paths containing spaces and preservation of library data.

## Validation still requiring external evidence

- No user-configured live provider has been used in this review. Mock HTTP contract tests establish request/response behavior, not factual summary quality or compatibility with every model.
- No real Mail submission or Kindle arrival is established here. A Mail handoff cannot confirm device delivery.
- No check on the user's Kindle establishes that the reported device-specific equation problem is resolved. EPUBCheck and browser rendering address different questions.
- Successful conversion or absence of automated audit flags does not prove semantic fidelity for arbitrary TeX. Use the current conversion-results and content-audit snapshots for corpus-specific outcomes.
- The install smoke tests used temporary paths in the current user environment. They do not establish first-use Keychain/Mail permission behavior on a clean macOS account.

## README assessment

The README distinguishes the recommended local library from the retained direct-send extension, states source-retention differences, identifies the optional TeX dependency, and avoids a promise that every paper converts. It also separates mocked API checks from live-provider quality and Mail submission from delivery. The reviewed claims match the implemented boundaries after the fixes above. Automatic overview wording was corrected to match its configured-AI default; automatic delivery remains off. Verification links deliberately avoid hard-coded corpus success totals while results are being refreshed.
