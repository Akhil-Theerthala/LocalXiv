# The v0.1.0 intro film: read first, ask in the margin

Date: 2026-10-22. Main at `5f6e20b`. No branch: this spec goes on `main`, as the owner asked, so that it moves with the code to a new device.

Source: [the positioning research of 2026-10-22](../../positioning-research-2026-10-22.md), cited below as "research 5.5" for its Section 5.5. Its Section 10 corrections are applied to its Sections 1–9. Also [the v0.1.0 release notes](../../releases/v0.1.0.md), [`CONTEXT.md`](../../../CONTEXT.md), [`tools/intro-video`](../../../tools/intro-video/), and the code at `5f6e20b`. Three storyboards (ONE SITTING, Your call, The margin) went to three judges: a launch marketer, a motion designer, and an honesty and feasibility check. This spec builds on the winner and applies the judges' grafts and must-fixes.

Status: design for the owner's review. Section 9 lists the decisions that are the owner's. Nothing is captured, rendered, or posted until the owner answers them. Section 10 lists the calls that this spec makes, which the owner can change.

## 1. Intent

### 1.1 The target viewer

The owner's words: "My target is the people who want controlled reading i.e., read before asking AI, the platform is reader-centric and lets people interact with AI tools only when they want to. This should let them know that there's a simpler way to think of reading stuff and if possible push them to use my tool."

So the viewer is a researcher or an ML engineer who reads papers and already uses AI. Most of them check AI claims against the source (research 3.2). They scroll X or LinkedIn on a phone with the sound off. They do not want a lecture against AI (research 3.5).

### 1.2 The one message

**There is a simpler way to read a paper: read it, mark it, ask when you choose, and keep your Notes. LocalXiv is the free Mac reader built that way.**

The film shows the message in its order. The reader reads and marks for 33 s before the first AI request. The first AI request is a click that the viewer sees the reader choose. The answer lands beside the words and points back to the page.

### 1.3 What success looks like

Before posting (a cheap test, inference): three to five people who do not know LocalXiv watch the master on a phone with the sound off. Each one can say (1) what LocalXiv is, (2) that AI comes only when the reader asks, and (3) where to get it.

After posting, measure these at 48 hours and at 7 days (research 6.6):

| Measure | Where | Baseline on 2026-10-22 |
| --- | --- | --- |
| Views, likes per 1,000 views, link clicks | X and LinkedIn analytics | — |
| GitHub stars | `gh api repos/Akhil-Theerthala/LocalXiv` | 2 stars |
| DMG downloads of v0.1.0 | the release assets' `download_count` | 2 downloads |
| New issues and papers that convert badly | GitHub issues, replies | — |
| Votes and replies for Linux | the Linux issue (Section 8.7), replies | — |

Expect hundreds to a few thousand views on X for an account of this size (research 6.6). Compare only with launches of similar reach, such as Pond and Textfold (research 6.5, 6.6). Success is movement above the baseline, replies that repeat the message, and real paper reports. The research gives no target numbers, so this spec sets none.

## 2. Goals, non-goals, anti-goals

**Goals**

1. A 90 s 16:9 master that works with the sound off, on a phone, at 720p.
2. Show the features of v0.1.0 that serve controlled reading: Reading preferences, Reference preview, Highlights in four named colours, Notes in the margin, Ask with a Question card, citations that open the passage, several quotes in one question, the Chat model, All Notes, the library Notes page with `#tags`, and Export EPUB with Notes.
3. Show how a Highlight is made and how Ask works inline, at a size a phone can read.
4. Put LocalXiv's name and category on screen by 3.6 s, and end on one action (the URL) with the Linux line last.
5. A 25 s Ask cutdown, thread clips, stills for a LinkedIn carousel, a thumbnail, and post drafts for X and LinkedIn.

**Non-goals**

- Paper search, Direct import, the bookmarklet, Explain, and Copy Notes from an older version. They are optional inserts (Section 6.5).
- A voice-over, a face on camera (Section 10), subtitles files.
- A Linux build, or any change to the app. Section 8.7 lists fixes outside the film as recommendations.

**Anti-goals: the film fails, even if it renders, if it does one of these**

| Anti-goal | Why it fails |
| --- | --- |
| Preaches against AI ("stop using AI", "AI makes you dumb") | Researchers who use AI push back (research 3.5). The film says "when you ask", never "never". |
| Shows an AI answer that a real model did not write, or edits one | It breaks the honesty limits. Every word in a Question card is real output (Section 7.5). |
| Calls Chat an agent | Chat sends one streamed request with no tool calls (research 4.3, 4.5). |
| Leads with Kindle | The owner said Kindle is not the main feature. Kindle is one beat at 77 s. |
| Has text a phone cannot read | Most viewers watch muted on a phone. Section 4.2 sets the floor. |
| Says "any paper", "every paper", "only", "first", "nothing leaves your Mac", or "no account" with no qualifier | Each one is false or not proven (research 4.5). |
| Shows UI that Mac users never see, or a drawn Mac window | The capture is the web shell in headless Chromium. The film crops to the content (research 5.10). |
| Shows the sample Paper's figures or tables | Its licence allows that reuse only in journalistic or scholarly works (research 5.10). |
| Promises Linux with a date | The repository has no Linux code (research 5.8). |

## 3. Message and words

### 3.1 The simple model of reading

**Read. Mark. Ask. Keep.**

- **Read:** the Paper itself, in your font, size, and theme. You check a reference and keep your place.
- **Mark:** your judgement, in four named colours (Key point, Question, Use in my work, Disagree), with Notes beside the words.
- **Ask:** when you choose, about the words that you select. The answer lands in a Question card beside them, and its citations open the passage.
- **Keep:** every Highlight, Note, and Question card, in All Notes, on the library Notes page, and in the EPUB.

The order is the message: AI is the third verb, not the first. In the film the verbs fill a small strip one at a time. At the close they come together as one line that a viewer can repeat.

### 3.2 Tagline

- In the film: "Read. Mark. Ask. Keep." (the four verbs, and the end-card subtitle).
- In the posts, the thumbnail, the carousel, and the README: tagline A, "Read the paper. Ask in the margin." (research 4.4). One exact-phrase search found no other use of it; that is not proof (research 8.2). Decision 5.

### 3.3 Card vocabulary

All cards of the master, in order. Each card has at most 6 words, except the name card. The words use the terms of `CONTEXT.md` exactly.

| # | Card | Scene | Why it is true |
| --- | --- | --- | --- |
| 1 | AI waits until you ask. | S01 | "Generate an Overview after importing" is off by default (`app/server.py:40`). Chat runs only on Ask. |
| 2 | LocalXiv / A Mac reader for arXiv papers. | S01 | The category of research 4.1. |
| 3 | Your font. Your size. Your theme. | S02 | Reading preferences. |
| 4 | Check a reference. Keep your place. | S03 | A Reference preview does not move the Reading position (`CONTEXT.md`). |
| 5 | You decide what matters. | S04 | Pillar 2 of research 4.3. |
| 6 | Notes sit beside the words. | S05 | Margin cards. |
| 7 | So far, no AI. | S06 | S01–S06 make no provider call. The conversion makes none. |
| 8 | Ask about the words you chose. | S06 | Ask is a question about the selected passage. |
| 9 | A Question card, beside the words. | S06 | `CONTEXT.md`, Question card. |
| 10 | Citations open the passage. | S07 | Research 4.5: not "every answer shows its source". |
| 11 | Your key. Or your Mac's model. | S08 | The Chat model presets, Local included. |
| 12 | No LocalXiv account. | S08 | Research 4.5: never "no account" with no qualifier. |
| 13 | Several quotes. One question. | S09 | Never a number: Add Quote hides after 4 added quotes. |
| 14 | Overview and Blog, if you ask. | S10 | Both are optional. |
| 15 | All Notes for this Paper. | S11 | — |
| 16 | Every Note, across your library. | S12 | Only with 2 or more Papers that have Notes. Else "Every Note, in one place." |
| 17 | Your Notes stay on your Mac. | S12 | Storage. The posts say what Chat sends. |
| 18 | Export EPUB with Notes. | S13 | The menu item's name. |
| 19 | Or Send to Kindle. | S13 | One beat. Nothing is sent. |

Other film text: the colour labels "Disagree", "Use in my work", and "Question" (S04); the verb strip "Read · Mark · Ask · Keep"; the hero line "Read. Mark. Ask. Keep." (S14); and the end card (S15): "LocalXiv", "Free and open source", "No LocalXiv account", "Apple Silicon · macOS 26 or newer", `github.com/Akhil-Theerthala/LocalXiv`, and the Linux line "Coming soon to Linux" (Section 10).

### 3.4 Words to use, and words never to use

Use (research 3.5, 4.5): "read, then ask"; "ask about the lines you do not understand"; "check the passage"; "Ask" and "Chat"; "your key, or a model on your Mac"; "no LocalXiv account"; "your library, Notes, and keys stay on your Mac"; "reflowed from the paper's LaTeX source or arXiv's HTML"; "83 of 100 papers in our test corpus open as reflowed text"; "no analytics library in the code"; "a free app; use your own key, or a model on your Mac"; "citations open the passage"; "found it on arXiv or alphaXiv? Read it in LocalXiv."

Never use (research 4.5, 10.3):

| Never | Say instead |
| --- | --- |
| "agent", "AI agent" | "Ask", "Chat" |
| "nothing leaves your Mac" | "your library, Notes, and keys stay on your Mac" |
| "any paper", "every paper" | "83 of 100 papers in our test corpus open as reflowed text" |
| "only", "first" (as a claim about LocalXiv) | "no product we found" in long text, or nothing |
| "no account" | "no LocalXiv account" |
| "no analytics" | "no analytics library in the code" |
| "accurate answers", "no hallucinations", "every answer shows its source" | "Citations open the passage." "Answers can be wrong." |
| "free AI" | "a free app; the provider charges for each request" |
| "find papers anywhere" | "found it on arXiv or alphaXiv?" |
| "works with VoiceOver" | nothing, until a test runs |
| "local-first", "chat with your paper", "understand a paper in minutes", "close reading" as a lead | tagline A |
| "cognitive debt", "brain rot", "AI makes you dumb", the MIT "Your Brain on ChatGPT" preprint | nothing |
| A date for Linux, or a promise of a Linux build on a date | "Coming soon to Linux", with no date (Section 10) |

The film and the main posts name no rival (research 4.6).

### 3.5 Prepared replies

Post these only as replies, politely and with facts (research 4.6):

