# Chat spikes P3 and P4: results

Date: 2026-10-18. Branch `claude/modest-almeida-e32d2f`, from `main` at `b41b7cf`. This is a report of two throwaway spikes. No app or `papers/` code changed.

Scope: items P3 (Chat answers) and P4 (WebKit) of Release 1 in `docs/highlights-notes-chat-plan-2026-10-18.md`, section 7. The plan file is in the main checkout and is not committed. Criteria 4 to 6 are the plan's acceptance criteria in its section 4.

The scripts, the step files, the raw runs, and the evidence are in `spikes/chat-2026-10-18/`. Section 4 tells how to run them again.

## 1. Summary

P3 passes criteria 4 to 6 on both providers. The whole Paper in a cached prefix is fast and cheap enough, so the plan's context strategy (5.2) holds.

| Criterion | Haiku 5.5, direct Anthropic | DeepSeek `deepseek-chat` | Result |
| --- | --- | --- | --- |
| 5. First words in 3 s or less (median, warm, pauses included) | 0.95 s median, 2.36 s p90, 4.22 s max (36 warm answers) | 1.29 s median, 1.88 s p90, 3.02 s max (46 warm answers) | **Pass** |
| 5. A pause over 5 minutes | The 5-minute cache is lost (0 of 5 warm). The 1-hour cache (5 of 5) and a pre-warm (5 of 5) keep it. | The cache stays (20 of 20 warm). | **Pass** with a 1-hour cache on Anthropic |
| 6. Citations name existing passages | 268 of 268 IDs. 2 answers use a range, such as `[p00033-p00037]`, that the app does not parse. | 280 of 282 IDs (99.3%). 1 References passage and 1 mistyped ID. | **Pass**, with the unverified mark of C5 |
| 6. A cited passage supports the claim (20 graded) | 9 of 10 yes, 1 partly | 8 of 10 yes, 2 partly | 17 yes, 3 partly, 0 no |
| 4. Offline | `APIConnectionError` after 1.49 s (SDK default 2 retries) | `URLError` after 0.007 s | **Pass** for the request. The card that keeps the question is UI work. |

The local-model run did not run. Ollama and LM Studio are not installed, and the user chose not to install one. The 4k selection path ran on Haiku 5.5 instead (section 2.7).

Total cost of every P3 request: $0.18 ($0.12 Haiku 5.5, about $0.06 DeepSeek). The budget was $3.

| P4 check | macOS 26 WKWebView | Browser pane (Chromium 152, a control) | Fallback |
| --- | --- | --- | --- |
| 1. A CSS Custom Highlight paints over inline MathML | **Fail.** Text paints. Each `<math>` element stays unpainted. | Partial. The tokens paint, with gaps between them. | Paint text with the Highlight API, and give each covered `<math>` element a background. It paints in WKWebView. |
| 2. The page reads a selection in a PDF Paper's frame | **Fail.** ⌘A selects the PDF page, and the page reads an empty selection. | Not testable. The pane shows no PDF viewer. | Keep plan 5.8: no Highlights and no Ask on PDF-only Papers. Chat reads the page text. |
| 3. A stream survives 120 s with a 70 s silent gap | **Pass.** 50 of 50 lines, the end at 120.1 s. | **Pass.** 50 of 50 lines, the end at 120.1 s. | Not needed. Section 3.3 gives a heartbeat rule for disconnects. |
| 4. How ⌘F treats text in a panel beside the Paper frame | ⌘F finds panel text and frame text. No attribute or style hides panel text. | Not tested. The browser's own find applies there. | Rule: Find covers the Paper and the panel. To keep panel text out, the panel must leave the page's document. |

## 2. P3: Chat answers

### 2.1 Setup

`spikes/chat-2026-10-18/chat_spike.py` reads each Paper from its library row, read only, and builds the AI view with `evidence_document` (`papers/reading.py:18`). It writes the passages with their IDs in the form that the Blog uses, `evidence_text` (`papers/coordinator.py:445`). The bibliography is not in it.

