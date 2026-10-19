# Release 1.1: Chat Follow-Ups Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the eight Chat items that Release 1 did not build, Clear Chat included.

**Architecture:** Part A changes the provider stream (`papers/ai.py`), the Chat request (`papers/chat.py`), the `ask` path in `app/server.py`, and the Question card client. It adds one NDJSON line type and one 409 answer, and it does not change the stored record. Part B builds on Release 2: the added quotes go on the Turn, and Clear Chat gets its own route on the `highlights` table.

**Tech Stack:** Python 3.14 standard library, the `anthropic` SDK 1.12 (installed), plain ES modules in `app/static/`, AppKit in `app/macos/`.

**Spec:** `docs/highlights-notes-chat-plan-2026-10-18.md`, criteria 9 and 11, sections 5.2, 5.3, 5.7, and 7 (C4, C5, C7, U3). The Release 1 plan is `docs/superpowers/plans/2026-10-18-chat-release-1.md`. The Release 2 plan is `docs/superpowers/plans/2026-10-19-notes-release-2.md` on the branch `notes-release-2`. The Release 1 final review lists these items as "Set aside" 2 to 6 and 8 to 10 (`/Users/silver/Developer/LocalXiv/.scratch/chat-release-1-ledger/final-review.md`).

## Two parts

| Item | Part | Why |
| --- | --- | --- |
| Retry on a stopped answer | A | The same route and body. Only the history rule in `chat.request` changes |
| The rate-limit line | A | One new NDJSON line type. No record change |
| The OpenRouter cache breakpoint | A | `papers/ai.py` only |
| A warning before a prompt over 100,000 tokens | A | One 409 answer and one body field |
| The "from an earlier version" mark | A | Client only. Each Turn already stores the text of each cited passage |
| Copy as Markdown | A | Client only |
| Several quotes in one question | B | It uses Release 2's toolbar items (its Task 8), its waiting state (Task 9, Place Again), and its Ask body (Task 1) |
| Clear Chat with undo | B | Its route works on Release 2's `highlights` table, which has no "all" delete (Release 2 Task 1) |

Part A continues on the branch that holds this plan, from `main` at `54f22df`. It merges before Release 2 starts its code. Part B starts on a new branch from `main` after Release 2 merges. Cost to Release 2: its Task 7 moves `margin.js:353-602` into `chat.js`, and Part A adds code in that region, so its line references go stale. Task 7 Step 3 updates them.

## Global Constraints

- Read `CODING_STANDARDS.md` and follow the `ponytail` rules. Run `uvx ruff check .` before each Python commit.
- Set up the worktree as the memory note says: copy `tests/` and `papers/html-snapshot/` from the main checkout, and symlink `.venv`. Run tests with `.venv/bin/python -m unittest discover -s tests`.
- Tests are component end-to-end tests through the server routes, in `tests/test_chat.py`. Release 1.1 adds six tests in total, each named in its task. Change an existing test only where a task names it. The earlier-version mark and Copy as Markdown are browser or `tools/native_shot.py` checks, not tests. A hook blocks writes into the main checkout, so new tests stay in the worktree copy. After each merge, put the changed test files in the shared notes folder `/Users/silver/Library/Application Support/Claude/side-session-notes/local_06319e3f-259a-4b36-aa0c-ba4ddffd1a57/` for the parent session to copy.
- Commit messages: the change only, with no AI attribution line (user rule).
- A provider key never goes to disk, a log, a response, or an NDJSON line.
- Copy is ASD-STE100 and uses the glossary terms of `CONTEXT.md`. The copy in this plan is final.
- Keep chat text out of the Chrome state (`app/static/shell.js:28-35`). Booleans only.
- Merge with `git merge --no-ff <branch>` in the main checkout (`/Users/silver/Developer/LocalXiv`, on `main`). Then delete the merged branch and prune its worktree.
- `docs/cleanup.md` (main checkout only) stays as it is. The user said "Not now" on 2026-10-19.

## Decisions this plan takes