- **"Why not alphaXiv?"** "alphaXiv is good for finding papers and for summaries. LocalXiv is where you read the paper itself, on your Mac, with your own key and your Notes. Found it on alphaXiv? Paste the link into LocalXiv."
- **"Why not Hugging Face Papers?"** "Hugging Face Papers helps you find and rank papers and links the code. Then it links out to the PDF. LocalXiv is the reader for after that: the paper as text, your Highlights and Notes in the margin, and Ask when you choose." (Say "found it on Hugging Face" only after Direct import accepts Hugging Face links, Section 8.7.)
- **"arXiv has HTML now."** "Yes, and LocalXiv uses it for some papers. LocalXiv adds your reading settings, a library on your Mac, Highlights and Notes in the margin, Ask, and EPUB export."
- **"Zotero 10 reflows PDFs now."** "Yes. LocalXiv builds the page from the paper's LaTeX source, or from arXiv's HTML, so equations are typeset."
- **"Is it an AI agent?"** "No. Ask sends one request with the Paper's text, your Highlights and Notes, and your question to the model you choose. The answer cites passages, and you open them to check."
- **"Does my data leave my Mac?"** "Your library, Notes, and keys stay on your Mac. When you Ask, Chat sends the Paper's text, your Highlights and Notes, and your question to the provider you choose, or to a model on your Mac. The app also contacts arXiv, Semantic Scholar, doi.org, and the update feed."

## 4. Deliverables and format

### 4.1 Deliverables

| Deliverable | Format | Length | Use |
| --- | --- | --- | --- |
| Master | 1920×1080, 60 fps, H.264 and AAC MP4 | 90.0 s = 180 beats = 5,400 frames | X main post, LinkedIn post, GitHub README link |
| Ask cutdown | 1920×1080 MP4 | 25.0 s = 50 beats | X reply 1, a later single-feature X post. Not on LinkedIn: videos under 30 s did 6.7% worse there (research 5.9). |
| Thread clip: Highlights | 1920×1080 MP4 | 15 s | X reply 2 |
| Thread stills | 1920×1080 PNG | — | X reply 3 (Chat pane on Local), reply 5 (end card) |
| 4:5 master (optional) | 1080×1350 MP4 | 90.0 s | A LinkedIn test, a week after launch |
| Thumbnail | 1920×1080 PNG | — | Upload on X desktop and on LinkedIn |
| Carousel | 12 slides, 1920×1080 PNG, joined as one PDF | — | LinkedIn, 2–4 days after launch |
| One still | 1920×1080 PNG | — | LinkedIn image post, about a week after launch |
| README loop | silent MP4, GIF fallback | 12 s | README, if the owner changes it (Section 8.7) |

The master is 90 s, inside the 60–90 s that research 5.1 recommends and under the 140 s limit of a free X account.

### 4.2 Type and caption rules for phones

The film has no voice, so the cards are the captions (research 5.5).

| Element | Font and size at 1080p | Cap height | Place |
| --- | --- | --- | --- |
| Card | Avenir Next Demi Bold 84 px, INK `#272820` | about 60 px | Lower-left band: left edge x = 115 px, bottom edge y ≤ 880 px |
| Name card | Icon 72 px, "LocalXiv" and the category line, both 84 px | about 60 px | Lower-left band, two lines |
| Colour label | Avenir Next Demi Bold 56 px in the colour's own ink, on a PAPER slip | about 40 px | Left gutter, with a 1.5 px leader line to the mark |
| Verb strip | Avenir Next Demi Bold 64 px; current verb in ACCENT `#3f573d`, earlier verbs in INK at 45% | about 45 px | Top-left: x = 115 px, top y = 65 px |
| Hero line (S14) | Avenir Next Demi Bold 160 px; full stops in ACCENT | about 113 px | Centre |
| End card | Wordmark 110 px; every other line 56 px or more; URL pill Menlo 64 px; Linux line 64 px | ≥ 40 px | Centre stack between y = 65 px and y = 880 px |

Rules:

- **Card surface.** One Card component: a PAPER `#fffdf7` scrim at 94%, radius 18 px, a 1 px LINE `#dedbcf` border, shadow `0 12px 30px #1f281714`. At most 2 lines and 42 characters a line. The card zone is 240 px tall, so two lines of 84 px fit.
- **Hold.** Each card stays at full opacity for at least max(1.2 s, 0.35 s a word). The fade does not count. A 6-word card needs 2.1 s (research 5.5). Section 5 gives every card's times, and a script checked them.
- **Contrast.** 4.5:1 or more against the worst background under the letters. INK on PAPER is 14.6:1. ACCENT and PAPER are 7.8:1. MUTED `#646456` on PAGE is 5.3:1. The four Highlight inks on PAPER are 5.2–5.6:1. INK at 70% on PAGE is 5.3:1, and MUTED at 70% is 2.9:1, so the end card uses INK for every line and dims to 70%, not lower.
- **Safe areas (16:9).** 6% (115 px) at each side. Nothing the viewer must read below y = 880 px: player controls cover the bottom 10–17% (research 5.2). No card covers the cursor's target. When the action is in the lower-left, the card moves to the top band.
- **Text zones.** At most two at once: the verb strip and the lower-left card, or the gutter labels and the lower-left card. No keycaps, no menu-path chips.
- **Size floor.** Nothing that the viewer must read is under 56 px font size (about 40 px cap height). Paper text and app text under 2x zoom are texture; the cards carry the meaning.
- **Captions files.** Upload no `.srt`. Turn off LinkedIn auto captions for this film (research 5.5).

### 4.3 Motion rules

- **Cards.** Enter: opacity 0 to 1 and a 12 px rise, 200 ms, ease-out `(0.16, 1, 0.3, 1)`. Exit: opacity 1 to 0 and a 6 px rise, 150 ms, ease-in `(0.7, 0, 0.84, 0)`. No word or letter stagger on any card.
- **One stagger, one spring.** The end-card wordmark rises letter by letter, 2 frames apart. The end-card icon fans out with the existing spring. Nothing else staggers, bounces, tilts, or overshoots.
- **Camera.** The existing `Camera` with ease-in-out `(0.65, 0, 0.35, 1)`. Moves take 400–500 ms, except the S14 pull-back (1.8 s). Zoom changes are at least 3 s apart. 2x is the default; 1.5x when the words and a margin card must share the frame. No zoom above 2.2x, so a capture at deviceScaleFactor 3 is never upscaled (upscale = 1.333 × zoom ÷ 3). A cut is not a zoom move.
- **Still under text.** The camera does not move while a Note or a question is typed, or while an answer streams. It pans only when a growing card leaves the frame.
- **Jumps are cuts.** A citation click and Back are instant in the app (`window.scrollTo` in `app/static/reader.js`), so the film cuts on the click. It never pans "with the jump".
- **App popovers.** The selection toolbar, the Highlight bar, and the previews use the captured frames. Where stills replace video: opacity and scale 0.97 to 1 from the anchor, 160–200 ms, ease-out. Dialogs open from the centre. The film adds no transition that the app does not have.
- **Cursor.** Drawn in stage space, outside the camera, at a constant 44 px height (the current 34×44 arrow), and an I-beam over text. Paths are quadratic arcs of 500–900 ms, ease-in-out, from the recorded real path. A press scales the cursor to 0.94 for 100 ms and shows one 2 px ring that grows from 0.6 to 1.4 in 300 ms. The cursor hides after 0.6 s idle.
- **Ellipsis dip.** A wait is cut with a visible 4-frame dip to PAGE `#f5f1e8`. A stream is never sped up.
- **Flashes.** The only flash is the app's passage flash. The film has no photosensitivity risk.

### 4.4 Music and sound

- The music is made in code by `music.mjs`, with no samples, so it needs no licence (research 5.7). Keep D major, I-V-vi-IV, 120 BPM, and the shared beat grid of `src/timeline.mjs` (1 beat = 0.5 s = 30 frames).
- The music follows the acts: Read is a pad, a soft pluck arpeggio, and a soft kick on bar downbeats. Mark adds quiet closed hi-hats. Before the Ask click the drums drop out and the pad holds a suspended chord. The full kick and bass enter on the click. Keep is a lighter groove. At the close the drums stop.
- The four Highlight colours each play one note of a rising D–F#–A–D arpeggio: Key point D, Disagree F#, Use in my work A, Question high D. The motif comes back as the four verbs gather.
- The Linux line gets one high bell on G that does not resolve.
- UI sounds (ticks, plucks, a pen stroke) are made in code and sit about 18 dB under the music.
- Master at −14 LUFS integrated, with true peaks at −1 dBTP or lower (research 5.7).
- The film works with the sound off. The cards carry the story.

## 5. Storyboard

### 5.1 Structure

| Act | Time | Scenes | Strip |
| --- | --- | --- | --- |
| Hook and name | 0.0–6.5 s | S01 | — |
| Read | 6.5–17.0 s | S02–S03 | Read |
| Mark | 17.0–29.0 s | S04–S05 | Read · Mark |
| Ask | 29.0–65.5 s | S06–S10 | Read · Mark · Ask |
| Keep | 65.5–79.0 s | S11–S13 | Read · Mark · Ask · Keep |
| Close | 79.0–90.0 s | S14–S15 | gathers into the hero line |

The Paper is the bundled sample, Attention Is All You Need (`1706.03762v7`), chapter `ch004`, section 3.2.1, text only (Decision 2). Every record of the film sits in passages p00019–p00024, so the S14 pull-back shows them all at once. After S02 the reading state is Charter, 20 px, Sepia.

The verb strip shows for about 3 s at each act change, then fades. It is not on screen the rest of the time.

### 5.2 Scene table

Times are in seconds from the start. Beats are counted from 0 at 120 BPM. A script checked that the scenes are contiguous and sum to 180 beats, that every card meets its hold, that zoom moves are at least 3 s apart, that no card is on screen during a stream, and that no more than two text zones show at once.