| Paper | Route | AI view (characters) | Haiku 5.5 tokens | DeepSeek tokens |
| --- | --- | --- | --- | --- |
| 1706.03762v7 Attention Is All You Need | Pandoc | 33,976 | 12,666 | 8,064 |
| 2609.16995v1 PaperDoctor | Pandoc | 52,433 | 19,229 | 11,648 |
| 2505.07309v1 Uncertainty Profiles | Pandoc | 72,400 | 26,022 | 15,744 |
| 2312.06942v5 AI Control | arXiv HTML | 148,241 | 52,212 | 33,024 |
| 2609.37725v1 Context Language Models | PDF | 87,730 | 39,688 | 25,088 |

The token counts are the cached part of each prompt. Haiku 5.5 counts 2.2 to 2.8 characters a token, and DeepSeek 3.5 to 4.6. The plan estimates 4 characters a token (5.2), so for Haiku 5.5 a Paper is about 1.5 times the plan's figure. A typical Paper is about 35,000 Haiku tokens, not 24,000.

The request order follows plan 5.2:

1. **System:** the Chat instructions, then the AI view of the Paper inside `<paper>`. On Anthropic the Paper block has an explicit `cache_control` breakpoint. DeepSeek caches by itself.
2. **User:** the selected passage inside `<selection>`, if the question has one, then the question.

Each question goes alone, with no earlier turns. The reasoning effort is Low, the plan's default: adaptive thinking with effort `low` on Haiku 5.5, and DeepSeek's thinking fields from `_reasoning_fields` (`papers/ai.py:41`). The output cap is 8,000 tokens. Each Paper has 10 questions in `questions.json`: 7 about the Paper and 3 about a selected passage. One question on each Paper asks for a fact that the Paper may not hold.

The schedule asks every Paper in turn at each step, so each Paper waits through each pause. The pauses lasted 367 to 388 s, all longer than 5 minutes.

| Step | Questions | Anthropic cache |
| --- | --- | --- |
| First | q0, then q1 and q2 warm | 5-minute |
| After a pause | q3 | 5-minute |
| After a pause, pre-warm | a `max_tokens: 0` request when "Chat opens", then q4 and q5 | 5-minute |
| After a pause | q6, then q7 warm | 1-hour |
| After a pause | q8, then q9 warm | 1-hour |

A smoke test before the run warmed the Attention Paper, so its q0 read the cache on both providers.

### 2.2 Time to first words (criterion 5)

"First words" is the first text token. Thinking tokens and DeepSeek's reasoning tokens do not count. The times are seconds from the request to the first text token, median of 5 Papers.

| Step | Haiku 5.5 median (max) | Haiku 5.5 warm | DeepSeek median (max) | DeepSeek warm |
| --- | --- | --- | --- | --- |
| q0 first | 1.19 (2.10) | 1 of 5 | 1.68 (2.29) | 1 of 5 |
| q1, q2 warm | 0.92, 0.95 (1.82) | 10 of 10 | 1.14, 1.18 (1.75) | 10 of 10 |
| q3 after a pause, 5-minute cache | 1.36 (2.60) | **0 of 5** | 1.51 (1.57) | 5 of 5 |
| q4 after a pause and a pre-warm | 1.20 (4.22) | 5 of 5 | 1.65 (2.60) | 5 of 5 |
| q6 after a pause, 1-hour write | 0.94 (2.54) | 0 of 5 (the write) | 1.14 (1.89) | 5 of 5 |
| q8 after a pause, 1-hour cache | 1.03 (2.16) | **5 of 5** | 1.20 (1.51) | 5 of 5 |
| All 50 | 0.99, p90 2.54 | 36 of 50 | 1.33, p90 1.89 | 46 of 50 |

Findings:

- **Both providers pass.** The warm median is 0.95 s on Haiku 5.5 and 1.29 s on DeepSeek. Only 3 of 50 Haiku answers and 1 of 50 DeepSeek answers took more than 3 s.
- **On Haiku 5.5 the cache saves money, not time.** A cold question that writes the cache gets its first words in 1.23 s (median of 14). The worst cold case, AI Control with 52,212 tokens, took 2.60 s.
- **The slow answers think.** The three Haiku 5.5 answers over 3 s had 1,057 to 1,215 output tokens, most of them thinking. Two of them are on AI Control, the longest Paper. Plan 5.3 says that Chat shows which passages it reads before the first words. That display covers these waits.
- **The 5-minute cache does not last through a reading pause.** On Haiku 5.5, 0 of 5 questions after a 6-minute pause read the cache. The 1-hour cache kept 5 of 5. The pre-warm also worked: 5 of 5 questions after it read the cache. Each pre-warm took 0.96 to 1.51 s.
- **DeepSeek's automatic cache lasted through every pause** (20 of 20). DeepSeek needs no pre-warm and no TTL.

