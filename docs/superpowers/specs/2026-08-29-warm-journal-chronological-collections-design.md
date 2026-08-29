# Warm Journal and Chronological Collections Design

## Goal

Make the extension feel like a compact war-research journal rather than a generic blue utility, then make every alphaXiv folder review and anthology use the papers' initial arXiv submission dates in oldest-to-newest order.

The visual redesign is implemented first. Chronology then becomes part of collection discovery so the reviewed preview and the submitted anthology share one order.

## Constraints

- Keep the existing MV3 popup, background worker, native-messaging host, Pandoc conversion, EPUB validation, and macOS Mail flow.
- Add no frontend framework, package, hosted service, private alphaXiv API, paper selector, drag reordering, queue, or persistent paper library.
- Keep one-click sending for a single paper after the Kindle address has been saved.
- Preserve the saved Kindle address, named job state, five-row collection preview, exact collection count, and 50-paper maximum.
- Keep page URL validation fail closed. ArXiv metadata must never make an untrusted page or link eligible.
- Do not change `native/host.py` or `tests/test_host.py` for this feature. The native anthology pipeline already preserves the URL order it receives, and both files contain unrelated user work.
- Do not fall back to folder DOM order, identifier lexicography, or an arXiv revision date when initial-submission metadata cannot be verified.

## Visual direction

The selected direction is a warm field journal mixed with restrained library index cards.

### Palette and typography

- Light mode uses warm ivory paper, graphite text, weathered gray borders, and a muted rust accent.
- Dark mode uses charcoal paper, warm off-white text, softened gray borders, and a lighter rust accent.
- Display headings use Georgia or the platform serif fallback.
- Controls and prose use Avenir Next or the platform sans-serif fallback.
- Dates, arXiv identifiers, counts, and compact status metadata use SFMono-Regular or the platform monospace fallback.
- Blue is removed from the identity, controls, links, focus treatment, and progress treatment.

### Paper texture

The popup background uses a sparse gray dotted grid. The dots must stay lower contrast than body text and card boundaries in both color schemes. There are no ruled lines, notebook stripes, faux tears, stains, or decorative marks behind copy.

### Identity and iconography

The header uses a rust bookmark mark containing a simple `K`, paired with the product name. The same mark is exported as 16, 32, 48, and 128 pixel extension icons and declared for the extension and popup action in the manifest.

### Layout hierarchy

The 360-pixel popup keeps one column:

1. compact brand header;
2. dominant job/status card, including progress when a job is running;
3. current paper or collection card;
4. delivery settings disclosure;
5. primary action.

Cards use a paper surface, a one-pixel border, a small radius, and minimal shadow. Collection rows resemble catalog entries through spacing and typography rather than heavy skeuomorphism.

The status card remains visible above page context so an older job result is not confused with the newly opened page. Running collection jobs show a native progress bar plus `current / total` and percentage when both values are available. Success and Mail-error states retain the saved-EPUB/manual-upload path.

The settings summary has a visible `Add` or `Edit` action and chevron. Form borders meet non-text contrast requirements. Invalid email input sets `aria-invalid="true"` until the value is corrected. All interactive controls keep a visible focus ring and a minimum 44-pixel target. Reduced-motion and dark-mode preferences remain supported.

## Current-page states

### Single paper

The card shows the paper label and its normalized arXiv identifier. The primary action remains `Send to Kindle`.

### Collection metadata loading

After trusted folder links are normalized and the count is confirmed to be between 1 and 50, the popup says it is checking initial arXiv dates. The send button remains disabled. No native job can start during this state.

### Collection ready

The popup says that the papers are ordered oldest to newest by first arXiv submission. The first five compact rows show:

- the reviewed alphaXiv title, or the existing arXiv-ID fallback;
- `YYYY-MM-DD · arXiv {ID}` in monospace metadata.

The existing `+ N more` summary follows when needed. `Compile and send N papers` submits exactly the order shown.

### Over the limit

A folder with more than 50 normalized papers is blocked before any arXiv API request. Visible copy states the limit and the primary button remains disabled.

### Chronology unavailable

Any incomplete or untrustworthy metadata result blocks sending. The card explains that initial submission dates could not be verified and exposes a direct `Retry dates` action. It never silently uses another order.

