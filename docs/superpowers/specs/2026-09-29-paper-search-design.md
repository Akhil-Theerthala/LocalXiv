# Paper search design

Date: 2026-09-29. Source: a grilling session from 2026-09-27 to 2026-09-29. The user decided every item below, or left the choice to the author where the text says so. External facts come from live requests to the arXiv API and the Semantic Scholar API on 2026-09-29. Domain nouns are `CONTEXT.md`'s: **Direct import**, **Paper search**, **Suggestions**, **Library search**, **Paper**, and **Paper queue**.

## Goal

The home field accepts only a link today. After this change, the same field also finds a Paper by title, author, or topic. The reader can then import the Paper without its link. A link or a bare arXiv ID goes straight to Direct import, with no search.

## Facts that shaped the design

| | arXiv API (`export.arxiv.org/api/query`) | Semantic Scholar (S2) Graph API |
|---|---|---|
| Latency | 0.4 to 0.6 s. A repeated identical GET comes from the CDN in 0.05 s. | `/paper/search` 1.2 s. `/paper/autocomplete` 0.7 s. |
| Rate limit | One request every 3 s, on one connection. | Without a key, one pool is shared by all anonymous users worldwide. 8 of 13 test requests got HTTP 429. A key gives its owner 1 request per second. |
| Ranking | Weak for well-known papers. `direct preference optimization` and `llama 2` did not put the paper people mean in the top 8. `ti:"attention is all you need"` put 1706.03762 at rank 1. `ti:"…" OR (all:…)` was worse than either query alone. | Good. The paper people mean was rank 1 or 2 for all three test queries. |
| arXiv ID | Every entry. | `/paper/search` returns `externalIds.ArXiv` when the paper has one. 17 of 25 test hits had it. `/paper/autocomplete` returns only `id`, `title`, and `authorsYear`, with no arXiv ID. |
| Terms | Asks for the sentence "Thank you to arXiv for use of its open access interoperability." | Requires the words "Semantic Scholar". Forbids shipping one key to all users. May keep the text of requests. |
| Freshness | A paper appears after its announcement. The worst case is about 3 days (Thursday afternoon to Sunday night). | Not measured. |

An arXiv API request for an unknown arXiv ID returns HTTP 200 with `opensearch:totalResults` 0, not an error entry.

The page CSP (`app/server.py:328`, `default-src 'self'`) blocks browser calls to both hosts. All outbound calls go through the Python server.

## Input rules

Before the browser does anything with the text in a search field, the browser sorts the text by these rules:

| Text | Kind | Enter does |
|---|---|---|
| Empty or only spaces | None | Nothing. |
| Text that starts with `http://` or `https://`, or that contains `arxiv.org/` or `alphaxiv.org/` | Direct import | Sends the text to `POST /api/import`. The server imports the Paper or rejects the text with its current message. No search request. |
| A bare arXiv ID: `1706.03762`, `1706.03762v7`, or `hep-th/9901001` | Direct import | Sends the ID to `POST /api/import`. No search request. |
| Anything else | Paper search | Opens the results page, unless the reader highlighted a suggestion. |

The browser uses the same ID pattern as `paper_id()`. The submit button next to the field does the same as Enter.

The server stays the one validator. `paper_id()` (`papers/acquire.py:14`) changes to accept a bare ID as well as a link. `POST /api/import` (`app/server.py:464`) changes a bare ID into `https://arxiv.org/abs/<id>` before `app.submit`, so a bare ID and its abstract link get the same job reservation hash. Links go to `app.submit` unchanged, so `metadata.json` keeps the pasted link as `original_url` (`papers/acquire.py:93`).

A Direct import from either field starts the import, closes the list, and clears the field. The reader stays on the current page. The Paper queue notice shows progress, and the setting "Open a paper when its import finishes" applies.

## Suggestions on the home field

The home field shows Suggestions under it while the reader types Paper search text.