### 2.3 Tokens and cost

Costs are per question, with the Haiku 5.5 prices of 2026-10-06: $0.10 input, $0.50 output, $0.01 cache read, $0.125 5-minute write, and $0.20 1-hour write, per million tokens. The DeepSeek cost uses its late-2025 list prices and is an estimate.

| Haiku 5.5, per question | Mean cost | Tokens (median) |
| --- | --- | --- |
| Warm (cache read) | $0.00044 | 26,022 read, 29 new, 322 output |
| 5-minute write | $0.0039 | 26,022 written |
| 1-hour write | $0.0061 | 26,022 written |
| Pre-warm, 5-minute write, no output | $0.0016 to $0.0065 | 12,666 to 52,212 written |

- **Plan 5.2's cost formula holds.** With T = 30,000 tokens and P = $0.10, the formula gives $0.0037 plus the output for the first question, and $0.0003 plus the output for each later one. The run measured $0.0039 and $0.00044.
- **The 1-hour cache is cheaper on any session with one pause.** A 1-hour write costs 2 times the input price, and a 5-minute write costs 1.25 times. One pause over 5 minutes makes a second 5-minute write, so the 5-minute cache then costs 2.5 times against 2 times.
- **DeepSeek:** about $0.0007 a warm question and $0.0035 to $0.0094 for a cold one. The whole DeepSeek run cost about $0.06.
- **Haiku 5.5 has two price levels.** A prompt over 100,000 tokens costs $0.50 per million input tokens, 5 times more. At 2.2 to 2.8 characters a token, an AI view over about 250,000 characters crosses that line. None of the 14 library Papers does.

### 2.4 Citations (criterion 6)

The script counts every ID inside a citation bracket with the app's own pattern (`papers/passages.py:7`). It then checks each ID against the IDs of the AI view.

| | Haiku 5.5 | DeepSeek | 4k selection path (Haiku 5.5) |
| --- | --- | --- | --- |
| IDs cited | 268 | 282 | 56 |
| IDs that exist in the AI view | 268 (100%) | 280 (99.3%) | 56 (100%) |
| Answers with no citation | 0 of 50 | 0 of 50 | 0 of 15 |
| Answers with a citation form the app does not read | 2 | 1 | 0 |

The three problems:

- **A range.** Haiku 5.5 wrote `[p00033-p00037]` and `[p00092–p00095, p00098]` in 2 of 50 answers. Neither `CITATION` (`papers/passages.py:7`) nor `renderProse` (`app/static/render.js:153`) reads a range, so the reader sees raw text.
- **A References passage.** DeepSeek cited `p00221`, a References entry of AI Control. `evidence_document` drops it from the AI view, so the model guessed the ID.
- **A mistyped ID.** DeepSeek wrote `p0031` for `p00031`.

C5 handles each case: an unknown ID becomes an unverified mark. For ranges, C5 either expands them in `CITATION` and `renderProse`, or the instructions say "cite each ID; do not write a range". The second is the smaller change.

### 2.5 Hand grades

Twenty answers, two from each Paper on each provider: a method question and a selected-passage question on Haiku 5.5, and a fact question and a question that the Paper may not answer on DeepSeek. Each claim was checked against the full text of each passage it cites. `grading-sheet.md` has the answers beside their passages, and `grades.json` has each grade with its reason.

The grader is this session, not a person. Criterion 6 still needs the person's check in V2.

| | Yes | Partly | No |
| --- | --- | --- | --- |
| Haiku 5.5 (10) | 9 | 1 | 0 |
| DeepSeek (10) | 8 | 2 | 0 |

The three "partly" answers:

- Haiku 5.5, Uncertainty Profiles q1: the ROUGE-L detail is in `p00069`, but the line cites `p00024`, `p00030`, and `p00070`.
- DeepSeek, PaperDoctor q6: correct that the Paper names no backbone model, but "the only model it names is Gemini-2.5-Flash" is false. `p00085` names GPT-4.
- DeepSeek, Context Language Models q6: one model cites a page that does not name it, and one claim is too broad.

