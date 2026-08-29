# Review-First Library Jobs Design

## Goal

Make long-running alphaXiv anthology jobs trustworthy without changing the existing one-click paper flow. The extension must prevent overlapping native jobs, show what a folder scrape collected before Mail starts, identify background and completed jobs, and release temporary paper sources as soon as each validated EPUB no longer needs them.

## Constraints

- Keep the current MV3 popup, service worker, native-messaging host, Pandoc, and macOS Mail architecture.
- Add no dependency, hosted service, alphaXiv account access, private API, queue, cancellation protocol, or persistent paper cache.
- Keep `chrome.storage.local.kindleEmail` as the durable setting.
- Clear every stale `chrome.storage.session` key after a terminal response contains `epub_path`, while keeping the fresh terminal `jobState` visible.
- Keep the single-paper action as one click after the Kindle address has been saved.
- Keep collection order equal to first-seen DOM order and the existing 50-paper maximum.
- Continue to download TeX only from arXiv and fail before Mail when conversion or validation fails.

## Chosen interaction

Three shapes were compared:

1. A patch-only popup would fix the race and enforce the 50-paper limit but would keep folder membership opaque.
2. A review-first folder popup would keep paper sending unchanged and show a small ordered collection preview before an anthology starts.
3. A job-center popup would add history, retry, cancellation, and queue controls around every conversion.

The second shape is selected. It fixes the trust problem with one compact preview and a named status card. It does not add selection, reordering, history, or a second popup view.

## Terminal-state race

The current worker marks itself idle before terminal state persistence finishes. `storeTerminalJob` then clears session storage before writing the result. An open popup sees the deleted `jobState` as idle and can start a second job. The first terminal callback resumes later and disconnects the shared global native port, which may now belong to the second job.

The worker will keep `working` true until terminal state persistence finishes. Each start will capture its native port in a local constant, and its listeners will disconnect only that port. A local `terminalReceived` flag will stop `onDisconnect` from overwriting a terminal response while session storage is still being updated.

For responses with `epub_path`, `storeTerminalJob` will:

1. read the current session keys;
2. write the fresh terminal `jobState` first;
3. remove every previously present key except `jobState`.

This preserves the requested cache cleanup without creating an observable empty `jobState` interval. Responses without `epub_path` will continue to preserve unrelated session state.

## Named job state

The background worker will derive one identity from the submitted request and copy it into working, progress, success, and error states:

- a paper job uses `Paper {arXiv ID}`;
- a collection job uses the cleaned folder title and its deduplicated paper count.

The stored fields are `job_label` and `paper_count`; no raw Kindle address, private page data, or full paper manifest is persisted. The popup will display the label inside the status card. A result from Folder A can therefore remain visible after the user navigates to Paper B without appearing to describe Paper B.

## Folder recognition and review

Collection discovery will fail closed. A page is eligible only when it is trusted HTTPS alphaXiv and its path starts with `/library/folders/` followed by a nonempty folder identifier. Query strings and fragments do not affect recognition. Other alphaXiv pages remain valid only when their own URL is a trusted `/abs/{id}` paper URL.

The active-tab script will return each anchor's URL and visible text. Shared normalization will:

- accept only trusted arXiv or alphaXiv abstract links;
- deduplicate by validated arXiv ID in first-seen order;
- collapse whitespace in the visible anchor text;
- use `Paper {arXiv ID}` when the text is empty;
- keep labels to 160 characters.

The collection context will retain the normalized ordered paper objects and their URLs. The popup will show the first five labels in an ordered list and `+ N more` when the collection is longer. The primary action remains `Compile and send N papers` for 1 through 50 papers. Counts above 50 will show the limit and keep the button disabled, so the native host remains a second trust-boundary check rather than the first user-visible rejection.

The public alphaXiv DOM could not be fetched during design. Folder routing and link normalization therefore live in shared helpers with literal route tests. A site change will fail closed and require one helper update instead of silently scraping a different page.

## Temporary anthology data

The native host needs only `PaperMetadata` and the validated per-paper EPUB after `convert_source` returns. After each successful paper conversion, it will remove that paper's downloaded archive and extracted source tree while retaining `paper.epub` for `build_anthology`. Cleanup is best effort because a local temporary-file removal problem must not invalidate an otherwise usable EPUB; the surrounding `TemporaryDirectory` remains the final cleanup boundary.

## Accessibility and copy

- The page-context region will announce the result of asynchronous discovery with `aria-live="polite"`.
- The ordered preview will use native `<ol>` and `<li>` elements.
- An over-limit collection will explain the exact 50-paper limit in visible text, not color alone.
- The saved-EPUB Amazon link will keep its existing manual-upload behavior and identify that it opens a new tab for assistive technology.

## Verification

Automated tests must prove:

- a second start is rejected while terminal session persistence is deliberately delayed;
- the first job disconnects only its own native port;
- terminal persistence publishes `jobState` without a deletion event and removes other prior session keys only when `epub_path` exists;
- only `/library/folders/{identifier}` pages can become collections;
- folder papers retain first-seen order, cleaned labels, URL normalization, and ID fallbacks;
- collections above 50 are disabled before submission while the native host still rejects them;
- working and terminal states keep the same job label and paper count;
- each converted paper's downloaded archive and extracted tree are gone before anthology assembly, while its EPUB remains;
- Python, JavaScript, shell, manifest, and whitespace checks pass;
- the full macOS test suite runs with Quick Look and SIPS access;
- visual inspection covers paper, valid folder, over-limit folder, working named job, success, and Mail-error states in light and dark color schemes.

No automated check will send Mail to Kindle.