## Chronology source and meaning

The canonical date is each Atom entry's `<published>` timestamp from the official arXiv API. ArXiv defines this as the time version 1 was submitted and processed. Entry `<updated>` describes the retrieved revision and feed-level `<updated>` describes the query, so neither participates in ordering.

The extension makes one batched request for the collection:

```text
https://export.arxiv.org/api/query?id_list=<comma-separated base IDs>&start=0&max_results=<count>
```

The manifest adds only `https://export.arxiv.org/*` as a host permission.

Version suffixes such as `v2` are removed only for metadata lookup and matching. The original normalized URL remains the conversion URL. Modern identifiers and legacy archive identifiers such as `cond-mat/0207270` remain supported.

## Data flow and ordering

1. The popup inspects the trusted alphaXiv folder and shared helpers normalize and deduplicate paper links in first-seen position.
2. Collections above 50 stop here.
3. The popup requests all base identifiers once from the official Atom endpoint.
4. A narrowly scoped Atom-entry parser accepts only arXiv abstract identifiers from the official feed shape. It does not weaken the existing HTTPS page-link parser.
5. Results are joined to papers by canonical identifier. Feed response order is ignored.
6. Every requested paper must have exactly one valid `<published>` timestamp, and the response must contain no unknown or error entry.
7. Papers sort by parsed timestamp ascending. Original folder position is the stable tie-breaker.
8. The sorted paper objects drive both the preview and the submitted `urls` array.
9. The worker forwards the request unchanged. The native host converts sequentially and builds its OPF spine and flat table of contents in the received order.

One bounded successful lookup may be cached in session storage by its exact ordered base-ID fingerprint. The request-start timestamp is also session-scoped so retries and rapid page changes can respect arXiv's minimum three-second request interval. Existing terminal cleanup removes these session values while preserving the fresh `jobState`; nothing becomes a durable paper cache.

## Failure and race handling

Chronology fails closed on:

- timeout, network error, HTTP 429, or HTTP 5xx;
- a non-success HTTP response;
- an oversized response;
- malformed XML or a parser error;
- an arXiv API error entry;
- a missing, duplicate, or unknown identifier;
- a missing or invalid `<published>` timestamp.

The lookup has a bounded timeout and response-size limit. Identical in-flight work is coalesced within the popup. A discovery generation token prevents a slow response from overwriting a newer page inspection. A changed page, changed membership, or active job invalidates the stale result. Metadata failure never calls the background worker or native host.

## Accessibility and copy

- Discovery, date lookup, readiness, failure, and job progress remain in polite live regions.
- The progress element has an accessible label and visible numeric text.
- Ordered preview rows remain native list items.
- Dates are displayed as calendar dates while sorting uses parsed instants.
- Error, loading, over-limit, and disabled states are communicated in text, not color alone.
- Links that open a new tab keep visible and assistive wording.
- The dotted background, borders, rust accents, and focus rings are checked in light and dark mode.

## Verification

Automated tests must prove:

- feed order is ignored and `<published>`, not either `<updated>`, controls sorting;
- modern, legacy, and version-suffixed IDs map correctly without relaxing page URL trust;
- mixed dates sort oldest first and equal timestamps retain original folder order;
- the first five preview rows and submitted URL array use the same chronological paper objects;
- the reviewed title remains attached to its paper after sorting;
- missing, duplicate, unknown, invalid-date, error-entry, malformed, timeout, HTTP-error, and oversized responses block submission and expose retry;
- a stale lookup cannot overwrite a newer inspection or start a native job;
- 50 papers use one batch request and 51 papers are rejected before lookup;
- running jobs render current, total, percentage, and progress semantics when available;
- single-paper context includes its arXiv identifier;
- email validation toggles `aria-invalid`;
- manifest JSON, JavaScript syntax, extension tests, Python tests, shell syntax, and whitespace checks pass.

Visual inspection at 360 CSS pixels covers light and dark paper, collection loading, chronologically ready, over-limit, working progress, success, chronology error, and Mail error states. It checks the quiet dotted grid, long-title wrapping, five-row preview, settings affordance, focus states, disabled controls, icon clarity, and horizontal overflow. Verification must not trigger macOS Mail.