All three questions about a fact that is not in the Paper got a correct "the Paper does not say" (speech results, the backbone model, GPT-4). All five selected-passage answers on Haiku 5.5 cite the selected passage.

### 2.6 Offline (criterion 4)

`chat_spike.py --offline` sends one question to `https://localxiv-offline.invalid`, a host that does not resolve.

| Client | Error | Time to the error |
| --- | --- | --- |
| Anthropic SDK, default 2 retries | `APIConnectionError` | 1.49 s |
| Anthropic SDK, 0 retries | `APIConnectionError` | 0.002 s |
| `urllib`, as in `papers/ai.py` | `URLError` (errno 8, host not known) | 0.007 s |

Chat can say "offline" in under 1.5 s on every path. The SDK retries add 1.5 s of backoff. The card that keeps the question and says why is UI work for C7, and this spike did not test it.

### 2.7 The 4k selection path, and the local model

**The local-model run did not run.** No local server is installed, and the user chose not to install one. Three questions of plan 5.1 stay open: does a local server accept the empty `Bearer` value that `papers/ai.py:117` sends, does it accept the 64,000-token output cap (`papers/ai.py:24`), and is a small model good enough at 4k.

To test the selection path itself, `--selection-only --context 4096` ran the 15 selected-passage questions on Haiku 5.5. The context is the selected passage, its section, and the passages beside it, within (4,096 - 1,024 - 800) × 3 characters.

- Each prompt was 2,618 to 3,743 tokens for the instructions and the excerpt, plus 88 to 608 tokens for the selection and the question.
- First words: median 0.88 s. All 56 citations name existing passages.
- One answer had 887 output tokens. With the prompt, that is 4,113 tokens, more than a 4,096-token context. At Haiku 5.5's 2.2 to 2.8 characters a token, a local preset needs a smaller excerpt budget, about 2,000 tokens, or a lower output cap.
- The selection path writes a cache entry for each excerpt, which costs 1.25 times and is never read again. C4 sends the selection path with no cache breakpoint.

### 2.8 What this decides for C4 and C5

1. **Keep the whole Paper in a cached prefix** (plan 5.2) for both providers. It meets criterion 5 with room to spare.
2. **On Anthropic, put a 1-hour `cache_control` on the Paper block.** Reading pauses are longer than 5 minutes, and the 1-hour write is cheaper after one pause. The current Overview and Blog request uses top-level automatic caching (`papers/ai.py:178`), so C4 adds the explicit breakpoint. A pre-warm when Chat opens works, but on Haiku 5.5 it saves about 0.3 s, so it is optional.
3. **Count the Context size in the model's own tokens.** The Haiku 5.5 tokenizer makes a Paper about 1.5 times the plan's 4-characters-a-token estimate.
4. **In C5, tell the model not to write ranges**, and keep the unverified mark for unknown and mistyped IDs.

## 3. P4: WebKit

### How the checks ran

- **WKWebView.** `spikes/chat-2026-10-18/native_spike.py` runs `tools/native_shot.py` and adds one throwaway route, `/spike/stream`, to the scratch copy of `app/server.py` that `native_shot.py` installs. The route is in `spike_routes.py`. The step files are `p4-steps.json`, `p4-steps-fallback.json`, and `p4-steps-fallback2.json`. The app is the macOS 26 test build, user agent `AppleWebKit/605.1.15`.
- **Browser pane.** `spike_server.py` runs the app server with the same route on port 8799. The pane is Chromium 152 in Electron, not WebKit, so its results are a control only. This spike did not use Safari.
- **Library.** `make_library.py` makes a scratch library with three Papers from the reader's library: the Attention Paper (Pandoc, 138 MathML elements), 2610.02887v1 (arXiv HTML), and 2609.37725v1 (a PDF Paper). The reader's library stays read only.

### 3.1 Check 1: a Highlight over MathML

Method: on passage `p00045` of the Attention Paper, which holds three inline formulas, the page makes a `Range` over the whole passage. It registers the range with the frame's `CSS.highlights` and adds a `::highlight()` rule to `#app-reading-style` (`app/static/reader.js:333-334`).

Result in WKWebView: **fail.** The Highlight API exists (`typeof Highlight` is `function`) and paints every text run. It paints nothing inside a `<math>` element: the three formulas stay on a white ground (`evidence/p4-1-wk-highlight.png`). A range that starts inside a formula token also paints nothing inside the formula.