| Scene | Time | Beats | On screen | Camera | Cards (full opacity) | Sound accent | Capture |
| --- | --- | --- | --- | --- | --- | --- | --- |
| S01 Hook and name | 0.0–6.5 | 0–13 | Frame 0 mid-drag on p00020. The toolbar. The cursor rests on Ask, then picks Key point. | 2.2x; pull to 1.5x at 3.2 | "AI waits until you ask." 1.1–3.2. Name card 3.6–6.2. | Pad from frame 0; suspended G on Ask; pluck D on Key point (b6) | Real drag, toolbar, Ask hover, paint |
| S02 Your page | 6.5–12.5 | 13–25 | Font, size 16→20, theme Sepia. The passage stays in place. | Locked 1.5x; pull to 1.2x at 10.5 | "Your font. Your size. Your theme." 9.7–11.8 (phrases from 7.0) | Ticks b14, b16–17.5; pad warms b19 | `prefs`, `text-size` states |
| S03 Reference preview | 12.5–17.0 | 25–34 | Hover [2] in p00023; the bibliography entry. | Pan; push to 2.0x at 13.6; pull to 1.4x at 16.6 | "Check a reference. Keep your place." 14.3–16.4 | Paper lift at 13.95 | Hover state |
| S04 Three more colours | 17.0–24.0 | 34–48 | Disagree, Use in my work, Question, each with a gutter label. | 1.4x, small pans | Labels 18.8–23.6. "You decide what matters." 22.2–23.8 | Plucks F# b37, A b40, high D b43 | Three real drags |
| S05 A Note | 24.0–29.0 | 48–58 | Highlight bar on Question; Note; type; Save. | Push to 2.0x at 24.5; pull to 1.5x at 28.3 | "Notes sit beside the words." 28.1–29.9 | Key ticks; Save A then D (b56) | Click, Note, typing, Save |
| S06 Ask | 29.0–43.5 | 58–87 | Drag; the toolbar; 1.5 s of stillness; click Ask (b66); type; Enter; dip; the answer streams; the Note above the answer. | 1.5x; 2.2x at 33.1; still during the stream; 1.5x at 41.5 | "So far, no AI." 30.8–32.4. "Ask about the words you chose." 34.0–36.1. "A Question card, beside the words." 41.8–43.9 | Drums out b61; full kick and bass on the click b66; settle b82 | The take (Section 7.5) |
| S07 Citation | 43.5–49.5 | 87–99 | Hover a chip; preview; click (cut); flash; Back (cut); push into "· this Mac ·". | 2.0x at 44.5; 2.2x at 47.9 | "Citations open the passage." 46.3–47.7 | Pluck b92; swell b95 | Preview, flash frames, Back |
| S08 Chat model | 49.5–54.5 | 99–109 | Match cut to the Chat pane on Local; one provider a beat; back to Local. | 1.6x static; cuts | "Your key. Or your Mac's model." 50.6–52.7. "No LocalXiv account." 53.2–54.4 | Thump b99; ticks b101–105; pluck b106 | Seven pane states |
| S09 Several quotes | 54.5–62.0 | 109–124 | Add Quote; drag in p00023; Add to Question; type; Enter; dip; the first words stream; cut. | 1.6x; 2.0x at 56.6 | "Several quotes. One question." 56.9–58.6 | Double pluck b113; bell b119 | The second take |
| S10 Overview and Blog | 62.0–65.5 | 124–131 | The Overview, then the Blog with its model line. | 1.0x drift to 1.08x | "Overview and Blog, if you ask." 62.4–64.5 | Whoosh b124, b127.5 | Saved views |
| S11 All Notes | 65.5–70.0 | 131–140 | All Notes over the Paper; the colour arrangement. | 1.2x; 1.4x at 66.4 | "All Notes for this Paper." 66.8–68.6 | Thup b132; tick b135 | Dialog states |
| S12 Notes page | 70.0–75.0 | 140–150 | The library Notes page; the `#attention` toggle. | 1.2x; 1.4x at 71.6 | "Every Note, across your library." 70.5–72.3. "Your Notes stay on your Mac." 72.7–74.8 | Pluck b143 | Page states |
| S13 EPUB with Notes | 75.0–79.0 | 150–158 | A marked EPUB page and its chapter; the Send to Kindle dialog. | 1.0x; cut to 1.3x | "Export EPUB with Notes." 75.4–76.9. "Or Send to Kindle." 77.3–78.7 | Whoosh b150; thup b154 | EPUB render, dialog |
| S14 Full margin | 79.0–83.0 | 158–166 | Pull back over p00019–p00024 with every record; the verbs gather. | 2.0x to 0.75x at 79.0 (1.8 s) | Hero line from 81.5 | Drums stop b158; motif b162–163.5 | Tall full-page capture |
| S15 End card | 83.0–90.0 | 166–180 | Icon, wordmark, verbs, chips, platform, URL; dim; the Linux line last. | None | End-card lines; Linux line 87.8–90.0 | Chord b166; bell on G b175 | None |

### 5.3 Scenes

Each card has an enter time, a full-opacity window, and an exit that ends 0.15 s after the window. "b" is a beat on the whole timeline.

**S01 Hook and name (0.0–6.5 s, b0–13).** The Paper view of the sample, chapter `ch004`, SF Pro 16 px, Light. No window chrome. Frame 0 is mid-gesture: the I-beam drags across the third sentence of p00020, "We compute the dot products of the query with all keys, divide each by √d_k, and apply a softmax function to obtain the weights on the values." Three words are already selected at frame 0, and the selection grows word by word. At 0.6 s the drag ends and the real selection toolbar appears above the words: four colour swatches, Note, Ask, Explain, and Copy. From 0.75 to 1.35 s the arrow moves on an arc to Ask. From 1.35 to 2.25 s it rests on Ask, and Ask shows its hover state. From 2.25 to 2.85 s it moves back past Note to the Key point swatch. At 3.0 s (b6) it clicks: the words paint in Key point and the toolbar closes. The camera starts at 2.2x, framed so that the selection and the toolbar sit in the upper right two thirds and the lower left is clear for the card, and it drifts 12 px a second. From 3.2 to 3.7 s it pulls back to 1.5x, so the painted sentence and the empty margin share the frame. Card "AI waits until you ask." enters at 0.9 s, is full from 1.1 to 3.2 s, and exits by 3.35 s. The name card enters at 3.4 s: the app icon (static, 72 px) beside "LocalXiv", and "A Mac reader for arXiv papers." below it. It is full from 3.6 to 6.2 s and exits by 6.35 s. Sound: the pad on D already sounds at frame 0, with a low pluck arpeggio; a soft high tick when the toolbar appears; a suspended G over D while the cursor rests on Ask; a plucked D and a paper tap on the Key point click, which resolve the suspension. Ask and Explain are on screen and not used; no AI runs. This is the pass over Ask that S06 pays off.

**S02 Your page (6.5–12.5 s, b13–25).** The strip shows "Read" (6.5–9.65 s). The camera is locked at 1.5x on p00020, which is the top passage at the frame line. At 7.0 s (b14) the font changes from SF Pro to Charter. At 8.0, 8.25, 8.5, and 8.75 s (b16–17.5) the text size steps from 16 to 20 px, one ⌘+ each. The lines rewrap, but the Key point sentence stays at the same height, because v0.1.0 keeps the passage that the reader reads in place. Equation (1) in p00022 stays typeset. At 9.5 s (b19) the theme changes from Light to Sepia. From 10.5 to 11.0 s the camera pulls back to 1.2x to show the column, the equation, and the empty margin. Each change is a crossfade between two real captures: 150 ms for the font and the size, 250 ms for the theme. The cursor is hidden, and no control shows. The card builds with the real changes: "Your font." at 7.0 s, "Your size." at 8.0 s, "Your theme." at 9.5 s. The full line is at full opacity from 9.7 to 11.8 s and exits by 11.95 s. Sound: a soft kick on bar downbeats from b16; a tick on the font change; four rising ticks on the size steps; the pad filter opens a little on Sepia. Charter 20 px Sepia stays for the rest of the film. The Mac app shows these settings in a native popover, which the web capture does not have, so the film shows the effects only.

**S03 Reference preview (12.5–17.0 s, b25–34).** From 12.5 to 13.0 s the camera pans down to p00023 at 1.2x. From 13.0 to 13.6 s the cursor moves to the citation [2] in p00023 and rests. At 13.95 s, after the app's 350 ms delay, the Reference preview opens over the passage and shows the bibliography entry (Bahdanau, Cho, and Bengio). From 13.6 to 14.05 s the camera pushes to 2.0x on the line and its preview, and it holds. At 16.3 s the cursor moves off, and the preview closes 550 ms later. The page never moves. From 16.6 to 17.1 s the camera pulls back to 1.4x on p00023 and p00024 with both gutters. Card "Check a reference. Keep your place." is full from 14.3 to 16.4 s. Sound: a soft paper lift as the preview opens. The film never hovers the "(Figure 2)" link in p00020 or a table link.

**S04 Three more colours (17.0–24.0 s, b34–48).** The strip shows "Read · Mark" (17.0–20.15 s). The camera is at 1.4x on p00023 and p00024, with small pans of 120 px or less (400 ms) that follow the cursor and no zoom change. Three short drags, each with the toolbar and one swatch on a beat:

1. 17.5–18.2 s, p00023: "dot-product attention is much faster and more space-efficient in practice, since it can be implemented using highly optimized matrix multiplication code." Toolbar at 18.3 s. Disagree at 18.5 s (b37).
2. 18.9–19.6 s, p00024: "additive attention outperforms dot product attention without scaling for larger values of d_k [3]". Toolbar at 19.7 s. Use in my work at 20.0 s (b40).
3. 20.4–21.2 s, p00024: "We suspect that for large values of d_k, the dot products grow large in magnitude, pushing the softmax function into regions where it has extremely small gradients". Toolbar at 21.3 s. Question at 21.5 s (b43).

Each new mark gets a label in the left gutter, in its colour's ink on a PAPER slip, with a leader line to the mark. "Disagree" is full from 18.8 s, "Use in my work" from 20.3 s, "Question" from 21.8 s; all three are full until 23.6 s and exit by 23.75 s. Card "You decide what matters." is full from 22.2 to 23.8 s. The drags are faster than in S01, because the reader now knows the tool. Sound: quiet closed hi-hats join at b34; each click plays one pluck: F# for Disagree, A for Use in my work, high D for Question. With the D of the hook's Key point, the four colours spell a rising D-major arpeggio. The labels are film graphics. The app names a colour in its own Highlight bar, which S05 shows.

**S05 A Note (24.0–29.0 s, b48–58).** From 24.0 to 24.4 s the cursor moves to the Question words. At 24.5 s a click with no movement opens the Highlight bar at the words: the name "Question", the four swatches with Question pressed, Note, Ask, and Delete. From 24.5 to 24.95 s the camera pushes to 2.0x on the bar and the mark. At 25.0 s (b50) the cursor clicks Note, and the Note editor opens as a card in the margin beside the words. From 25.2 to 25.65 s the camera pans right to the card, with no zoom change. From 25.7 to 27.5 s the reader types "A guess, not a result. #attention"; the camera is still. At 28.0 s (b56) the reader saves, and the card settles beside its words. From 28.3 to 28.8 s the camera pulls back to 1.5x, so the paragraph and its Note share the frame. Card "Notes sit beside the words." is full from 28.1 to 29.9 s. Sound: very soft key ticks (−24 dB); on Save, a two-note pluck, A then D. The Note is the reader's own text, typed by the capture. Its `#attention` tag comes back in S12.