- Library matches update on every keystroke from the first character. They make no request.
- Remote results start at 3 characters, 400 ms after the last keystroke. The 3-character minimum applies only to Suggestions. Enter opens the results page for Paper search text of any length.
- A request counter drops responses to old keystrokes, the same way `detailRequest` does in `app/static/app.js`.
- The list shows up to 3 library matches first, marked **In library**. Remote results follow, up to 8 rows in total.
- A remote row shows the title, the first 3 authors and then "et al.", the year, and the arXiv ID without a version.
- A remote row is for a library Paper when its `arxiv_id` equals the `arxiv_id` of a library Paper without the `vN` suffix. Remove that remote row if its Paper is already a row in the library group. Otherwise, keep it and mark it **In library**.
- If the response has `error: "unavailable"`, the list shows the library group and the line "Search is down. You can still paste a link."
- If there are no remote results, the list shows only the library group. If the list has no rows, it closes.
- The footer line reads: "Suggestions from Semantic Scholar. Thank you to arXiv for use of its open access interoperability."

The keys follow a browser address bar:

| State | Key | Result |
|---|---|---|
| No suggestion highlighted | Enter | Opens the results page for the text. |
| Suggestions not arrived yet | Enter | Opens the results page. |
| A suggestion highlighted with ↓ or ↑ | Enter | If that Paper is in the library, opens it. Otherwise, imports it. |
| Any | Click on a suggestion | Same as highlight and Enter. |
| List open | Esc | Closes the list and keeps the text. |

No suggestion is highlighted by default. When the reader chooses a remote row for a Paper that is not in the library, the browser sends its link to `POST /api/import` at once. That route starts the import job. The import downloads from arXiv, so no separate arXiv check runs first. A library Paper opens by its versioned `id`.

The field becomes a WAI-ARIA combobox. Give `#home-url` `role="combobox"`, `aria-expanded`, `aria-controls` set to the list's ID, and `aria-activedescendant` set to the highlighted row's ID. Give the list `role="listbox"`, and give each row `role="option"`. `#home-url` changes from `type="url" required` (`app/static/index.html:8`) to `type="search"`, because the browser's URL check rejects words and bare IDs before `onsubmit` runs.

## Results page

When the text is Paper search and no suggestion is highlighted, Enter opens the results page (`view.page === 'search'`). The results page is an in-app view, like Home and the Library.

- The results page has its own field at the top, the results field. The results field has the same input rules and Suggestions as the home field, so the reader can change the query there.
- The heading is "Results for "<query>"".
- Up to 5 library matches come first, in their own group. Up to 20 remote results follow. There is no paging and no "More results" button. There are no filters and no sort control. The author chose the limit of 5.
- The page shows "Searching…" under the library group until its `POST /api/search` request (`limit` 20) returns. The page uses its own request counter and ignores responses to old queries.
- Each remote row shows the title, the first 6 authors and then "et al.", the year, the arXiv ID, and the first 2 lines of the abstract. A click on the abstract shows all of it.
- Each draw computes a row's state from `state.papers` and `state.jobs`. A Paper in the library gives an **Open** button and an **In library** mark. An active import job for the same arXiv ID without version gives "Adding…". Otherwise, the row gives an **Add** button. If the job fails or is cancelled, the button returns to **Add**, and the job notice shows the error.
- **Add** keeps the reader on the page while the import runs. If "Open a paper when its import finishes" is on (the default), the Paper opens when the import finishes, with **← Results**. If the setting is off, the button changes to **Open**.
- The empty state reads: "No papers found. Papers from the last few days may not appear yet. Paste the link instead."
- The failure line reads: "Search is down. You can still paste a link." Library matches still show.
- The footer line is the same as for Suggestions.

The grilling session also asked for the primary arXiv category on each row. S2 does not return the category, so rows do not show it.

## Navigation

Navigation state stays in the in-memory `view` object (`app/static/app.js:16`). The results page does not change the URL or the browser history. `HOME` (`app/static/view.js:2`) gains `from: null`, and `applyView` (`app/static/view.js:4`) gains the `search` page.

- `openPaper` sets `from: 'search'` when `view.page === 'search'`. In all other cases, it keeps `from`, so the `openPaper(selected)` call from `refresh` does not lose it. `goHome` (`app/static/app.js:260`) sets `from: null`.
- `applyView` labels `#reader-home` **← Results** when `reading && from === 'search'`. Otherwise, it keeps **← Library** while reading and **← Home** elsewhere.
- The `#reader-home` handler (`app/static/app.js:275`) reads `from` first. When `from === 'search'`, the handler calls `goHome()`, as `showLibrary()` does, so `selected`, `detail`, and the reading panels are cleared. Then it calls `setView({page: 'search', from: 'search'})` and restores the kept scroll position. The page redraws the kept query and results without a new request.
- From the results page, **← Home** goes home.
- The mobile navigation gets no new item. The reader reaches the results page only from the home field or the results field.

