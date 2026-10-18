# Release 1: Chat and Ask Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A reader asks about a Paper or a selected passage, and gets a streamed, cited answer from a Chat model with its own provider and key. The question and its answer stay as a question card in the margin beside the words.

**Architecture:** A new module `papers/chat.py` builds the request (the whole Paper as a 1-hour cached prefix, the selection last) and checks the citations. `Provider.stream()` streams both transports. A new route `POST /api/papers/<id>/chat` runs outside the Paper queue and writes newline-delimited JSON with a heartbeat. The library keeps one row per question card in a `chat_threads` table. Two new web modules draw the selection toolbar and the margin of question cards. The Native shell gets a Chat Settings pane and two Paper menu items.

**Tech Stack:** Python 3.14 standard library (`http.server`, `urllib`, `sqlite3`), the `anthropic` SDK already pinned, plain ES modules in `app/static/`, AppKit in `app/macos/`.

**Spec:** `docs/highlights-notes-chat-plan-2026-10-18.md` (sections 4, 5.1 to 5.3, 5.7, 6.1, 7 Release 1, and 9). The P3 and P4 results are in its section 7 and in `docs/chat-spikes-2026-10-18.md` on the branch `claude/modest-almeida-e32d2f`.

## Global Constraints

- Read `CODING_STANDARDS.md` and invoke the `ponytail` skill before code. Run `uvx ruff check .` before each Python commit.
- Tests are component end-to-end tests under `tests/` (untracked by the user's choice). Run them with `.venv/bin/python -m unittest discover -s tests`. Write no unit tests of private helpers.
- Commit messages: the change only, no AI attribution line (user rule).
- Never write a provider key to disk, a log, or a response. The Chat key lives in Keychain under the account `chat:<endpoint>`; the Overview key stays under `<endpoint>`.
- Never name a table `messages` or `passage_search`: library startup drops both (`papers/library.py:48-49`).
- UI rules from 2026-10-14: window minimum 700 pt, no phone layouts, selection in the system accent, green only for content accents, a calm toolbar, no controls fixed to the bottom of the window.
- Copy is ASD-STE100 Simplified Technical English and uses the glossary terms of `CONTEXT.md`.
- Release 1 has no Highlights. The selection toolbar has **Ask** and **Explain** only. Colours, Note, and Highlight storage come in Release 2.

## Decisions this plan takes (smallest version that meets the spec)

- One row per question card: `chat_threads(id, paper, value)`. A card's turns are inside `value`. The spec's `chat_turns` name becomes `chat_threads`, because the card, not the turn, is the unit that the reader keeps, discards, and restores.
- No Evidence selection fallback. When a whole-Paper question does not fit the Chat model's Context size, the route answers 400 with "This Paper is larger than the Chat model's context size. Select a passage and ask about it." The selection path covers small models. `shortcut:` comment in `papers/chat.py`; upgrade when a reader with a small model asks.
- Token counts are estimates: 2.5 characters a token on `api.anthropic.com`, 3.5 elsewhere (P3 measured 2.2 to 2.8 and 3.5 to 4.6). `shortcut:` comment; upgrade to a token-count request if a Paper near the limit fails.
- No explicit Stop route. Stop closes the response; the heartbeat lets the server see it within about 10 s (P4, check 3).
- Undo is client-held: delete returns the removed records, and restore writes them back.

## Review Focus

1. A reader presses Stop, or closes the Paper, while a reasoning model is silent for a minute: the provider request must end within about 10 s, and the partial answer must stay marked as stopped (Task 5 test `test_closing_the_stream_stops_the_provider_request`).
2. A selection that crosses an inline formula: the stored quote must be found again in its passage, so the card sits at its words (Task 6 browser check 2).
3. A reimport with a different `document_digest` while cards exist: the cards stay, and a card whose words are gone shows at its passage, else in All Notes (Task 5 test `test_reimport_keeps_chat_threads`, Task 6 browser check 6).
4. A reader changes or removes the Overview key after Copy: the Chat key must not change, and Settings must say which key each role uses (Task 2 test `test_copy_is_one_time`).
5. A window too narrow for the margin: cards fold to markers, and a marker opens its card beside it (Task 6 browser check 5).

---

### Task 1: Chat storage and glossary

**Files:**
- Modify: `papers/library.py` (schema near `:40-50`, `remove_paper` near `:238-240`, new methods beside `get_reading`)
- Modify: `app/server.py:342-347` (`GET /api/papers/<id>` adds `chat`)
- Modify: `CONTEXT.md` (new entries)
- Test: `tests/test_chat.py`

**Interfaces:**
- Produces: `Library.save_chat_thread(thread: dict) -> dict`, `Library.get_chat_thread(paper_id: str, thread_id: str) -> dict | None`, `Library.list_chat_threads(paper_id: str) -> list[dict]` (creation order), `Library.delete_chat_threads(paper_id: str, ids: list[str] | None) -> list[dict]` (`None` deletes all, returns the removed records).
- Thread record: `{id, paper, passage, href, quote, whole: bool, kept: bool, created_at: float, document_digest, turns: [Turn]}`. Turn: `{question, answer: {text, cites: [{id, href, section, text}], unknown: [str], model, host, created_at, tokens: {cached, new, output}, stopped: bool, error: str | None}}`.

- [ ] **Step 1: Write the failing tests** in `tests/test_chat.py`, with a server fixture copied from `tests/test_reading_state.py` (`make_server(root, 0, 'token')`, `call(path, body)`).
  - `test_paper_detail_includes_chat_threads`: save a thread for the sample Paper through `app.library`, then `GET /api/papers/<id>` returns `chat == [thread]`.
  - `test_remove_paper_deletes_its_chat_threads`: after `POST /api/papers/<id>/remove`, `list_chat_threads(id) == []`.
- [ ] **Step 2: Run** `.venv/bin/python -m unittest discover -s tests -p test_chat.py`. Expected: FAIL (no method `save_chat_thread`).
- [ ] **Step 3: Implement** `CREATE TABLE IF NOT EXISTS chat_threads (id TEXT PRIMARY KEY, paper TEXT NOT NULL, value TEXT NOT NULL)` and `CREATE INDEX IF NOT EXISTS chat_paper ON chat_threads(paper)` in `Library.__init__`; the four methods; one `DELETE FROM chat_threads WHERE paper=?` in `remove_paper`'s transaction; `'chat': app.library.list_chat_threads(parts[2])` in the paper detail response. Change the Remove dialog text (`app/static/index.html:90`) to name "Chat questions".
- [ ] **Step 4: Add glossary entries** to `CONTEXT.md`: **Chat** (questions and answers about one Paper, on the Chat model), **Chat model** (the provider, model, and key that Chat uses, separate from the Overview and Blog model), **Ask** (a question about the selected passage), **Explain** (Ask with the fixed question "Explain this passage."), **Question card** (one question and its follow-ups, in the margin beside the words it asks about; All Notes lists every Question card of a Paper).
- [ ] **Step 5: Run the tests.** Expected: PASS. **Commit** `Store Chat questions per Paper`.

### Task 2: The Chat connection in settings

**Files:**
- Modify: `papers/settings.py`
- Modify: `papers/library.py:15-18` (`SETTING_KEYS`), `app/server.py:34` (`DEFAULTS`), `public_settings` (`:62-70`), `/api/settings` (`:405-441`), `/api/test-connection` (`:393-404`), error redaction (`:158-164`)
- Test: `tests/test_chat.py`

**Interfaces:**
- Produces: `chat_account(endpoint: str) -> str` (`'chat:' + endpoint.rstrip('/')`), `delete_key(account: str) -> None` in `papers/settings.py`.
- Settings: `chat_endpoint` (default `''`), `chat_model` (`''`), `chat_reasoning` (`'low'`, one of `REASONING_EFFORTS`), `chat_context` (int, 2,048 to 2,000,000, default 200,000).
- `public_settings()` adds `has_chat_key: bool` and `chat_ready: bool` (`chat_model` set, and a Chat key saved or the endpoint on loopback).
- `/api/settings` accepts `chat_api_key: str`, `chat_copy: true` (copy `endpoint`, `model`, and the Overview key into the Chat fields and the Chat account, once), and `chat_delete_key: true`.
- `/api/test-connection` accepts `role: 'chat'`, then tests `chat_endpoint`, `chat_model`, and the Chat key.

- [ ] **Step 1: Write the failing tests**, with `patch('app.server.get_key')`, `patch('app.server.set_key')`, and `patch('app.server.delete_key')` as in `tests/test_paper_search_settings.py:22-24`:
  - `test_chat_key_has_its_own_keychain_account`: saving `chat_endpoint='https://api.anthropic.com/v1'` and `chat_api_key='chat-secret'` calls `set_key('chat:https://api.anthropic.com/v1', 'chat-secret')` and never `set_key('https://api.anthropic.com/v1', ...)`.
  - `test_copy_is_one_time`: with an Overview key `ov-secret`, `chat_copy: true` writes `chat:<endpoint>` with `ov-secret` and copies the endpoint and model. A later Overview key change leaves the Chat account alone.
  - `test_local_endpoint_is_ready_without_a_key`: `chat_endpoint='http://127.0.0.1:11434/v1'`, `chat_model='qwen'`, no key, gives `chat_ready: true`.
  - `test_chat_settings_are_validated`: `chat_context=100` and `chat_reasoning='max'` answer 400.
  - `test_test_connection_uses_the_chat_role`: `role: 'chat'` reads `get_key('chat:<chat_endpoint>')`.
- [ ] **Step 2: Run.** Expected: FAIL.
- [ ] **Step 3: Implement.** `delete_key` uses the declared `SecKeychainItemDelete` (`papers/settings.py:19-22`). The redaction at `app/server.py:158-164` also replaces the Chat key. Keep the `Provider(...)` endpoint check (`:433`) for `chat_endpoint` too.
- [ ] **Step 4: Run the tests.** Expected: PASS. **Commit** `Add the Chat model connection with its own Keychain account`.

### Task 3: `Provider.stream()`

**Files:**
- Modify: `papers/ai.py`
- Test: `tests/test_chat.py` (a loopback OpenAI-compatible stub) and the scripted Anthropic transport pattern of `tests/test_anthropic_provider.py`

**Interfaces:**
- Produces: `Provider.stream(self, system: list[str], messages: list[dict], on_text: Callable[[str], None], *, reasoning: str | None = 'low', max_tokens: int = 8000, stop: Callable[[], bool] = lambda: False) -> dict` returning `{'text': str, 'usage': {'cached': int, 'new': int, 'output': int}, 'stopped': bool}`.
- `system[-1]` is the Paper block. On Anthropic it carries `cache_control: {'type': 'ephemeral', 'ttl': '1h'}`; the other blocks have none. On the compatible path the system blocks join into one system message, and the request sends `stream: true` and `stream_options: {'include_usage': true}`.

- [ ] **Step 1: Write the failing tests.**
  - `test_compatible_stream_sends_text_in_order`: a stub `http.server` on `127.0.0.1` answers SSE `data:` chunks with a `: comment` line and `data: [DONE]`. `on_text` receives the chunks in order, and the result has the joined text and usage.
  - `test_stream_never_passes_on_the_key`: the stub echoes the key split across two chunks. Neither `on_text` nor the result contains the key.
  - `test_stop_closes_the_request`: `stop` turns true after the first chunk. The stub sees the connection close, and the result has `stopped: True`.
  - `test_loopback_without_key_sends_no_authorization`: with key `''`, the stub sees no `Authorization` header.
  - `test_rate_limit_retries_once`: the stub answers 429 with `Retry-After: 1`, then 200. The result is the second answer. Two 429 answers raise `ProviderError` that names HTTP 429.
  - `test_anthropic_stream_caches_the_paper_for_an_hour`: through a scripted `httpx2` transport, the request body's last system block has `ttl: '1h'`, and `text_delta` events reach `on_text`.
- [ ] **Step 2: Run.** Expected: FAIL.
- [ ] **Step 3: Implement** with `urllib` on the compatible path (read lines, skip lines that start with `:`, stop at `[DONE]`, raise on a chunk with `finish_reason: 'error'`) and `self.anthropic.messages.stream(...)` text events on Anthropic. Hold back the last `len(key) - 1` characters of the buffer before `on_text`, so a key split across chunks never leaves. Send `Authorization` only when the key is not empty. `complete()` stays as it is.
- [ ] **Step 4: Run the tests and `tests/test_anthropic_provider.py`.** Expected: PASS. **Commit** `Stream provider answers for Chat`.

### Task 4: The Chat request and its citations

**Files:**
- Create: `papers/chat.py`
- Modify: `papers/passages.py`
- Test: `tests/test_chat.py`, and `tests/test_blog_workflow.py` must still pass

**Interfaces:**
- Consumes: `evidence_document(document)` (`papers/reading.py:18`), `evidence_text(evidence)` (`papers/coordinator.py:445`).
- Produces: `chat_citations(items: list[dict], text: str) -> tuple[list[dict], list[str]]` in `papers/passages.py` (cited passages in order, unknown IDs; never raises). `papers/chat.py`: `INSTRUCTIONS: str`, `request(paper: dict, thread: dict, question: str, notes: list[str], context_tokens: int, host: str) -> tuple[list[str], list[dict]]` (raises `ValueError` with the exact message of "Decisions" when a whole-Paper question does not fit), `answer(provider, paper: dict, thread: dict, question: str, settings: dict, on_text, stop) -> dict` (a Turn).

- [ ] **Step 1: Write the failing tests** (through the route of Task 5 where possible; these two run `chat.answer` with a fake provider whose `stream` calls `on_text`):
  - `test_unknown_citations_are_marked_not_fatal`: an answer citing `[p00007]` and `[p99999]` gives `cites` with `p00007` and `unknown == ['p99999']`.
  - `test_ordinary_p_numbers_are_not_citations`: the text "p50 latency rose [p00007]" gives `unknown == []`. Also: `cited_in` (the Blog) no longer raises on "p50" outside brackets.
  - `test_selection_goes_last`: with a quote, the last message ends with the quote inside `<selection>` and then the question; the Paper is in `system[-1]` and has no bibliography passage.
  - `test_whole_paper_too_large_says_select`: `context_tokens=2048` and no quote raise `ValueError` with the exact message.
  - `test_small_context_uses_the_selection_path`: `context_tokens=4096` with a quote sends only the quoted passage, its section, and its neighbours, within 2,000 tokens.
- [ ] **Step 2: Run.** Expected: FAIL.
- [ ] **Step 3: Implement.** `INSTRUCTIONS` says, in STE: answer only from the Paper; cite each passage you use as `[p00017]`; cite each ID on its own and never write a range; say "The Paper does not say" when it does not. `notes` go after the Paper as a second user block, so the cache holds. The turn budget keeps the last turns that fit `context_tokens` minus the Paper and 8,000 output tokens. `chat_citations` checks only IDs inside `CITATION` brackets; change `cited_in`'s unknown-ID check to the same rule.
- [ ] **Step 4: Run the tests and the Blog tests.** Expected: PASS. **Commit** `Build Chat requests with the Paper cached and the selection last`.

### Task 5: The streaming Chat route

**Files:**
- Modify: `app/server.py` (`Application.__init__`, `remove_paper`, `prepare_update`, `dispatch`)
- Test: `tests/test_chat.py`, with the loopback stub of Task 3 as the Chat endpoint

**Interfaces:**
- Consumes: Tasks 1 to 4.
- Produces, for Task 6:
  - `POST /api/papers/<id>/chat` with `{thread?: str, passage?: str, quote?: str (≤ 2,000 characters), question: str (≤ 4,000 characters)}`. Response 200, `Content-Type: application/x-ndjson`, no `Content-Length`, body ends when the connection closes. Lines: `{"type":"thread","thread":{...}}` first, then `{"type":"text","text":"..."}`, a blank line about every 5 s while the provider is silent, and last `{"type":"done","thread":{...}}` or `{"type":"error","message":"...","thread":{...}}`.
  - `POST /api/papers/<id>/chat/update` `{thread, kept: bool}` → `{thread}`.
  - `POST /api/papers/<id>/chat/delete` `{threads: [ids] | "all"}` → `{removed: [records]}`.
  - `POST /api/papers/<id>/chat/restore` `{threads: [records]}` → `{chat: [records]}` (each record's `paper` must equal `<id>`).
  - 400 with "Connect a Chat model in Settings › Chat." when `chat_ready` is false. Chat never reads the Overview key.

- [ ] **Step 1: Write the failing tests.**
  - `test_chat_streams_an_answer_and_stores_the_thread`: the lines arrive in order; the stored thread has the turn, `model`, `host`, `tokens`, and `document_digest`.
  - `test_chat_does_not_wait_behind_a_running_blog`: with a Blog job held in the Paper queue (patch `generate_blog` to wait on an event), a Chat question answers.
  - `test_closing_the_stream_stops_the_provider_request`: the stub stays silent for 30 s; the client closes after 2 s; the stub sees its connection close within 12 s; the stored turn has `stopped: true`.
  - `test_remove_paper_stops_a_running_answer`: removing the Paper during an answer ends the stream and leaves no `chat_threads` row.
  - `test_update_waits_for_no_answer`: `prepare_update` stops running answers and answers busy until they end.
  - `test_chat_never_uses_the_overview_key`: with only an Overview key, the route answers the exact 400 message, and `get_key` is never called with the Overview account.
  - `test_rejected_key_is_an_error_line`: the stub answers 401; the `error` line says "Provider rejected authentication. Check the saved key and model access." and the route does not retry.
  - `test_offline_is_an_error_line`: an unreachable Chat endpoint gives an `error` line within 3 s and keeps the question in the thread.
  - `test_delete_and_restore_threads` and `test_reimport_keeps_chat_threads` (a reimport through `Library.retain_paper` with a new digest keeps the rows).
- [ ] **Step 2: Run.** Expected: FAIL.
- [ ] **Step 3: Implement** a `respond_stream` path beside `respond()` (`app/server.py:283-310`) that sends the headers with the same security headers and no `Content-Length`. Run `chat.answer` in a worker thread that puts text into a `queue.Queue`; the handler writes each item, or a blank line after 5 s of nothing. A write error sets the thread's stop event. `Application.chats: dict[str, tuple[str, threading.Event]]` (thread id → paper id, stop event) under `self.lock`. Read the Paper from the library row (`get_paper`), not from files.
- [ ] **Step 4: Run all tests.** Expected: PASS. **Commit** `Stream Chat answers outside the Paper queue`.

### Task 6: Selection toolbar and question cards in the margin

**Files:**
- Create: `app/static/selection.js` (the toolbar and the selection-to-text map), `app/static/margin.js` (layout, cards, connector, All Notes, the stream client)
- Modify: `app/static/reader.js` (dispatch `lx-chapter` after `frame.onload`; export `goPassage(href)`, the non-Split branch of `openPassage`, `:643-654`), `app/static/app.js` (`readerActions()`: `ask-paper` "Ask About the Paper…" and `all-notes` "All Notes"), `app/static/app.css` (a "Margin" section with Question colour tokens for Light, Sepia, and Dark), `app/static/shell.js` (`editing` in the Chrome state)
- Reference: the prototype on branch `notes-chat-prototype` (`app/static/prototype.js`, `prototype-b.js`) for the layout, connector, and fold rules. Rewrite, do not copy.

**Interfaces:**
- Consumes: Task 5 routes; `GET /api/papers/<id>` `chat`.
- Produces: `mountMargin()` and `unmountMargin()` from `margin.js`, called by `reader.js` when the Paper view shows or hides. `selection.js` exports `selectionToolbar({ask, explain})` and `rangeText(passageElement, range) -> string`.

- [ ] **Step 1: Start the dev server with a stub Chat endpoint.** Write `tests/chat_stub.py` (a loopback OpenAI-compatible SSE server with canned cited answers and a `--silent` mode). Point `chat_endpoint` at it in a scratch library.
- [ ] **Step 2: Build** the toolbar (Ask, Explain; keyboard reachable after a Shift selection), the margin layout (text at least 520 px, cards up to 300 px, fold to markers below 210 px), the question card (dashed mark on its words, streaming answer with Stop, tokens, model, date, follow-up input, Keep as Note, Discard with undo), the moving dotted connector with Reduce Motion, All Notes, Ask About the Paper anchored to the first sentence of the top passage, and the provider host on each card ("Asks Anthropic (api.anthropic.com)"). With no Chat model, Ask opens a card with **Use my Overview connection** (one `chat_copy` call) and **Set up Chat…** (`openSettings('chat')`), never a silent fallback. A streaming answer is in an `aria-live="polite"` region, and every card control is reachable by Tab. A citation in a card scrolls the Paper with `goPassage` and flashes the passage; Chat stays open.
- [ ] **Step 3: Check in the browser pane**, with `read_console_messages` clean:
  1. Ask on a plain selection: the card shows at its words, the answer streams, citations open their passages.
  2. Ask on a selection across an inline formula: the card finds its words.
  3. Explain sends with no typing.
  4. Stop during a `--silent` answer: the card shows "Stopped", and the stub sees the close.
  5. A 1,000 px window: markers; a marker opens its card.
  6. Reimport the Paper with a changed digest (scratch library): cards stay; a card whose words are gone shows at its passage.
  7. Offline (stub stopped): the card keeps the question and shows the offline message.
- [ ] **Step 4: Commit** `Ask about a passage and keep the answer in the margin`.

### Task 7: The Chat Settings pane

**Files:**
- Modify: `app/static/index.html` (a `section.pane[data-pane="chat"]` after the AI pane, and its pane button), `app/static/app.js` (`PANES` at `:571` adds `chat`; `providerControls(setup)` at `:582` becomes `providerControls(prefix)` with `''`, `'setup-'`, and `'chat-'`; `fillSettings`, `settingsPayload`, `showKeyStatus`, `testConnection`), `app/macos/SettingsWindow.swift:7-9` (pane `chat`, label "Chat", symbol `bubble.left.and.bubble.right`)
- Test: `tests/test_chat.py` covers the server side (Task 2); check the pane in the browser and with `tools/native_shot.py`

- [ ] **Step 1: Build** the pane: Provider (the five presets, **Local** with `http://127.0.0.1:11434/v1`, Custom), Model, API key (hidden for Local), **Copy from Overview and Blog**, Test Connection, Reasoning effort (default Low), Context size, a key line that names which key each role uses, and the help text: "Chat sends the Paper's text and your question to <host>. Highlights and Notes stay on this Mac." The AI pane help changes to "Overviews and Blogs run for minutes. A strong model gives better results here."
- [ ] **Step 2: Check** in the browser dialog and in the Settings window (a `tools/native_shot.py` step that opens the Chat pane): each field saves on commit, Copy fills the fields once, Test Connection reports the Chat role.
- [ ] **Step 3: Commit** `Add the Chat pane to Settings`.

### Task 8: Native shell

**Files:**
- Modify: `app/macos/Menus.swift` (`fill()` at `:100` maps `ask-paper` to ⇧⌘A and `all-notes` to ⌥⌘N; `validateMenuItem` at `:143-144` gives up ⌘⌫ when the Chrome state says `editing`), `app/macos/Shell.swift:6-47` (decode `editing`), `app/macos/Automation.swift` (identifiers for the new items)

- [ ] **Step 1: Build** the two Paper menu items (they come through `actions.more`) and the `editing` flag that `shell.js` sets while a card input or a Settings field has focus.
- [ ] **Step 2: Check** with `tools/native_shot.py`: the Paper menu shows both items with their keys; ⌘⌫ in a card's follow-up field deletes text and does not open the Remove dialog.
- [ ] **Step 3: Commit** `Add Chat commands to the Paper menu`.

### Task 9: Release 1 verification

- [ ] **Step 1: Run** `uvx ruff check .` and `.venv/bin/python -m unittest discover -s tests`. Expected: all pass.
- [ ] **Step 2: Native screenshots** at 700, 1000, 1200, and 1440 pt with the sidebar shown and hidden (V4): no overlap, the text column never under 45 characters. In the same run, ⌘F finds a word that is only in an answer and a word that is only in the Paper (criterion 15).
- [ ] **Step 3: Live run (V2), only with the user's yes and key:** 5 Papers, 10 questions each, through direct Anthropic on Haiku 5.5, with pauses over 5 minutes, measured in the app end to end. Pass: median first words at most 3 s, at least 95% of citations valid, model and date on each answer. The user grades a sample for criterion 6.
- [ ] **Step 4: Report** the results in the plan's section 7 and ask the user about the merge into `main` (`--no-ff`).