**S06 Ask (29.0–43.5 s, b58–87).** The hero scene. At 1.5x, from 29.3 to 30.1 s, the reader makes one slow drag over the next sentence of p00024: "To counteract this effect, we scale the dot products by 1/√d_k." At 30.3 s the same toolbar as in S01 appears. From 30.4 to 30.9 s the cursor moves up and stops in the gap between the swatches and Note, with no hover. From 30.9 to 32.4 s nothing moves. Card "So far, no AI." is full from 30.8 to 32.4 s. From 32.5 to 32.75 s the cursor moves to Ask, and Ask shows its hover state. At 33.0 s (b66) the reader clicks Ask. The strip shows "Read · Mark · Ask" from the click to 36.15 s. A Question card opens in the margin below the Note card: the quote, the field with "Ask about these words", the Ask button, and the host line "Asks a model on this Mac (127.0.0.1). Answers can be wrong. Check the cited passages." From 33.1 to 33.6 s the camera pans and zooms to 2.2x on the Question card. From 34.0 to 35.6 s the reader types "Why does this scaling help?". Card "Ask about the words you chose." is full from 34.0 to 36.1 s. At 36.0 s (b72) the reader presses Return: Ask becomes Stop, and "Reading the Paper…" shows. At 36.75 s a 4-frame dip to PAGE cuts the wait. From 36.8 to 41.0 s the answer streams at the captured speed, line by line, with its citation chips. No film card is on screen, and the camera is still; it pans only if the card grows past the frame. If the real stream ends before 41.0 s, the finished answer holds. If it runs past 41.0 s, one more dip cuts inside the stream. At about 41.0 s the answer ends: Stop becomes Ask, and the provenance line shows "<model> · this Mac · <date>". From 41.5 to 42.0 s the camera pulls back to 1.5x: the Question Highlight with the reader's Note above it, and the Question card with the AI answer below it, beside the words. Card "A Question card, beside the words." is full from 41.8 to 43.9 s. Sound: at b61 (30.5 s) the drums and the arpeggio drop out, and the pad holds a suspended chord (Dsus4) with no riser. At b66 the click lands with the first full kick, the bass, and a soft bell, and the chord resolves to D. The arpeggio stops at Return and comes back on b74, after the first words. A small settle chord at b82. Every word in the card is real output of the model that the provenance line names (Section 7.5). The film never edits it, retypes it, or speeds it up, and no card claims speed.