Result in Chromium: partial. The math tokens paint, but the spaces between tokens do not (`evidence/p4-1-highlight-mathml-chromium-zoom.png`). alphaXiv issue #176 reports a similar gap over equations.

Fallback, tested in WKWebView: keep the Highlight API for text, and give each `<math>` element inside the Highlight a background colour through a class in `#app-reading-style`. The formulas then paint (`evidence/p4-1-fallback-math.png`). Thin light lines stay where the band of a formula is shorter than the band of the text line. A `<span>` wrapper with a background around each `<math>` element also paints, with the same thin lines (`evidence/p4-1-fallback-span.png`). The class is the smaller change, because it adds no element. Plan 5.4 already snaps a selection edge inside a formula to the whole formula, so a whole-formula background agrees with the anchor rule. The class changes no text, and the Reference preview copy keeps no classes (`app/static/reader.js:588-600`).

### 3.2 Check 2: a selection in a PDF Paper's frame

Method: the reader opens 2609.37725v1. For a PDF Paper the frame has no `sandbox` attribute (`app/static/reader.js:267`), and the server sends the PDF with `default-src 'none'` (`app/server.py:301-304`). The step clicks inside the PDF, presses ⌘A, and reads `getSelection()` in the page and in the frame.

Result in WKWebView: **fail.** The frame document is same-origin and readable. Its `contentType` is `application/pdf`, and its body holds one `<embed>`. ⌘A selects the whole PDF page in WebKit's PDF view (`evidence/p4-2-pdf-select-all.png`), but the page and the frame both return an empty string. The selection lives in the PDF plug-in, outside the DOM.

Result in Chromium: not testable. The browser pane shows an empty frame for the PDF, because it has no PDF viewer.

Fallback: keep plan 5.8 as written. PDF-only Papers get Chat on their page text (`papers/pdf.py:36-40`), and no Highlights or Ask. Two later options exist, and this spike did not test them: show PDF Papers in a native `PDFView`, which gives `currentSelection` to the shell, or render them with PDF.js, which puts the text in the DOM.

### 3.3 Check 3: a long silent stream, and a disconnect

Method: from the page, `fetch('/spike/stream?...')` reads the body with a `ReadableStream` reader. The route writes one line a second for 120 s, with no write from 25 s to 95 s. A second stream has a 50 s gap. A third stream aborts with `AbortController` at 10 s. The route is on the app's own `Handler`, so the HTTP/1.0 response, the body that ends on close, and the 15 s socket timeout (`app/server.py:278`) are the real ones.

| Stream | WKWebView | Chromium |
| --- | --- | --- |
| 120 s, 70 s silent gap | 50 of 50 lines. The first line after the gap arrives at 95.0 s. The body ends at 120.14 s. | 50 of 50 lines. After the gap at 95.0 s. Ends at 120.12 s. |
| 90 s, 50 s silent gap | 40 of 40 lines. Ends at 90.11 s. | Not run. |
| Abort at 10 s | `AbortError` at 10.01 s. The server's write at 10.05 s succeeds. The write at 11.06 s raises `BrokenPipeError`. | `AbortError` at 10.0 s. The write at 10.04 s succeeds. The write at 11.05 s raises `BrokenPipeError`. |

Result: **pass** in both. A 70 s silence did not stop the stream in WKWebView. The 15 s socket timeout does not apply, because the handler does not read or block on a send during the gap.

What a disconnect does: the first write after the client leaves succeeds, and the second write raises `BrokenPipeError`. `handle_request` already catches it (`app/server.py:506`). So the server learns of a disconnect only when it writes twice. During a long silent reasoning phase it writes nothing, so it cannot see that the reader pressed Stop or closed the Paper.

Rule for C3: while the provider is silent, the Chat route writes a heartbeat byte about every 5 s. Then a Stop or a closed page ends the provider request within about 10 s, which criterion 9 needs. A whitespace byte before the answer text is enough, and the page ignores it. If a later WebKit version drops a silent stream, the same heartbeat keeps the stream alive.

### 3.4 Check 4: ⌘F and a panel beside the Paper frame

Method: the Native shell's Find bar calls `WKWebView.find` on the whole web view (`app/macos/Shell.swift:365-367`), and its field says "Find in this view" (`:314`). The step adds a panel to the page, beside the Paper frame, with a unique word. Then it types words in the Find bar and reads the status and the selection.