## Library matching

Library search and the library group in Paper search use one shared rule. Every word of the query must appear in the lowercase text `${title} ${authors} ${arxiv_id || id}`. Today the filter in `app/static/render.js:242` matches the whole query as one substring, so `attention vaswani` finds nothing. Move the rule into one exported function. Call it from `renderLibrary` (`app/static/render.js:238`), the Suggestions list, and the results page. The rule does not look at Tag or Collection names. Library matching runs in the browser on `state.papers`, so it makes no request, and it runs even when Suggestions are off.

## Server

A new module, `papers/search.py`, owns every outbound search call. `POST /api/search` takes `{"query": str, "limit": 8 | 20}` and calls `paper_search(query, limit)`. On success, the route returns HTTP 200 with `{"results": [...], "source": "semantic_scholar" | "arxiv"}`. When every service that `paper_search` tried fails, the route returns HTTP 200 with `{"results": [], "error": "unavailable"}`. The route uses POST because the existing `api()` helper (`app/static/app.js:61`) sends a JSON body only with POST.

`paper_search(query, limit)` picks the source in this order:

1. If the query uses an arXiv field prefix (`ti:`, `au:`, `abs:`, `co:`, `jr:`, `cat:`, `rn:`, `all:`), send the query to arXiv unchanged.
2. Otherwise, if S2 is not cooling down, call `GET /graph/v1/paper/search?query=…&limit=<2 × limit>&fields=title,year,authors,externalIds,abstract`. Keep only rows that have `externalIds.ArXiv`, then cut the list to `limit`. Do not use the S2 autocomplete endpoint.
3. If S2 returns 429, times out, or fails, stop S2 calls for 60 s and use arXiv. Never retry S2 inside the cooldown, because the S2 license forbids working around its rate limits.
4. If S2 succeeds but no row has an arXiv ID, use arXiv. Do not start the cooldown. The author chose this fallback.
5. For the arXiv call, send `ti:"<text>"` when `limit` is 8 (Suggestions). Send `all:<w1> AND all:<w2> …` when `limit` is 20 (the results page). Send `sortBy=relevance` with both, and with a prefix query from step 1.

Rules for both services:

- Each request has an 8 s timeout, a 1 MB response limit, and the User-Agent `LocalXiv/0.1 (personal local paper reader)` that `download()` sends (`papers/acquire.py:40`). The arXiv call uses `ArxivRedirect` from `papers/acquire.py`.
- Catch `OSError`, `ValueError`, `http.client.HTTPException`, and `xml.etree.ElementTree.ParseError` around each outbound call and its parsing. Treat each error as a failure of that service: an S2 failure goes to step 3, and an arXiv failure gives `error: "unavailable"`. If these errors are not caught, `handle_request` (`app/server.py:499-509`) turns a `ValueError` into a 400 with its message, turns a `URLError` into a generic 500, and sends no response for a `ConnectionResetError`.
- One process-wide gate spaces arXiv requests 3 s apart. When a key exists, a second gate spaces S2 requests 1 s apart. A Suggestions request that waits at a gate returns HTTP 200 with `{"results": []}` if a newer Suggestions request arrived during the wait. The browser's request counter already ignores that response. A results-page request always runs.
- Successful results stay in an in-memory cache for 10 minutes, keyed by source, query, and limit, with at most 100 entries. The cache never keeps a dropped or `unavailable` response. A cache hit does not wait at a gate.
- The Atom parser is tolerant, because the live feed differs from the arXiv API manual. Entry IDs use `http://`, `primary_category` has no `scheme`, element order changes, and titles and abstracts contain newlines and TeX. Normalize whitespace.
- Each result is `{arxiv_id, title, authors: [str], year, abstract}`. `arxiv_id` has no version. The browser sends the link without a version to `POST /api/import`, so `acquire()` pins the latest version (`papers/acquire.py:74-81`). A Paper chosen from Paper search always imports the latest version. A Direct import of a link or an ID with a version keeps that version.

## Settings

A new **Paper search** section in the Settings dialog holds two controls:

