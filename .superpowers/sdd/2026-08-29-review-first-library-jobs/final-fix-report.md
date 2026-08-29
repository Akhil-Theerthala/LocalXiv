# Final review-fix report

Date: 2026-08-29

Base commit: `44d3383bda81b22ccaa785f7eaa9a02a91bf8242`

Implementation commit: `f9f48e8` (`fix: harden extension job state races`)

## Outcome

The four Important whole-branch review findings are fixed in the extension code and covered by focused regressions. The change does not touch the native Python host, installer, dependencies, or Mail delivery.

## RED and GREEN evidence

1. Terminal stale-snapshot read failure

   - RED: `node --test tests/test_extension.js` reported 23 passed and 1 failed. `storeTerminalJob preserves a saved EPUB when stale session inspection fails` rejected with `Session inspection failed.`
   - GREEN: the same command reported 24 passed and 0 failed after making the stale-key read best effort. The terminal `set` still rejects on failure, and successful cleanup remains `set` before `remove`.

2. Malformed non-array `request.urls`

   - RED: the focused run reported 23 passed and 2 failed. `jobIdentity({ urls: {} })` failed with `values is not iterable`, and the worker identity-error test threw `Malformed collection input.` before responding.
   - GREEN: the next corrected run reported 25 passed and 0 failed. `jobIdentity` checks `Array.isArray` before normalization, and the worker catches identity errors before reserving `working` or `activeJob`.
   - Final coverage also sends `{ urls: {} }` to the native host, lets the native host reject it, and proves a later valid start succeeds.

3. Inspected-URL route change

   - RED: the focused run reported 25 passed and 1 failed. A tab that changed from an alphaXiv folder to search still rendered `alphaXiv library` instead of `Unsupported page`.
   - GREEN: the next run reported 26 passed and 0 failed after the injected collector returned `location.href` and discovery validated that inspected URL.

4. Delayed start response and rapid double submit

   - RED: the focused run reported 26 passed and 2 failed. A delayed start response replaced a newer terminal state with `Working`, and two immediate submits made 2 runtime calls instead of 1.
   - GREEN: the next run reported 28 passed and 0 failed after adding a synchronous local reservation and a session job-state revision guard.
   - Final coverage confirms valid single-paper and inspected in-limit collection requests still submit with the saved Kindle address.

## Final verification

- `node --test tests/test_extension.js`: 31 passed, 0 failed.
- `node --check extension/shared.js`: passed.
- `node --check extension/background.js`: passed.
- `node --check extension/popup.js`: passed.
- `node --check tests/test_extension.js`: passed.
- `python3 -m json.tool extension/manifest.json`: passed.
- `git diff --check`: passed before the implementation commit.

## Changed files

- `extension/shared.js`
- `extension/background.js`
- `extension/popup.js`
- `tests/test_extension.js`
- `.superpowers/sdd/2026-08-29-review-first-library-jobs/final-fix-report.md`

## Event-sequence self-review

- Terminal EPUB plus stale-read failure: the read failure becomes an empty snapshot, the terminal job is stored, and no cleanup runs.
- Terminal EPUB plus cleanup failure: the terminal job is stored first, cleanup failure is ignored, and the manual EPUB path remains.
- Malformed identity: identity construction fails before reservation, the caller receives `{ ok: false }`, and the next valid start can reserve the worker.
- Folder route change: discovery uses the URL read inside the inspected page, so valid paper links on search or another unsupported route cannot enable submission.
- Delayed popup response: a newer session job event advances the revision, so neither a late success nor a late error can replace the authoritative job display. A local working reservation blocks a second synchronous submit before the first await.

## Constraints and concerns

- One-paper submission remains supported and covered.
- No Mail action was run.
- No dependency was added.
- No native Python or installer behavior changed.
- No merge or push was performed.
- The popup and worker checks use VM-backed Chrome API doubles. Real Chrome/native-host/Mail integration was intentionally not run for this review-fix wave.