| Word | Where | Found |
| --- | --- | --- |
| `zqxpanelword` | panel in the page | yes. The page selection is the word. |
| `desiderata` | Paper frame only | yes. The frame selection is the word. |
| `self-attention` | both | yes. The first two matches are in the frame. |
| `zqxinert` | panel with `inert` | yes |
| `zqxnoselect` | panel with `user-select: none` | yes |
| `zqxshadow` | panel in an open shadow root | yes |
| `zqxariahidden` | panel with `aria-hidden="true"` | yes |
| `zqxmissing` | nowhere | no ("Not found") |

A loaded same-origin `<iframe>` panel is searched too: Find selected `journalistic` inside it (`p4-steps-fallback2.json`, `evidence/p4-4-find-iframe-panel.png`). A `srcdoc` panel rendered empty under the page's policy, so its "Not found" proves nothing.

Result: `WKWebView.find` searches the page document and every frame in it. No attribute or style that a Chat panel can keep hides its text from Find.

Rule for criterion 15: **Find covers the Paper and the Chat panel.** The Find bar already says "Find in this view". Search inside Chat answers is also a request in alphaXiv's tracker (#293). The test for the rule: a word that is only in an answer is found, and a word that is only in the Paper is found.

Fallback, if the rule must be "Find covers the Paper only": move the panel out of the page's document. An `<iframe>` panel does not do it. Two ways: a second `WKWebView` or a native AppKit panel in the Native shell, or a Find of our own that searches the Paper frame's text and paints the matches with the Highlight API. Browser mode then keeps the browser's own Find, which also searches every frame.

## 4. How to run the spikes again

Run each command from the repository root with the main checkout's `.venv` Python. Every script reads the reader's library read only. The P3 scripts read a provider key from LocalXiv's Keychain item for the endpoint URL, put it only in the request header, and never write it.

```bash
python spikes/chat-2026-10-18/chat_spike.py anthropic --model claude-haiku-5-5 --key keychain --out spikes/chat-2026-10-18/runs/anthropic.jsonl
```

```bash
python spikes/chat-2026-10-18/chat_spike.py compatible --endpoint https://api.deepseek.com --model deepseek-chat --key keychain --out spikes/chat-2026-10-18/runs/deepseek.jsonl
```

```bash
python spikes/chat-2026-10-18/summarize.py spikes/chat-2026-10-18/runs/anthropic.jsonl spikes/chat-2026-10-18/runs/deepseek.jsonl
```

- `chat_spike.py --smoke` asks one question with no pause. `--offline` runs the criterion 4 test. `--selection-only --context 4096` runs the selection path for a local model. `--budget` stops a run at a measured cost, $1.50 by default.
- `grade_sheet.py` writes each sampled answer beside the passages it cites.
- `make_library.py OUT` makes the P4 scratch library. `native_spike.py --log FILE --library OUT --steps p4-steps.json --out DIR` runs the WKWebView checks. It needs Xcode and installs nothing outside `DIR`.
- `spike_server.py --port 8799 --data-dir OUT --log FILE` serves the same route for a browser.

## 5. Limits

- **One run each.** Each P3 number comes from one run on one evening, from one network. Provider load changes from hour to hour, so a second run can move the medians.
- **One turn per question.** Each question goes alone, with no earlier turns, Highlights, or Notes after the Paper. The cache breakpoint is after the Paper, so later turns change the new tokens per question, not the cached part.
- **The grader is this session.** Plan criterion 6 asks a person to check a sample in V2. The 20 grades in section 2.5 are a first pass by Claude, not that check.
- **No local model.** Ollama and LM Studio are not installed, and the user chose not to install one. So the 4k selection path ran on Haiku 5.5 only, and three questions of plan 5.1 stay open: does a local server accept an empty `Bearer` value (`papers/ai.py:117`), does it accept the 64,000-token output cap (`papers/ai.py:24`), and is a small model good enough at 4k.
- **No Safari.** P4 ran in the macOS 26 WKWebView and in the Chromium browser pane. Safari uses the same WebKit as the WKWebView, but the spike did not open it.
- **DeepSeek cost is an estimate.** The script prices DeepSeek with late-2025 list prices. The Haiku 5.5 cost uses the prices in the Claude API reference of 2026-10-06.