- **Retry** asks the same question again as a new turn. The stopped or failed turn stays on the card (criterion 9). Only finished answers go to the model as history: `chat.request` leaves out a turn whose answer stopped or has an error, as it leaves out a turn with no text today.
- **A question on a card whose answer still runs** stops that answer, waits up to 10 s for it to save, and then goes. The client sends a question on a card only after its own stream ended, so such an answer is one that the reader stopped before the heartbeat let the server see the close.
- **Rate limit:** one retry after HTTP 429, and after 529 on Anthropic. The wait is the `Retry-After` value in whole seconds, from 1 to 60, else 10 s. The Anthropic Chat stream sets `max_retries=0`, so the SDK no longer retries silently. Other failures then fail at once, and the card shows Retry.
- **The cause** names a Blog or an Overview only when a job of that kind runs or waits, and the Overview connection has the same host and the same key as Chat (one shared rate limit).
- **OpenRouter:** the breakpoint goes only to the host `openrouter.ai` with a model ID that starts with `anthropic/`. Other compatible servers can refuse a system message made of parts.
- **The warning** starts when the estimate of `chat.request` is over `LARGE_PROMPT = 88_000` tokens. 88,000 is 100,000 × 2.2 / 2.5: P3 measured 2.2 characters a token on Haiku 5.5, and `_tokens` counts 2.5. It applies to every Chat model, once per Paper in each page session, because follow-ups send the same prefix. The copy names the Haiku 5.5 factor (5 times, from the Claude API pricing: $0.10 and $0.50 per million tokens up to 100K, $0.50 and $2.50 above). It does not state what cache reads cost.
- **Copy as Markdown** numbers the citations across the whole card and adds a Sources list, so the copy keeps its evidence. Release 2's Notes export removes citations; this copy is one card.
- **Several quotes:** `turn.quotes` holds the added quotes only, at most 4 for each question, each of 1 to 2,000 characters. The card's own words stay its anchor. Added quotes get no paint and no search after a reimport.
- **Clear Chat** deletes each open Question card (`kept: false`) and removes the turns of each kept record. Every Highlight, Note, and colour stays. This goes past "delete the records with turns": a Note with answers keeps its Note. It has no confirm dialog. ⌘Z undoes it, as for Discard.

## Review Focus

1. Stop, then Retry within 5 s, on a provider that is silent: the retry goes and does not answer "Wait for the answer…". Pinned in Task 1's test.
2. Stop during a rate-limit wait: the provider gets no second request, and the turn is stopped. Pinned in Task 2's test.
3. A citation after a reimport, where its passage text changed or its passage is gone: the card shows the stored text marked "from an earlier version", never the other text at that ID. Pinned in Task 5's browser check.
4. Clear Chat while an answer streams, then a Note edit, then ⌘Z: the answer stops and is not saved, each card comes back once, and the Note keeps its edit. Pinned in Task 9's test and browser check.
5. Copy as Markdown in the Native shell: the clipboard gets the text after a real click. Pinned in Task 6's native check.

---

## Part A

### Task 1: Retry on a stopped answer

**Files:** Modify `papers/chat.py` (history filter `:99-100`), `app/server.py` (`ask`, the running-card check `:184-187`), `app/static/margin.js` (`fillTurn` `:392-403`, `drawTurns` `:360-370`). Test: `tests/test_chat.py`.

**Interfaces:**
- Produces: a **Retry** button (title "Ask this question again.") on the last turn of a card when its answer stopped or has an error and no answer runs. It calls `send(card, turn.question)`. Task 4 adds `large` to the body, and Task 8 adds the turn's quotes.

- [ ] **Step 1: Write the failing test** `test_a_retry_after_stop_goes_and_sends_no_stopped_answer` in `ChatRouteTest`: a stub with two replies, `['Part of ', 30]` and `CITED`. Ask on a new card, read the thread line and the first text line, and close the response. At once, ask on the same thread with the same question. It answers 200, and its last line is `done`. The stored card has two turns: the first has `stopped: True` and the text `'Part of '`. The stub's second request has no assistant message.
- [ ] **Step 2: Run** `.venv/bin/python -m unittest tests.test_chat.ChatRouteTest.test_a_retry_after_stop_goes_and_sends_no_stopped_answer`. Expected: FAIL with "Wait for the answer to this question to finish, then ask again."
- [ ] **Step 3: Implement.** The history filter keeps a turn only when its answer has text, is not stopped, and has no error. In `ask`, before the locked block, set the stop event of a running answer on the same card, then poll every 0.05 s for up to 10 s until `self.chats` no longer holds that entry. After 10 s, keep today's message. Add the Retry button.
- [ ] **Step 4: Run all tests, and check in the browser** with `tests/chat_stub.py --silent`: Stop, then Retry, shows the stopped turn and a new answer. Stop the stub: the offline turn shows Retry, and after the stub starts again, Retry answers. **Commit** `Retry a stopped or failed Chat answer`.

