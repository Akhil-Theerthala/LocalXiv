# LocalXiv v0.1.0: positioning, intro video, and launch posts

Date: 2026-10-22. Main at `5f6e20b`. Release v0.1.0, published 2026-10-22 [S169].

**Purpose.** This report supports three decisions by the owner: (a) the positioning of LocalXiv, (b) the storyboard of an intro video for v0.1.0 (this report recommends 60–90 s), and (c) the launch posts on X and LinkedIn.

**Inputs.** Six web-research lanes, each with a skeptic pass: Hugging Face Papers and Papers with Code; alphaXiv changes after 2026-10-17; AI paper readers; read-first sentiment; launch playbook; demo-video craft. One capture map from a reading of the LocalXiv code, with no skeptic pass. The internal brief of 2026-10-17 [S137]. Facts from the repository [S134–S136; S166–S170]. One critic pass on 2026-10-22 with Exa searches and checks in the repository. Its corrections are applied to Sections 1–9, and Section 10 keeps its notes as a record.

**Rules.** A claim that a skeptic or the critic pass refuted is not used here; Section 8 lists it. A claim that a skeptic marked unclear carries the mark *unconfirmed*. "Company claim" marks what a company says about itself. "Inference" marks a recommendation that no source states. Each fact has a citation key with a date, for example [S41, 2026-08-17]. Section 9 gives the URL and date for each key.

## 1. Summary

- **Sell a reader, not an AI tool.** Put LocalXiv after discovery: "Found it on arXiv or alphaXiv? Read it in LocalXiv." Today Direct import accepts arxiv.org and alphaxiv.org links, not other hosts [S134]. Hugging Face Papers, the Papers with Code revival, and alphaXiv help readers find, rank, and summarize papers. Hugging Face Papers has no reader view. alphaXiv and paperswithcode.co show the PDF. LocalXiv is a complement to all three (Section 4.6). arXiv's own HTML view is free and reflows most new papers, so do not imply that reflow is new [S142].
- **Read-first is resonant, with one condition.** Say "read the paper, then ask". Do not say "read instead of AI". Peer-reviewed studies show that AI summaries make findings broader and give shallower learning. But 84% of researchers use AI, and posts against AI get pushback (Section 3).
- **Lead with the combination.** Each single feature has a rival. No product we found has all four parts together: (1) the paper reflowed from its LaTeX source or from arXiv's HTML; (2) the reader's named Highlights and Question cards in the margin beside the words; (3) no LocalXiv account, with the key sent from the Mac directly to the provider; (4) Notes that move to a new arXiv version and go into the EPUB (Section 4). PaperMaster comes close: highlights, margin notes, Ask AI on a selection, an own key, and no account [S151]. So say "no product we found". Never say "only" or "first".
- **Recommended tagline: "Read the paper. Ask in the margin."** Do not lead with "chat with your paper", "understand a paper in minutes", "answers with citations", "local-first", or Kindle. Other products use each of these.
- **Video: one 16:9 master of about 86 s, with music and text cards.** The first frame is product motion, not a logo: a two-column PDF reflows into one column. The hero scene is Ask: select words, the answer streams into a Question card in the margin, a citation opens its passage. The end card ends with a Linux line with no date. The wording is the owner's decision, because the repository has no Linux code yet [S170]. Chat is not an agent: say Ask and Chat. Make a 25 s Ask cutdown (Section 5).
- **Posts: native video, link in the post, no hashtags, Tuesday to Thursday.** On LinkedIn, post from the personal profile as a first-person story, with the plain URL as the last line. Post a document carousel 2–4 days later. Do not post on the same day as alphaXiv's hinted launch in the week of 2026-10-26, on Apple's Mac event (2026-10-28), on US Election Day (2026-11-03) or the day after, or near the CVPR deadlines (2026-11-10 and 2026-11-16). Inference: Thursday 2026-11-05, or Tuesday 2026-11-17 to Wednesday 2026-11-18, is the safer window (Section 6.2).
- **Expect small reach.** The project has 2 GitHub stars [S169]. alphaXiv has 58.2K followers on X, and its reader-feature posts got 5K–21K views [S23, 2026-10-22]. Launch on Show HN and Indie Hackers on the same day.
- **Do four things before launch.** (1) Accept `huggingface.co/papers/<id>` links in Direct import; old Papers with Code links redirect there too [S134; S4, 2025-12-12]. (2) Rewrite the capture script and fix its two blockers, the real Keychain and Mail.app (Section 7.2). (3) Choose how the Ask answer in the video stays true (Section 7.3). (4) Change the README, the repository description ("Your library, managed locally."), and the owner's project page. They lead with Kindle or the library, and the README feature list names no Highlights, Notes, or Chat. The film's one action is the GitHub URL [S166; S169; S161].

## 2. Market map

Reader jobs: **Discover** (find and rank new papers), **Code** (get the code), **Understand** (summaries, explanations, chat), **Read** (a surface to read the full text), **Keep** (highlights, notes, library).

