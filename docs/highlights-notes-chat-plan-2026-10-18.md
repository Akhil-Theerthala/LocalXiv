# Highlights, Notes, and Chat: product analysis and plan

Date: 2026-10-18. Main at `b41b7cf`.

Scope: Highlights on the Paper, Notes and their arrangement, Chat with the Paper, and Ask about a selected passage. Chat uses its own model, provider, and API key, separate from the Overview and Blog model. The source is [the alphaXiv brief](competitive-brief-alphaxiv-2026-10-17.md), sections 8 and 9.

Status: analysis and plan. On 2026-10-18 you chose **B · Margin** from five clickable prototypes (section 6). The plan separates the work that every option needs from the work that B needs. The P3 and P4 spikes ran on 2026-10-18, and their results are in [the spike report](chat-spikes-2026-10-18.md), on the branch `claude/modest-almeida-e32d2f`.

## 1. Summary

- **Build one loop, not three copies of alphaXiv.** A reader marks a passage, asks about it, and keeps the answer with the mark. The Notes leave the app as Markdown, and later in the EPUB that goes to the Kindle. alphaXiv cannot close this loop, because it has no EPUB and no Kindle export.
- **Chat with your own key is the clearest opening.** alphaXiv's tracker has 7 issues with 18 reactions that ask for an own key or endpoint, and the team said "No plans" ([#232](https://github.com/alphaXiv/feedback/issues/232)). Chat is alphaXiv's second most praised feature. The issue with the most reactions ([#244](https://github.com/alphaXiv/feedback/issues/244), 12) asks for the strong models back, or an own key.
- **Chat gets its own model because you asked for it, and because it fits the job.** Chat sends the whole Paper with every question, so a cheap, fast model keeps the cost of each question low, while the Blog keeps a strong model. A separate key on a separate account does not share the Blog's rate limits. A local model can answer with nothing leaving the Mac. Speed itself comes from streaming and from no queue (C2, C3), which a second key does not give.
- **"Solid" has 15 acceptance criteria** (section 4). The main ones: no Highlight is ever lost, Chat never waits behind a job, every citation opens a passage, and a backup exists.
- **LocalXiv had a chat on the server that nothing used.** A `/chat` route and a `chat` job came in with the local app server (`65092e6`, 2026-09-06). No tracked page code called the route. Its only form was in `app/prototypes/`, which v0.0.9 removed (`1d6e0c7`). The 2026-10-11 cleanup removed the route (`9b48e44`) because it was unused. The old chat ran in the Paper queue, did not stream, and deleted its messages when the document changed. The new design differs on each point, and it builds the interface and the server together.
- **Presentation: B · Margin, your choice.** Notes and questions sit beside their words. A click on a card draws a moving dotted line to the words. Ask opens only on a click. Each card carries its Highlight's colour, and on a narrow page the cards fold to coloured markers. The judges scored the first B lowest, mainly for the narrow-window folding, which section 6.1 now fixes. Release Chat first, then Highlights and Notes, then the library Notes page and the Kindle export. About 14 weeks of work for one developer.

## 2. Who needs this, and when

LocalXiv's reader reads one Paper in depth, often over several sittings, on the Mac and on a Kindle. Three jobs follow.

| Job | When | The reader wants to | Today |
| --- | --- | --- | --- |
| Mark | While reading | Mark the passages that matter, so the Paper keeps what they found | Not possible. The reader copies text to another app. |
| Keep and arrange | After a section or after the Paper | See all marks and thoughts in an order that suits a review, a related-work paragraph, or a talk | Not possible. No Notes, Collections, or Tags. |
| Ask | At a passage they do not understand | Ask about that exact passage and get an answer from the Paper, with the passage it came from, without leaving the Paper | The reader copies the passage into a general chat app, which does not know the rest of the Paper. |

Evidence from other products (section 11 lists the sources):

- Most readers combine three things: marks with a list, a popover on the selection, and a panel for longer chat (Readwise Reader, Moonlight, SciSpace, Zotero, Kindle).
- Users of every product ask for notes that leave the app with links back to the source. NotebookLM, MarginNote, and Apple Books lose users on export.
- Highlights get lost when the document changes. A study of Hypothesis annotations found that 53% were at risk of becoming orphans. Kindle tells publishers that updates can erase notes. Hypothesis keeps lost highlights visible as orphans, which is the best practice.
- Chat loses the selection or the notes: alphaXiv [#272](https://github.com/alphaXiv/feedback/issues/272) (fixed 2026-10-02) and [#376](https://github.com/alphaXiv/feedback/issues/376) (open). ChatGPT allows one quote per message. Cursor's "Add to Chat" once opened a new chat by mistake.

## 3. Where LocalXiv can lead

Parity is not the goal. Each feature has one property that alphaXiv does not match.

| Feature | alphaXiv | LocalXiv edge |
| --- | --- | --- |
| Highlights | Rectangles on a PDF page, for one paper version, in an account | On reflowed text that keeps every Reading preference, offline, with no account |
| Notes | In its cloud. A hidden page across papers with no tags or search ([#209](https://github.com/alphaXiv/feedback/issues/209)). No Markdown export ([#267](https://github.com/alphaXiv/feedback/issues/267)) | On the Mac, with search, a Markdown export, a library page with Tags, and later a Notes chapter in the EPUB |
| Chat | alphaXiv's models and quotas, no own key, a filtered set of pages as context ([#168](https://github.com/alphaXiv/feedback/issues/168), [#202](https://github.com/alphaXiv/feedback/issues/202)) | The reader's own key and model, the whole Paper as context, the model, date, and tokens on each answer, and citations with a Reference preview. A local model can answer with no data leaving the Mac. |
| Ask on a selection | A quote chip in the chat panel | Several quotes in one question, and the answer joins the Highlight it answers |

## 4. What "solid" means

These are the acceptance criteria for the whole feature. Each one is a test.

1. **No lost work.** A Highlight, a Note, or a Chat answer survives a reimport, a new parser release, a Reading preferences change, a theme change, and an app update. A Highlight whose text the app cannot find again stays in the Notes list with its quote and note, marked **Not found in this version**. The app never deletes it.
2. **A backup exists.** The library takes a snapshot with the SQLite backup API before each migration and once a day. Highlights, Notes, and Chat export to one JSON file and import back.
3. **Same words after reflow.** A Highlight covers the same words at every font, text size, margin, and line spacing.
4. **Offline works.** Highlights and Notes work with no network. Chat says why it cannot answer and keeps the question.
5. **Fast answers.** "First words" is the first answer token, not the first reasoning token. With a fast Chat model, the median time to first words is 3 seconds or less when the cache is warm. Reading sessions have pauses longer than 5 minutes, so the measure includes them (V2). Before the first words, Chat shows which passages it reads.
6. **Real citations.** Each citation opens a passage that exists. A citation that the app cannot check shows as unverified, never as a broken link. In V2, a person checks a sample: the cited passage supports the claim.
7. **Clear provenance and cost.** Each answer shows the model, the provider, the date, and its tokens (cached, new, and output). The Chat composer names the provider host that gets the Paper.
8. **No queue, no lost streams.** A Chat question never waits behind an import, an Overview, or a Blog of the same Paper. Remove from Library and an app update stop a running answer first.
9. **Real stop.** Stop closes the provider request. The partial answer stays, marked as stopped.
10. **One history.** Each Paper has one Chat history, and it includes the questions asked from a selection. alphaXiv splits them and calls it intended ([#376](https://github.com/alphaXiv/feedback/issues/376)).
11. **Undo and honest removal.** ⌘Z restores a deleted Highlight, a deleted Note, and a cleared Chat during the session. Remove from Library says that it deletes the Paper's Notes and Chat, and offers Export Notes first.
12. **Keys stay keys.** ⌘⌫ in a note or chat field deletes text and does not open the Remove dialog. Menu keys never take a key that a text field needs.
13. **Accessible.** A keyboard selection can make a Highlight and start Ask. VoiceOver reaches each Highlight, with its colour name, through the Notes list. A streamed answer is in a polite live region. Each colour has a name, and the colours pass a contrast check in Light, Sepia, and Dark.
14. **No silent fallback.** With no Chat model, Ask shows a card with **Use my Overview connection** (one explicit copy) and **Set up Chat…**. Chat never uses the Overview key by itself.
15. **One rule for Find.** ⌘F finds text in the Paper and in the margin cards. P4 showed that `WKWebView.find` searches the page and every frame, and that no attribute or style hides card text from it. The Find bar already says "Find in this view". The test: a word that is only in an answer is found, and a word that is only in the Paper is found.

## 5. Product decisions

Each decision has a recommendation. Section 6 has the presentation, and section 9 has the open questions for you.

### 5.1 Chat model, provider, and key

Recommendation: a second, full connection for Chat, with its own key.

- Settings gets a Chat group, or a Chat pane, with Provider, Model, API key, Test Connection, Reasoning effort (default Low), and **Context size**. The app cannot ask an OpenAI-compatible endpoint for its context size, so the reader sets it. Each preset has a default.
- **Copy from Overview and Blog** fills the Chat fields once. After the copy, Chat keeps its own Keychain item. Settings shows which key each role uses. When the reader changes or removes the Overview key, Settings offers to change the Chat copy too. A silent link would hide which key pays for Chat.
- A **Local** preset for Ollama and LM Studio on loopback. A local model needs no key. Three gates require one today: Test Connection (`app/server.py:398-400`), the AI gate (`app/server.py:483`), and `aiReady` (`app/static/app.js:65`). `papers/ai.py:117` sends an empty `Bearer` value, and P3 checks that local servers accept it. Ollama's FAQ gives a default context window of 4,096 tokens, so the Local preset uses the selection path in 5.2.
- Chat gets its own output cap. The host caps today are 64,000 to 131,072 tokens (`papers/ai.py:15-24`). A small local model may fail on them. P3 checks this.
- The Settings help says that Chat sends the Paper to one more provider when the Chat provider is not the Overview provider.
- The first-run Setup dialog keeps its Overview fields. It gets one line: "Chat can use another model. Set it up in Settings › Chat."
- Precedents: Continue gives each role a full connection. Zed and Aider keep one key per provider and pick a model per role. Readwise Reader uses a separate model for its preset prompts.

Code facts that this decision changes:

- The Keychain account is the endpoint URL (`papers/settings.py:32-33`). Chat on the same provider would share the item. Chat needs its own account name, for example `chat:<endpoint>`.
- `SETTING_KEYS` drops unknown settings without a message (`papers/library.py:15-18`, `:308`). New Chat settings go there, get defaults in `DEFAULTS` (`app/server.py:34`), and get validation in `/api/settings` (`app/server.py:405-441`), which checks only the Overview endpoint today.
- `has_key` covers the Overview endpoint only (`app/server.py:65`). Chat needs `has_chat_key`.
- No code deletes a Keychain item (`papers/settings.py:19-22` declares the call only). Two keys make delete a real need.

### 5.2 What Chat sends to the model

Recommendation: the whole Paper in a cached prefix, and the selection at the end.

- **Prefix, the same for every question on a Paper:** the Chat instructions, then the AI view of the Paper: the passages with their `[p00017]` IDs and without the bibliography (`papers/reading.py:18-79`). P3 measured the size in each model's own tokens. Haiku 5.5 counts 2.2 to 2.8 characters a token, so a typical Paper is about 35,000 Haiku tokens (12,666 to 52,212 on 5 Papers). DeepSeek counts 3.5 to 4.6. The Context size therefore counts the model's own tokens, not an estimate of 4 characters a token.
- **After the prefix:** the reader's Highlights and Notes for this Paper (they change, so they go after the cached part), the last turns, the selected quotes with their passage IDs, then the question. The selection goes last, because models use text at the end of a long context best.
- **Turn budget:** keep the last turns that fit the Context size. Show a line when older turns no longer go to the model.
- **Caching:** Anthropic gets an explicit **1-hour** cache breakpoint after the Paper. In P3, the 5-minute cache was lost in 5 of 5 questions after a 6-minute pause, and the 1-hour cache kept 5 of 5. A 1-hour write costs 2 times the input price and a 5-minute write 1.25 times, so the 1-hour cache costs less after one pause. A pre-warm when Chat opens also works, but it saves only about 0.3 s, so it is optional. DeepSeek kept its own cache through every pause (20 of 20). OpenAI caches by itself. OpenRouter passes the breakpoint for Anthropic models. Today it gets none, and 0 of 313 such requests read the cache.
- **Selection path:** for a model with a small Context size, send the selected passages, their section, and the passages beside them, with no cache breakpoint: the excerpt changes with each question, so a cache write is never read. No extra request is needed. P3 ran it at a 4k context on Haiku 5.5: all 56 citations were valid, but one answer went over 4,096 tokens, so the excerpt budget for a 4k model is about 2,000 tokens.
- **Fallback:** if the AI view is larger than the Context size, use Evidence selection. It costs one more request, about 9 seconds (median, measured). `select_evidence` needs a `Coordinator`, makes a run folder, forces JSON, and reads the Overview reasoning setting (`papers/coordinator.py:133-143`, `:263`, `:281`). C4 moves the selection call out of it.
- **Text source:** Chat reads passages from the Paper's library row, not from the Paper files. A reimport renames the folders while an answer can still run (`papers/library.py:183-197`).
- **Rate limits:** a Blog sends up to 6 requests at once (`papers/blog_prompts.py:238`). A Chat key copied from the Overview shares that account's limits, and each Chat request adds about 25k input tokens. Chat reads `Retry-After`, retries once, and says the cause: "The provider is busy with your Blog. Chat will retry in 20 s."
- **Cost, as a formula:** with a Paper of T tokens, an input price P, and an output price Q, the first question costs about 1.25 × P × T plus the output. Each later question inside the cache time costs about 0.1 × P × T plus the new tokens and the output. P3 confirmed the formula. With Haiku 5.5, a warm question cost $0.00044 and a first question $0.0039 (5-minute write) or $0.0061 (1-hour write). DeepSeek cost about $0.0007 a warm question. Every P3 request together cost $0.18. Haiku 5.5 charges 5 times the input price for a prompt over 100,000 tokens, which an AI view of over about 250,000 characters reaches. None of the 14 local Papers does, but C4 warns before such a request.

### 5.3 How answers cite and stream

- Answers use the Blog's citation form `[p00017]`, rendered by `renderProse` (`app/static/render.js:142-172`).
- Two changes are needed. The citation hover is bound only to `#blog-text`, with a sources map that `drawBlog` builds (`app/static/reader.js:630-633`, `:691`), so the Chat pane needs its own binding and map. `renderProse` drops an unknown ID without a mark (`app/static/render.js:160`), so the unverified mark needs a change there.
- The app checks citations after the stream ends. An unknown ID becomes an unverified mark. It does not fail the answer, which `cited_in` does today (`papers/passages.py:10-20`).
- The instructions say: cite each ID, and never write a range. In P3, 2 of 50 Haiku 5.5 answers wrote ranges such as `[p00033-p00037]`, which `CITATION` and `renderProse` do not read.
- Fix one false match first: `cited_in` treats any `p` plus digits in the text as a citation (`papers/passages.py:15`). "p50 latency" then fails.
- Each saved answer keeps the quote of every passage it cited. Passage IDs are positions (`papers/document.py:698`), so after a reimport an old ID can name other text. The stored quote keeps the old citation readable, marked "from an earlier version".
- A citation click in Chat scrolls the Paper and flashes the passage, and the Chat stays open. It does not open Split view, which would take the column that the panel uses. Back (⌘[) returns to the reading place.

### 5.4 How a Highlight is anchored

Recommendation: store the words, not the position.

- Each Highlight stores the exact quote, about 32 characters before and after it, the passage ID, the DOM anchor from `passage.href`, the section heading, and the `document_digest` at creation. A selection that crosses passages stores a start and an end.
- The DOM anchor comes from `passage.href`, not from the passage ID. For arXiv HTML Papers the two differ in every passage (`S1.p1.1` against `p00017`). The Reading position misses these Papers for this reason (`app/static/reader.js:296-297`), and F7 fixes it.
- **One text** for the browser, the server, and the export: the passage text that `papers/document.py:250-268` builds. Each formula becomes ` $tex$ ` from its `alttext`, else from its TeX annotation, and whitespace collapses. The EPUB math images keep the same TeX in `alt` (`papers/document.py:314-327`), so the export finds the same quote. The browser maps a selection to this text, and a selection edge inside a formula snaps to the whole formula. A test checks that the JavaScript and the Python produce the same text for every corpus file.
- **Text outside a passage** gets a fallback anchor: the nearest element `id` and the quote. Citeproc bibliographies (`div.csl-entry`) are not passages, and they are 14% to 37% of the text in 3 of 8 local Pandoc Papers (measured). List bibliographies are passages.
- **When to search again:** a different `document_digest` after a reimport. `conversion_revision` is compared by no code (`papers/convert.py:159`). The search tries the passage, then the section, then the whole Paper, then a fuzzy match. The result is *found*, *moved* (text changed a little), or *not found*. The reader can place a not-found Highlight again by selecting new text.
- **Measured on 8 parser corpus runs:** an exact match finds 99.2% to 100% of test quotes again when the converter is the same, but only 92.4% to 100% stay in the same passage ID. When 5 of 16 converters changed, 89.2% were found. So the passage ID is a hint, and a fuzzy match is necessary.
- **The gate:** the same arXiv version can change route (Pandoc, arXiv HTML, LaTeXML) on a limit or a failure (`papers/convert.py:50-56`), and a parser fix can restore text that a quote did not have. A hard "0 not found" would block parser fixes. So the gate runs for each route and uses a reviewed allow-list, as the parser corpus gate does.
- **Paint** text with the CSS Custom Highlight API, which changes no DOM. P4 showed that WebKit paints no Highlight inside a `<math>` element, so each formula that a Highlight covers also gets a background through a class in `#app-reading-style`. The class adds no element, and the Reference preview drops every `class` attribute (`app/static/reader.js:600-601`). A selection edge inside a formula snaps to the whole formula, so a whole-formula background agrees with the anchor. A `<mark>` wrapper would lose its text in the Reference preview (`app/static/reader.js:591-598`). The prototypes use `<mark>` for speed only.
- A new arXiv version is a new Paper row (`papers/acquire.py:80-95`). Copying Highlights from v1 to v2 is an offer when v2 opens, never automatic (E3).

### 5.5 How Notes are arranged

"Arrange" has two meanings, and the reader needs both.

- **In one Paper:** by position (the default), by colour, by date, or by the reader's own groups. Groups can be renamed and ordered, a card can go to an exact place, and a written note can sit between quotes. The export follows the order the reader made. Colours have names, so "by colour" gives, for example, the list of open Questions.
- **One Paper note** belongs to no Highlight, and the Notes list has search. alphaXiv has both.
- **An answer joins its Highlight.** Save as Note on an answer to a Highlight adds the answer, with its citations and model line, to that Highlight. An answer to a new selection makes a Question Highlight.
- **Across the library:** a Notes page groups every Highlight and Note by Paper, by Tag, or by colour, with search. Tags and Collections are in the glossary (`CONTEXT.md`) but not in the library. Notes are the first reason to build Tags.

A free canvas (LiquidText, MarginNote) is out of scope. Users report it as slow to arrange, with weak export and no search, and it needs a large window.

### 5.6 Notes leave the app

- **Markdown export** per Paper and per library: the quote, the note, the colour name, the section, and a `localxiv://` link back to the passage once the URL scheme exists (brief, item 7).
- **JSON backup and restore** of Highlights, Notes, and Chat (criterion 2).
- **EPUB (phase 4):** the Paper export and Send to Kindle get an option to include Highlights and Notes. The export marks the quotes and adds a Notes chapter with links to the passages. It finds each quote again in the EPUB text by the same `$tex$` text. EPUBCheck runs again. A person checks the result on a real Kindle.

### 5.7 One toolbar on a selection

A selection in the Paper shows one small toolbar, placed by the Reference preview's placement code:

- Four named colours: Key point (yellow), Question (purple), Use in my work (orange), and Disagree (pink). The colours stay away from the system accent, which marks a selection, and from the content green. One click makes a Highlight with no note, and nothing else on screen moves. alphaXiv broke this once, and five readers reacted ([#157](https://github.com/alphaXiv/feedback/issues/157)).
- **Note**: a Highlight with the note editor open.
- **Ask**: the quote goes to Chat. Several quotes can go into one question.
- **Explain**: Ask with no typing. It sends "Explain this passage" at once, as alphaXiv's Quick explain does.

A click on a Highlight opens a small card at the mark: change the colour, edit the note, Ask, or Delete. alphaXiv has no colour change ([#420](https://github.com/alphaXiv/feedback/issues/420)). The same commands are in the Paper menu and in a context menu on the selection, as in Apple Books, so every command has a menu item. Keyboard shortcuts are chosen in U4 against the Apple list. ⌥⌘I is the standard inspector key. ⌘J (Jump to Selection) and ⌘E (Use Selection for Find) are taken.

### 5.8 Scope for the first releases

In scope: Chat on every Paper. Ask, Explain, the selection toolbar, Highlights, and Notes on converted Papers (EPUB and arXiv HTML). The Chat model in Settings, the Markdown export, and the backup.

Out of scope, with the reason:

| Item | Reason |
| --- | --- |
| Highlights and Ask on PDF-only Papers (17 of 100 corpus Papers) | The app reads no DOM from a PDF frame (`app/static/reader.js:330`, `:348`). P4 confirmed that the selection lives in WebKit's PDF plug-in, and the page reads an empty string. These Papers get Chat on their page text (`papers/pdf.py:36-40`). Later options: a native `PDFView`, or PDF.js. |
| Highlights on the Overview and the Blog | The Blog changes on Regenerate, and MathJax replaces its formulas. Ask on a Blog selection is a cheap later step. |
| Sync, sharing, and public comments | No account, by design. The brief lists comments under "do not build". |
| Chat across several Papers | The brief lists research agents under "do not build". |
| Canvas and mind maps | See 5.5. |

Set aside, worth a later look:

- **Suggested Highlights** from the Overview's evidence. The Digest already links each component to its passage. Moonlight has an Auto Highlight.
- **Kindle highlights back into LocalXiv.** A Kindle records personal documents in `My Clippings.txt`. If this holds for Send to Kindle documents, a reader can highlight on the Kindle and see it on the Mac. Cheapest test: send one Paper, highlight on the Kindle, read the file.
- **A list of open questions** for a group meeting: the Question Highlights with no answer.

## 6. Presentation options

Five prototypes run on the real reader with the bundled Attention Paper (section 10 says how to open them). Each one is a full approach, not a skin. The selection toolbar is the same in all five.

| | A · Inspector (mix) | B · Margin | C · Notebook | D · In place | E · Reader view |
| --- | --- | --- | --- | --- | --- |
| Highlights and Notes live | A list in a trailing panel with Notes and Chat tabs | Cards in the margin beside their passages | A document pane with sections the reader makes | Only in the text, with a card at the mark | A's two tabs as a fourth reader view |
| Chat lives | The Chat tab | A question card at the passage | The pane's composer. Each answer is a block | A card at the selection, then a Chat view | The Chat tab of the view. On a wide page, the Paper sits beside it in Split view |
| Arrangement | Position, colour, date, or own groups (rename, order, written notes) | Reading order only | Drag blocks into sections | A library Notes page | Same as A |
| Width | Beside the Paper on a page of 980 px or more. Over the Paper below that | Cards need a page of about 1100 px. Below, they fold to dots | A pane of about 46% of the page | No cost | No cost. Split view at a page of 1200 px |
| Main conflict | Shares the right column with Split view and the toasts | Folds at common widths. Splits the Chat history | Every Highlight goes to an Inbox to sort | Loses an answer on a scroll. Hides the Paper for Chat | A fourth item in the view switch, against the calm toolbar. Below a page of 1200 px, Chat hides the Paper, as in D |
| Build cost | M, plus the overlay mode | L | L | M | M, mostly the view list in Swift and JS |

Rules that every option keeps, from the 2026-10-14 UI decisions: window minimum 700 pt, no phone layouts, selection in the system accent, green only for content accents, a calm toolbar, and no controls fixed to the bottom of the window. Width facts: in the Native shell the page starts beside the sidebar. At the 700 pt window with the sidebar shown, the page is 500 px (`app/macos/Shell.swift:146-150`). Split view needs a page of 1200 px (`app/static/reader.js:14`), so a window of about 1450 pt with the sidebar shown.

Four judges scored A to D from 1 to 5 (E came later, from the engineering judge):

| Lens | A | B | C | D | Pick |
| --- | --- | --- | --- | --- | --- |
| A PhD reader on a 14-inch MacBook with a Kindle | 3.6 | 1.2 | 3.2 | 3.4 | A + C's ordered groups + D's library page and card at the mark |
| An alphaXiv user who wants an own key | 4.0 | 1.5 | 2.5 | 2.0 | A + D's selection card and colour change + C's cited answer blocks + D's library page |
| Build cost and risk in this code | 3.0 | 1.0 | 2.0 | 3.5 | D + A's Notes list, as a fourth reader view (now E) |
| The UI decisions and the Apple guidelines | 4.0 | 2.0 | 2.5 | 3.0 | A + D's card at the mark, library row, and composer after the last answer |

Prototype A now includes the parts the judges asked for: the card at the mark, groups that can be renamed and ordered with written notes, the answer that joins its Highlight, the composer after the last answer, the overlay mode, and the link to D's library Notes page.

What the prototypes do not show: the native sidebar, toolbar, menus, and Settings window are AppKit, and the prototypes show their web twins. Only your eye can judge the AppKit result and the Liquid Glass. The prototypes keep data in memory, use canned answers, paint with `<mark>`, and show only a Pandoc Paper.

My recommendation before your choice was A. You chose **B**. The judges' main points against the first B, and how the B prototype now answers each one:

| Point against the first B | B now |
| --- | --- |
| Cards fold to dots at common widths | The reading column and the margin size together. The margin takes up to 300 px while the text keeps at least 26.75 em of the reading size, so that each full line has at least 45 characters. In the Native shell at the default 1180 pt window with the sidebar shown, the cards show at about 260 px. Below 1131 pt with the sidebar shown, or 881 pt with it hidden (at the 18 px size), cards fold to markers in their Highlight's colour, and a click opens the card beside its marker |
| Each passage has its own thread, so the Chat history is split | All Notes lists every note and every question of the Paper in reading order. It is the one Chat history of the Paper (criterion 10) |
| Close discards a thread, and nothing is stored | A question is stored like a Highlight. Keep as Note makes it a Question Highlight. Discard removes it, and ⌘Z brings it back (criterion 11; the prototype has no undo yet) |
| A question about the whole Paper has no place | It anchors to the first sentence of the passage at the top of the view |
| Ask is always open in a dock | Ask opens only on a click: from a selection, from a card, or from Ask about the Paper |

### 6.1 What B adds to the plan

Your feedback on the B prototype became these requirements:

- **Stored everywhere.** Highlights, Notes, and questions stay after a reload and in the Offline state. Offline, a question card keeps the question and its words and says why it cannot answer.
- **Colour on both sides.** The words of every card show its colour in the Paper, and the card has a stripe in the same colour. An open question marks its words with a dashed outline.
- **The line.** A click on a card, or on a marker, draws a moving dotted line from the card to its words, and the words pulse once. The line follows scrolling and ends on a click elsewhere or on Escape. With Reduce Motion on, the line does not move and the words get an outline.
- **Selections across formulas.** The prototype showed the bug: the browser writes math as styled letters (𝑑 for d), so a stored quote never matched the text. The fix is the one text of 5.4. The selection maps to the text that the search uses.

| ID | Item | Size |
| --- | --- | --- |
| B1 | Margin layout: the reading column and the margin as one unit, cards placed at their words and pushed apart, the active card at its words. It runs again on every Reading preferences change, frame resize, and chapter load | L |
| B2 | Markers below the margin width rule, with a floating card | S |
| B3 | The connector line and the pulse, with Reduce Motion | S |
| B4 | Question cards stored as Highlights with a thread. Keep as Note, Discard with undo, and a whole-Paper question anchored to a passage | M |
| B5 | All Notes: every note and question, with search and the arrangements of 5.5 (position, colour, date, and your own groups). The margin itself always shows reading order | M |
| B6 | Native shell: Ask about the Paper and All Notes as toolbar or menu items, not a web bar | S |

B1 to B6 replace U2 and U3 in the releases below. Release 1 needs B1, B3, B4, and B6 for questions. Release 2 adds the note cards, B2, and B5.

## 7. Plan of action

Sizes for one developer: S is up to 1 day, M is 2 to 4 days, L is a week or more. Each release ships on its own.

### Release 1: Chat and Ask (about 7 weeks)

This release is the brief's opening (own key). Ask needs only the selected text and its passage, not stored Highlights, so the risky anchor work does not block it.

| ID | Item | Size | Depends on |
| --- | --- | --- | --- |
| P1 | Choose the presentation, and answer section 9 | None | None |
| P3 | Done 2026-10-18. Haiku 5.5 and DeepSeek pass criteria 4 to 6: warm first words in 0.95 s and 1.29 s (median), 548 of 550 citations valid, 17 of 20 hand-graded answers fully supported and 3 partly. The local-model run did not run | S | None |
| P4 | Done 2026-10-18. Highlight over MathML: fails, fallback chosen (5.4). PDF selection: fails, scope stays (5.8). A 120 s stream with a 70 s silent gap: passes. ⌘F: covers the Paper and the cards (criterion 15) | S | None |
| C0 | Glossary terms for Chat, Chat model, Ask, and Explain. A `chat_turns` table keyed by Paper, with a migration under `user_version < 2`, and a line in `remove_paper` (`papers/library.py:238-240`). Never name it `messages`, because startup drops that table (`papers/library.py:48-49`) | S | P1 |
| C1 | Chat connection: settings, a Keychain account per role, `has_chat_key`, Test Connection per role, key redaction for both keys, key delete, Copy from Overview and Blog, the Local preset with no key, Context size, the Chat output cap | M | P1 |
| C2 | `Provider.stream()` on both transports, with a text callback, redaction that holds the end of each chunk, and stop by closing the response | M | C1 |
| C3 | Streaming route `POST /api/papers/<id>/chat`, outside the Paper queue. The server holds the history, so a request stays under the 64 KB body limit (`app/server.py:380`). The server speaks HTTP/1.0, so the answer is a body that ends when the connection closes. A disconnect stops the request. P4 showed that the 15 s socket timeout does not stop a silent stream, and that the server sees a disconnect only on the second write after it. So while the provider is silent, the route writes a whitespace byte about every 5 s, and a Stop or a closed page ends the provider request within about 10 s. Remove from Library (`app/server.py:107-113`) and the update check (`app/server.py:99-105`) stop running answers first | M | C2, P4 |
| C4 | Context builder: the cached prefix with a 1-hour Anthropic breakpoint, the selection path with no breakpoint, the turn budget in the model's own tokens, Evidence selection moved out of `Coordinator`, the OpenRouter breakpoint, and a warning before a prompt over 100,000 tokens | M | C3, P3 |
| C5 | Citations: no ranges in the instructions, fix the `p50` match, check after the stream, the unverified mark in `renderProse`, the Chat hover binding, stored quotes | S | C4 |
| C6 | Chat storage per Paper in the C0 table: turns, quotes, model, endpoint (never the key), date, tokens, `document_digest`. Chat survives a reimport. Clear Chat with undo | S | C0, C3 |
| C7 | Failure states: no Chat model (criterion 14), offline, rejected key, rate limit with `Retry-After`, a stopped answer with Retry | S | C3 |
| F5 | Selection toolbar with Ask and Explain: the preview's `place()` takes a rectangle, previews stay closed during a selection, the Paper menu and a context menu get the commands | M | P4 |
| U3 | Question cards in the margin (B1, B3, B4, B6): several quotes per question, Stop, tokens, Copy as Markdown | L | C3, F5 |
| U4a | Native shell for Chat: the panel or view toggle, View menu items, the `editing` flag that keeps ⌘⌫ in a text field (`app/macos/Menus.swift:143-144`), automation identifiers | M | U3 |
| U5 | Settings: the Chat group or pane, in the browser dialog and in the Settings window | S to M | C1 |
| V2 | Live runs: 5 Papers, 10 questions each, with real pauses, through direct Anthropic (OpenRouter's cache is not used today) | S | all above |

Two items move out of Release 1:

- PDF-only Papers get no Chat. The margin mounts only on the DOM Paper view, so Chat on their page text (5.8) moves to a later release.
- No Clear Chat control. `POST /api/papers/<id>/chat/delete` accepts `"all"`, and `/chat/restore` writes back the cards that it removed. A later release adds the control.

### Release 2: Highlights and Notes (about 5 to 6 weeks)

| ID | Item | Size | Depends on |
| --- | --- | --- | --- |
| F1 | Glossary: Highlight, Note, Paper note, Note group, Not found. Keep a user Note apart from the sidebar's `note` row kind (`app/macos/Sidebar.swift:8`) and the Overview node kind `note` (`papers/figures/schema.py:98`) | S | None |
| F2 | Storage: tables for Highlights, Notes, and Note groups, keyed by Paper. Never name a table `passage_search`, because startup drops it. Add them to `remove_paper`. Release 1 rows move into the new table at start; `user_version` stays 1 | M | F1 |
| F3 | The one text, in JavaScript and Python, with the parity test on the corpus. It starts with the anchor spike: exact plus fuzzy matching over the corpus runs | M | F2 |
| F4 | Search again after a reimport: found, moved, not found. Place Again. The per-route gate with an allow-list | M | F3 |
| F6 | Markdown export of Notes, per Paper and per library | S | F2 |
| F7 | Fix the Reading position on arXiv HTML Papers, which looks for `p` plus digits instead of `passage.href` (`app/static/reader.js:296-297`) | S | F3 |
| F8 | Backup: a SQLite backup snapshot before each migration and daily, and JSON export and import of Highlights, Notes, and Chat | M | F2 |
| U1 | Highlights in the Paper: paint, the card at the mark, four named colours, Delete with undo | M | F2, F3, F4 |
| U2 | Note cards in the margin, markers (B2), and All Notes with search (B5). A Paper note | M | U1 |
| U4b | Native shell for Notes: Highlight and Add Note in the Paper menu, keys, VoiceOver labels | S | U2 |
| V1 | The per-route anchor gate (F4) | S | F4 |
| V3 | `tools/native_shot.py` steps: panel open and close, menus, ⌘⌫ in a note field | S | U4b |
| V4 | Screenshots at 700, 1000, 1200, and 1440 pt, with the sidebar shown and hidden | S | U2 |

### Release 3: Notes leave the Paper (about 2 weeks)

| ID | Item | Size |
| --- | --- | --- |
| E1 | EPUB and Send to Kindle: marked quotes and a Notes chapter, EPUBCheck, a check on a real Kindle | M to L |
| E2 | Library Notes page with search and Tags on Notes | M |
| E3 | Offer to copy Highlights from v1 when v2 of a Paper opens | S |

Keep note text and chat text out of the Chrome state. Each state change sends the whole state to Swift (`app/static/shell.js:28-35`), so streamed words would rebuild the menus many times a second.

The cost against the brief: the brief ranks conversion coverage first (section 9.1, item 1). These releases delay it by about three months, unless conversion work runs beside them.

## 8. Risks and the cheapest test

| Risk | If it is wrong | Cheapest test |
| --- | --- | --- |
| You and other readers use Chat inside LocalXiv, although general chat apps exist | Chat is unused, as the old route was | Ship Release 1 to yourself first, and count your questions for two weeks |
| The whole Paper in a cached prefix is fast and cheap enough | Answers are slow or expensive after reading pauses | Passed in P3, with a 1-hour cache on Anthropic |
| A local model is good enough at a 4k context | The Local preset disappoints | Not run in P3: no local server is installed. Three questions stay open: the empty `Bearer` value, the 64,000-token output cap, and answer quality |
| Quote anchors survive a parser change | Highlights move or get lost after an update | F3's anchor spike on the corpus runs |
| The CSS Custom Highlight API paints over MathML in WKWebView | Formulas stay unpainted | Failed in P4. Fallback chosen: a class background on each covered formula (5.4) |
| A long silent stream survives in WKWebView | Answers from reasoning models stop | Passed in P4 (70 s silence). The heartbeat in C3 also covers a later change |
| A Kindle shows the Notes chapter and its links | Notes on the Kindle are hard to use | Send one EPUB with a Notes chapter |

## 9. Your decisions

You answered every question on 2026-10-18. For 4 to 7, 9, and 10 you accepted my recommendation.

| # | Question | Decision |
| --- | --- | --- |
| 1 | Which presentation? | Decided: B · Margin |
| 2 | Release order? | Decided: Chat and Ask first, then Highlights and Notes, then the export |
| 3 | May Chat copy the Overview connection with one button? | Decided: yes, a one-time copy into Chat's own Keychain item. Settings shows which key each role uses |
| 4 | May a Local Chat model run with no key? | Decided: yes. It is the strongest privacy story. C1 removes the key requirement from the three gates in 5.1 for the Local preset |
| 5 | Does Chat see your Highlights and Notes, and the Overview and Blog? | Decided: Highlights and Notes, yes, after the cached Paper (5.2). Overview and Blog, no: the Paper is the source |
| 6 | One Chat thread per Paper, or several? | Decided: one history per Paper. In B, each question is a card beside its words, and All Notes lists every question of the Paper as that one history. Clear Chat has undo |
| 7 | Show tokens on each answer? | Decided: yes. Each answer stores its own tokens in the Chat table (C6), from the usage that `Provider` returns with the text (`papers/ai.py:150`, `:222`). The `usage` cleanup in `docs/cleanup.md` can still run |
| 8 | Why was the old `/chat` route removed? | Answered: it was unused. No interface called it, so the cleanup removed it. The plan stays as written. |
| 9 | Must the features work in browser mode too? | Decided: yes. The web shell is a full twin today (`app/static/shell.js`) |
| 10 | On Remove from Library, delete Notes or export first? | Decided: the Remove dialog offers Export Notes, then deletes |

## 10. How to open the prototypes

The prototypes are throwaway code on the branch `notes-chat-prototype`, in the worktree `.worktrees/notes-chat-prototype`. Nothing is committed yet. Start the server `notes-chat-prototype` from `.claude/launch.json` (port 8790, with a scratch library in `.scratch/localxiv-proto/`), then open `/?variant=A` up to `?variant=E`. The black bar at the bottom switches the variant, the reliability state (No Chat model, Offline, Highlight not found), and the Settings layout. The ← and → keys also switch the variant.

## 11. Research notes

The research ran on 2026-10-18: seven parallel reports (the reader, storage and export, AI and keys, the Native shell, alphaXiv, other readers, and anchoring and chat technology), one completeness check, four judges, and two critics. Each code claim cites `path:line`, and each web claim cites a URL. The reports are in `.scratch/notes-chat-research/`, which git ignores, so they stay on this Mac only.

- **Reader.** The Paper is a same-origin frame with `allow-same-origin allow-scripts` (`app/static/index.html:84`), so the page can read the selection. No selection code exists. The preview's placement already works across the frame boundary (`app/static/reader.js:530-543`).
- **Width.** At the default window, the frame has a gutter of about 127 px beside the text, too small for note text.
- **Old chat.** A `chat` job in the Paper queue with an FTS5 passage search and a 12,000-character question limit. It deleted its messages on a digest change. The web app showed only a job label for it.
- **Caching measured in run logs.** Direct Anthropic: 137 of 326 requests read the cache. Anthropic models through OpenRouter: 0 of 313. DeepSeek: 279 of 306, by its own automatic cache.
- **Request times measured in run logs.** One Evidence selection request: median 9.0 s. One Blog section: median 12.8 s.

### alphaXiv features

Observed on 2026-10-18 on alphaxiv.org (signed out), in its public web-client code, and in its tracker ([alphaXiv/feedback](https://github.com/alphaXiv/feedback)). Signed-in screens come from code and user reports only.

How it works:

- **One popup on a selection** has Ask AI or Note, a model picker, and Translate. Send with an empty input runs Quick explain (`⌘E`). Keys `1` to `7` pick one of seven highlight colours.
- **A Highlight is a private note with an empty body.** It is stored as rectangles on a PDF page, for one paper version.
- **The Notes panel** has one free note for the whole paper (all versions) and a Highlights list in page order, with search.
- **Across papers,** a `/notes` page lists note cards by paper. The app has no link to it, and it has no tags, colour filter, or search.
- **The Assistant panel** docks right at about 47% of the window, or left, floating, or full screen. A selection becomes a quote chip with its page. Answers have "Jump to page N" chips, and Resume reading goes back.
- **Chat history** belongs to one paper version. Chats started from a highlight do not show in the main history ([#376](https://github.com/alphaXiv/feedback/issues/376)).
- **Export:** a PDF with annotations, and chat as Markdown to the clipboard. No Markdown export of notes, no Zotero, no EPUB.
- **Limits:** a 5-hour and a 7-day window, shown as a percentage with no published numbers.

What its users report (107 of 423 tracker issues are about these features):

| Group | Issues | Examples |
| --- | --- | --- |
| Chat interface (scroll, keys, panel, search in chat) | 23 | [#293](https://github.com/alphaXiv/feedback/issues/293) no search in chat, [#397](https://github.com/alphaXiv/feedback/issues/397) half the screen only |
| Chat history lost, hidden, or split by version | 12 | [#89](https://github.com/alphaXiv/feedback/issues/89) chats lost in a migration, [#289](https://github.com/alphaXiv/feedback/issues/289) history on the old version |
| Chat outages | 11, with 29 reactions | [#181](https://github.com/alphaXiv/feedback/issues/181), [#219](https://github.com/alphaXiv/feedback/issues/219), [#249](https://github.com/alphaXiv/feedback/issues/249) |
| Notes arrangement and export | 10, 6 open | [#209](https://github.com/alphaXiv/feedback/issues/209) see every note, [#267](https://github.com/alphaXiv/feedback/issues/267) Markdown export |
| Quota and paywall | 10 | [#259](https://github.com/alphaXiv/feedback/issues/259) one request used a weekly limit |
| Highlight bugs and requests | 15 | [#157](https://github.com/alphaXiv/feedback/issues/157) no highlight without a note, [#420](https://github.com/alphaXiv/feedback/issues/420) no colour change, [#176](https://github.com/alphaXiv/feedback/issues/176) gaps over equations |
| Own key or endpoint | 7, with 18 reactions | [#232](https://github.com/alphaXiv/feedback/issues/232) "No plans", [#269](https://github.com/alphaXiv/feedback/issues/269) privacy of unreleased work |
| Chat reads only some pages | 5 | [#168](https://github.com/alphaXiv/feedback/issues/168), [#202](https://github.com/alphaXiv/feedback/issues/202) |

What this plan takes from it: one-step Explain, one free Paper note, Highlights in reading order with search, one Chat history per Paper that includes selection chats, a Highlight in one click with a colour change later, the whole Paper as context, and a library Notes page with tags and search.