### Task 2: The rate-limit line

**Files:** Modify `papers/ai.py` (`_status_error` `:83-90`, `stream` `:175-206`, `_stream_compatible` `:218-232`, `_stream_anthropic` `:276-291`), `papers/chat.py` (`answer`), `app/server.py` (`ask`'s `work`), `app/static/margin.js` (`receive` `:516-534`). Test: `tests/test_chat.py`. Change `test_rate_limit_retries_once` (`:300-311`) to the new error text. Change `scripted` in `tests/test_anthropic_provider.py:42-55`: an optional third item for each response (its headers), and a `max_retries` keyword (default 0).

**Interfaces:**
- `Provider.stream(..., on_wait=lambda seconds: None)`: called once, with the wait in seconds, before the one retry. The wait reads `stop()` every 0.25 s. A stop returns `stopped: True` and sends no second request.
- `chat.answer(..., on_wait=lambda seconds: None)` passes it on.
- NDJSON line `{"type": "wait", "seconds": 20, "message": "..."}`, with one of: `The provider is busy with your Blog. Chat will retry in 20 s.`, `The provider is busy with your Overview. Chat will retry in 20 s.`, `The provider is busy. Chat will retry in 20 s.` The client shows the message in place of "Reading the Paper…".
- `_status_error` for HTTP 429 and 529: `The provider is still busy (HTTP status 429). Ask again in a minute.`

- [ ] **Step 1: Write the failing test** `test_a_rate_limit_says_its_cause_and_retries_once`:
  1. Overview and Chat on the same stub URL, with the same key. A Blog job is held as in `test_chat_does_not_wait_behind_a_running_blog`. The stub answers `{'status': 429, 'headers': {'Retry-After': '1'}}`, then `CITED`. The lines are `thread`, `wait` with `seconds: 1` and the Blog message, the text lines, and `done`.
  2. Chat on `api.anthropic.com`, through `patch('app.server.Provider', <a subclass that calls scripted(self, ..., max_retries=2)>)`: a 429 with `retry-after: 1`, then `stream_body('It weighs the words [p00001].')`. One `wait` line with "The provider is busy. Chat will retry in 1 s.", then `done`, and the transport saw exactly 2 requests.
  3. Two 429 answers on the stub: the last line is `error` with the still-busy message.
  4. `Retry-After: 30`: read up to the `wait` line and close. After 7 s, the stub has 1 request, and the stored turn has `stopped: True`.
- [ ] **Step 2: Run** it. Expected: FAIL (no `wait` line).
- [ ] **Step 3: Implement.** One private wait helper for both transports. On Anthropic, open the stream with `self.anthropic.with_options(max_retries=0)`, and read the header from `exc.response.headers`. In `work`, `on_wait` puts the line. The cause compares `urlsplit(settings['endpoint']).hostname` with the Chat host and `get_key(settings['endpoint'])` with the Chat key, and reads the kinds of `self.library.list_jobs(recent=0)` and of the first job of each `self.queues` entry.
- [ ] **Step 4: Run all tests.** Expected: PASS. **Commit** `Say why Chat waits after a rate limit`.

### Task 3: The OpenRouter cache breakpoint

**Files:** Modify `papers/ai.py` (`_stream_compatible` `:209-211`). Test: `tests/test_chat.py`.

**Interfaces:** On the host `openrouter.ai` with a model ID that starts with `anthropic/`, the system message `content` is a list with one `{'type': 'text', 'text': block}` for each system block. The last part also has `'cache_control': {'type': 'ephemeral', 'ttl': '1h'}`. Every other host and model keeps one joined string.

- [ ] **Step 1: Write the failing test** `test_openrouter_caches_the_paper_for_anthropic_models`: `chat_endpoint='https://openrouter.ai/api/v1'`, `chat_model='anthropic/claude-haiku-5.5'`, a Chat key from the patched `get_key`, and `papers.ai.urllib.request.build_opener` patched so that each opener sends its request to the stub with the same path after the base URL, the same data, and the same headers. The stub's first message `content` is the two parts above. `reasoning` is `{'effort': 'low'}`. With `chat_model='openai/gpt-5'`, `content` is a string.
- [ ] **Step 2: Run** it. Expected: FAIL (`content` is a string).
- [ ] **Step 3: Implement.** Run all tests. **Commit** `Cache the Paper for Anthropic models through OpenRouter`.

### Task 4: The warning before a prompt over 100,000 tokens

**Files:** Modify `papers/chat.py` (`request`), `app/server.py` (`ask`, and the `/chat` branch of `dispatch` `:670-686`), `app/static/margin.js` (`send` `:484-514`, `drawCompose` `:417-445`). Test: `tests/test_chat.py`.

**Interfaces:**
- `chat.request(...)` adds `info['tokens']`, the estimate of the whole prompt without the output reserve.
- `chat.LARGE_PROMPT = 88_000` (read at call time, so a test can patch it), and `class LargePrompt(Exception)`. `ask` raises `LargePrompt(message)` when `info['tokens'] > chat.LARGE_PROMPT` and `body.get('large') is not True`. The route answers 409 `{"error": message, "confirm": "large"}`.
- The message, with `n = round(tokens, -3)`: `This question sends about {n:,} tokens. Some models charge more for each token when a prompt has more than 100,000 tokens. Claude Haiku 5.5 charges 5 times as much.`
- The client: on that 409, the question stays in the field, and the error line shows the message and an **Ask Anyway** button. Ask Anyway adds the Paper to a page-session set and sends the field's question again. Each later body for that Paper, Retry included, has `large: true`.

- [ ] **Step 1: Write the failing test** `test_a_prompt_over_100000_tokens_waits_for_a_confirmation`: with `patch('papers.chat.LARGE_PROMPT', 1000)`, a whole-Paper question answers 409 with `confirm == 'large'` and the exact message. The stub got no request, and the library has no new card. The same body with `large: True` ends in `done`.
- [ ] **Step 2: Run** it. Expected: FAIL (200).
- [ ] **Step 3: Implement.** Run all tests. **Check in the browser** with `LARGE_PROMPT` set low in a scratch run: Ask Anyway sends, and a follow-up sends with no second warning. **Commit** `Warn before a Chat prompt over 100,000 tokens`.

### Task 5: The "from an earlier version" mark

**Files:** Modify `app/static/render.js` (`renderProse` `:142-185`), `app/static/margin.js` (`prose` `:405`), `app/static/reader.js` (export `openPreview` `:503`), `app/static/app.css` (beside `.prose .cn .unverified` `:377`).

**Interfaces:**
- `earlier(source) -> boolean` in `margin.js`: true when `detail.paper.passages` has no passage with `source.id`, or that passage's `text` differs from `source.text`. `prose()` adds `earlier: true` to such references. A streaming answer cites current passages, so it never gets the mark.
- `renderProse` draws a reference with `earlier: true` as a numbered link with the class `citation is-earlier`, the `aria-label` "Source {n}, from an earlier version of the Paper", and the title "From an earlier version of the Paper". It is a link also when its chapter is gone. A click calls `io.openEarlier(mark, source)`.
- `openEarlier` calls `openPreview(mark, '{section} · From an earlier version', <the stored text in a p.clamp>, actions, note)`. When the chapter of `source.href` exists, `actions` is `[['Open in Paper', 'doc', () => goPassage(source.href), true]]` and the note is "The Paper has other text at this place now." Else `actions` is empty and the note is "This version of the Paper does not have this passage."
- CSS: the colour of `.unverified` (`var(--label-3)`) and a dotted underline.

- [ ] **Step 1: Build** it.
- [ ] **Step 2: Make a reimport in a scratch library:** change the words of one cited passage in the row's passage text and in the chapter XHTML, delete a second cited passage from the row, and set the row's `document_digest` with `papers.library.document_digest`.
- [ ] **Step 3: Check in the browser**, with `read_console_messages` clean: the first citation has the mark, and a click shows the stored text with Open in Paper. The second has the mark and no action. All Notes shows the same marks. A citation of an unchanged passage opens the Paper as before. **Commit** `Mark Chat citations from an earlier version of the Paper`.

### Task 6: Copy as Markdown

**Files:** Modify `app/static/margin.js` (`drawActions` `:469-479`), `app/static/app.js` (export `copy` `:324`).

**Interfaces:** A **Copy as Markdown** button (title "Copy this question and its answers as Markdown.") on a card with an answer text. The click builds the text from `card.record` in the same task, with no await, and calls `copy(text, 'Question card')`. The format:

```
[<Paper title>](https://arxiv.org/abs/<arXiv ID>) · <section of the card's passage>
> <quote>                       (a whole-Paper card: *Question about the Paper*)

**<question>**

<answer, each cited ID as [n] and an unknown ID as [?]>
*Stopped.*                       (only when stopped)
*<error>*                        (only when set)

Sources
[n] <section>: "<first 200 characters of the stored text>…" (from an earlier version)
```

The title is plain text when the Paper has no arXiv ID. Each turn follows the first in the same form. `n` counts in first-citation order across the card. "…" shows only when the text is longer than 200 characters, and "(from an earlier version)" only when Task 5's `earlier()` is true.

- [ ] **Step 1: Build** it.
- [ ] **Step 2: Check in the browser** (the notice "Question card copied."), and with `tools/native_shot.py`: a `js` step logs the button's rectangle, a `click` step clicks its centre, and `pbpaste` afterward gives the text in the format above. **Commit** `Copy a Question card as Markdown`.

### Task 7: Part A verification and merge

- [ ] **Step 1: Run** `uvx ruff check .` and all tests. Expected: all pass.
- [ ] **Step 2: Check in the browser** that Release 1's checks 1, 3, 4, and 7 still pass (Ask, Explain, Stop, Offline; Release 1 plan, Task 6 Step 3).
- [ ] **Step 3: Live check, only with the user's yes and an OpenRouter key:** two questions on one Paper with an `anthropic/` model. The second answer's tokens line shows cached tokens.
- [ ] **Step 4: Merge.** In the spec's section 7, mark what Part A built under C4, C5, C7, and U3, and commit. Merge into `main` with `--no-ff`. Put the changed test files in the shared notes folder.
- [ ] **Step 5: Update the Release 2 plan**, only when the worktree `.worktrees/notes-release-2` is clean and no session works there: merge `main` into it with `--no-ff`, correct the plan's line references into `margin.js`, `app/server.py`, `papers/ai.py`, `papers/chat.py`, and `tests/test_chat.py`, and commit `Update the Release 2 plan's line references after Release 1.1 Part A`.

## Part B (after Release 2 merges)

Before Task 8, read Release 2's merged code. The names below come from its plan, and its code wins where they differ.

### Task 8: Several quotes in one question

**Files:** Modify `papers/chat.py` (`INSTRUCTIONS`, `request`, `answer`), `app/server.py` (`ask`), `app/static/chat.js` (compose, turns, `send`, Retry, Copy as Markdown), the module that holds Release 2's waiting state, `app/static/app.css`. Test: `tests/test_chat.py`.

**Interfaces:**
- Consumes: Release 2's `selectionToolbar(items)` and `anchor(range)` (its Task 8), the waiting state of Place Again (its Task 9), the Ask body `{anchor, question}` (its Task 1), and `chat.answer(..., notes)` (its Task 6).
- The Ask body adds `quotes: [{passage: str, quote: str}]`, with 0 to 4 items, each `quote` of 1 to 2,000 characters, and `passage` an ID of the Paper or `''`. Else 400 `Add at most 4 quotes of at most 2,000 characters each.` The server adds each `href`, and the Turn stores `quotes: [{passage, href, quote}]` (`[]` when there are none).
- `chat.request(..., quotes=())` and `chat.answer(..., quotes=())`: the last message has the card's selection, then one `<selection passage="…">` block for each added quote, then the question. A history turn sends its own quotes before its question. On the excerpt path, `info['passages']` also holds the passage of each added quote, so its citations are checked.
- The last line of `INSTRUCTIONS` becomes `Each <selection> block is text that the reader selected. Answer about that text.`
- The client: an **Add Quote** button (title "Add more words from the Paper to the next question.") in the compose row, hidden at 4 quotes. It starts the waiting state. The next selection's toolbar shows **Add to Question** and **Cancel**, and Escape cancels. While the card waits, a pointerdown in the Paper keeps the card active and its draft. The added quotes show above the field, each with a **Remove** button (`aria-label` "Remove this quote"). Send takes them with the question and empties the list. A turn shows its quotes above its question. Retry sends the turn's quotes again. Copy as Markdown writes them as `>` lines above the question. A draft with added quotes stays, as a draft with typed text does.

- [ ] **Step 1: Write the failing test** `test_several_quotes_go_with_one_question`: a new card with two added quotes. The stub's last message holds three `<selection` blocks in order and then the question. The stored turn has `quotes` with each `href`. A follow-up's history has the two quotes before the first question. Five quotes, or one quote of 2,001 characters, answer 400 with the exact message.
- [ ] **Step 2: Run** it. Expected: FAIL.
- [ ] **Step 3: Implement**, and check in the browser: add a quote from another section and send, Remove a quote, Escape during the wait, and Discard then ⌘Z keeps each turn's quotes. **Commit** `Ask one question about several quotes`.

### Task 9: Clear Chat with undo

**Files:** Modify `papers/library.py` (`clear_chat`), `app/server.py` (the route), `app/static/app.js` (`readerActions().more` and the `action` handler `:371-384`), `app/static/chat.js` or `margin.js` (`clearChat`, the undo `restore`), `app/macos/Menus.swift` (`firstPaperActions`). Test: `tests/test_chat.py`.

**Interfaces:**
- Consumes: Release 2's `list_highlights`, `/highlights/restore`, `drop_chats`, and the undo entry `{paper, records, question}` (its Tasks 1 and 8).
- `Library.clear_chat(paper_id) -> list[dict]`: in one transaction, it deletes each record with `kept` false, and writes each other record that has turns with `turns: []`. It returns each deleted or changed record as it was.
- `POST /api/papers/<id>/chat/clear` with `{}` → `{removed: [records]}`. Under `app.lock`, it calls `drop_chats(paper_id)` first.
- The Paper menu item `clear-chat` "Clear Chat", after All Notes, enabled when `view === 'paper' && paper.format !== 'pdf'`, with no key. `firstPaperActions` gets `.init(id: "clear-chat", label: "Clear Chat")` after `all-notes`.
- `clearChat()`: with no removed records, the notice "This Paper has no Chat questions." Else it drops the open cards, empties the turns of the kept records, pushes `{paper, records: removed, question: '', clear: true}`, and shows "Chat cleared. Press ⌘Z to undo." The undo of a `clear` entry sends `/highlights/restore`: a record that still exists keeps its current fields and gets back only its `turns`.

- [ ] **Step 1: Write the failing test** `test_clear_chat_removes_questions_and_keeps_highlights`: a Highlight with a Note and one turn, a kept Question card, an open Question card, a Highlight with no turns, and an open card whose answer streams from a silent `ChatStub`. The clear ends that stream, and `removed` holds the four records with turns, or open, as they were. The detail lists the Note and the kept card with `turns == []` and the plain Highlight unchanged, with no open card. After 2 s the silent answer is not saved. A restore of `removed` brings back every record with its turns. A second clear gives `removed == []`.
- [ ] **Step 2: Run** it. Expected: FAIL (404).
- [ ] **Step 3: Implement.** Check in the browser that a Note edited after the clear keeps its edit after ⌘Z, and with `tools/native_shot.py` that the Paper menu has Clear Chat, enabled in a Paper and disabled on Home. **Commit** `Clear the Chat of a Paper, with undo`.

### Task 10: Part B verification and merge

- [ ] **Step 1: Run** `uvx ruff check .` and all tests. Expected: all pass.
- [ ] **Step 2: Mark** in the spec's section 7 the items that Part B built (5.7 "Several quotes", the Clear Chat line under Release 1).
- [ ] **Step 3: Merge** into `main` with `--no-ff`. Put the changed test files in the shared notes folder.