| Product (status) | Reader jobs | Reading surface | Inline ask with passage citations | Highlights and notes | Local library; own key | Linux | Price |
|---|---|---|---|---|---|---|---|
| **Hugging Face Papers** | Discover, Code, Understand | Abstract page with links to the arXiv PDF. No reader view. Markdown for agents [S8, 2026-10-22; S10, 2026-03-24]. | A chat sidebar on paper pages since 2026-01-07 [S7, 2026-01-07]. At launch the chat used the arXiv HTML of a paper. About 27,000 indexed papers with no HTML got chat only after an OCR run [S9, 2026-04-07]. A third-party summary says that the OCR read at most 30 pages of each paper [S145]. One user reported poor answers after the OCR change [S9]. A login appears to be needed for the chat (page code only; *unconfirmed*). Public paper pages need no login, but that covers the page, not the chat [S171]. Passage citations: *unconfirmed*. | No highlights. Upvotes, comments, collections [S12, 2024-09-23; S8]. | No. Hugging Face account. | Web | Free to browse. Whether the chat is free: *unconfirmed* [S7]. |
| **paperswithcode.co** (revival operated by Hugging Face; launched about 2026-05-17 [S143]) | Discover (leaderboards, trending), Code, Read, Understand | "Read paper" PDF viewer [S6, 2026-08-20]. Accepts non-arXiv PDFs since 2026-08-28 (company claim) [S144]. | Chat on the PDF. Selected text goes into the chat's context; the site calls its chat an agent [S6]. The chat offers GLM-5.3 Flash, and "@" compares papers (company claims) [S144]. Passage citations: *unconfirmed*. | None found | No. Sign in with Hugging Face; the chat page shows "Sign in" (undated crawl) [S144]. The privacy policy says chat traces keep the full question and answer, not redacted. An option to bring your own provider: *unconfirmed* [S6]. | Web | Not found |
| **Papers with Code** (paperswithcode.com) | Shut down on 2025-07-24 | — | — | — | — | — | The domain redirects to Hugging Face Trending Papers [S1, 2026-10-22; S2, 2025-07-25] |
| **arXiv HTML** (arXiv's own HTML view) | Read | Reflowed HTML made from the TeX source. The largest reflowed reader of arXiv papers. About 97% of new submissions produce some HTML, and about 75% convert with no LaTeXML errors. Since March 2026 readers can make the page chrome smaller [S142, 2026-05-15]. | Not checked | Not checked | Not checked | Web | Free [S142] |
| **alphaXiv** | Discover, Understand, Read, Keep | PDF. No reflowed view found up to 2026-10-22 [S27, 2026-10-18]. | Yes: select, then Ask AI. Chat references jump to the PDF passage. Resume reading returns after a jump [S28, 2026-10-12; S30, 2026-10-12]. | Several colours, notes, annotated PDF download. The assistant reads notes since 2026-10-02 [S29; S30]. | No own key; staff say an option for all users is difficult [S32, 2026-06-29]. Account for chat and notes. Library on alphaXiv's servers. | Web; iOS app [S27]; Android app on Google Play since September 2026 (third-party data) [S164]. (OpenResearch, a Linux desktop app, is a separate product.) | Free (strict limits), Go $8 ($5 for students), Pro $20, Pro 5x $100 a month. Company plans, read on 2026-10-05 [S26]. alphaXiv has no public pricing page. |
| **Zotero 10** with AI plugins | Keep, Read; Understand only with a plugin | PDF, and since 2026-08-17 Reading Mode: reflowed text made from the PDF layout. Images, tables, and figures show as in the PDF [S41, 2026-08-17; S147]. | No built-in AI [S43]. llm-for-zotero (AGPL, 3,378 stars): select and ask, citations jump to the passage, own key or local model [S19, 2026-10-22]. Beaver: login needed, requests go through Beaver's server [S44]. | Colours, notes, search by colour [S41; S42, 2026-01-22] | Local use needs no account [S42]. Own key through plugins. | Yes (ARM Linux since Zotero 8) [S42] | Free, open source. Beaver Plus $10 or $20 a month; own key unlimited [S44]. |
| **Rectoly** | Read, Keep | Reflowed text made from the PDF; inline formulas are PDF images [S45, 2026-10-13] | No chat screen (company claim) [S45] | Annotations on reflowed text; sync to Zotero or Mendeley [S45] | On-device AI or own key, for translation and paper cards only. Opens a PDF without sign-in [S45]. | Yes, since 2.1 (shipped between 2026-09-22 and 2026-10-13) [S45] | 14-day trial, then $19.99 or $49.99 once [S45] |
| **Moonlight** | Understand, Read | PDF in Chrome or on the web | Select and press E to explain; chat. Passage citations in chat: *unconfirmed* [S46]. | Manual colours and comments; AI auto-highlights [S46] | Google login. No key option found [S46]. | Chrome or web | Free (3 papers a week), Pro $10–12, Premium $49–59 a month [S46] |
| **SciSpace** | Understand, Read | PDF | Select to explain. Answers have citations that open the section [S47]. | Highlights and notes [S47] | Account. No key option found. | Web, Chrome | Basic free; Premium $20 a month ($12 billed yearly). Chat with PDF stays after credits run out [S47]. |
| **Readwise Reader** | Read, Keep, Understand | Reflowed articles and EPUB; PDFs stay PDF [S50] | Select and ask (Ghostreader). Global Ghostreader cites passages since 2026-08-07 [S50]. | Highlights, notes, tags [S50] | OpenAI key only, on top of a paid plan and a cloud account [S50] | Web only | $9.99 a month billed yearly, or $12.99 monthly [S50] |
| **Artifact** (withartifact.com) | Read, Understand, Keep | PDF in a web app | Highlight a sentence to open a thread pinned to it. Citation chips open the passage [S52]. | Margin notes rail [S52] | Account. Own Fireworks key. Free daily allowance [S52]. | Web | Free tier. MIT licence, 26 stars [S52]. |
| **Gemini Notebook** (NotebookLM until 2026-07-16 [S146]) | Understand | Source viewer beside chat | Citations open the passage. Select-and-ask in a source: not found [S49]. | No | Google account. No key [S49]. | Web | Free to $200 a month (third-party read) [S49] |
| **Semantic Reader** (Ai2) | Read, Understand | Augmented PDF of arXiv papers | No chat with passage citations found | AI skimming highlights. No built-in notes [S18]. | No | Web | Free. Last dated evidence is from 2024 [S18]. |
| **LocalXiv v0.1.0** | Read, Keep, Understand; Discover only through Paper search and Direct import | Reflowed text from the paper's LaTeX source (61 of 100 corpus papers) or from arXiv's HTML (22 of 100). 17 of 100 corpus papers open as the original PDF [S137]. | Yes: Ask and Explain. The answer streams into a Question card in the margin. Passage citations open the passage. Several quotes in one question. Chat sends one streamed request with no tool calls [S138; S168]. | Four named colours. Notes as margin cards. All Notes. Library Notes page with #tags. Notes move to a new arXiv version [S138]. | No LocalXiv account. Library and keys on the Mac. The app calls the provider directly from the Mac [S135]. | Not yet; planned. No Linux code in the repository yet [S170]. | Free, AGPL. The provider charges for each request. |

Also in the space:

- Google PAIR's Lumi is a free prototype for arXiv papers under Creative Commons licences. Its answers stay tied to the selection, and it shows the paper with AI as a supplement [S53, 2025-09-30].
- Elicit moved Chat with Papers into its Research Agent on 2026-09-30. It has left the reader lane [S48].
- The old Papers with Code benchmark job is split across CodeSOTA, Wizwand (now SOTA2), hyper.ai, and CatalyzeX. None of them is a reading tool [S13, 2026-07-21].
- Seven small Mac or desktop paper readers, each found on 2026-10-22:
  - Zoro: AGPL; macOS, Windows, and Linux; local-first; translates arXiv HTML; an in-app AI assistant with tool calls; an MCP server; 37 stars [S148].
  - Freddie: macOS; reads arXiv HTML first, then ar5iv; OpenAI-compatible providers; MIT; 20 stars [S149].
  - Episteme: macOS; local-first, no account; select text in the PDF and ask; citations tied to page regions; uses the Codex CLI [S150].
  - PaperMaster: macOS; highlights, margin notes, Ask AI on a selection, own OpenAI-compatible key, no account; 15 stars [S151].
  - Sift: macOS; ad hoc signed; highlights and a chat grounded in the paper; no account [S152].
  - PaperShelf: macOS; signed and notarized; arXiv search, highlights, MCP; last release 2026-03-04 [S153].
  - Embark Reader: native Mac and iOS arXiv reader with offline PDFs (company page, undated) [S154].

**What the map shows.**

- **Discovery is crowded and free.** Hugging Face Daily Papers, Scholar Inbox, Emergent Mind, and alphaXiv serve it [S12; S16; S17; S35]. LocalXiv does not compete there.
- **Chat on a paper is everywhere.** Hugging Face, paperswithcode.co, alphaXiv, Moonlight, SciSpace, Readwise, Artifact, Gemini Notebook, and Zotero plugins have it. Small Mac apps such as Zoro, Episteme, PaperMaster, and Sift have it too [S148; S150; S151; S152].
- **Reflowed text is contested.** arXiv's own HTML view is free, and it is the largest reflowed reader of arXiv papers [S142]. Zotero 10 and Rectoly reflow from the PDF layout. Freddie reads arXiv's HTML, and Zoro translates it [S149; S148]. LocalXiv builds the page from the paper's LaTeX source (61 of 100 corpus papers) or from arXiv's HTML (22 of 100), and typesets equations [S137]. No side-by-side test exists yet (Section 8.2).
- **Own key with no account is common among small open-source Mac apps.** Readwise, Beaver, MarginNote Max, Heptabase, and Artifact accept a key. Each one needs an account, and Beaver sends requests through its own server [S44; S50; S52; S57; S58]. Small open-source projects need no account: llm-for-zotero and Academic-Paper-Copilot send the key direct [S19; S55], and PaperMaster takes an own OpenAI-compatible key [S151]. Episteme and Sift also need no account [S150; S152]. Inference: "no LocalXiv account" is part of the base, not the lead.
- **The margin card is close to Artifact, alphaXiv, and PaperMaster.** Artifact pins a thread to a sentence. alphaXiv answers on a selection. PaperMaster has margin notes and Ask AI on a selection [S151]. LocalXiv puts the card beside the words of a reflowed page.
- **Watch Hugging Face (inference).** Hugging Face serves Markdown of every indexed paper at `/papers/<id>.md` [S10], and paperswithcode.co already has a PDF reader with chat [S6]. A reflowed reader on Hugging Face is one interface step away. If it ships, Hugging Face joins arXiv HTML as a reflowed reader on the web. Local data, own key, margin Notes, and EPUB stay.

## 3. The read-first verdict

**Verdict: resonant, with one condition.** The message must read as "read the paper, then ask about it". If people hear "read instead of using AI", the message becomes risky.

### 3.1 Evidence that summaries are not enough

| Evidence | What it shows | Limit | Source |
|---|---|---|---|
| Peters and Chin-Yee, Royal Society Open Science | Use the skeptic's wording: "Across 4,900 summaries from 10 LLMs, most models broadened scientific conclusions. On 100 clinical articles, summaries by GPT-4 Turbo, ChatGPT-4o and DeepSeek were almost 5 times as likely as expert-written NEJM Journal Watch summaries to overgeneralize." The odds ratio is 4.85. Prompts that asked for accuracy made it worse. Claude models did not differ significantly from the abstracts. | Science and medical texts, not ML papers. The abstract states the five-times comparison in general words; the body limits it to three models. Do not quote the abstract sentence alone. | [S60, 2025-04-30] |
| Isch and Jennings, ACL 2026 | Six late-2025 models made direct causal claims in 44% of summaries, against 34% of the abstracts. Cautious prompts reduced this, mainly for large models. | 100 social-science abstracts; results averaged across models | [S61, 2026-07] |
| Melumad and Yun, PNAS Nexus | More than 10,000 people in seven experiments. People who learned from LLM syntheses built shallower knowledge than people who learned from web links, also when the output had links. | Everyday topics. The authors say the effect may not hold for advanced science. | [S62, 2025-10-28] |
| Kreijkes and others, Computers & Education | Randomised and pre-registered, n=405. Students who used an LLM alone understood and kept less after three days than students who took notes, alone or with an LLM. Most students still preferred the LLM. | Students aged 14–15, not researchers | [S63, 2025-11-24] |
| Lee and others, CHI 2025 | Workers with more confidence in GenAI report less critical thinking. GenAI moves effort to checking the output. | Self-reported survey of 319 workers | [S64, 2025-04-25] |
| Hallucinated citations | At least 146,932 hallucinated citations in 2025 papers (preprint). GhostCite: 1.07% of 56,381 papers had invalid citations, up 80.9% in 2025. | Preprints | [S68, 2026-05-08; S69, 2026-02-06] |
| Product evidence | An independent review says alphaXiv's Overviews paraphrase with confidence even when slightly wrong, and that non-experts cannot easily see this [S37, 2026-06-14]. alphaXiv's audio Overview scripts changed for the worse without notice; staff confirmed it [S33, 2026-10-08]. | About one product; do not use it to attack | [S37; S33] |

The Kreijkes study fits LocalXiv best: an LLM plus notes beat an LLM alone. That is Highlights, Notes, and Ask together.

**Gap.** No source tests readers of arXiv ML papers. In public copy, say "studies of science summaries". Do not say "studies of ML papers".

### 3.2 The audience already uses AI, and checks it

- Nature surveyed about 3,800 PhD students in May–June 2025. 71% find AI use acceptable, 81% do not fully trust AI tools, and 65% worry that AI weakens their thinking, research, and writing skills [S65, 2026-03-16].
- Wiley (company survey, n=2,430, called "indicative"): 84% of researchers use AI. Of those who use AI in literature work, 50% always check claims against the primary source, and 25% do this most of the time [S66, 2025-08].
- Springer Nature (company claim, unpublished survey, n=2,021): 57% used AI to keep up with research or to read papers [S67, 2025-11-13].

### 3.3 Respected voices practise "read, then ask"

- Karpathy reads pass 1 by hand, then asks an LLM to explain, then asks questions [S70, 2025-11-18]. The post is about blogs, articles, and book chapters, not papers. The same post says writers may come to write for LLMs, so do not quote its first half alone. On the same day Karpathy released reader3, an EPUB reader for reading books together with LLMs [S70; S163].
- fast.ai teaches "close reading" with an LLM [S71, 2026-01-21]. The phrase now belongs to fast.ai. Do not use it as a tagline.
- Sebastian Raschka reads first, offline, and prints hard papers [S72, 2025-11-11].

### 3.4 The audience's own words

- r/MachineLearning: researchers use LLMs for triage and for specific questions, then check the paper. One caught a model that made up a method detail [S73, about 2026-02-25].
- Hacker News: a post calls the summary habit pretend learning. It proposes a move from "summarize it for me" to "debate it with me". Replies split, and several people say LLMs made them read more [S74, about 2026-04].
- Hacker News: experienced readers ask about jargon and equations, not for a summary, because a paper is already a summary of years of work [S75, about 2026-10-10].
- LinkedIn: a Stanford GSB professor hears from PhD students that nobody reads papers any more. Replies split between "this is the norm now" and "I want to read again" [S76, 2026-06-17].
- Reddit: a PhD student found AI summaries too shallow for deep reading and kept nothing [S77, about 2026-05].
- Under alphaXiv's Paperscrolling post, a user asked to tap an AI claim and go to the paragraph behind it [S40, 2026-10-06].
- Independent users already separate discovery from reading. They pull Hugging Face Daily Papers into Zotero, read there, and use AI as a discussion partner [S20, 2026-06-18].

### 3.5 What breaks the message

- A preachy "stop asking LLMs to summarize papers" post got replies that called it harmful and misguided [S79, 2025-05-03]. Educators who argue for primary literature often use the same tone [S78, 2026-03-26]. Do not copy it.
- The words of read-first are not free. Lumi, Rectoly ("Read, don't manage"), Elsevier LeapSpace, Nature Research Assistant, and Artifact use similar words [S53; S45; S54; S52]. Show read-first in the product. Do not depend on the phrase.

**Use these words in copy:** "read, then ask"; "ask about the lines you do not understand"; "check the passage"; "read what you cite".

**Keep out of copy:** "cognitive debt", "brain rot", "AI makes you dumb", and the MIT "Your Brain on ChatGPT" preprint (n=54, criticised for its methods) [S80].

## 4. Positioning recommendation

### 4.1 Category

**A Mac reader for arXiv papers.** Use the plain category "paper reader". Read-first is the stance, not the name of the category.

These labels are taken or crowded: "AI research assistant", "chat with PDF", "AI colleague" (Moonlight [S46]), "copilot of reading" (Readwise in 2022), "close reading" (fast.ai [S71]), "local-first" (note.md, pi-tree, PaperDock, alphaXiv's OpenResearch, Zoro, Episteme [S56; S55; S21; S148; S150]).

### 4.2 Positioning statement

> For researchers and engineers who still read the paper, LocalXiv is a free, open-source Mac reader. It reflows arXiv papers from their LaTeX source or arXiv's HTML, keeps your Highlights and Notes beside the words, and answers your questions in the margin with passages you can open. It uses your own key and needs no LocalXiv account.

### 4.3 Three pillars

All three stand on one base: no LocalXiv account, no analytics library in the code, library and keys on the Mac, AGPL source [S137; S135]. The app contacts arXiv, Semantic Scholar, doi.org, the update feed, and the chosen provider [S137]. So never write "nothing leaves your Mac".

| Pillar | Promise | v0.1.0 proof points | Limit to state |
|---|---|---|---|
| **1. Read: the paper, made readable** | The paper itself is the product. | Reflowed text from the paper's LaTeX source or arXiv's HTML, with typeset equations. Reading preferences: font, size, margins, line spacing, and the Light, Sepia, and Dark themes. Reference preview of a citation, figure, table, footnote, or equation; Back returns to the paragraph. The Paper reopens at the Reading position. Paper search by title or author. Direct import of arXiv and alphaXiv links. | In our test corpus, 61 of 100 papers convert from LaTeX, 22 from arXiv's HTML, and 17 open as the original PDF [S137]. The app bundles older Pandoc and EPUBCheck versions than the corpus [S136]. arXiv's own HTML view reflows most new papers [S142]. Zotero 10 and Rectoly also reflow, from the PDF [S41; S45]. |
| **2. Keep: your judgement, beside the words** | You decide what matters. The AI does not. | Four named Highlight colours: Key point, Question, Use in my work, Disagree. Notes as cards in the margin. Paper notes. All Notes with search, arrangements, and Note groups. A library Notes page with search and #tags. Notes move to a new arXiv version; a Not found Highlight keeps its quote and its Note. Export EPUB with Highlights and Notes. Send to Kindle (secondary). | alphaXiv has colours, notes, and annotated export [S30]. LiquidText carries annotations to a newer document [S51]. Moonlight and Semantic Reader highlight with AI, which is the opposite approach [S46; S18]. |
| **3. Ask: AI that points back to the page** | Citations open the passage. | Select words, then Ask or Explain. The answer streams into a Question card in the margin. Citation chips preview the passage, and a click opens it. Several quotes in one question. A separate Chat model: OpenAI, Anthropic, Gemini, DeepSeek, OpenRouter, a custom endpoint, or a model on the Mac. The app calls the provider directly from the Mac [S135]. The Overview and the Blog are optional and name the model and the date. | Answers can be wrong. The model decides whether to cite, and a small model may cite badly (Section 7.3). The provider charges for each request. Chat sends the selected text and the Paper's Highlights and Notes to the chosen provider [S136]. Chat sends one streamed request with no tool calls, so it is not an agent [S168]. |

### 4.4 Tagline candidates (under 9 words)

| Candidate | Words | Use |
|---|---|---|
| **A. "Read the paper. Ask in the margin."** (recommended) | 7 | Video cards, end card, X first line, README |
| B. "The paper first. AI in the margin." | 7 | Alternative that states the stance more directly |
| C. "For people who still read the paper." | 7 | Identity line for the first line of a post |

Why A:

- Both feeds now match posts to readers by the text itself: LinkedIn retrieves posts with LLMs since 2026-03-12, and X ranks with a Grok-based model [S106; S94]. So the first words must name the job in plain words.
- A states read-first without the crowded phrase.
- A names the visible difference: the margin.
- A uses no label from Section 4.1.
- One exact-phrase search found no other use of A. This is not proof.

Test A against C as the first line of the X post (Section 6.3).

Companion line for the complement position: **"Found it on arXiv or alphaXiv? Read it in LocalXiv."** Direct import accepts arxiv.org and alphaxiv.org links, not other hosts, and Paper search finds arXiv papers [S134]. Use "Find papers anywhere. Read them in LocalXiv." only after Direct import accepts more hosts, for example Hugging Face.

### 4.5 What not to claim

| Claim to avoid | Why | Say this |
|---|---|---|
| "The only app that reflows papers" | arXiv's HTML view, Zotero 10, and Rectoly reflow [S142; S41; S45] | "Reflowed from the paper's LaTeX source or arXiv's HTML." Claim that it reads better than other reflow only after a side-by-side test on papers with much maths (Section 8.2). |
| "First" or "only" select-and-ask, or "answers you can check" as unique | alphaXiv, Beaver, Artifact, and SciSpace have select-and-ask with passage citations [S28; S44; S52; S47]. alphaXiv marketed "highlight any section to ask" in about November 2025 (about 50K views) [S39]. PaperMaster and Episteme also ask on a selection [S151; S150]. Hugging Face has chat on its paper pages, but its passage citations are *unconfirmed* [S7; S9]. | Show the Question card beside the words on a reflowed page. |
| "Nothing leaves your Mac" | Chat sends the selection and the Highlights and Notes to the provider [S136]. The app also contacts arXiv, Semantic Scholar, doi.org, and the update feed [S137]. | "Your library, notes, and keys stay on your Mac. AI text goes only to the provider you choose, or to a model on your Mac." |
| "Notes survive any new version", or "first" to do it | LiquidText moves annotations to a newer document [S51] | "Your Notes move to the new arXiv version of the Paper." |
| "Any paper" or "every paper" | 17 of 100 corpus papers stay PDF [S137]. The app bundles older Pandoc and EPUBCheck versions than the corpus [S136]. | "83 of 100 papers in our test corpus open as reflowed text." |
| "Accurate answers" or "no hallucinations" | LocalXiv does not control the reader's model, and the audience doubts such claims [S60; S73] | "You choose the model. You see the source." |
| "Free AI" | The provider charges for each request | "A free app. Use your own key, or a model on your Mac." |
| "Works with VoiceOver" | No VoiceOver pass ran [S136]. alphaXiv's selection menu breaks screen readers [S31, 2026-10-21]. | Test first. Then say it. |
| "Local-first", "chat with your paper", or "understand a paper in minutes" as the lead | Crowded (Section 4.1; [S46; S47]) | Lead with tagline A. |
| Kindle or EPUB as the lead | The owner's choice. Readwise also sends to Kindle [S50]. | One beat near the end. |
| "Replaces Papers with Code" or "a better Hugging Face" | Papers with Code is shut down [S2]. Hugging Face is a complement. | Name neither in the video. |
| "AI agent" for Chat | Chat sends one streamed request with the selection, the passages, and the Notes. It has no tool calls [S168]. Hugging Face chat runs on an MCP server, Zoro's assistant calls tools, and paperswithcode.co calls its chat an agent [S7; S148; S6]. | "Ask" and "Chat". |
| "Every answer shows its source" | The model decides whether to cite, and a small local model may cite badly (Section 7.3). | "Citations open the passage." |
| "No account" with no qualifier | A cloud provider still needs its own account and key. | "No LocalXiv account." Or show the model on the Mac. |
| "No analytics" with no qualifier | The app contacts arXiv, Semantic Scholar, doi.org, the update feed, and the provider [S137]. | "No analytics library in the code." |
| "Find papers anywhere. Read them in LocalXiv." | Direct import accepts arxiv.org and alphaxiv.org links, and Paper search finds arXiv papers. Hugging Face links fail today [S134]. | "Found it on arXiv or alphaXiv? Read it in LocalXiv." |
| "Coming soon to Linux" as a promise | The repository has no Linux code, build, or issue, and the shell is AppKit [S170]. | The Linux line that the owner chooses, with no date (Section 5.8). |

**State these limits in the post text, not in the video:** early preview; Apple Silicon and macOS 26 or newer; ad hoc signed and not notarized, so macOS may block the first launch [S136]; AI is optional and can be wrong.

Do not show star counts. Do not use alphaXiv's OpenResearch telemetry event against it: it concerns another product, and alphaXiv fixed it by 2026-10-21 [S34].

### 4.6 Placement next to Hugging Face Papers and alphaXiv

- **Hugging Face Papers: a complement.** It finds, ranks, links code, and summarizes. Then it links out to the PDF [S8]. Workflow line, after Direct import accepts Hugging Face links: "Found it on Hugging Face Daily Papers. Read it in LocalXiv." Users already work this way with Zotero [S20]. Today Direct import rejects `huggingface.co/papers` links [S134]. Accept them before launch. Old `paperswithcode.com/paper/...` links also redirect there [S4, 2025-12-12].
- **paperswithcode.co: a complement on ranking and code, and a partial competitor on reading.** It shows the PDF with chat behind a Hugging Face sign-in [S6]. Since 2026-08-28 it also accepts non-arXiv PDFs (company claim) [S144].
- **alphaXiv: a complement on discovery, and a partial competitor on reading and understanding.**
  - Parity, not an edge: highlights in colours, notes, select-and-ask, chat references that open the passage, Resume reading after a jump, and an assistant that reads your notes [S28; S29; S30].
  - Differences that hold: reflowed text; the margin card on that text; your own key with no LocalXiv account; the library on the Mac; EPUB and offline reading [S27; S32].
  - LocalXiv already imports `alphaxiv.org` links: "Found it on alphaXiv? Paste the link."
- **Name no rival in the video or the main posts.** Answer in replies, politely and with facts. Prepared replies:
  - "Why not alphaXiv or Hugging Face chat?" — "They help you find papers and summarize them. LocalXiv is where you read the paper itself, on your Mac, with your key and your notes."
  - "Zotero 10 reflows PDFs now." — "Yes. LocalXiv builds the page from the paper's LaTeX source, or from arXiv's HTML, so equations are typeset."
  - "arXiv has HTML now." — "Yes, and LocalXiv uses it for some papers. LocalXiv adds your reading settings, a library on your Mac, Highlights and Notes in the margin, Ask, and EPUB export." The hook H1 invites this reply (Section 5.3) [S142].

## 5. Video implications

### 5.1 Length

- **Master: about 86 s (inside 80–90 s).** It is inside the 60–90 s that this report recommends. The owner's request names no length, and the current film is 44 s [S167]. It also fits the free X limit of 140 s [S81, 2026-10-11]. High-reach X launches had a median length of 83 s, and 89% were 16:9. Low-reach launches had a median of 32 s [S90, 2026-08-26]. In a second study, videos of 90 s or more had the highest median views [S89, 2026-08-17]. Both are vendor studies, and they show correlation only.
- **Optional extended cut: 2–3 min**, only if the X account has a paid tier. For accounts under 25K followers, 1–4 min videos reached about 3 times the views per follower of clips under 30 s [S92, 2026-10-12].
- **Cutdown: 25 s** of one job, Ask (Section 5.9).

### 5.2 Aspect ratios to render

| Ratio | Size | Use | Evidence |
|---|---|---|---|
| **16:9 (master)** | 1920×1080, H.264/AAC MP4 | X main post, GitHub README, LinkedIn default | 16:9 had about 11 times the median views of 9:16 among X launches [S89]. 16:9 shows the whole frame on iPhone in both orientations [S88, 2026-07-16]. |
| **4:5** | 1080×1350 | LinkedIn test or second post | Contested. One company page and some ad data favour landscape. LinkedIn's own ad research favours vertical [S116, 2026-10-13]. Render it and test it. |
| 9:16 | 1080×1920 | Optional, for the X iOS video tab | X says portrait suits its full-screen player [S87, 2026-02-18], but launch data favour 16:9. Low priority. |

Safe area for every ratio: about 6% margin on each side [S88]. Keep the bottom 10–17% clear of player controls [S128].

### 5.3 Hook options for the first 3 seconds

The first frame must be product motion. Among X launch videos, text-card opens had the lowest median views (164), face opens the highest (976), and product-demo opens were between (332) [S89]. Do not open on a logo, a title, or an "Introducing" card.

| Option | First 3 s | Card by about 2 s |
|---|---|---|
| **H1 (recommended)** | A dense two-column arXiv PDF on a laptop screen. The page reflows into one readable column at a large text size. Show a page of text, not figures or tables, unless the Paper's licence permits (Section 5.10). | "Same paper. Your page." |
| H2 | A fast scroll of an arXiv new-submissions list. One paper opens and reflows. Do not show the Hugging Face or alphaXiv interface. | "You found it. Now read it." |
| H3 | The hero loop already in motion: words selected on a reflowed page, the answer streaming into a margin card. | "Read the paper." then "Ask in the margin." |
| H4 (owner decides) | 2–3 s of hands on a keyboard, or the owner's face, then H1. | — |

A question such as "Do you still read the paper?" can sit over product motion. It must not stand alone on a blank card.

H1 invites the reply "arXiv already has HTML" [S142]. Use the prepared reply in Section 4.6.

### 5.4 Feature order and seconds (storyboard for the master)

The reading base comes before any AI, so the paper is the product [S73; S75]. Each act finishes one job, because straight feature lists were only 4% of high-reach scripts [S90].

| Time | s | Beat | Card text (at most 6 words a card) | Capture (Section 7) |
|---|---|---|---|---|
| 0:00–0:05 | 5 | Hook H1: the two-column PDF reflows | "Same paper. Your page." | Easy (H) |
| 0:05–0:11 | 6 | Name and what it is | "LocalXiv. A Mac reader for arXiv." / "Read the paper." / "Ask in the margin." | — |
| 0:11–0:20 | 9 | Reading base: theme to Dark or Sepia, font, size. Hover a citation and a figure for a Reference preview. Back. | "Your font. Your margins." / "Check a reference. Keep your place." | Easy (#8, #12). Show figure and table previews only from a Paper whose licence permits it (Section 5.10). |
| 0:20–0:33 | 13 | Highlights: Key point, then Disagree, Question, Use in my work. Type a Note with a #tag. The card appears in the margin. | "Mark what matters." / "Disagree is a colour." / "Notes sit beside the words." | Easy (#1–#3) |
| 0:33–0:54 | 21 | Ask: select words, Ask, type, "Reading the Paper…", the answer streams into the Question card. Hover a citation chip, click, the passage flashes, Back. Then Add Quote: two quotes, one question. | "Ask about these words." / "Answers point back to the page." / "Several quotes. One question." | Medium, needs a model (#4, #5) |
| 0:54–1:01 | 7 | Chat settings: the provider list with a model on this Mac. Never show a key. | "Your key. Or your Mac's model." / "No LocalXiv account." | Easy with the server patch (#11) |
| 1:01–1:09 | 8 | All Notes, then the library Notes page with a #tag toggle. Optional: a new arXiv version with the Notes in place. | "Every Note. Every Paper." | Easy to medium (#6, #7). Version shot hard (V). |
| 1:09–1:14 | 5 | Overview and Blog, short | "Optional. Model and date shown." | Easy (#12) |
| 1:14–1:17 | 3 | Export EPUB with Notes; the Send to Kindle dialog | "Take your Notes to your e-reader." | Easy. Never click Send (#10). |
| 1:17–1:26 | 9 | End card (Section 5.8) | — | — |

Optional (the owner decides): a 2–3 s beat of the `localxiv://` bookmarklet, which adds the arXiv or alphaXiv page in one click [S166]. It links the discovery sites to LocalXiv. The browser's permission prompt shows on screen.

Total: 86 s. Pace: a cut about every 3.5 s, the median of 1,952 launch films [S120]. In the opening, change something on screen every 1–2 s (vendor advice [S141, 2026-07-16]).

### 5.5 Caption rules for phones

The film has text cards and music and no voice, so the cards are the captions. Both feeds can autoplay video muted [S116; S140; S165].

- Use a heavy sans type: white with a 2–3 px dark outline, or a local scrim [S132, 2026-08-28].
- Use at most 2 lines, 42 characters a line, and 6 words a card [S128].
- Cap height: about 56–64 px for main cards and 100–140 px for hero lines at 1080p (inference from a floor of 36–60 px [S128] and a phone minimum of 38 px [S131]). Nothing the viewer must read is under 40 px.
- Hold each card at full opacity for at least max(1.2 s, 0.35 s a word). A fade does not count. A 6-word card needs 2.1 s [S129, 2026-09-01].
- Keep contrast at 4.5:1 or more against the worst background under the letters [S129].
- Use the app's terms exactly: Highlight, Note, Question card, Ask, Key point, Question, Use in my work, Disagree.
- Upload no .srt file for a film without a voice: burned-in text plus an .srt shows the text twice [S132]. If you add a voice, upload an .srt from the X desktop composer, which is the only place that accepts it [S86, 2026-06-04], and on LinkedIn. X makes auto-captions only for videos above a view threshold, which a small account may not reach [S85, 2026-08-20].
- On LinkedIn, turn off auto captions for a film with no voice [S165].
- Check every card on a phone at arm's length.

### 5.6 Zoom and cursor

- Never ask the viewer to read the full app window. At 1920 px wide, paper text on a phone is about 6–7 pt (inference). Free X accounts play video at 720p [S82].
- Push in 2x by default. Use about 1.5x when the paragraph and its margin card must both show. Ease over 350–500 ms. Hold 1.5–2 s on text. Zoom at most once every 3–4 s [S130, 2026-04-10].
- Capture at Retina 2x, so zooms stay sharp.
- Use a smooth cursor path, a slightly large cursor, and a quiet click ripple. Hide the cursor when idle. Select text with one slow drag. Show each result for at least 1.5 s [S130; S90].

### 5.7 Music and sound

- Music-led with no voice is the most common style among 1,333 launch films [S121]. Granola's Briefs film is a 32 s example with typed headlines and no voice [S125]. But 51% of high-reach X launches had a voice [S90]. Write the cards as a story in sentences to make up for this.
- About 120 BPM is the most common launch tempo [S120]. The beat grid in `tools/intro-video` already uses it [S167]. Cuts need not fall on the beat [S122]. Accent the UI reveals, as the Raycast teaser does [S123].
- Master at about −14 LUFS, with peaks at −1 dBTP or lower, for X [S131].
- The film must work with the sound off. Use only music that you have the rights to use on X and LinkedIn. The music of `tools/intro-video` is made in code by `music.mjs`, with no samples, so it needs no licence [S167].

### 5.8 End card and the Linux line

- Hold about 9 s.
  - Line 1: **LocalXiv**
  - Line 2: "Free and open source. No LocalXiv account."
  - Line 3: "macOS 26 · Apple Silicon"
  - Line 4: `github.com/Akhil-Theerthala/LocalXiv`
- After a short brightness or scale drop, show a smaller last line: the Linux line. Give no date. The Raycast teaser puts its "coming" news in the last beat the same way [S123].
- The wording of the Linux line is the owner's decision. The repository has no Linux code, build, or issue, and the shell is AppKit [S170]. Zoro already ships on Linux with AGPL, arXiv HTML, and an AI assistant, and Zotero 10 Reading Mode runs on Linux [S148; S147; S42]. Options: **"Coming soon to Linux."** only if Linux work starts before launch; otherwise **"Linux: in the works."** or **"Linux: planned."**
- More than half of launch films end on their own name [S120]. Give one action only: the URL.
- After Raycast's undated "Coming 2026" teaser, users were impatient, and Raycast later posted a video with a firm date [S123]. So in the post text, make the Linux line a demand test: open a GitHub issue for the Linux build, and link it so that people can add a vote. Count the votes and the replies.

### 5.9 Cutdowns and stills

- **25 s Ask cutdown:** 0–2 s, a selection already on a reflowed page; 2–14 s, the answer streams into the margin card with the model name visible; 14–20 s, a citation click opens the passage; 20–25 s, the end card. Use it as an X reply or a later single-feature post. Do not post it on LinkedIn: there, videos under 30 s did 6.7% worse than the author's average [S117, 2026-09-25].
- **4–6 clips of 15–40 s** for the X thread: Highlights, Ask, several quotes, the Notes page, your key and no LocalXiv account, Linux.
- **12–15 stills** for the LinkedIn document carousel.
- **Thumbnail:** the reflowed page with one coloured Highlight and a margin card. Upload it on X desktop and on LinkedIn [S105].
- **One strong still** for a later LinkedIn image post. For authors under 1,000 followers, images got +30.5% and video showed no lift [S117].

### 5.10 Honesty in the frame

- Use only real captures of the app.
- Every answer and citation on screen is real output from a real model. Section 7.3 gives the options.
- Choose a Paper that converts cleanly. Use no card that says "any paper".
- Choose a Paper with a licence that permits the use. The first page of the sample, 1706.03762v7, lets others reproduce its tables and figures, with attribution, "solely for use in journalistic or scholarly works" [S155]. A launch film is promotion. Choose a paper with a CC BY licence on its arXiv page, or show only the text of the sample. The app also includes this paper as its sample; the owner may want to check that use too. This is a risk to check, not legal advice.
- Crop a Chromium capture to the page. Show no window chrome that the Mac app does not have (Section 7.2).
- Never call Chat an agent. It sends one streamed request with no tool calls [S168].
- Keep the model name and the date visible where the app shows them.

## 6. Posting plan inputs for X and LinkedIn

### 6.1 Decide these first

| Question | Why it matters | Source |
|---|---|---|
| Which X tier does the account have? | Free: 140 s, 512 MB, 720p playback, no edits. Paid tiers: longer video, 1080p, 5 edits in 1 hour. On 2026-10-12 xAI started The X Subscription. It is open to new customers, and existing subscribers keep their plans [S84]. That X stopped selling X Premium (Basic included) to new buyers is *unconfirmed*. The entry plan is Plus at $8 a month. A third-party reading of X Help says that Plus, Premium, Super, and Ultra include longer videos and editing [S162]. 1080p on Plus is *unconfirmed*. | [S81; S82; S83; S84; S162] |
| How many followers on each platform, and in which time zone? | The posting windows below are in the audience's local time. Benchmarks depend on account size. | [S127] |
| A face on camera, or text only? | Face opens correlate with higher reach. | [S89] |
| Which Linux line, and where are votes counted? | The repository has no Linux code yet. The end card and the posts depend on it (Section 5.8). | [S170] |
| Notarize before launch? | The v0.1.0 DMG is ad hoc signed and has 2 downloads. If it stays unnotarized, put the steps to open an app that macOS blocks ([`docs/macos-release.md`](macos-release.md)) in the first X reply and in the first Hacker News comment. | [S136; S169] |
| Say that AI helped build LocalXiv? | The owner's project page says that the owner built it mostly with GPT-6 Astra in Codex. Hacker News readers, and the LinkedIn penalty on text that sounds like AI, make this a real choice. | [S161; S117] |

### 6.2 Timing

| Date | Event | Effect | Source |
|---|---|---|---|
| Week of 2026-10-26 | alphaXiv hinted at "something exciting next week" in a reply on 2026-10-21 or 2026-10-22 (seen only on a mirror) | Do not launch on the same day as alphaXiv. | [S24] |
| 2026-10-28 | Apple's Mac event | Inference: Mac news fills the feeds on that day. | [S158] |
| 2026-10-30 to 2026-11-01 | alphaXiv judges the ScienceClaw hackathon (company claim) | — | [S25] |
| 2026-11-03 | US general election | Inference: US news fills the feeds on that day and the day after. | [S156] |
| 2026-11-10 and 2026-11-16 | CVPR 2027 registration and submission deadlines, Anywhere on Earth | Inference: many ML readers are busy in the week before a CVPR deadline. | [S157] |

- Inference: Thursday 2026-11-05, or Tuesday 2026-11-17 to Wednesday 2026-11-18, is the safer window. Post at 14:00–18:00 UTC. Inference, by the US rule (no source): daylight saving time ends on the first Sunday of November, 2026-11-01, so 14:00 UTC is then 6 a.m. US Pacific and 9 a.m. US Eastern.
- **X:** Tuesday to Thursday. 84% of high-reach launches posted between 14:00 and 18:00 UTC [S90]. Sprout gives Tuesday to Thursday, 11 a.m.–4 p.m. local time, for tech [S101, 2026-03-31]. Weekends are weak [S92].
- **LinkedIn:** Tuesday to Thursday, 11 a.m.–4 p.m. local time [S113, 2026-03-31]. Buffer's 2026 data supports a test at 3–5 p.m. [S139, 2026-10-05]. For personal profiles the hour mattered little (−2% to +4%) [S117]. Post when you can answer comments for 1–2 hours.

### 6.3 X

| Item | Input | Source |
|---|---|---|
| Format | One main post with the 16:9 master as a native upload. Post by hand from x.com on a desktop, which allows a custom thumbnail. Do not use a scheduler: since 2026-04-20 X charges $0.20 per API post with a link, and some schedulers remove links. | [S98, 2026-04-22] |
| Text length | About 35–50 words of plain text. Open with tagline A, or with the name and what it is. 34% of high-reach captions started with "Introducing", against 9% of low-reach ones. Use few or no emoji (12% against 50%). | [S90] |
| Link | Put the GitHub link in the post body. X's head of product says to put links in the body with context, and X says it has not penalised links for over a year (company claims). Independent data conflict: Buffer found near-zero engagement on link posts from free accounts in 2025, and a study of 60 small accounts found 1.05 times the impressions in 2026. Test it on your own account. | [S119, 2026-04-13; S95, 2026-07-30; S96, 2025-10-14; S97, 2026-10-10] |
| Hashtags | None, or one. Posts with no hashtags did 7.5% better than the same accounts' other posts. | [S99, 2026-10-22] |
| Tags | Tag only people in the video or people who will reply. Do not name alphaXiv: its team replies fast and its users like it. | [S21] |
| Thread | 4–5 replies under the main post. The first post must work alone, because the ranking discounts replies. A thread's first post got 1.25 times the engagement of the same account's single posts. | [S94; S100, 2026-09-09] |
| After posting | Stay online for 2 hours and reply with content. In the ranking code, a reply weighs 5, a reply between mutual followers adds 15, a share by copied link weighs 20, a share by DM 5, a like 0.66, and a finished video view 0. The weights change often. | [S93, 2026-10-21] |
| Friends | Ask friends to follow the account before launch day. Do not DM them the link: actions on a post opened from a direct link do not count for ranking. | [S93] |
| Tone | Avoid "trending" bait and star counts. Researchers question upvotes as a quality signal. | [S14, 2026-10-04] |
| Pin and repost | Pin the launch post. Repost it only as a quote post with new information. Each extra post by the same author on one day scores lower. | [S94] |

**X thread ideas (inference):**

1. Main post: tagline A, two lines on what it does, the video, the link.
2. Reply 1: the 25 s Ask cutdown. "Select words. Ask. The answer cites the passage, and a click opens it."
3. Reply 2: a Highlights clip. "Four named colours, Disagree included. Notes sit beside the words."
4. Reply 3: a still of Chat settings. "Your key, or a model on your Mac. No LocalXiv account. No analytics library. AGPL."
5. Reply 4: honest limits. "Early preview. Apple Silicon, macOS 26. Not notarized. Some papers stay PDF. AI can be wrong." If the app stays unnotarized, add the steps to open it ([`docs/macos-release.md`](macos-release.md)).
6. Reply 5: the Linux line that the owner chooses, and a link to the GitHub issue for votes (Section 5.8). Add one real question: "Send me a paper that LocalXiv converts badly."

### 6.4 LinkedIn

| Item | Input | Source |
|---|---|---|
| Account | Post from the personal profile, not a company page. Superwhisper's company-page post got 39 reactions for the same launch that passed 605K views on X. alphaXiv's company-page product posts get 11–34 reactions. | [S133; S127; S36] |
| Format | Native video upload from a desktop, never a YouTube link. Custom thumbnail. 16:9 master; test 4:5 later. Length: the same 80–90 s master. 1–2 min videos did 6.2% better than the author's average; another set found 1–5 min best. | [S105; S117; S110, 2026-06-05] |
| Text | About 150–200 words (the best band for video posts is 176–200), or about 1,000–1,500 characters. Write a first-person story: why you built a reader for reading the paper, one concrete detail, one honest limit. "I", "my", or "we" in the first line gained about 19%. Story openers +31%. Text that sounds like AI −21%. Write it yourself. | [S118; S111; S117] |
| First line | Do not open with a question (about −17%). Do not use "Comment KEYWORD" (about −24% since July 2026). A belief line has a precedent: Granola opened its launch on "writing is thinking" (about 104K views on X). An example (inference): "Reading is thinking. I built LocalXiv so AI helps me read the paper, not skip it." | [S111, 2026-10-13; S126, 2024-05-22] |
| Link | Put the plain URL as the last line of the text. A link-preview card cost the most (0.51 within author). A URL in the last fifth of the text scored 1.24. "Link in the first comment" showed no gain. Another analysis put one external link at −18.8% median reach. | [S107, 2026-10-09; S115, 2026-05-22] |
| Hashtags and tags | 0–2 hashtags. Tag only people who appear in the post or will comment. | [S112, 2026-10-16; S107] |
| Feed rules | Since 2026-03-12, LinkedIn ranks with LLMs and acts against engagement pods. Do not coordinate engagement. | [S106] |
| Follow-up 1 | 2–4 days later, a PDF document carousel of 10–12 slides. Documents reached more people than video in every 2026 dataset, for example 1.39 times against 0.86 times the median reach. | [S108, 2026-06-02; S109, 2026-10-21] |
| Follow-up 2 | About a week later, one strong still with a short story. | [S117] |
| Featured | Add the launch post to the profile's Featured section. No Premium is needed. | [S114] |
| Proof point | One research link at most: Kreijkes and others (notes plus AI beat AI alone) [S63], or Peters and Chin-Yee in the wording of Section 3.1 [S60], or the TU Eindhoven library note [S59, 2026-02-24]. | — |

**Carousel slides (inference):** (1) "Read the paper. Ask in the margin." (2) The two-column PDF problem. (3) The same page, reflowed. (4) Reading preferences. (5) Reference preview and Back. (6) The four named colours. (7) A Note in the margin. (8) Ask and the Question card. (9) A citation opens its passage. (10) Your key, no LocalXiv account. (11) The Notes page with #tags. (12) "Free and open source. macOS now.", the Linux line that the owner chooses, and the URL.

### 6.5 Other channels on the same day

- **Show HN.** For Textfold, a Mac app whose developer had 2 X followers, Show HN brought most visitors and X brought almost none [S104, 2026-10-20]. Hacker News gave 206 points to the Papers with Code revival [S5, 2026-06-08]. Stress AGPL, the local library, and no LocalXiv account. The earlier LocalXiv post on Hacker News got 1 point [S137], so the title and the first comment matter. A new version is usually not enough for Show HN; a major overhaul probably is. A repost is acceptable when the earlier post got little attention. Hacker News asks for text that a person writes and forbids requests for votes [S160].
- **Indie Hackers.** It gave Textfold its best feedback [S104].
- **r/macapps.** It removed Textfold's post as spam [S104]. Read the rules first, and post from an account with history.
- **Product Hunt.** The owner's page says that LocalXiv launched there in September 2026 [S161]. Product Hunt asks for two months between posts and a significant update; before two months, a relaunch request is necessary [S159]. Find the date of the first launch first.

### 6.6 Expectations and measurement

- Small indie Mac launches from accounts with 5–6K followers got about 6K–25K views on X in the 30 days before 2026-10-22 [S127]. alphaXiv's reader-feature posts got 5K–21K views from 58.2K followers [S23]. Its launches about discovery and agents did far better; Paperscrolling got about 132K views [S22]. Reader features are a hard sell on X even for a large account. For a project with 2 stars and a v0.1.0 DMG with 2 downloads [S169], plan for hundreds to a few thousand views.
- The closest similar launch is Pond: a free, open-source Mac app with local data and an own key or a local model. From a 15K-follower account, with the link in the body and a 1:04 video, it got about 58K views and 1.5K bookmarks [S103, 2026-10-15].
- Big-launch numbers are not a fair benchmark. 5 of 10 checked high-reach launches had paid quote reposts [S90]. Do not buy undisclosed promotion.
- Record views, likes per 1,000 views, link clicks, GitHub stars, DMG downloads, issues, and Linux replies. Compare only with launches of similar reach.

## 7. Capture feasibility

Source: the capture-map lane read `app/static`, `app/server.py`, `papers/chat.py`, `papers/ai.py`, and `tools/intro-video/capture.mjs` [S138]. **No skeptic pass ran on this lane. Nobody ran the native app or `native_shot.py`.** The critic pass checked two items: Chat sends one streamed request with passages and has no tool calls [S168], and the beat grid is 120 BPM [S167]. Sample Paper: 1706.03762v7, chapter `reader/text/ch004.xhtml`. Its first page allows reuse of its tables and figures only in journalistic or scholarly works [S155]. Prefer shots of its text, or choose another Paper (Section 5.10).

### 7.1 Per feature

| # | Feature | How to stage | Needs AI | Feasibility | Main risk |
|---|---|---|---|---|---|
| H | Hook: two-column PDF to reflowed text | Screen-record the arXiv PDF of the Paper, then the Paper view. Join them in Remotion (inference; not in the capture map). | No | Easy | It is an edit, not an app transition. Do not imply that the app animates it. Show text, not figures or tables, unless the Paper's licence permits (Section 5.10). |
| 1 | Selection toolbar (4 swatches, Note, Ask, Explain, Copy) | Open the Paper, Paper view, ch004. Find words with `findWords` from `onetext.js`. Use a real mouse drag, and save its path to `rects.json` for the Remotion cursor. | No | Easy | A scroll hides every bar. A selection made in JS paints grey in Chromium. |
| 2 | A Highlight in each colour; the card at a mark | Select words in p00020, p00023, p00024, and p00027, and click each swatch. A click with no movement on painted words opens the Highlight bar. | No | Easy | The CSS Custom Highlight API in the headless Chromium build is not verified. Without it, no colour paints. |
| 3 | Note on a Highlight; Paper note | Toolbar Note, type slowly, Save. Add #tags for #7. Make a Paper note from All Notes. | No | Easy | Margin cards fold to markers when the margin is under 210 px. Keep a 1440 px width and 16 px text. |
| 4 | Ask: Question card, streamed answer, citation chips, preview, click to the passage, Stop | Use a fake or a real model (Section 7.3). Select words in p00024, Ask, Enter. Wait for the end of the answer before a citation hover. | Yes | Medium | The hover preview does not open on a streaming turn. Inline TeX shows raw while streaming, so script plain words. |
| 5 | Several quotes in one question | Ask on p00020, "Add Quote", select words in p00027, "Add to Question". Add Quote hides after 4 added quotes, so with the card's own selection a question can carry 5 [S168]. | Yes | Medium | A quote far from the card makes the card follow the view. Keep quotes near each other. |
| 6 | All Notes | `localxiv.command({name:'action', id:'all-notes'})`. Show search, arrangements, and Note groups. Make 6–8 records first. | No | Easy | Copy All and Export start clipboard or download actions. |
| 7 | Library Notes page with #tags | `{name:'go', to:'notes'}`. Toggle one tag. | No | Medium | The temporary library holds only the sample, so the page shows one Paper. More Papers need real imports over the network. |
| 8 | Reference preview | Hover the [2] citation in p00023, the Figure 2 link in p00020, the Table link to ch007, and the footnote in p00024. Wait about 450 ms. | No | Easy | The sample has no equation cross-reference, so no Equation preview without another Paper. Figure and table previews of the sample fall under its licence line [S155]. |
| 9 | Paper search Suggestions | Type "attention is all" in `#home-url`. Stub `/api/search` with one live response that you recorded and checked. | No | Easy | A live search can hit a 429 limit. The test fixture mixes real and made-up rows; do not copy it. |
| 10 | Export EPUB with Notes; Send to Kindle dialog | `#tb-more`, Share, "Export EPUB with Notes". For Kindle, set the placeholder `your-name@kindle.com`, open the dialog, check "Include Highlights and Notes", then close it. | No | Easy | **Blocker: never click `#send` and never submit `#kindle-form`.** The send job hands the EPUB to Mail.app on the real Mac. |
| 11 | Chat settings | `{name:'settings', pane:'chat'}`. With Option A in Section 7.3, a real model on `127.0.0.1:11434` makes the Local preset true. | No | Easy, with the server patch | **Blocker: Done or Escape after an edit saves keys to the real login Keychain.** The Local preset also sets Context size to 4096. |
| 12 | Overview, Blog, Split view, Reading preferences | Keep the "connected" route rewrite. Hover a Blog citation, then "Open in Paper" at a width of 1200 px or more. Use `#tb-aa` for preferences. | No | Easy | The sample's Overview and Blog come from an older pipeline. Check that they match v0.1.0 output. |
| V | Notes move to a new arXiv version | Needs a Paper with two arXiv versions, real imports, and the copy-Notes flow. | No | Hard | Not possible with the sample. Keep it optional in the storyboard. |

### 7.2 Blockers and fidelity risks

1. **`capture.mjs` is stale.** It dates from 2026-09-25, and the shell redesign merged on 2026-10-14. Most of its selectors no longer exist, for example `#tab-paper`, `#share-open`, and `#reading-preferences-dialog`. Rewrite it on `window.localxiv.command(...)`, the same commands that the Native shell sends.
2. **Keychain.** The temporary server reads and writes the owner's real login Keychain. If `chat_endpoint` points at a provider that the owner uses, the server finds the real key and makes a real, billed call. Patch `get_key`, `set_key`, and `delete_key` in the spawned server, as `tests/test_chat.py` does.
3. **Mail and outside actions.** Never click `#send`, `#reader-pdf`, or `#reader-arxiv`. Keep `auto_send` false. "Add" on a search row starts a real import.
4. **Web chrome against the native app.** Chromium shows the web toolbar and sidebar. v0.1.0 shows the AppKit shell in WebKit. Crop to the content, and show no window chrome that the Mac app does not have. Or capture natively. `native_shot.py` takes the front window and key focus, so ask the owner before any native run.
5. **Fonts and paint.** New York may fall back to Georgia in Chromium; Charter gives a stable look. Selection colours and `::highlight` may look different from WebKit.

### 7.3 The chat-stub approach, and how the answer stays true

**How the stub works.** The Chat path accepts any OpenAI-compatible endpoint. HTTP is allowed on loopback, and a loopback endpoint needs no key.

1. Start a small fake server (about 30 lines of Node inside `capture.mjs`) at `http://127.0.0.1:PORT/v1`.
2. Set `chat_endpoint`, `chat_model`, `chat_context: 200000`, and `onboarding_complete: true` through `/api/settings`.
3. The fake receives `POST /v1/chat/completions` with `stream: true`. It answers with Server-Sent Events: one `data:` line per text part, then a chunk with `finish_reason: "stop"`, then `data: [DONE]`. Without `[DONE]`, the app shows a provider error.
4. Send no usage chunk, so the card shows no false token count.
5. Pause about 1.5 s before the first text, to show "Reading the Paper…". Pause 0.1–0.3 s between words.
6. Keep the fake alive when the client closes the socket, because Stop closes it.
7. Choose the reply by the question text, so one fake serves Ask, Explain, and the several-quote question.

**Citation format.** Write `[p00024]` or `[p00020, p00023]`, with no space inside the brackets; the chip pattern in `render.js` is stricter than the server's. Cite only passages in ch004, so a click stays in the loaded chapter. Never cite the References (ch009). Good passages: p00020 (definition of scaled dot-product attention), p00023 (dot-product against additive attention), p00024 (why the scores are scaled), p00027 (several heads), p00030 (8 heads, cost).

**Honesty.** With a loopback endpoint, the provenance line of the saved turn reads "<chat_model> · this Mac · <date>". So:

- **Option A (recommended, inference):** run a real model on the Mac through the Local preset. The answer, the provenance line, and the "model on your Mac" claim are then all true. Test it on p00024 first, because a small model may cite badly.
- **Option B:** record one real answer from a model, then replay it through the fake for stable timing. If that model ran in the cloud, the "this Mac" line is false. Crop the line out, or use Option A or C.
- **Option C:** capture the native app with the owner's real cloud key. This needs a native run; ask the owner first.

Do not edit the page to show another provider. Do not show a real API key.

**Capture order.** Fake Chat server; patched app server; settings; Home and Suggestions; open the sample (it opens on the Overview); Overview and Blog shots; Paper view on ch004; Reference previews with no selection active; the four colours; Notes with #tags; Ask, Explain, and Stop; the several-quote question; All Notes; Notes page; Share menu and Kindle dialog; Chat settings last.

## 8. Claims refuted or unconfirmed

### 8.1 Refuted: do not repeat these

| Claim | What is true | Source |
|---|---|---|
| Papers with Code served 9,327 leaderboards, 79,817 paper-code links, and 5,628 datasets (CodeSOTA) | These are old 2022 figures with wrong labels. The later archive is much larger. | Skeptic check of [S4] and [S11] |
| Papers with Code data survives only as frozen archives | The Hugging Face archive powers paperswithcode.co and still changes. | [S11, 2026-10-22] |
| Meta deprioritised Papers with Code, so no one could maintain it | Ross Taylor says that the team of Ross Taylor at Meta pivoted to LLMs and that the founders left Meta. | [S3, 2025-07-25] |
| alphaXiv's $7M seed is its only round on record, and there was no press after 2026-10-17 | PitchBook lists three deals, and machine-written TipRanks items exist. The true part: no new funding round was found after 2026-10-17. | [S38] |
| "Across 4,900 summaries from 10 LLMs, LLM summaries were about 5 times more likely than expert summaries to overgeneralize" | The 5x figure covers 3 models on 100 clinical articles. Use the wording in Section 3.1. | [S60] |
| X has no working auto-captions | X auto-captions videos above a view threshold, now with Grok. The .srt upload on the desktop composer is still correct. | [S85, 2026-08-20] |
| PPC Land read the X ranking weights on 2026-08-13 | The article is dated 2026-09-21. | Skeptic check of [S93] |
| LocalXiv rebuilds 83 of 100 corpus papers from the TeX source | 61 convert from TeX, 22 from arXiv HTML, and 17 stay PDF. | [S137] |
| Own key with no account is rare | It is common among small open-source Mac apps, for example PaperMaster [S151]. Episteme and Sift also need no account [S150; S152]. | Critic pass |
| Hugging Face has chat on every paper since 2026-01-07 | At launch the chat used arXiv HTML. About 27,000 papers with no HTML got chat after an OCR run. | [S9, 2026-04-07] |
| paperswithcode.co launched on 2026-05-18 | About 2026-05-17: on 2026-05-24 Niels Rogge wrote that it launched one week earlier. | [S143] |
| Zotero 10 Reading Mode shows some maths as page images | The Zotero text names images, tables, and figures, not maths. | [S147] |
| A LocalXiv question carries at most 4 quotes | Add Quote hides after 4 added quotes. With the card's own selection, a question can carry 5. | [S168] |
| v0.1.0 was published on 2026-10-21 | GitHub published v0.1.0 on 2026-10-22. | [S169] |

### 8.2 Unconfirmed: mark as such, or do not use

- Whether the Hugging Face chat on paper pages is free, needs a login, or cites passages [S7]. Public paper pages need no login [S171], but that covers the page and its `.md` file, not the chat. Owner test, about 1 minute: open `huggingface.co/papers/<id>` while logged out, ask one question, and look for passage links.
- That the Hugging Face OCR read at most 30 pages of each paper. Only a third-party summary says so [S145].
- Whether paperswithcode.co lets users bring their own provider. Only privacy-policy wording suggests it [S6].
- Whether chat answers in Moonlight and paperswithcode.co cite passages that you can click [S46; S6].
- Select-and-ask inside a Gemini Notebook source [S49].
- Custom AI for all MarginNote Max users. The manual and the pricing FAQ disagree [S57].
- 1080p for the X Plus plan after 2026-10-12. A third-party reading of X Help says that Plus includes longer videos and editing [S84; S162].
- That X stopped selling X Premium (Basic included) to new buyers on 2026-10-12. The xAI text says that The X Subscription is open to new customers and that existing subscribers keep their plans [S84].
- That a link added to an X post by a later edit gains reach. No source tests it.
- That LocalXiv's page, from LaTeX or arXiv's HTML, reads better than PDF reflow or arXiv's own HTML view on papers with much maths. Run 5–10 corpus papers in Zotero 10, arXiv HTML, and LocalXiv first [S41; S142].
- That tagline A is free to use. One exact-phrase search found no other use. This is not proof.
- That LocalXiv works with VoiceOver. No test ran [S136].
- The 19-hour counts for alphaXiv's Library post (129 likes, 6,409 views). The skeptic did not see them [S21].
- Third-party size estimates for alphaXiv (1.13M visits a month, a team of 8 or 9).
- An agency claim that Granola's Apple Watch film passed 2.5M views on X.
- That llm-for-zotero and zotero-ai-explain are unfunded. No source says so. Also, zotero-ai-explain supports Zotero 8–9 only and has 6 stars.
- Results of a follow-up study by Peters and others (only a pre-registration exists), and an eLife essay on AI summaries (the page did not load).
- That a founder presents the Raycast Pro film, and that the Linear Releases film shows no words in its first 3 s.

### 8.3 Statements in the brief of 2026-10-17 that are now out of date

- "Comfortable reading of the paper itself: Unclaimed" → contested by arXiv's own HTML view, and since Zotero 10 Reading Mode (2026-08-17) and Rectoly [S142; S41; S45].
- "alphaXiv, unlike Hugging Face Papers, has an assistant on every paper" → Hugging Face has chat on paper pages since 2026-01-07, and on about 27,000 papers with no HTML since an OCR run [S7; S9].
- "LocalXiv has no chat with the Paper" → v0.1.0 has Chat, Ask, and Explain.
- "Users still report no way back after a citation (#416)" → alphaXiv has Resume reading. #416 closed as fixed on 2026-10-12 [S28].
- "Your own model: unclaimed by a funded product" → only partly true. Readwise, Beaver, MarginNote, Heptabase, and Artifact accept a key, each with an account [S44; S50; S52]. Among small open-source Mac apps, an own key with no account is common [S19; S55; S151].
- "Model and date on each explanation: LocalXiv strong" → Hugging Face names the model on its one-line summary, with no date [S8]. LocalXiv's edge is narrower: the model and the date on each explanation, plus passage citations.
- Papers with Code as a competitor → shut down on 2025-07-24 [S2].
- Hugging Face Papers under "could add reading" → it now has chat and no reader. Its revival paperswithcode.co has a PDF reader with chat [S6].
- Competitive set → add Zotero 10, Rectoly, llm-for-zotero, and the seven Mac or desktop readers of Section 2 (Zoro, Freddie, Episteme, PaperMaster, Sift, PaperShelf, Embark Reader) to the direct set [S148–S154]. Keep arXiv HTML and ar5iv in the direct set, as the brief had them [S142]. Remove Elicit from the reader set [S48].
- "Android app (2026-10-06)" → alphaXiv's Android app is on Google Play since September 2026 (version 1.5.0 on 2026-09-28) [S164]. 2026-10-06 is the date of the Paperscrolling launch.

### 8.4 Weak sources: do not cite in public

- The MIT "Your Brain on ChatGPT" preprint [S80].
- GPTZero's NeurIPS count. GPTZero sells detection. If you use it, write "about 100 hallucinated citations in more than 50 accepted papers, GPTZero says."
- The Springer Nature quote by a CMU dean. It supports skimming, not reading [S67].
- The GhostCite figure that 41.5% copy BibTeX without a check. It comes from 94 responses [S69].

## 9. Sources

Keys are grouped by lane. A gap in the numbers is a key that the report does not use. Keys S142–S171 come from the critic pass. They are under "Critic pass" below and also in Section 10.6.

### Hugging Face Papers and Papers with Code

| Key | Source | Date | URL |
|---|---|---|---|
| S1 | paperswithcode.com returns HTTP 302 to Hugging Face Trending Papers (curl check) | 2026-10-22 | https://paperswithcode.com/ |
| S2 | Julien Chaumond (Hugging Face), LinkedIn: Papers with Code sunset, Trending Papers | 2025-07-25 | https://www.linkedin.com/posts/julienchaumond_breaking-weve-partnered-with-meta-and-activity-7354483119762153472-H9lJ |
| S3 | Ross Taylor (Papers with Code co-founder), LinkedIn | 2025-07-25 | https://www.linkedin.com/posts/rosstaylor90_the-sun-has-set-on-papers-with-code-activity-7354499081848688640-jJKx |
| S4 | GitHub issue #116, paperswithcode-data, with replies by Julien Chaumond (redirects set up 2025-12-12) | 2025-08-14 to 2025-12-16 | https://github.com/paperswithcode/paperswithcode-data/issues/116 |
| S5 | Hacker News, "Reviving Papers with Code" (206 points). For the launch date (about 2026-05-17), see S143. | 2026-06-08 | https://news.ycombinator.com/item?id=48443644 |
| S6 | Niels Rogge (Hugging Face), LinkedIn: chat with PDF on paperswithcode.co. Also the paperswithcode.co privacy policy, effective 2026-08-11 (URL not recorded). | 2026-08-20 | https://www.linkedin.com/posts/niels-rogge-a3b7a3127_introducing-chat-with-pdf-on-papers-with-activity-7496198957870682113-KHvQ |
| S7 | Hugging Face changelog, HuggingChat for Papers | 2026-01-07 | https://huggingface.co/changelog/huggingchat-papers |
| S8 | Hugging Face paper page 2510.04871: AI summary names its model; links to the PDF; no body text | observed 2026-10-22 | https://huggingface.co/papers/2510.04871 |
| S9 | Niels Rogge, Hugging Face blog: OCR of about 27,000 papers for chat | 2026-04-07 | https://huggingface.co/blog/nielsr/ocr-papers-jobs |
| S10 | Hugging Face changelog, papers for agents | 2026-03-24 to 2026-10-08 | https://huggingface.co/changelog/papers-for-agents |
| S11 | Hugging Face pwc-archive dataset (says it powers paperswithcode.co) | read 2026-10-22 | https://huggingface.co/pwc-archive |
| S12 | Hugging Face blog, Daily Papers | 2024-09-23 | https://huggingface.co/blog/daily-papers |
| S13 | Coursera, Papers with Code article (updated 2026-10-05) | 2026-07-21 | https://www.coursera.org/articles/papers-with-code |
| S14 | Repost of Junyang Lin's X post on bought upvotes | 2026-10-04 | https://airebao.com/item/39814 |
| S16 | Scholar Inbox, ACL 2025 demo paper | 2025-06-14 | https://arxiv.org/html/2504.08385v2 |
| S17 | Emergent Mind home page (company) | 2026-08-21 | https://www.emergentmind.com/ |
| S18 | Semantic Scholar FAQ and the Semantic Reader page | last dated evidence 2024-09-19 | https://semanticscholar.org/faq ; https://www.semanticscholar.org/product/semantic-reader |
| S19 | llm-for-zotero README and GitHub API | 2026-10-22 | https://github.com/yilewang/llm-for-zotero |
| S20 | Blog on a daily-paper workflow (Hugging Face Daily Papers into Zotero) | 2026-06-18 | https://yanxingliu.github.io/posts/2026/06/daily-paper-workflow/ |

### alphaXiv

| Key | Source | Date | URL |
|---|---|---|---|
| S21 | alphaXiv on X (nitter mirror): Library relaunch, Flint post, 58.2K followers | 2026-10-21 to 2026-10-22 | https://nitter.rdrama.net/askalphaxiv |
| S22 | alphaXiv launch posts on X (mirror search for "Introducing") | counts read 2026-10-22 | https://nitter.rdrama.net/search?f=tweets&q=from%3Aaskalphaxiv+Introducing |
| S23 | alphaXiv citation and highlight-and-ask posts on X (mirror search) | counts read 2026-10-22 | https://nitter.rdrama.net/askalphaxiv/search?q=citations |
| S24 | alphaXiv reply that hints at a launch "next week" (TwStalker mirror) | 2026-10-21 or 2026-10-22 | https://ww.twstalker.com/askalphaxiv |
| S25 | alphaXiv post on ScienceClaw (mirror), and the hackathon site | 2026-10-15 | https://nitter.rdrama.net/askalphaxiv/media ; https://scienceclawhack.ai/ |
| S26 | ToolGPA, alphaXiv prices as read from alphaxiv.org | 2026-10-05 | https://toolgpa.com/tools/alphaxiv/pricing |
| S27 | alphaXiv iOS App Store listing and version history (2.0.0) | about 2026-10-18 | https://apps.apple.com/us/app/alphaxiv/id6782411985 |
| S28 | alphaXiv feedback #416, Resume reading | 2026-10-10 to 2026-10-12 | https://github.com/alphaXiv/feedback/issues/416 |
| S29 | alphaXiv feedback #272, notes for the assistant | 2026-10-02 | https://github.com/alphaXiv/feedback/issues/272 |
| S30 | alphaXiv feedback #419, highlight colours and selection menu | 2026-10-12 | https://github.com/alphaXiv/feedback/issues/419 |
| S31 | alphaXiv feedback #429, selection menu breaks screen readers | 2026-10-21 | https://github.com/alphaXiv/feedback/issues/429 |
| S32 | alphaXiv feedback #317, own key request | 2026-06-29 | https://github.com/alphaXiv/feedback/issues/317 |
| S33 | alphaXiv feedback #406, audio Overview change | 2026-10-01 to 2026-10-08 | https://github.com/alphaXiv/feedback/issues/406 |
| S34 | OpenResearch releases v0.2.19 and v0.2.20, and issue #658 | 2026-10-14 to 2026-10-21 | https://github.com/alphaXiv/OpenResearch/releases ; https://github.com/alphaXiv/OpenResearch/issues/658 |
| S35 | alphaxiv.org home page (company wording) | 2026-10-22 | https://www.alphaxiv.org/ |
| S36 | alphaXiv company page on LinkedIn, citation-hover post | 2026-09-15 | https://www.linkedin.com/posts/alphaxiv_research-papers-are-filled-with-citations-activity-7505697007202807808-k-HG |
| S37 | ToolCenter, alphaXiv review after four months of use | 2026-06-14 | https://www.toolcenter.ai/en/articles/alphaxiv-review-2026 |
| S38 | PitchBook profile of alphaXiv | read 2026-10-22 | https://pitchbook.com/profiles/company/770062-33 |
| S39 | Mirror of alphaXiv's X post: Gemini 3 Pro, highlight any section to ask | about 2025-11 | https://www.24vids.com/video/introducing-gemini-3-pro-for-understanding-research-papers-highlight-any-p-tw-1991051362550038582 |
| S40 | Reply under alphaXiv's Paperscrolling post that asks for claim-to-source links | 2026-10-06 | https://nitter.cf/askalphaxiv/status/2107486537206419769 |

### AI paper readers

| Key | Source | Date | URL |
|---|---|---|---|
| S41 | Zotero changelog, 10.0 Reading Mode | 2026-08-17 | https://www.zotero.org/support/changelog |
| S42 | Zotero 8.0 changelog (ARM Linux, themes) | 2026-01-22 | https://www.zotero.org/support/8.0_changelog |
| S43 | Zotero forum, "AI elephant in the room" | 2026-06-03 to 2026-08-12 | https://forums.zotero.org/discussion/132016/ai-elephant-in-the-room-what-is-zotero-s-strategy |
| S44 | Beaver docs: API key and credits | accessed 2026-10-22 | https://www.beaverapp.ai/docs/api-key ; https://www.beaverapp.ai/docs/credits |
| S45 | Rectoly site and blog (company); Show HN on 2026-09-22 | 2026-10-13 | https://rectoly.com/ ; https://rectoly.com/blog/on-device-ai-notes-paper-cards/ |
| S46 | Moonlight pricing (company) | accessed 2026-10-22 | https://www.themoonlight.io/en/pricing |
| S47 | SciSpace Chat with PDF. Prices from the SciSpace credits guide (2026-03-12) and searchsagar.com (2026-10-07); URLs not recorded. | accessed 2026-10-22 | https://scispace.com/chat-pdf |
| S48 | Elicit changelog | 2026-09-30 | https://support.elicit.com/en/articles/14823097-changelog |
| S49 | Google Workspace, Gemini Notebook. Prices from a third-party guide (2026-09). Rename date from Google (S146). | accessed 2026-10-22 | https://workspace.google.com/products/gemini-notebook/ |
| S50 | Readwise docs, Global Ghostreader | 2026-08-07 | https://docs.readwise.io/reader/guides/ghostreader/global |
| S51 | LiquidText App Store listing | accessed 2026-10-22 | https://apps.apple.com/us/app/liquidtext/id922765270 |
| S52 | Artifact repository and site | repository created 2026-03-23 | https://github.com/levensti/artifact ; https://www.withartifact.com/ |
| S53 | Google PAIR, Lumi | 2025-09-30 | https://medium.com/people-ai-research/read-smarter-not-harder-with-lumi-6a1a8210ccc7 |
| S54 | Elsevier LeapSpace page (read-first wording) | accessed 2026-10-22 | https://researcher.elsevier.com/ |
| S55 | Academic-Paper-Copilot (AGPL, no account, own key) | 2026-09-21 | https://github.com/Marastraluster/Academic-Paper-Copilot |
| S56 | note.md on Product Hunt (via hunted.space) | 2026-06-26 | https://hunted.space/dashboard/note-md |
| S57 | MarginNote 4 manual, Custom AI | 2025-10 | https://manual.marginnote.com.cn/mn4/en/custom-ai-api-configuration/ |
| S58 | Heptabase plans and pricing | 2026-10-12 | https://support.heptabase.com/en/articles/12990121-plans-and-pricing |
| S59 | TU Eindhoven library, AI summaries for study and research | 2026-02-24 | https://www.tue.nl/en/our-university/library/library-news/24-02-2026-are-ai-generated-summaries-suitable-for-studying-and-research |

### Read-first evidence

| Key | Source | Date | URL |
|---|---|---|---|
| S60 | Peters and Chin-Yee, Royal Society Open Science 12(4) | 2025-04-30 | https://royalsocietypublishing.org/rsos/article/12/4/241776/235656/Generalization-bias-in-large-language-model |
| S61 | Isch and Jennings, ACL 2026 | 2026-07 | https://aclanthology.org/2026.acl-long.746.pdf |
| S62 | Melumad and Yun, PNAS Nexus 4(10) | 2025-10-28 | https://academic.oup.com/pnasnexus/article/4/10/pgaf316/8303888 |
| S63 | Kreijkes and others, Computers & Education 243 | 2025-11-24 | https://doi.org/10.1016/j.compedu.2025.105514 |
| S64 | Lee and others, CHI 2025 | 2025-04-25 | https://dl.acm.org/doi/full/10.1145/3706598.3713778 |
| S65 | Nature, PhD students and AI (Linda Nordling) | 2026-03-16 | https://www.nature.com/articles/d41586-026-00843-y |
| S66 | Wiley ExplanAItions 2025 (survey 2025-07-31 to 2025-08-18) | 2025-08 | https://www.wiley.com/content/dam/wiley-com/en/pdfs/about/wiley-explanaitions-2025-the-evolution-of-ai-in-research.pdf |
| S67 | Springer Nature, Perspectives on AI in scholarly communications (blog dated 2025-11-13) | 2025-11-13 | https://stories.springernature.com/AI-perspectives/ |
| S68 | Zhao and others, hallucinated citations audit (arXiv preprint) | 2026-05-08 | https://arxiv.org/abs/2605.07723 |
| S69 | GhostCite (arXiv preprint) | 2026-02-06 | https://arxiv.org/html/2602.06718v1 |
| S70 | Karpathy's X post, via a LinkedIn repost | 2025-11-18 | https://www.linkedin.com/posts/stshapiro_andrej-karpathy-karpathy-on-x-activity-7396399596622684160-asyR |
| S71 | fast.ai, AI for close reading | 2026-01-21 | https://www.fast.ai/posts/2026-01-21-reading-LLMs/ |
| S72 | Sebastian Raschka, on reading | 2025-11-11 | https://sebastianraschka.com/blog/2025/reading-books.html |
| S73 | r/MachineLearning thread via a mirror | about 2026-02-25 | https://reddit.sentinel-team.org/posts/1rdcw0o/snapshots/2026-02-25T18%3A59%3A41.410411Z |
| S74 | Hacker News, "making lazy look productive" | about 2026-04 | https://news.ycombinator.com/item?id=47555081 |
| S75 | Hacker News comment on reading papers with LLMs | about 2026-10-10 | https://news.ycombinator.com/item?id=49852743 |
| S76 | Kuang Xu, LinkedIn | 2026-06-17 | https://www.linkedin.com/posts/kuangxu_lately-more-and-more-people-i-talk-to-and-activity-7473158561557295104-MPYd |
| S77 | Reddit post by a PhD student, via a mirror | about 2026-05 | https://reddit.sentinel-team.org/posts/1tjmmvh/snapshots/2026-05-22T05%3A20%3A12.458066Z |
| S78 | The Transmitter, students should read primary literature | 2026-03-26 | https://www.thetransmitter.org/neuro-education/friction-maxxing-in-school-students-should-read-primary-literature-not-ai-summaries/ |
| S79 | LinkedIn post against AI summaries, and its replies | 2025-05-03 | https://www.linkedin.com/feed/update/urn:li:activity:7324528531126833152 |
| S80 | MIT "Your Brain on ChatGPT" preprint (do not cite) | 2025-06-10 | https://arxiv.org/abs/2506.08872 |

### Launch playbook

| Key | Source | Date | URL |
|---|---|---|---|
| S81 | X Help, videos (Wayback copy) | captured 2026-10-11 | http://web.archive.org/web/20261011092349/https://help.x.com/en/using-x/x-videos |
| S82 | X developer docs, media best practices (720p and 1080p) | fetched 2026-10-22 | https://docs.x.com/x-api/media/quickstart/best-practices |
| S83 | X Help, edit post (Wayback copy) | captured 2026-05-10 | http://web.archive.org/web/20260510040207/https://help.x.com/en/using-x/edit-post |
| S84 | xAI, The X Subscription (also TechCrunch, 2026-10-13) | 2026-10-12 | https://x.ai/news/x-subscription |
| S85 | xAI, auto-captions on X with Grok | 2026-08-20 | https://x.ai/stories/x |
| S86 | RNID, captions on X | 2026-06-04 | https://rnid.org.uk/information-and-support/technology-and-products/social-media-captions/twitter/ |
| S87 | TechCrunch, X vertical video player | 2026-02-18 | https://techcrunch.com/2026/02/18/x-continues-to-bet-on-vertical-video-with-its-latest-update/ |
| S88 | note.com, device test of X video crops | 2026-07-16 | https://note.com/rco/n/na8d4edd12c94?hl=en |
| S89 | Infinite, study of launch videos (vendor) | 2026-08-17 | https://hub.infinite.fast/research/launch-videos |
| S90 | Indie Hackers, 293 X launch videos (Distribb, vendor) | 2026-08-26 | https://www.indiehackers.com/post/product-launch-video-7-steps-from-293-x-launches-8ad570fb47 |
| S92 | Doomers, what predicts a big launch (vendor) | 2026-10-12 | https://doomers.ai/guides/what-predicts-a-big-launch |
| S93 | xai-org/x-algorithm, `param.rs` | sync 2026-10-21 | https://github.com/xai-org/x-algorithm/blob/main/home-mixer/params/param.rs |
| S94 | xai-org/x-algorithm, README | 2026-01-19 | https://www.github.com/xai-org/x-algorithm |
| S95 | PPC Land, X drops the link penalty | 2026-07-30 | https://ppc.land/x-drops-year-old-link-penalty-musk-tells-zuckerberg-on-platform/ |
| S96 | Buffer, links on X | 2025-10-14 | https://buffer.com/resources/links-on-x/ |
| S97 | OpenTweet, does X penalize links in 2026 | 2026-10-10 | https://opentweet.io/answers/does-x-penalize-links-2026 |
| S98 | TechCrunch, X API link price | 2026-04-22 | https://techcrunch.com/2026/04/22/x-makes-it-more-expensive-to-post-links-through-its-api/ |
| S99 | PlayerSells, hashtags on X | 2026-10-22 | https://playersells.com/insights/hashtags |
| S100 | PlayerSells, threads against single posts | 2026-09-09 | https://playersells.com/learn/do-threads-beat-single-posts-on-x-measured-within-account |
| S101 | Sprout Social, best times to post on X | 2026-03-31 | https://sproutsocial.com/insights/best-times-to-post-on-twitter/ |
| S103 | Launch Video Company directory, Pond | 2026-10-15 | https://www.launchvideo.com/directory/pond |
| S104 | Textfold, first paying customer | 2026-10-20 | https://textfold.app/blog/first-paying-customer |
| S105 | LinkedIn Help, video specifications | read 2026-10-22 | https://www.linkedin.com/help/linkedin/answer/a7486279 |
| S106 | LinkedIn news, improving the feed | 2026-03-12 | https://news.linkedin.com/2026/ImprovingTheFeed |
| S107 | NBK Social, what works on LinkedIn (74,119 posts) | 2026-10-09 | https://www.nbksocial.com/research/what-works-on-linkedin/ |
| S108 | ContentIn, LinkedIn statistics (AuthoredUp data) | 2026-06-02 | https://contentin.io/blog/linkedin-content-statistics/ |
| S109 | MyFeedIn, best LinkedIn post format | updated 2026-10-21 | https://myfeedin.co/best-linkedin-post-format |
| S110 | MagicPost, LinkedIn video length (122K videos) | 2026-06-05 | https://magicpost.in/es/blog/best-linkedin-post-format |
| S111 | Flypost, LinkedIn study 2026 (vendor) | 2026-10-13 | https://www.flypost.io/press/linkedin-study-2026/flypost-linkedin-study-release-C.pdf |
| S112 | PostNext, hashtags on LinkedIn | 2026-10-16 | https://postnext.io/blog/do-hashtags-work-on-linkedin/ |
| S113 | Sprout Social, best times to post on LinkedIn | 2026-03-31 | https://sproutsocial.com/insights/best-times-to-post-on-linkedin/ |
| S114 | LinkedIn Help, Featured section | read 2026-10-22 | https://www.linkedin.com/help/linkedin/answer/a550399/manage-featured-samples-of-your-work-on-your-linkedin-profile?lang=en |
| S115 | Summary of Richard van der Blom's 2026 report | 2026-05-22 | https://melaniegoodmanlinkedinconsultant.substack.com/p/linkedin-algorithm-2026-reach-topic-authority |
| S116 | PostInstantly, LinkedIn video posts (autoplay; summary of LinkedIn Creative Labs ad data) | 2026-10-13 | https://postinstantly.com/guides/linkedin-video-posts |
| S117 | LigoSocial, LinkedIn post formats (134,522 posts, vendor) | 2026-09-25 | https://ligosocial.com/research/linkedin-post-formats |
| S118 | Willow, LinkedIn caption length report (vendor) | posts 2024-09 to 2026-09 | https://willow.co/assets/media/LinkedIn-Caption-Length-Report-Willow.pdf |
| S119 | Roboin, X recommends links in the post | 2026-04-13 | https://roboin.io/article/en/2026/04/13/x-denies-link-deboost-recommends-in-post-links/ |
| S139 | Koldflux, best time to post on LinkedIn (compares Sprout, Buffer, Hootsuite) | 2026-10-05 | https://koldflux.com/learn/growth-and-analytics/best-time-to-post/best-time-to-post-on-linkedin |
| S140 | Socialkit, X video size (autoplay muted) | verified 2026-06 | https://socialk.it/en/sizes/x-video-size |

### Demo-video craft

| Key | Source | Date | URL |
|---|---|---|---|
| S120 | Refs, 1,952 measured launch films (vendor) | 2026-10 | https://refs.video/ |
| S121 | Cutmap, 1,333 launch films (vendor) | accessed 2026-10-22 | https://cutmap.co/kind/launch |
| S122 | Refs, Cursor 2.0 film (film posted 2025-10-29) | observed 2026-10-10 | https://refs.video/v/yt-An8IM-kPyms |
| S123 | Refs, Raycast teaser (X post 2025-12-18; dated follow-up video 2026-02-26) | 2025-12-18 | https://refs.video/v/2001658927302267296 |
| S125 | Cutmap, Granola Briefs film (feature launched 2026-05-20) | 2026-05-20 | https://cutmap.co/v/granola-briefs |
| S126 | Mirror of Granola's launch post on X | 2024-05-22 | https://www.24vids.com/video/writing-is-thinkingif-a-bot-is-writing-notes-for-you-its-thinking-for-you-p-tw-1793298597456253314 |
| S127 | GetXAnalytics, Mac productivity launches on X | read 2026-10-22 | https://getxanalytics.com/category/mac-productivity/launches |
| S128 | Showtime, typography for video | undated | https://faviovazquez.github.io/showtime/docs/typography.html |
| S129 | Sutrahaus, caption legibility floors | 2026-09-01 | https://sutrahaus.com/blog/caption-legibility-floors/ |
| S130 | Screenify, auto-zoom in screen recordings (vendor) | 2026-04-10 | https://www.screenify.studio/blog/2026-04-10-auto-zoom-screen-recording |
| S131 | Refs, delivery plate for an X launch film (loudness, type size) | 2026-10-10 | https://refs.video/v/2107474804496351557 |
| S132 | Blitzcut, captions on X video (vendor) | 2026-08-28 | https://blitzcutai.com/blog/how-to-add-captions-x-twitter-video |
| S133 | Superwhisper company page on LinkedIn, Meetings launch | about 2026-10-15 | https://www.linkedin.com/posts/superwhisper_introducing-superwhisper-meetings-the-first-activity-7516523888751718400-v1mO |
| S141 | Clickstrike, product launch video guide (vendor) | 2026-07-16 | https://clickstrike.com/blog/product-launch-video-guide/ |

### LocalXiv repository

| Key | Source | Date | Location |
|---|---|---|---|
| S134 | Direct import accepts only arxiv.org and alphaxiv.org links | main `5f6e20b` | [`papers/acquire.py`](../papers/acquire.py), lines 22–26 |
| S135 | Anthropic SDK pinned to `https://api.anthropic.com`; other providers get a direct `urllib` POST to the configured endpoint | main `5f6e20b` | [`papers/ai.py`](../papers/ai.py), lines 176 and 240 |
| S136 | v0.1.0 release notes: no VoiceOver pass (line 30); older Pandoc and EPUBCheck versions than the corpus (line 34); Chat sends Highlights and Notes to the provider (line 38); ad hoc signed, not notarized (line 44) | main `5f6e20b` | [`docs/releases/v0.1.0.md`](releases/v0.1.0.md) |
| S137 | Competitive brief: alphaXiv (corpus: 61 of 100 from TeX, 22 from arXiv HTML, 17 PDF only; no analytics library; the hosts that the app contacts; arXiv HTML and ar5iv as direct competitors; HN post with 1 point) | 2026-10-17 | [`docs/competitive-brief-alphaxiv-2026-10-17.md`](competitive-brief-alphaxiv-2026-10-17.md) |
| S138 | Capture-map lane: code reading of `app/static`, `app/server.py`, `papers/chat.py`, `papers/ai.py`, `tools/intro-video/capture.mjs`. No skeptic pass. | 2026-10-22 | research lane output |

### Critic pass (2026-10-22)

The same rows as Section 10.6.

| Key | Source | Date | URL or location |
|---|---|---|---|
| S142 | Ginev and others, "Scaling Accessible Mathematics on arXiv: HTML Conversion and MathML 4" (arXiv) | 2026-05-15 | https://arxiv.org/html/2605.16562 |
| S143 | Niels Rogge, Hugging Face blog, "Relaunching PapersWithCode with new features" | 2026-05-24 | https://huggingface.co/blog/nielsr/paperswithcode-launch |
| S144 | Niels Rogge, LinkedIn: non-arXiv PDFs on Papers with Code; GLM-5.3 Flash in chat | 2026-08-28 | https://www.linkedin.com/feed/update/urn:li:activity:7499033216134148096 |
| S145 | ZenML LLMOps Database, summary of the Hugging Face OCR run (third-party) | undated, read 2026-10-22 | https://www.zenml.io/llmops-database/large-scale-ocr-processing-of-academic-papers-using-ai-coding-agents-and-serverless-gpu-infrastructure |
| S146 | Google blog, "NotebookLM is now Gemini Notebook" | 2026-07-16 | https://blog.google/innovation-and-ai/products/gemini-notebook/notebooklm-gemini-notebook/ |
| S147 | Zotero blog, Zotero 10, and the 10.0 changelog | 2026-08-17 | https://www.zotero.org/blog/zotero-10/ ; https://www.zotero.org/support/10.0_changelog |
| S148 | Zoro repository | created 2026-03-18 | https://github.com/ruihanglix/zoro |
| S149 | Freddie repository | created 2026-04-10 | https://github.com/SYYANI/Freddie |
| S150 | Episteme repository | created 2026-05-01 | https://github.com/caopulan/episteme |
| S151 | PaperMaster repository | created 2026-03-08 | https://github.com/Henry839/PaperMaster |
| S152 | Sift repository | created 2026-05-15 | https://github.com/abhiramm7/sift |
| S153 | PaperShelf repository | created 2026-02-08; last release 2026-03-04 | https://github.com/dakl/papershelf |
| S154 | Embark Reader home page (company) | undated, read 2026-10-22 | https://embarkreader.com/ |
| S155 | arXiv PDF of 1706.03762v7, permission line on page 1 | 2023-08-02 | https://export.arxiv.org/pdf/1706.03762v7.pdf |
| S156 | timeanddate, Election Day 2026 | read 2026-10-22 | https://www.timeanddate.com/holidays/us/election-day |
| S157 | CVPR 2027 dates and deadlines | read 2026-10-22 | https://cvpr.thecvf.com/Conferences/2027/Dates |
| S158 | Analytics Insight, Apple "Pro and Tell" event on 2026-10-28 | 2026-10-20 | https://www.analyticsinsight.net/news/apples-pro-and-tell-teaser-has-mac-fans-watching-october-28 |
| S159 | Product Hunt Help, "Can I relaunch my product?" | 2026-07-07 | https://help.producthunt.com/en/articles/484934-can-i-relaunch-my-product |
| S160 | Hacker News, Show HN guidelines and FAQ | undated, read 2026-10-22 | https://news.ycombinator.com/showhn.html ; https://news.ycombinator.com/newsfaq.html |
| S161 | Akhil Theerthala, LocalXiv project page (owner's site) | undated, read 2026-10-22 | https://akhiltheerthala.com/artifacts/localxiv/ |
| S162 | PostInstantly, X limits 2026 (reads X Help) | 2026-10-13 | https://postinstantly.com/limits/x-limits |
| S163 | karpathy/reader3 repository | created 2025-11-18 | https://github.com/karpathy/reader3 |
| S164 | AppBrain, alphaXiv for Android (third-party data) | data 2026-10-17 | https://www.appbrain.com/app/alphaxiv/org.alphaxiv.mobileapp |
| S165 | LinkedIn Help, auto captions; muted autoplay | read 2026-10-22 | https://www.linkedin.com/help/linkedin/answer/a1327025 ; https://www.linkedin.com/help/linkedin/answer/a565326 |
| S166 | `README.md`: lead line "On your Mac or Kindle"; feature list with no Highlights, Notes, or Chat; the `localxiv://` bookmarklet | main `5f6e20b` | [`README.md`](../README.md), lines 7–29 |
| S167 | `tools/intro-video/README.md` (44 s, 60 fps, music from `music.mjs` with no samples); `src/timeline.mjs` (120 BPM) | main `5f6e20b` | [`tools/intro-video/`](../tools/intro-video/) |
| S168 | Chat makes one streamed provider request with no tool definitions; Add Quote hides after 4 added quotes | main `5f6e20b` | [`papers/chat.py`](../papers/chat.py); [`papers/ai.py`](../papers/ai.py); [`app/static/chat.js`](../app/static/chat.js), line 134; [`app/static/margin.js`](../app/static/margin.js), line 433 |
| S169 | GitHub API: 2 stars, 0 forks, description "Your library, managed locally."; v0.1.0 published 2026-10-22T10:07:12Z; v0.1.0 DMG downloaded 2 times | 2026-10-22 | `gh api repos/Akhil-Theerthala/LocalXiv` |
| S170 | Repository search: no Linux code, build, or issue; "linux" appears only in the brief | main `5f6e20b` | `grep -ri linux` |
| S171 | Hugging Face skills, `huggingface-papers` SKILL.md (reading paper pages and `.md`; no login for public pages) | undated, read 2026-10-22 | https://github.com/huggingface/skills/blob/main/skills/huggingface-papers/SKILL.md |

## 10. Critic notes (applied to Sections 1-9 on 2026-10-22)

The corrections in this section are applied to Sections 1–9 on 2026-10-22. This section stays as a record of the critic pass.

Date: 2026-10-22. Method: one completeness pass on Sections 1–9; 21 Exa searches and 3 Exa fetches; checks in the repository at `5f6e20b` and with the GitHub API. New keys start at S142 (Section 10.6). "Closed" means that a new source settles an item. "Inference" means that no source states it.

### 10.1 Errors to correct before use

Highest impact first.

1. **The launch day in Section 6.2 is US Election Day.** Tuesday 2026-11-03 is the US general election [S156]. Inference: US news fills the feeds on that day and the day after. Two more dates affect the window: Apple's Mac event on 2026-10-28 [S158], and the CVPR 2027 deadlines, registration on 2026-11-10 and submission on 2026-11-16, Anywhere on Earth [S157]. Many ML readers are busy in the week before a CVPR deadline. Inference: Thursday 2026-11-05, or Tuesday 2026-11-17 to Wednesday 2026-11-18.
2. **The market map leaves out arXiv's own HTML view.** It is free, and it is the largest reflowed reader of arXiv papers. About 97% of new submissions produce some HTML, and about 75% convert with no LaTeXML errors. A March 2026 change lets readers make the page chrome smaller [S142, 2026-05-15]. The brief of 2026-10-17 listed arXiv HTML and ar5iv as direct competitors [S137]; this report removed them. The hook H1, "Same paper. Your page.", invites the reply "arXiv already has HTML". Prepare an answer (Section 10.5).
3. **"Rebuilt from the TeX source" is true for 61 of 100 corpus papers, not 83.** In the v0.0.19 corpus, 61 papers convert from TeX, 22 from arXiv HTML, and 17 stay PDF [S137]. Section 2, Section 4.5, and the prepared Zotero reply in Section 4.6 must change (Section 10.3, item 2).
4. **Hugging Face chat was not on every paper from 2026-01-07.** At launch the chat used the arXiv HTML of a paper. About 27,000 indexed papers had no HTML, and they got chat only after an OCR run [S9, 2026-04-07]. A third-party summary says that the OCR read at most 30 pages of each paper [S145]. Under the same blog post, one user reported poor chat answers after the OCR change (comment of 2026-04-14) [S9].
5. **The competitor set misses seven Mac or desktop paper readers.** Each one was found on 2026-10-22:
   - Zoro: AGPL; macOS, Windows, and Linux; local-first; translates arXiv HTML; an in-app AI assistant with tool calls; an MCP server; 37 stars; created 2026-03-18 [S148].
   - Freddie: macOS; reads arXiv HTML first, then ar5iv; OpenAI-compatible providers; MIT; 20 stars; created 2026-04-10 [S149].
   - Episteme: macOS; local-first, no account; select text in the PDF and ask; citations tied to page regions; uses the Codex CLI; created 2026-05-01 [S150].
   - PaperMaster: macOS; highlights, margin notes, Ask AI on a selection, own OpenAI-compatible key; 15 stars; created 2026-03-08 [S151].
   - Sift: macOS; ad hoc signed; highlights and a chat grounded in the paper; no account; created 2026-05-15 [S152].
   - PaperShelf: macOS; signed and notarized; arXiv search, highlights, MCP; last release 2026-03-04 [S153].
   - Embark Reader: native Mac and iOS arXiv reader with offline PDFs (company page, undated) [S154].

   Effect: "Own key with no account is rare" (Section 2) is wrong; it is common among small open-source Mac apps. The combination claim in Section 1 still holds for the products found. None of them puts Question cards in the margin of a reflowed page and also exports Notes in an EPUB. But PaperMaster has highlights, margin notes, select-and-ask, an own key, and no account. So say "no product we found", and never "only".
6. **paperswithcode.co changed after 2026-08-20.** It accepts non-arXiv PDFs since 2026-08-28. Its chat offers GLM-5.3 Flash, and "@" compares papers (company claims) [S144; S6]. Niels Rogge wrote on 2026-05-24 that the site launched one week earlier, so about 2026-05-17, not 2026-05-18 [S143].
7. **"X stopped selling X Premium (Basic included) to new buyers on 2026-10-12" is not in the xAI text that this pass read.** That text says that The X Subscription is open to new customers and that existing subscribers keep their plans [S84]. Mark the Basic claim *unconfirmed*.
8. **The release date.** The header says 2026-10-21. The tag is from 2026-10-21, but GitHub published the v0.1.0 release on 2026-10-22 at 10:07 UTC [S169].
9. **Minor.**
   - "Up to 4 quotes in one question": the code hides Add Quote after 4 added quotes, so with the card's own selection a question can carry 5 [S168]. In copy, say "several quotes".
   - Zotero 10: the Zotero text names images, tables, and figures as areas shown as in the PDF. It does not name maths [S147]. Mark "some maths" as inference, or remove it.
   - alphaXiv's Android app is on Google Play since September 2026 (version 1.5.0 on 2026-09-28; about 2.1K installs, third-party data) [S164]. The brief's date of 2026-10-06 is the Paperscrolling launch.

### 10.2 Status of the unconfirmed items

| Item | Status after this pass | Source |
|---|---|---|
| Gemini Notebook was NotebookLM | **Closed.** Google renamed it on 2026-07-16. Replace the third-party source. | [S146] |
| Hugging Face chat: login, price, passage citations | **Open.** The Hugging Face agent skill says that public paper pages need no login [S171]; that line covers reading the page and its `.md` file, not the chat. Owner test, about 1 minute: open `huggingface.co/papers/<id>` while logged out, ask one question, and look for passage links. | [S9; S171] |
| paperswithcode.co: sign-in, passage citations | **Partly closed.** The chat page shows "Sign in" (undated crawl). Passage citations: still *unconfirmed*. | [S6; S144] |
| Video limits of X Plus | **Narrowed.** A third-party reading of X Help (2026-10-13) says that the Plus, Premium, Super, and Ultra plans include longer videos and editing. 1080p on Plus: still *unconfirmed*. | [S162] |
| Peters and Chin-Yee | **Confirmed.** 4,900 summaries, 10 models, odds ratio 4.85. The abstract states the five-times comparison in general words; the body limits it to three models against NEJM Journal Watch. The wording in Section 3.1 stands. Do not quote the abstract sentence alone. | [S60] |
| Karpathy's reader3 | **Confirmed.** The repository was created on 2025-11-18 and describes reading books together with LLMs. | [S163] |
| alphaXiv prices | **Confirmed** as read on 2026-10-05. alphaXiv has no public pricing page. | [S26] |
| alphaXiv's launch hint for the week of 2026-10-26 | **Unchanged.** Seen only on a mirror. | [S24] |
| Tagline A is free to use | **No collision found** in one exact-phrase search. This is not proof. | — |
| Section 7, the capture map | **Still no skeptic pass and no native run.** Two items checked here: Chat sends one streamed request with passages and has no tool calls [S168]; the beat grid is 120 BPM [S167]. | [S167; S168] |
| "It fits the owner's 60–90 s brief" (Section 5.1) | **No source.** The owner's request names no length. The current film is 44 s [S167]. Treat 60–90 s as a recommendation. | [S167] |

### 10.3 Over-claims against the honesty limits

1. **"AI agent."** The owner's request says "chat with an AI agent in-app". LocalXiv Chat sends one streamed request with the selection, the passages, and the Notes. It has no tool calls [S168]. Hugging Face chat runs on an MCP server, Zoro's assistant calls tools, and paperswithcode.co calls its chat an agent [S7; S148; S6]. Do not call LocalXiv Chat an agent in the film or the posts. Use "Ask" and "Chat".
2. **"Rebuilt from the authors' TeX source."** Say "reflowed from the paper's LaTeX source or arXiv's HTML". Change the Zotero reply to: "LocalXiv builds the page from the paper's LaTeX source, or from arXiv's HTML, so equations are typeset."
3. **"83 of 100 test papers."** It is a corpus number, and the app bundles older Pandoc and EPUBCheck versions than the corpus [S136]. Say "83 of 100 papers in our test corpus".
4. **"Find papers anywhere. Read them in LocalXiv."** Direct import accepts only arxiv.org and alphaxiv.org links, and Paper search finds arXiv papers [S134]. Hugging Face links fail today. Until import accepts more hosts, say "Found it on arXiv or alphaXiv? Read it in LocalXiv."
5. **"Every answer shows its source"** (Pillar 3 promise). The model decides whether to cite, and a small local model may cite badly (Section 7.3). Say "Citations open the passage."
6. **"No account."** True for LocalXiv. A cloud provider still needs its own account and key. Say "No LocalXiv account", or show the model on the Mac.
7. **"Coming soon to Linux."** The repository has no Linux code, build, or issue [S170], and the shell is AppKit. Zoro already ships on Linux with AGPL, arXiv HTML, and an AI assistant [S148], and Zotero 10 Reading Mode runs on Linux [S147; S42]. Recommendation: on the end card, say "Linux: planned" or keep "Coming soon to Linux" only if work starts before launch. In the post, link a GitHub issue where people can add a vote.
8. **Rights of the sample paper.** The first page of the 1706.03762v7 PDF lets others reproduce its tables and figures, with attribution, "solely for use in journalistic or scholarly works" [S155]. A launch film is promotion. The hook H1 and the Reference preview shots in Section 5.4 show its figures and tables. Choose a paper with a CC BY licence on its arXiv page, or show only its text. The app also includes this paper as its sample; the owner may want to check that use too. This is a risk to check, not legal advice.
9. **Capture surface.** A Chromium capture shows the web shell, not the WebKit and AppKit app that people download (Section 7.2, item 4). Crop to the page, and show no window chrome that the Mac app does not have.
10. **"No analytics."** Keep the words of Section 4.3. Never write "nothing leaves your Mac". The app contacts arXiv, Semantic Scholar, doi.org, the update feed, and the chosen provider [S137].

### 10.4 Questions for the owner that the report leaves open

1. Which Paper goes in the film? It needs a licence that permits the use (10.3, item 8), a clean conversion from LaTeX, visible equations, and a passage that suits Ask.
2. Which model writes the answer in the hero shot: a model on the Mac (Option A), or a cloud model in a native run with the owner's key (Option C)? Test the model on the chosen passage first.
3. Extend the current Remotion project or start a new one? It has music made in code with no samples, so it needs no licence, and a 120 BPM grid; its scenes lead with Kindle [S167]. Section 5.7 can say that the music rights are already solved. `capture.mjs` is stale (Section 7.2).
4. Which word for Chat (10.3, item 1)?
5. The README, the repository description ("Your library, managed locally."), and the owner's project page lead with Kindle or the library. The README feature list names no Highlights, Notes, or Chat [S166; S169; S161]. The film's only action is the GitHub URL. Change these before launch? This is a fourth item for "Do three things before launch" in Section 1.
6. Notarize before launch? The v0.1.0 DMG has 2 downloads [S169]. If not, put the steps to open an app that macOS blocks (`docs/macos-release.md`) in the first X reply and in the first Hacker News comment.
7. Relaunch on Product Hunt? The owner's page says that LocalXiv launched there in September 2026 [S161]. Product Hunt asks for two months between posts and a significant update; before two months, a relaunch request is necessary [S159]. Find the date of the first launch.
8. How to frame Show HN? A new version is usually not enough for Show HN; a major overhaul probably is. A repost is acceptable when the earlier post got little attention; the earlier LocalXiv post got 1 point. Hacker News asks for text that a person writes and forbids requests for votes [S160].
9. Say that AI helped build LocalXiv? The owner's page says that the owner built it mostly with GPT-6 Astra in Codex [S161]. Hacker News readers, and the LinkedIn penalty on text that sounds like AI [S117], make this a real choice.
10. What does "coming soon to Linux" mean, and where are votes counted (10.3, item 7)?
11. Show the bookmarklet? The README has a `localxiv://` bookmarklet that adds the arXiv or alphaXiv page in one click [S166]. A 2–3 s beat can link the discovery sites to LocalXiv. The browser's permission prompt shows on screen.
12. Which launch date (10.1, item 1)?
13. On LinkedIn, turn off auto captions for a film with no voice [S165].

### 10.5 What to add to the report

- **Section 2:** a row for arXiv HTML [S142], and a line for the seven readers in 10.1, item 5.
- **Section 4.6, a prepared reply:** "arXiv has HTML now." Answer: "Yes, and LocalXiv uses it for some papers. LocalXiv adds your reading settings, a library on your Mac, Highlights and Notes in the margin, Ask, and EPUB export."
- **Section 6.2, a dates table:** 2026-10-28 Apple event [S158]; week of 2026-10-26 alphaXiv hint [S24]; 2026-11-03 US election [S156]; 2026-11-10 and 2026-11-16 CVPR deadlines [S157].
- **Section 6.5:** Product Hunt rules [S159] and Show HN rules [S160].

### 10.6 New sources

| Key | Source | Date | URL or location |
|---|---|---|---|
| S142 | Ginev and others, "Scaling Accessible Mathematics on arXiv: HTML Conversion and MathML 4" (arXiv) | 2026-05-15 | https://arxiv.org/html/2605.16562 |
| S143 | Niels Rogge, Hugging Face blog, "Relaunching PapersWithCode with new features" | 2026-05-24 | https://huggingface.co/blog/nielsr/paperswithcode-launch |
| S144 | Niels Rogge, LinkedIn: non-arXiv PDFs on Papers with Code; GLM-5.3 Flash in chat | 2026-08-28 | https://www.linkedin.com/feed/update/urn:li:activity:7499033216134148096 |
| S145 | ZenML LLMOps Database, summary of the Hugging Face OCR run (third-party) | undated, read 2026-10-22 | https://www.zenml.io/llmops-database/large-scale-ocr-processing-of-academic-papers-using-ai-coding-agents-and-serverless-gpu-infrastructure |
| S146 | Google blog, "NotebookLM is now Gemini Notebook" | 2026-07-16 | https://blog.google/innovation-and-ai/products/gemini-notebook/notebooklm-gemini-notebook/ |
| S147 | Zotero blog, Zotero 10, and the 10.0 changelog | 2026-08-17 | https://www.zotero.org/blog/zotero-10/ ; https://www.zotero.org/support/10.0_changelog |
| S148 | Zoro repository | created 2026-03-18 | https://github.com/ruihanglix/zoro |
| S149 | Freddie repository | created 2026-04-10 | https://github.com/SYYANI/Freddie |
| S150 | Episteme repository | created 2026-05-01 | https://github.com/caopulan/episteme |
| S151 | PaperMaster repository | created 2026-03-08 | https://github.com/Henry839/PaperMaster |
| S152 | Sift repository | created 2026-05-15 | https://github.com/abhiramm7/sift |
| S153 | PaperShelf repository | created 2026-02-08; last release 2026-03-04 | https://github.com/dakl/papershelf |
| S154 | Embark Reader home page (company) | undated, read 2026-10-22 | https://embarkreader.com/ |
| S155 | arXiv PDF of 1706.03762v7, permission line on page 1 | 2023-08-02 | https://export.arxiv.org/pdf/1706.03762v7.pdf |
| S156 | timeanddate, Election Day 2026 | read 2026-10-22 | https://www.timeanddate.com/holidays/us/election-day |
| S157 | CVPR 2027 dates and deadlines | read 2026-10-22 | https://cvpr.thecvf.com/Conferences/2027/Dates |
| S158 | Analytics Insight, Apple "Pro and Tell" event on 2026-10-28 | 2026-10-20 | https://www.analyticsinsight.net/news/apples-pro-and-tell-teaser-has-mac-fans-watching-october-28 |
| S159 | Product Hunt Help, "Can I relaunch my product?" | 2026-07-07 | https://help.producthunt.com/en/articles/484934-can-i-relaunch-my-product |
| S160 | Hacker News, Show HN guidelines and FAQ | undated, read 2026-10-22 | https://news.ycombinator.com/showhn.html ; https://news.ycombinator.com/newsfaq.html |
| S161 | Akhil Theerthala, LocalXiv project page (owner's site) | undated, read 2026-10-22 | https://akhiltheerthala.com/artifacts/localxiv/ |
| S162 | PostInstantly, X limits 2026 (reads X Help) | 2026-10-13 | https://postinstantly.com/limits/x-limits |
| S163 | karpathy/reader3 repository | created 2025-11-18 | https://github.com/karpathy/reader3 |
| S164 | AppBrain, alphaXiv for Android (third-party data) | data 2026-10-17 | https://www.appbrain.com/app/alphaxiv/org.alphaxiv.mobileapp |
| S165 | LinkedIn Help, auto captions; muted autoplay | read 2026-10-22 | https://www.linkedin.com/help/linkedin/answer/a1327025 ; https://www.linkedin.com/help/linkedin/answer/a565326 |
| S166 | `README.md`: lead line "On your Mac or Kindle"; feature list with no Highlights, Notes, or Chat; the `localxiv://` bookmarklet | main `5f6e20b` | [`README.md`](../README.md), lines 7–29 |
| S167 | `tools/intro-video/README.md` (44 s, 60 fps, music from `music.mjs` with no samples); `src/timeline.mjs` (120 BPM) | main `5f6e20b` | [`tools/intro-video/`](../tools/intro-video/) |
| S168 | Chat makes one streamed provider request with no tool definitions; Add Quote hides after 4 added quotes | main `5f6e20b` | [`papers/chat.py`](../papers/chat.py); [`papers/ai.py`](../papers/ai.py); [`app/static/chat.js`](../app/static/chat.js), line 134; [`app/static/margin.js`](../app/static/margin.js), line 433 |
| S169 | GitHub API: 2 stars, 0 forks, description "Your library, managed locally."; v0.1.0 published 2026-10-22T10:07:12Z; v0.1.0 DMG downloaded 2 times | 2026-10-22 | `gh api repos/Akhil-Theerthala/LocalXiv` |
| S170 | Repository search: no Linux code, build, or issue; "linux" appears only in the brief | main `5f6e20b` | `grep -ri linux` |
| S171 | Hugging Face skills, `huggingface-papers` SKILL.md (reading paper pages and `.md`; no login for public pages) | undated, read 2026-10-22 | https://github.com/huggingface/skills/blob/main/skills/huggingface-papers/SKILL.md |