**S07 Citation (43.5–49.5 s, b87–99).** From 43.5 to 44.0 s the cursor moves to the first citation chip of the answer and rests. At 44.35 s the passage preview opens from the chip: the section name, the passage text, and Open in Paper. From 44.5 to 44.95 s the camera pushes to 2.0x on the chip and its preview, and it holds to 46.0 s. At 46.0 s (b92) the reader clicks. The film cuts on the click to the cited passage at 2.0x, because the app jumps at once, and the passage flashes for 1.2 s. Card "Citations open the passage." is full from 46.3 to 47.7 s. At 47.5 s (b95) the reader goes Back (⌘[), and the film cuts back to the Question card at 2.0x. From 47.9 to 48.4 s the camera pushes to 2.2x on the provenance line, centred on "· this Mac ·", and holds to 49.5 s. Sound: a soft tick on the hover; a higher pluck on the click; a quiet shimmer (−20 dB) on the flash; a short reverse swell on Back. The chip is the one that the real take has. If a take has no citation, use another take; never add a chip. The cited passage must be in `ch004`, never in the References (`ch009`).

**S08 Chat model (49.5–54.5 s, b99–109).** At 49.5 s a match cut: "this Mac" in the provenance line becomes the Chat pane of Settings, cropped from the Provider label down, at 1.6x. The Provider is Local. The Model field names the model of the take. The key line ends with "A Local Chat model uses no key." Then one real state a beat, in the order of the list: OpenAI (50.5 s, b101), OpenRouter (51.0 s), DeepSeek (51.5 s), Gemini (52.0 s), Anthropic (52.5 s), and Local again (53.0 s, b106). In each cloud state the API key field is empty ("Paste your API key"), and the key line names that provider's host and says "No key saved. LocalXiv keeps keys in macOS Keychain." Each change is a hard cut between two captures. Card "Your key. Or your Mac's model." is full from 50.6 to 52.7 s. Card "No LocalXiv account." is full from 53.2 to 54.4 s. Sound: a low thump on the match cut; a dry tick on each step, rising; a resolved pluck on Local. The crop starts at the Provider label, because the help paragraph above it says "Nothing leaves this Mac." for Local (`app/static/app.js:787`), and the film makes no such claim. The key line starts with a sentence about the Overview and Blog key; show the line as the app draws it, or crop it out whole. Never edit it. No key is ever on screen.

**S09 Several quotes (54.5–62.0 s, b109–124).** At 54.5 s a 200 ms crossfade back to the Paper at 1.6x: p00023, p00024, and the Question card with its first answer. At 55.0 s (b110) the reader clicks Add Quote under the answer, and the app's notice says "Select the words in the Paper, then choose Add to Question. Press Escape to cancel." From 55.3 to 56.3 s the reader drags over p00023: "Additive attention computes the compatibility function using a feed-forward network with a single hidden layer." At 56.4 s the toolbar shows Add to Question and Cancel. At 56.5 s (b113) the reader clicks Add to Question, and the quote shows in the card above the field. From 56.6 to 57.1 s the camera pushes to 2.0x on the card. From 57.2 to 59.1 s the reader types "Why does additive need no scaling?". Card "Several quotes. One question." is full from 56.9 to 58.6 s. At 59.5 s (b119) the reader presses Return, and "Reading the Paper…" shows. At 60.25 s a dip cuts the wait, and from 60.3 to 62.0 s the first words of the second answer stream at the captured speed. At 62.0 s the film cuts away; the answer keeps streaming, and S14 shows it finished. Sound: a tick on Add Quote; a soft pen stroke under the drag; a double pluck on Add to Question; a soft bell on Return; the arpeggio stops and comes back on b121. Both quotes are in section 3.2.1, so the card stays still. The second answer is real output, like the first.

**S10 Overview and Blog (62.0–65.5 s, b124–131).** The first scene to cut if the film feels long. At 62.0 s a cut to the Paper's Overview: one figure that the app made, not the paper's figure. The camera drifts from 1.0x to 1.08x over 1.75 s. At 63.75 s (b127.5) a 200 ms crossfade to the Blog: its title, a question heading, and the line "Generated with <model>. AI text can contain errors." with its date. Card "Overview and Blog, if you ask." is full from 62.4 to 64.5 s. Sound: a light air whoosh on each switch. These are the sample's saved views. They are real output of the model named in the sample, from the run of 2026-09-10, by a pipeline older than v0.1.0 (`app/sample/attention/README.md`). The card claims nothing about the model, the date, or the design (Section 10). If S10 is cut, every later scene moves up 3.5 s, and the master is 86.5 s.

**S11 All Notes (65.5–70.0 s, b131–140).** At 65.5 s a cut to the Paper at 1.2x with the four colours, the Note card, and the Question card. The strip shows "Read · Mark · Ask · Keep" (65.5–68.65 s). At 66.0 s (b132) All Notes opens over the Paper from the centre (opacity and scale 0.97 to 1, 200 ms): a row for each Highlight, the Note, and the Question card with its two questions, with search and the four arrangements. From 66.4 to 66.9 s the camera pushes to 1.4x on the list. At 67.5 s (b135) the reader clicks the colour arrangement, and the rows change order: a cut between two real states, with no drawn reorder. Card "All Notes for this Paper." is full from 66.8 to 68.6 s. At 69.5 s All Notes closes in 150 ms. Sound: a low soft thump when the dialog opens; a tick on the arrangement. In the Mac app, ⇧⌘N opens All Notes (`app/macos/Menus.swift`), and All Notes is web content in both shells.

**S12 Notes page (70.0–75.0 s, b140–150).** At 70.0 s a 200 ms crossfade to the library Notes page, content only, at 1.2x: rows grouped by Paper, the search field, four colour toggles, and the `#tag` toggles. Card "Every Note, across your library." is full from 70.5 to 72.3 s; with the sample alone in the library, the card is "Every Note, in one place." At 71.5 s (b143) the reader clicks `#attention`, and the list keeps the rows with that tag, from two Papers (a cut between real states). From 71.6 to 72.1 s the camera pushes to 1.4x on the rows. Card "Your Notes stay on your Mac." is full from 72.7 to 74.8 s. Sound: a pluck on the tag. "Stay on your Mac" is about storage. The posts say what Chat sends when the reader asks. The other Papers' titles and quotes show on screen, so their licences must allow it.

**S13 EPUB with Notes (75.0–79.0 s, b150–158).** At 75.0 s a cut to the exported EPUB with Notes, in a rounded panel (radius 20 px, soft shadow) on the brand background, at 1.0x: one page where the Question Highlight shows in its colour with its number, then the "Highlights and Notes" chapter entry with the quote, the colour name, and the Note. Card "Export EPUB with Notes." is full from 75.4 to 76.9 s. At 77.0 s (b154) a cut to the Send to Kindle dialog over the Paper, at 1.3x: "To your-name@kindle.com", and "Include Highlights and Notes" checked. The cursor stays away from Send. Card "Or Send to Kindle." is full from 77.3 to 78.7 s. Sound: an airy whoosh on the EPUB; a soft thump on the dialog. No Kindle device has read the EPUB with Notes, so the film shows no e-ink device and no coloured marks on a Kindle. Kindle is one beat.

**S14 Full margin (79.0–83.0 s, b158–166).** At 79.0 s a cut to the Paper at 2.0x on the Question card, now with both turns finished. From 79.0 to 80.8 s one long pull-back (ease-in-out) to 0.75x shows section 3.2.1 from p00019 to p00024 with every record of the film in place: the Key point, Disagree, Use in my work, and Question Highlights, the Note, and the Question card with two turns, each beside its words. Below 1.0x the content shows as a rounded panel on the brand background, with no title bar, toolbar, or sidebar. At 80.6 s the strip shows all four verbs. From 81.0 to 81.5 s the panel dims under a PAGE scrim to 40%, and the strip moves to the centre and grows to 160 px as one group, in one move (500 ms): "Read. Mark. Ask. Keep.", with the full stops in ACCENT. Sound: at b158 the drums stop; the pad and a soft arpeggio stay; from b162 to b163.5 the motif D–F#–A–D plays in eighth notes while the line moves. The layout is the app's real layout; the edit moves no card. The frame at 80.9 s is slide 1 of the carousel.

**S15 End card (83.0–90.0 s, b166–180).** From 83.0 to 83.3 s the panel leaves (opacity 1 to 0, scale 1 to 0.98, ease-in). The brand background (the existing `Background` glow) stays. The verb line shrinks to 64 px and becomes the subtitle. The centre stack, top to bottom:

1. The app icon, 120 px, fanning out with the existing spring (83.0 s).
2. "LocalXiv", 110 px, weight 650, letters rising 2 frames apart (83.4 s).
3. "Read. Mark. Ask. Keep.", 64 px, INK.
4. Two chips, "Free and open source" and "No LocalXiv account", 56 px, INK on PAPER (84.0 s, b168).
5. "Apple Silicon · macOS 26 or newer", 56 px, INK (84.5 s).
6. The URL pill `github.com/Akhil-Theerthala/LocalXiv`, Menlo 64 px, PAPER on ACCENT (85.0 s, b170). This is the one action.
7. At 87.0 s (b174) everything above the URL dims to 70% and scales to 0.98 (400 ms). The URL stays at full opacity.
8. At 87.5 s (b175) the last line rises 8 px into place below the URL, at full opacity: **"Coming soon to Linux"** (64 px, INK), full from 87.8 to 90.0 s. The wording is the owner's. No date.

Each line enters with the card recipe. The stack fits between y = 65 and y = 880 px, inside the 115 px side margins. Sound: the end chord on D from b166; a low bell on the URL; one beat of near silence at b174; at b175 one high bell on G that does not resolve; the pad tail fades by 90.0 s. The last frame is the complete card, so a loop restarts from a full frame.

### 5.4 The hook with a two-column Paper (Decision 2, option B)

If the owner picks a two-column Paper with a CC BY licence, S01 can open on the PDF-to-page edit (H1 of research 5.3) in the same 0.0–3.2 s:

- Two layers, both captured in the same 1440×900 window and shown at the same camera zoom, so zoom does not make the difference. Below a 3 px ACCENT rule: the arXiv PDF of the passage, text only. Above the rule: the same passage in LocalXiv. The anchor sentence sits at the same height in both.
- From 0.0 to 1.0 s the rule moves down to the bottom edge (ease-in-out). The visible rule shows that this is an edit, not an app animation.
- The same cards: "AI waits until you ask." at 1.1–3.2 s, then the name card.
- The pass over Ask then moves to S04, on its first drag (the cursor rests on Ask for 0.9 s, then picks a colour).
- Gate: watch the frame at 1.5 s on a phone at 720p, at arm's length. If the two layers do not look different at a glance, use the in-app hook of Section 5.3.

This option changes every passage ID in Section 5.3. The new Paper needs the same passage roles: an opening paragraph with a display equation; a citation; a claim to disagree with; a hedged sentence ("we suspect") and the sentence after it; a nearby sentence for the second quote; all in one section.

## 6. Cutdown and other formats

### 6.1 The 25 s Ask cutdown (50 beats)

16:9, from the same captures and music stems. It shows one job: Ask. It starts in the pause before the click, so the reader's choice is the first thing a viewer sees.

| Scene | Time | Beats | On screen | Cards (full opacity) |
| --- | --- | --- | --- | --- |
| K1 The choice | 0.0–2.5 | 0–5 | Frame 0 mid-drag on the p00024 sentence at 1.5x, with the Question Highlight and its Note card above. Release at 0.5 s; toolbar at 0.7 s; the cursor stops between the swatches and Ask (0.8–1.2 s); stillness to 2.25 s; the cursor goes to Ask. Pad alone, suspended. | "AI waits until you ask." 0.4–2.3 |
| K2 Ask | 2.5–10.5 | 5–21 | Click Ask at 2.5 s (b5): the drums and the bass enter; the Question card opens with its host line. Zoom to 2.2x at 2.6 s. Typing 3.2–4.8 s. Return at 5.0 s (b10); "Reading the Paper…"; dip at 5.75 s; the same take streams 5.8–10.0 s at captured speed; provenance line by 10.5 s. | "Ask about the words you chose." 3.1–5.2 |
| K3 Citation | 10.5–16.0 | 21–32 | The cursor goes to a chip; the preview opens at 11.25 s; click at 13.0 s (b26), cut to the passage, flash; Back at 14.5 s (b29), cut to the card; pan to "· this Mac ·" and hold. | "Citations open the passage." 13.3–14.7 |
| K4 Chat model | 16.0–20.0 | 32–40 | Match cut to the Chat pane on Local at 16.0 s; Anthropic at 17.0 s (b34); Local at 18.0 s (b36); hold. | "Your key. Or your Mac's model." 16.3–18.4 |
| K5 End card | 20.0–25.0 | 40–50 | Icon and "LocalXiv" (20.0 s); "Read. Mark. Ask. Keep." (20.3 s); the two chips (20.6 s, full 20.8–22.3 s); the URL pill (21.0 s, full 21.2–25.0 s); at 22.3 s everything but the URL dims to 70%; the Linux line at 22.6 s, full 22.8–25.0 s. | — |

The cutdown keeps the Chat pane: it fits, and it shows the reader's choice of model. "No LocalXiv account" is a chip on its end card, because a separate card would hold for only 1.05 s.

### 6.2 X thread clips

All 16:9. Each video clip ends on a 3 s end card with the URL and the Linux line last.

| Reply | Media | Source |
| --- | --- | --- |
| 1 | The 25 s Ask cutdown | Section 6.1 |
| 2 | Highlights clip, 15 s | S04 and S05 (17.0–29.0 s) plus the 3 s end card |
| 3 | Still: the Chat pane on Local, no key | S08 at 53.5 s |
| 4 | Text only | — |
| 5 | Still: the end card | S15, last frame |

A later post can use a Keep clip: S11 and S12 (65.5–75.0 s) plus the 3 s end card, 12.5 s.

### 6.3 4:5 (1080×1350), optional

The same timeline, cards, and music, rendered from the same composition with a format prop and its own camera keys. At 4:5 the 1440 CSS px content maps to 1080 px at 1.0x, so a capture at deviceScaleFactor 3 stays sharp up to 4x; use 2.6–3.0x for paper text and margin cards.

| Scenes | Change |
| --- | --- |
| All | Cards 72 px (cap about 51 px) in a top band, y = 150–360 px, under the strip at y = 70 px. Keep the bottom 230 px clear. Side margins 65 px. |
| S01, S06, K1 | Frame the selection and the toolbar at 2.8x. The pause and the click read the same. |
| S02 | 2.6x on the anchor sentence; the stillness still shows the passage stays in place. |
| S04 | 2.6x; labels in the left gutter at 48 px; pan on the beat between the three marks. |
| S05, S06, S07, S09 | The words and the margin card do not fit side by side. The camera pans between them on the beat and does not zoom out. During a stream the camera holds on the card. |
| S08 | 2.4x on Provider, Model, and the key line. |
| S10–S13 | Fit the width; the Overview fits the width and drifts down. |
| S14 | Pull back to 1.0x; the column fills the width, and the margin cards show under it as the app lays them out at that crop. |
| S15 | The stack, centred; the URL pill at 52 px Menlo so it fits the width, and the Linux line at 52 px. |

9:16 is low priority: only the Ask cutdown, if at all (research 5.2).

### 6.4 Thumbnail, stills, carousel, README loop

- **Thumbnail:** the S06 frame at 42.1 s with the film card hidden: the Question Highlight, the reader's Note above, and the Question card with the real answer and a citation chip. Tagline A on a paper slip at the left, Avenir Next Demi Bold 96 px. Never a frame with only the logo. Upload it by hand on X desktop and on LinkedIn.
- **One still** for a LinkedIn image post about a week later: the S14 frame at 80.9 s.
- **Carousel**, 12 slides, each a real capture with at most 12 words of slide text:

| Slide | Frame | Slide text |
| --- | --- | --- |
| 1 | S14 at 80.9 s | Read the paper. Ask in the margin. |
| 2 | S01 at 1.8 s (the cursor on Ask) | AI waits until you ask. |
| 3 | S02 at 11.5 s | Your font. Your size. Your theme. |
| 4 | S03 at 15.5 s | Check a reference. Keep your place. |
| 5 | S04 at 23.0 s | Key point, Question, Use in my work, Disagree. |
| 6 | S05 at 28.9 s | Notes sit beside the words. |
| 7 | S06 at 31.6 s | So far, no AI. |
| 8 | S06 at 42.1 s | Ask about a line. The answer lands beside it. |
| 9 | S07 at 46.6 s | Citations open the passage. |
| 10 | S08 at 53.5 s | Your key, or a model on your Mac. No LocalXiv account. |
| 11 | S12 at 72.5 s | Every Note, across your library. |
| 12 | S15, last frame | Free and open source. Coming soon to Linux. The URL. |

- **README loop:** 12 s, S06 from 29.3 to 41.3 s, silent MP4 with a GIF fallback. The README change is a recommendation (Section 8.7).

### 6.5 Optional inserts and an extended cut

Only if they are captured for real:

- The `localxiv://` bookmarklet on an arXiv page, for a later post ("Found it on arXiv or alphaXiv? Read it in LocalXiv."). The browser's permission prompt stays in the shot.
- Paper search Suggestions for "attention is all", with `/api/search` stubbed by one recorded real response.
- Copy Notes from an older version, on a Paper with two arXiv versions in the library.

An extended cut of 2–3 min only if the X account has a paid tier (Decision 6). It adds the inserts above and Explain.

## 7. Production approach

### 7.1 What changes in `tools/intro-video`

Extend the project. Keep the beat grid, the brand, `Camera`, and `music.mjs`.

| File | Change |
| --- | --- |
| `src/timeline.mjs` | New `SCENES`: S01 13, S02 12, S03 9, S04 14, S05 10, S06 29, S07 12, S08 10, S09 15, S10 7, S11 9, S12 10, S13 8, S14 8, S15 14 (180 beats). New `CUES` in beats from each scene's start for every click, step, dip, and stream window of Section 5.3. A second grid for the cutdown (K1 5, K2 16, K3 11, K4 8, K5 10). |
| `src/brand.jsx` | Keep the palette, fonts, `EASE_OUT`, `EASE_IN`, `EASE_IN_OUT`, `Icon`, and `arc`. Remove `BACK`. Replace `Caption` (it staggers words) with one `Card` component (Section 4.2). `Background` gates its kick glow on `START.Add` and `START.Outro`; move it to the new scene ids. |
| `src/stage.jsx` | Remove `Window`, `LAYOUTS`, the tilt, and the fly-in. `Camera` maps the 1440×900 content full-bleed to 1920×1080 (scale 4/3, so a 16:10 to 16:9 crop of 60 px at the top and the bottom at 1.0x), with ease-in-out moves of 400–500 ms. Below 1.0x the content shows as a rounded panel on the background. Keep `Shot` and `Crop`. |
| `src/scenes/` | Remove `Title`, `Add`, `Library`, `Read`, `Overview`, `Blog`, `Kindle`, and `Outro`, and the e-reader arrival. Add one file a scene, S01–S15. |
| New components | `Cursor` (stage space, constant size, arrow and I-beam, press and ring), `Strip`, `Label`, `Dip`, and `Stream` (plays the screenshots of a take at their recorded times). |
| `src/index.jsx` | Compositions: `Intro` (16:9, 5,400 frames), `AskCutdown` (1,500 frames), `Intro45` (1080×1350), `HighlightsClip`, and still compositions for the thumbnail and the carousel. |
| `README.md` | Rewrite for the new film, the capture modes, and the safety rules. |

### 7.2 `capture.mjs` on `window.localxiv.command(...)`

The current script dates from 2026-09-25. The shell redesign of 2026-10-14 removed most of its selectors, such as `#tab-paper`, `#share-open`, and `#reading-preferences-dialog`, and the onboarding tour (`#tour-skip`) (research 7.2). Rewrite it on the commands that the Native shell sends (`app/static/shell.js:67`):

- **Server.** Spawn the temporary server as now, but first patch the three Keychain names that `app.server` imports: `unittest.mock.patch('app.server.get_key', return_value='')`, and plain patches of `app.server.set_key` and `app.server.delete_key`, all started before `make_server`. Set `onboarding_complete: true` through `/api/settings`.
- **Browser.** Remotion's `chrome-headless-shell`, viewport 1440×900 CSS px, `deviceScaleFactor: 3`.
- **Commands.** Open the sample with `{name: 'open', id: '1706.03762v7'}`; it opens on the Overview, so then `{name: 'view', view: 'paper'}`. Reading preferences with `{name: 'prefs', patch: {font: 'sf-pro', size: 16, theme: 'light', margins: 'normal'}}`, then `{name: 'prefs', patch: {font: 'charter'}}`, `{name: 'text-size', step: 1}` four times, and `{name: 'prefs', patch: {theme: 'sepia'}}`. Back with `{name: 'back'}`. All Notes with `{name: 'action', id: 'all-notes'}`. The Notes page with `{name: 'go', to: 'notes'}`. The Overview and Blog with `{name: 'view', view: 'overview'}` and `'blog'`. Export with `{name: 'action', id: 'export-epub-notes'}`. Send to Kindle with `{name: 'action', id: 'send-kindle'}`. Chat settings with `{name: 'settings', pane: 'chat'}`, or a second page at `?panel=settings`, which is the web content of the native Settings window. A page command is ignored while a dialog is open (`shell.js:62`), so close each dialog first.
- **Selections.** Find the words with `findWords` from `app/static/onetext.js` in the reader frame. Drag with a real mouse (`page.mouse` down, move in steps, up). A selection made in JavaScript paints grey in Chromium. Save each path and each click point to `rects.json`.
- **Hovers.** `page.mouse.move`, then wait for the app's 350 ms open delay; a preview closes 550 ms after the pointer leaves (`reader.js:550`, `556`). With no selection active.
- **The passage that stays.** Before the size steps of S02, scroll until p00020 is the top passage at the frame line; the app holds that passage only after a scroll into the Paper (`reader.js:357`).
- **The "connected" rewrite.** The current script fakes `has_key: true` and `model: 'demo'` so the saved Overview and Blog show. Turn it on only around the S10 shots. With it on, the Chat pane says "Overview and Blog use the key for api.openai.com." with no key saved, which is false.
- **Output.** `public/<scene>/<state>.png` for each state, `rects.json`, and `public/takes/<take>/frames.json` with each stream screenshot and its recorded time.

### 7.3 What each capture records, and the gates

Run the gates first. If a gate fails, stop and report to the owner.

1. **Highlight paint.** `CSS.highlights` (`app/static/margin.js:297`) paints in `chrome-headless-shell`. No test checks it. If it does not paint, try Playwright WebKit (untested with this app), then ask the owner about a native run (Section 10).
2. **Full-margin layout.** At 1440 px, Charter 20 px, Sepia, and Margins Normal, the margin is 210 px or wider (`margin.js:19`), so no card folds to a marker. All records of the film sit in p00019–p00024, each card beside its words, and the Question card with two turns does not push the other cards far from their words. A full-page capture of the section stays under Chromium's screenshot height limit (about 16,384 px), or it is taken in tiles.
3. **The take.** Section 7.5.

| Scene | States and data |
| --- | --- |
| S01 | 6–8 drag states on p00020; toolbar; Ask hovered; Key point painted; the 1.5x frame. Rects of the toolbar and each button. |
| S02 | SF Pro 16 Light; Charter 16, 17, 18, 19, 20 Light; Charter 20 Sepia. The anchor sentence's rect in each. |
| S03 | [2] preview open; its rect. |
| S04 | Three drags, each toolbar, each paint; the rect of each mark. |
| S05 | Highlight bar; empty Note editor; each typed character (or prefix widths); saved card. |
| S06 | Drag; toolbar; cursor at rest; Ask hovered; Question card with host line; each typed character; "Reading the Paper…"; one screenshot for each streamed chunk; the finished card; the 1.5x frame. |
| S07 | Chip preview; the flash at 0.1 s steps across 1.2 s; the card after Back; the provenance line. |
| S08 | The Chat pane, last of all: Local, OpenAI, OpenRouter, DeepSeek, Gemini, Anthropic. Set each with `selectOption`; an open select list does not paint in headless Chromium. Never type a key. |
| S09 | Add Quote notice; drag; Add to Question toolbar; quote block; each typed character; status; the first streamed chunks. |
| S10 | Overview; Blog top with its model line (rewrite on). |
| S11 | All Notes by position and by colour; row rects. |
| S12 | Notes page before and after `#attention`. Needs 1–2 imported CC BY Papers with real Notes tagged `#attention` (Section 10). |
| S13 | The exported EPUB's marked page and its "Highlights and Notes" chapter, rendered from its XHTML with its own `reading.css` in the capture browser; the Kindle dialog with the placeholder address and the box checked. |
| S14 | One tall capture of p00019–p00024 after the second answer ends. |

### 7.4 Safety rules

- **Keychain.** Patch `get_key`, `set_key`, and `delete_key` in the spawned server. Without the patch, Done or Escape after an edit in Settings writes to the owner's real login Keychain, and a provider endpoint makes a real, billed call (research 7.2). Option D changes only `get_key`, and only with the owner's yes.
- **Mail.** Never click `#send`, never submit `#kindle-form`, keep `auto_send` false. The send job hands the EPUB to Mail.app on the real Mac. Never touch Mail.app.
- **Other outside actions.** Never click `#reader-pdf` or `#reader-arxiv`. Never click Add on a search row. Never click Copy All, Export, or Back Up Notes in All Notes or on the Notes page.
- **Keys and e-mail.** No real key and no real e-mail address on screen, ever. The Kindle address is the placeholder `your-name@kindle.com`.
- **Native windows.** No native run and no `tools/native_shot.py` without the owner's yes: it takes the front window and key focus while the owner works.
- **The owner's library.** The capture uses a temporary library, never the owner's.

### 7.5 The Chat answer

Every answer on screen must be real output of a real model. The host line and the provenance line come from the Chat endpoint: a loopback endpoint reads "Asks a model on this Mac (127.0.0.1)" and "<model> · this Mac · <date>" (`app/static/chat.js:97`, `151`). The Chat pane matches the endpoint to a preset by its exact URL (`app.js` `renderProvider`), so only `http://127.0.0.1:11434/v1` shows as Local.

| Option | How | True on screen | Cost |
| --- | --- | --- | --- |
| **A. A model on this Mac, recorded once and replayed** (recommended) | Run a local OpenAI-compatible server (for example Ollama, LM Studio, or llama.cpp) on another port. A small recording proxy on `127.0.0.1:11434` forwards the app's real request and saves each streamed chunk with its time. Record several takes; choose one. For the capture, a loopback stub on the same port replays the chosen take and sends chunk n only after the screenshot of chunk n−1, and the film plays each screenshot at its recorded time. | The words, the timing, the host line, the provenance line, the Model field, and the Local preset. "Your key. Or your Mac's model." and the push into "· this Mac ·". | A local model and server. Context size set to the model's real limit (the Local preset starts at 4096; a Paper that does not fit goes as an excerpt around the selection, which is also real). A small model may cite badly or stream raw TeX: several takes. No key, no bill, no native run. This Mac has no local model server yet, and it has 16 GB of memory (Decision 1). Record and replay on the same day, so the date in the provenance line is the date of the answer (Section 10). |
| B. A real answer from any model, replayed through a loopback stub | As A, but the recorded model ran in the cloud. | Nothing about the source: the host line, the provenance line, and the Model field would all say "this Mac". | Ruled out by the honesty judge. If the model ran on the Mac, it is option A. |
| C. A native capture with the owner's cloud key | `tools/native_shot.py` on the Mac app, with the owner's saved Chat key. | The host line "Asks <Provider> (<host>)", a provenance line that names the provider, the pane on that provider with "A key is saved in macOS Keychain." and an empty field. The real AppKit window. | The owner's yes for a native run. A billed call per take. No stream-frame pipeline exists for native captures. The "· this Mac ·" push and the "model on your Mac" story go; S07, S08, and K3–K4 change. |
| D. A headless capture with the owner's real cloud key | The temporary server reads the owner's Chat key from the Keychain (`get_key` not patched; `set_key` and `delete_key` patched) and calls the owner's provider once a take. | Same as C, in the web capture. | The owner's yes. A billed call per take. A key must be saved under the Chat account of that host. The temporary server reads the real Keychain. The "· this Mac ·" story goes, as in C. |

**Recommendation: A.** It is the only option that keeps every line on screen true, costs no key and no bill, and keeps the film's best line of proof, "this Mac". Use D if no local model gives a clean answer with citations after several takes. Use C only if the owner wants the native window. Never B.

For a good take: the answer cites `ch004` passages in the chip form `[p00024]` or `[p00020, p00024]`, never the References (`ch009`); it has 40–70 words in plain words; and it has no raw TeX while it streams. The questions are "Why does this scaling help?" and "Why does additive need no scaling?". Accept the large-Paper confirmation (Ask Anyway) once before the filmed take, if it shows. Test the model on p00024 before the shoot.

### 7.6 The Paper

The first page of the 1706.03762v7 PDF allows reuse of its tables and figures, with attribution, "solely for use in journalistic or scholarly works". A launch film is promotion. The app also ships this paper as its sample. This is a risk to check, not legal advice (research 5.10).

- **Default: the sample, text only.** The passage map of Section 5.3 is checked against `app/sample/attention/reader/text/ch004.xhtml`. No figure, table, or Figure preview of the sample shows. The hook is in the app (Section 5.3), because the sample's PDF is one column: at an equal camera zoom, a PDF-to-page edit shows little difference. The owner should still check that showing its text in a promotional film is acceptable.
- **Option B: a two-column Paper with a CC BY licence on its arXiv page.** It allows the PDF-to-page hook (Section 5.4) and Figure previews. It costs a clean conversion check, a new passage map, new takes, and new Overview and Blog views, which need a provider call.

### 7.7 Music

- `music.mjs` reads `SCENES` and `CUES` from `src/timeline.mjs` and gates the drums on `START.Add` and `START.Outro`. Rewrite those gates for the new acts: the pad from frame 0 with no fade from silence; the soft kick from b16; the hi-hats from b34; the drop at b61; the full groove from b66 (the Ask click); the lighter groove from b131; the stop at b158; the end chord from b166; the G bell at b175.
- Add the UI sound cues of Section 5.3 as `CUES`, about 18 dB under the music.
- Run `node music.mjs` again after any change to `timeline.mjs`.
- Measure the rendered master with ffmpeg's `ebur128` filter (with `peak=true`). Target −14 LUFS integrated and −1 dBTP or lower. Adjust the master gain in `music.mjs`, not in the render.

### 7.8 Render commands

Run these in `tools/intro-video`. The repository `.venv` and the root `node_modules` must exist. The `--record` flag is a proposal for this spec; the builder names it.

```bash
npm install
npx remotion browser ensure
node capture.mjs --record   # Option A: records takes through the proxy; the owner's local model server must run
node capture.mjs            # replays the chosen take and saves every state to public/
node music.mjs
npm run render              # dist/intro-video/localxiv-intro.mp4
npx remotion render src/index.jsx AskCutdown ../../dist/intro-video/localxiv-ask-25s.mp4 --audio-codec=aac
npx remotion render src/index.jsx HighlightsClip ../../dist/intro-video/localxiv-highlights-15s.mp4 --audio-codec=aac
npx remotion render src/index.jsx Intro45 ../../dist/intro-video/localxiv-intro-4x5.mp4 --audio-codec=aac
npx remotion still src/index.jsx Thumbnail ../../dist/intro-video/thumbnail.png
```

### 7.9 Checks before posting

1. Watch every scene on a phone at arm's length, with the sound off. Each card reads, and the story holds.
2. Watch a 720p copy (`ffmpeg -vf scale=-2:720`), as a free X account plays it.
3. The timeline script passes: 180 beats; every hold at least max(1.2 s, 0.35 s a word) after the fade; zoom moves 3 s apart; no card during a stream; at most two text zones.
4. Contrast 4.5:1 or more under each card, label, and end-card line.
5. Step through every frame of S06–S09 and K2–K4: no key, no real e-mail address, no help paragraph with "Nothing leaves this Mac.", no "demo" model, and the model in the provenance line matches the Model field.
6. No window chrome, no web toolbar or sidebar, no New York font (it shows as Georgia in Chromium), and no figure or table of the sample.
7. Each stream plays at its recorded speed, and each wait cut is a visible dip.
8. Search the cards and the post texts for "agent", "any paper", "every paper", "nothing leaves", "only", "first", "no account", "free AI", and a date for Linux.
9. Loudness: −14 LUFS integrated, −1 dBTP or lower.
10. The three-to-five-viewer test of Section 1.3.

## 8. Launch plan for X and LinkedIn

### 8.1 Timing

| Date | Event | Effect |
| --- | --- | --- |
| Week of 2026-10-26 | alphaXiv hinted at a launch "next week" (seen only on a mirror) | Do not post on the same day. |
| Wednesday 2026-10-28 | Apple's Mac event | Mac news fills the feeds (inference). |
| 2026-10-30 to 2026-11-01 | alphaXiv judges the ScienceClaw hackathon | — |
| Tuesday 2026-11-03 | US general election | US news fills the feeds on that day and the next (inference). |
| Tuesday 2026-11-10, Monday 2026-11-16 | CVPR 2027 registration and submission deadlines | Many ML readers are busy in the week before (inference). |

**Recommendation (inference): Tuesday 2026-11-17, 14:00–18:00 UTC.** It is after both CVPR deadlines and clear of the other dates. Wednesday 2026-11-18 is the second choice. Thursday 2026-11-05 is the early option, but it is in the week before the CVPR registration deadline that research 6.2 warns about. After daylight saving time ends in the US on 2026-11-01, 14:00 UTC is 6 a.m. US Pacific and 9 a.m. US Eastern (research 6.2).

The sequence:

| Day | X | LinkedIn | Other |
| --- | --- | --- | --- |
| Launch day | Main post and 5 replies, by hand from x.com on a desktop; pin the main post; stay online 2 hours and reply with content | The video post from the personal profile; add it to Featured | Show HN and Indie Hackers (optional, Section 8.5) |
| +2 days | — | The carousel (Thursday 2026-11-19 for a 2026-11-17 launch) | — |
| +7 days | The cutdown as a single-feature post (optional) | One strong still with a short story; the 4:5 test after that (optional) | — |

### 8.2 X: the main post and the thread

Post by hand from x.com on a desktop, so the custom thumbnail uploads. Do not use a scheduler: X charges for API posts with links, and some schedulers remove links. Upload the 16:9 master as native video. No hashtags. Upload no `.srt`. Do not DM the link to friends; ask them to follow the account before launch day (research 6.3).

Each draft fits the 280-character limit of a free account (a link counts as 23 characters).

**Main post** (47 words, 279 characters):

> Read the paper. Ask in the margin.
>
> LocalXiv is a free, open-source Mac reader for arXiv papers. Mark words in four named colours, keep Notes beside them, and ask about a passage when you choose, with your key or a model on your Mac. No LocalXiv account.
>
> https://github.com/Akhil-Theerthala/LocalXiv

**Reply 1** [video: the 25 s Ask cutdown]:

> Ask is for the lines you do not understand. Select words, choose Ask, and the answer streams into a Question card beside them. Citations open the passage. One question can carry several quotes. Each new card says it: answers can be wrong, so check the cited passages.

**Reply 2** [video: the 15 s Highlights clip]:

> Reading comes before any AI. Mark words as Key point, Question, Use in my work, or Disagree, and write a Note beside them. All Notes and the library Notes page keep them, with a toggle for each #tag. Export EPUB with Notes takes them with you.

**Reply 3** [image: the Chat pane on Local, no key]:

> Your library, Notes, and keys stay on your Mac. No LocalXiv account. No analytics library in the code. AGPL. Chat calls the provider you choose with your key, or a model on your Mac. When you ask, it sends the Paper's text, your Highlights and Notes, and your question.

**Reply 4** (text only):

> Limits: early preview, Apple Silicon, macOS 26 or newer. Not notarized, so macOS may block the first launch: open System Settings › Privacy & Security, then Open Anyway. 83 of 100 papers in our test corpus open as reflowed text; the rest open as the PDF. AI answers can be wrong.

Check the first-launch path on macOS 26 before posting. The repository has no such steps yet: the README points to `docs/macos-release.md`, which has none (Section 8.7).

**Reply 5** [image: the end card]:

> Coming soon to Linux. No date yet. If you want the Linux build, add a vote here: [link to the Linux issue]. And send me an arXiv paper that LocalXiv converts badly. I will look at each one.

Open the Linux issue before launch day (Section 8.7).

### 8.3 LinkedIn: the post

A draft in the owner's voice. **The owner must rewrite it in their own words** and confirm each personal line. Text that sounds machine-written does worse on LinkedIn (research 6.4). Post from the personal profile, with a native upload of the same 90 s master from a desktop, a custom thumbnail, auto captions off, and the plain URL as the last line. No link-preview card. 0–2 hashtags.

> I built LocalXiv because I want to read a paper before I ask AI about it.
>
> A summary tells me what a paper claims. It does not show me where I am lost. I find that out when I read, mark what matters, and write beside it. After that, AI is useful: I can point at one sentence and ask about it.
>
> [One true moment from your own reading, in one or two sentences.]
>
> LocalXiv is a free, open-source Mac reader for arXiv papers. It shows a paper as text in your font, size, and theme. You mark words in four colours: Key point, Question, Use in my work, and Disagree. Your Notes sit in the margin beside the words.
>
> When a line stops you, select it and Ask. The answer streams into a card in the margin, and its citations open the passage. Use your own key or a model on your Mac. There is no LocalXiv account.
>
> One honest limit: this is an early preview for Apple Silicon Macs with macOS 26 or newer, and some papers still open as the PDF.
>
> Coming soon to Linux. There is no date yet.
>
> https://github.com/Akhil-Theerthala/LocalXiv

The draft has 182 words without the slot for the owner's moment. Keep the moment to about 15 words, or cut one sentence, so that the post stays inside the 150–200 band for video posts (research 6.4).

### 8.4 LinkedIn: the carousel

2–4 days after the video: the 12 slides of Section 6.4 as one PDF document post, with a short first-person text and the URL as the last line. Add alt text to each slide where LinkedIn allows it.

### 8.5 Other channels (optional)

- **Show HN**, the same day. Hacker News asks for text that a person writes and forbids requests for votes. The earlier LocalXiv post got 1 point, so the title and the first comment matter. A major overhaul can qualify; v0.1.0 adds Chat, Highlights, and Notes. A title idea: "Show HN: LocalXiv – read arXiv papers on a Mac, with Notes and questions in the margin". The first comment: AGPL, a local library, no LocalXiv account, the 83 of 100 corpus number, the first-launch steps, and what the owner wants to learn. Say how the app was built if asked (Decision 7).
- **Indie Hackers**, the same day. It gave Textfold its best feedback (research 6.5).
- **r/macapps**: read the rules first, and post from an account with history.
- **Product Hunt**: the owner's page says LocalXiv launched there in September 2026. Product Hunt asks for two months between launches and a significant update. Find the first launch date before a relaunch.

### 8.6 What to measure

At 48 hours and at 7 days: X views, likes per 1,000 views, and link clicks; LinkedIn impressions, reactions, and comments; GitHub stars; v0.1.0 DMG downloads; new issues; Linux votes; papers sent in. Note which post or reply each comment came from. Compare only with launches of similar reach (Section 1.3).

### 8.7 Fixes before launch, outside the film (recommendations)

The film sends viewers to the GitHub page. Today that page and the README lead with Kindle or the library (research 1).

1. **README lead line and feature list.** Change "Read arXiv papers comfortably. On your Mac or Kindle." to tagline A and the category, for example "Read the paper. Ask in the margin. A free, open-source Mac reader for arXiv papers." Add Highlights, Notes, Ask, and Chat to the feature list; move Kindle down. Embed the 12 s loop.
2. **The GitHub repository description.** Change "Your library, managed locally." to the category and the stance, for example "A free, open-source Mac reader for arXiv papers. Highlights and Notes in the margin. Ask when you choose."
3. **The owner's project page.** The same lead.
4. **Hugging Face links in Direct import.** Accept `huggingface.co/papers/<id>` (`papers/acquire.py`, lines 22–26). Old Papers with Code links redirect there. A separate code change with its own test.
5. **Notarization or first-launch steps.** Notarize (Decision 3), or write the steps to open an app that macOS blocks, check them on macOS 26, and put them in the README and `docs/macos-release.md`.
6. **A GitHub issue for the Linux build,** where people add a vote. Reply 5 links it.
7. **Product Hunt:** find the date of the first launch.

## 9. Decisions for the owner

Only the questions whose answers change what gets built or posted, most important first. Section 10 settles the smaller ones.

| # | Question | Options | Recommendation | What it changes |
| --- | --- | --- | --- | --- |
| 1 | Where does the Chat answer come from? | A (a model on this Mac, recorded and replayed), C (native, the owner's key), D (headless, the owner's key). B is ruled out. | A, after a trial. This Mac (Mac16,12, 16 GB) has no local model server today: no `ollama`, `lms`, or `llama-server`, and nothing listens on port 11434. A needs the owner's yes to install a server and a model that fits in 16 GB, a download of several GB. If no take cites cleanly after 3–5 tries, use D. | The host and provenance lines, S07's push, S08, K3–K4, the install, the bill. |
| 2 | Which Paper is in the film? | (a) The sample, text only, with the in-app hook. (b) A two-column Paper with a CC BY licence, with the PDF-to-page hook. | (a). The passage map is checked, no new conversion test, no figure licence issue. The owner checks the use of the sample's text in promotion. | S01, every passage ID, the takes, S10. |
| 3 | Which fixes of Section 8.7 come before launch, and does the launch wait for them? | (a) Items 1, 2, 5 (as checked first-launch steps), and 6 before launch; the others later. (b) All of Section 8.7, notarization included. (c) None before launch. | (a). The one action of the film is the GitHub page, which leads with Kindle today. Reply 4 needs checked first-launch steps, and reply 5 needs the Linux issue. Notarize only if a Developer ID is available: a notarized DMG is a new release, and the film then shows that release (Section 10). | The critical path to the launch, X replies 4 and 5, the README loop, the build in the film. |
| 4 | The launch date and time, and where most of the owner's followers live | Tuesday 2026-11-17, Wednesday 2026-11-18, or Thursday 2026-11-05 | 2026-11-17, 14:00–18:00 UTC. 14:00 UTC is 19:30 in India, 15:00 in Central Europe, and 09:00 US Eastern, so one window reaches all three. Change the time if most followers live elsewhere. | The posting plan, and the 2 hours online after the post. |
| 5 | The tagline of the posts, the thumbnail, the carousel, and the README | A "Read the paper. Ask in the margin.", B "The paper first. AI in the margin.", C "For people who still read the paper." | A in the posts; "Read. Mark. Ask. Keep." in the film. | The thumbnail, slide 1, the first line of the X post, the README. |
| 6 | The X account tier | Free (140 s, 720p) or paid (longer video and edits; 1080p *unconfirmed*) | Free is enough for the 90 s master. A paid tier adds the extended cut. | The extended cut, the 720p check. |
| 7 | Say that AI helped build LocalXiv? | Yes, in the Show HN text and when asked; or no | Say it plainly in the Show HN text. Hacker News readers ask, and the owner's page already says it. | The Show HN text and replies. |

## 10. Calls made by the writer

Each is a default that the owner can change.

- **The base concept is ONE SITTING.** Two of three judges chose it, and its beats already summed. From The margin it takes the full-margin pull-back (S14), the match cut into the Chat pane, the equal-zoom rule for a PDF hook, and the record-and-replay take. From Your call it takes the hook, "So far, no AI.", the card recipe, the 64 px URL, and the stream rules.
- **The hook is in the app, not a PDF edit,** because the sample's PDF is one column and the honesty judge's equal-zoom rule removes most of the contrast. The marketer's must-fix allows this.
- **The verbs live in a strip that shows for about 3 s at each act change.** There are no hero verb cards over the gestures. Two judges flagged the text load and verbs that land on key actions. The one big type moment is the S14 gather.
- **"So far, no AI." sits in the pause before the Ask click, and "When you choose." is gone,** so the film states its stance twice (hook and pause), not three times. The marketer warned that a stance said too often reads as preaching.
- **The posts say that Chat sends "the Paper's text, your Highlights and Notes, and your question".** This is a short form of the app's own Settings text (`app/static/app.js:787`), which also names the earlier questions on the Question card, and of `papers/chat.py:156`. The honesty limit in the task said "the selection and the Paper's Highlights and Notes", which leaves out the Paper's text.
- **Streams play at the captured speed in fixed windows (4.2 s in S06), with a visible dip for the wait.** The total stays at 180 beats without a speed-up.
- **The second answer is cut after its first words in S09,** and S14 shows it finished. This keeps the Ask act inside its time.
- **The order of the Ask act is Ask, Citation, Chat model, Several quotes, Overview and Blog,** so the match cut comes straight from the first answer's provenance line, and the AI summaries come last and short.
- **One Reference preview ([2] in p00023), not two.** The footnote preview did not fit a 1.5 s hold.
- **Reading state Charter 20 px Sepia from S02,** because the honesty judge reported about 470 px of room for the margin at 20 px in a 1440 px viewport. The motion judge proposed 19 px; the 210 px gate decides.
- **Provider steps go one a beat, in the list's order,** so each name can be read.
- **The drums come back on the Ask click, not on the first streamed words,** so the music marks the reader's choice. The motion judge asked for this.
- **Capture in Chromium at deviceScaleFactor 3, with no zoom above 2.2x.** Playwright WebKit is a fallback, because nobody has tested it with this app.
- **The S10 Overview and Blog are the sample's saved views,** shown with their model line and no claim about their design.
- **The EPUB is shown rendered from its XHTML in a plain panel,** not in Apple Books, so no native window is needed.
- **Labels and the end card use INK; the end card dims to 70%,** so the last frame keeps 4.5:1.
- **The cutdown keeps the Chat pane** and moves "No LocalXiv account" to its end card.
- **The thumbnail is the S06 frame with the Note above the answer.** Carousel slide 1 is the S14 frame.
- **The launch date default is 2026-11-17,** not the research's 2026-11-05, which falls in a CVPR week.
- **The LinkedIn draft uses the insight line, not the study of students.** The marketer judged that researchers can wave away a study of 14–15-year-olds. The draft has a slot for one true moment and invents no event.
- **The Linux line is "Coming soon to Linux", the owner's own words, with no date.** The repository has no Linux code, so expect replies that ask when. Reply 5 says "No date yet" and links a GitHub issue for votes.
- **No face on camera.** The in-app hook is product motion, and the cards carry the story.
- **No native run, unless the highlight-paint gate fails (Section 7.3).** Then the builder stops and asks the owner, because a native run takes the front window and key focus.
- **S10 shows the sample's saved Overview and Blog,** with their model line and no claim about their design. If the film feels long, S10 is the first cut (86.5 s).
- **The Notes page uses two more Papers with a CC BY licence,** imported into the temporary capture library, with real Notes tagged `#attention`. Nothing goes into the owner's library.
- **The film shows the build that people download on launch day:** the commit of the latest published release. Today that is the v0.1.0 tag at `5f6e20b`. If a new release ships before the launch, capture from its tag, and add its DMG to the baseline of Section 1.3.
- **The take logs go into git; the screenshots and the renders do not.** A take cannot be made again, because a new recording gives other words. So commit each chosen take as a small JSON file in `tools/intro-video/takes/`: the request, each chunk with its time, the model, and the date. The screenshots (several GB at deviceScaleFactor 3) and the MP4s come again from the takes and the code. `public/` and `dist/` stay ignored.
- **The provenance line shows the date on which the model wrote the answer.** `papers/chat.py` sets `created_at` from `time.time()` when the replay runs. So replay on the day of the recording, or set the capture server's clock for Chat to the time of the recording.
- **The Keychain patch is written out in this spec (Section 7.2),** because `tests/` is not in git and does not move to a new device.

## 11. Left to the builder

- The exact word ranges, rects, cursor paths, and arcs, from `findWords` and `rects.json`.
- The local model and server for option A, the recording proxy and the replay stub, and the choice among the takes, within the rules of Section 7.5.
- The exact `CUES` frames, inside the times of Section 5.3, and a check script in the video project that asserts the rules of Section 7.9, item 3.
- The music's voicing, levels, and UI sounds, inside Section 4.4.
- The end card's spacing inside its box, and the 4:5 camera keys.
- How the dip, the stream player, and the full-page tiles work in Remotion.
- Whether `?panel=settings` or the settings dialog gives the cleaner Chat pane crop.
- The two CC BY Papers for the Notes page (Section 10), and their tagged Notes.
- The README of `tools/intro-video`, rewritten for the new film.
- The names of the compositions, the capture flags, and the output files.