- **Show suggestions while typing** (checkbox, on by default). Add `search_suggestions` to `SETTING_KEYS` (`papers/library.py:14`), to `DEFAULTS` (`app/server.py:34`), and to the boolean list that `/api/settings` checks. When the checkbox is off, typed text leaves the Mac only when the reader presses Enter. The list under the field still shows library matches while the reader types.
- **Semantic Scholar API key** (optional password field). The browser sends the key in its own body field, `s2_api_key`. `/api/settings` removes `s2_api_key` from `values` beside `api_key` (`app/server.py:439`) and saves it with `set_key` (`papers/settings.py:61`) under the account `https://api.semanticscholar.org`. `public_settings()` (`app/server.py:60`) adds `has_s2_key`, so the dialog can say that a key is saved. The page never receives the key, and a blank field keeps the saved key. When a key exists, `papers/search.py` sends it in the `x-api-key` header. If `get_key` raises `RuntimeError`, `papers/search.py` continues without a key. When no key exists, the app uses the shared pool and the arXiv fallback.

## Text

The user left the exact text to the author.

| Place | Text |
|---|---|
| Home field placeholder | Search arXiv or paste a link |
| Home field label (screen readers) | Search for a paper, or enter an arXiv or alphaXiv link or ID |
| Home field button (`#empty-import`, `app/static/index.html:8`) | Go ↗ (screen-reader label: Search or add a paper) |
| Tour step (`app/static/app.js:783`) | Search by title or author, or paste an arXiv or alphaXiv link. Your papers stay in your library on this Mac. |
| Suggestions and results footer | Suggestions from Semantic Scholar. Thank you to arXiv for use of its open access interoperability. |
| `NOTICE` | The same acknowledgement line. |

## Build order

Each step ends in a state you can check:

1. **Direct import of bare IDs.** Change `paper_id()` and `POST /api/import`. Check: send `1706.03762` and then `https://arxiv.org/abs/1706.03762` to `POST /api/import` before the first job finishes. Both responses carry the same job ID.
2. **`papers/search.py` and `POST /api/search`.** Check: the recorded-response tests below pass.
3. **Settings.** Add the checkbox and the key field. Check: the setting survives a restart, and the key is in Keychain and not in `/api/state`.
4. **Shared library matching.** Check: `attention vaswani` finds the sample Paper in Library search.
5. **Home Suggestions.** Check these in the app preview: the key table under "Suggestions on the home field", the library group, and a stale response. A stale response must not replace a newer one.
6. **Results page and navigation.** Check these in the app preview: **Add**, **Open**, **← Results**, the empty line, and the failure line.
7. **Text.** Update the home field placeholder, label, and button, the tour step, the footer line, and `NOTICE`.

## Tests

Put the tests in `tests/test_paper_search.py`. They are component end-to-end tests that call the real `/api/search` route through `make_server(root, token='local-test')`, as `tests/test_paper_jobs.py` does. Replace the outbound calls with responses from `tests/fixtures/paper_search/`. Record each response once from a live request. Cover these cases:

- S2 search results with and without `externalIds.ArXiv`.
- S2 results where no row has an arXiv ID. The request uses arXiv, and the cooldown does not start.
- An S2 429 response. The request falls back to arXiv, and a second request within 60 s does not call S2.
- An S2 failure and an arXiv failure. The route returns `error: "unavailable"`.
- An arXiv prefix query. The request does not call S2.
- An arXiv feed with `totalResults` 0.
- Bare IDs through `/api/import`: `1706.03762`, `hep-th/9901001`, and `1706.03762v7`.

One live test calls both services only when `LOCALXIV_LIVE=1` is set.

## Not in scope

- Natural-language queries, which the user expects to add to Paper search later.
- Paging, filters, sort controls, and matching on Tags or Collections.
- A LocalXiv-hosted proxy or a shared S2 key.
- A button that removes a saved S2 key. The AI key has none either.

## Open items

- **Search failure design.** The failure line above is a placeholder. The user wants the full behavior designed later: what the reader sees during the S2 cooldown, when arXiv is also throttled, when the Mac is offline, and when S2 rejects the key (HTTP 401 or 403).
- **arXiv rate-limit scope.** The arXiv terms count "all machines under your control" as one client. They do not say whether separate installs of LocalXiv count as one.
- **S2 data licenses.** Some S2 data is CC BY-NC. The license matters only if LocalXiv becomes commercial or stores S2 results. Decide whether the 10-minute in-memory cache counts as storage.
- **S2 key for LocalXiv users.** The S2 API key request form does not show whether S2 grants keys to individual readers of a desktop app.
