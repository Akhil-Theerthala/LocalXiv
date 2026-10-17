# Competitive brief: alphaXiv

Date: 2026-10-17. Main at `136ffd5`, release v0.0.19.

Scope: a full product comparison of alphaXiv and LocalXiv. The brief informs feature priority: what LocalXiv must build, make equal, or not build.

Shelf life: alphaXiv shipped about 60 dated launches from January 2025 to October 2026. Prices, model lists, and mobile features change monthly. Check sections 4 and 9 again before you use them after 2026-12.

Method: three research passes on 2026-10-17 read alphaxiv.org, its public web-client code, its store listings, its public bug tracker ([alphaXiv/feedback](https://github.com/alphaXiv/feedback), 423 issues), press, Hacker News, and Reddit. LocalXiv facts come from this repository. "alphaXiv says" marks a number that only alphaXiv gives.

## 1. Summary

- **alphaXiv is an adjacent competitor, not a direct one.** It wins on finding papers, community, and instant AI on every paper. It has a network, funding, and distribution that LocalXiv cannot equal.
- **alphaXiv is weak where LocalXiv is strong.** Its reader shows only the PDF. It has no EPUB, no Kindle export, no offline reading, and no option to use your own model key. Its users ask for each of these.
- **The strongest opening is your own key.** Bring-your-own-key is the most repeated request in alphaXiv's tracker, and alphaXiv said "probably not". Two users built their own alphaXiv-like readers for this reason. LocalXiv already uses the reader's own key, but it has no chat with the Paper.
- **Conversion is the moat, and it has a time limit.** alphaXiv tried an HTML view in 2024 and went back to PDF. Phone users now ask for reflowed text. alphaXiv has the money to try again.
- **The Blog has the weakest edge.** alphaXiv gives a free, instant, page-cited Overview for every paper. Section 9.4 gives the evidence for a decision.
- **LocalXiv has almost no users.** Every recommendation below assumes that distribution is the first constraint.

## 2. LocalXiv today

| Item | State on 2026-10-17 |
| --- | --- |
| Users | 2 GitHub stars, 0 forks, 0 issues. About 2 DMG downloads for each release. One Hacker News post (2026-09-06), 1 point. |
| Platform | macOS 26 or newer, Apple Silicon only. Ad hoc signed, not notarized. |
| Conversion | In the 100-paper corpus, 61 papers convert from TeX, 22 from arXiv HTML, and 17 end with the original PDF only ([v0.0.19 notes](releases/v0.0.19.md)). [The parser audit](parser-audit-2026-10-15.md) lists open defects, for example a lost table in 2603.22797v1 and no EPUB for 2409.02094v1, cause not found. |
| AI | Optional, on the reader's own key. Generation can take several minutes or fail. Offline tests use scripted responses, so live reliability is not measured. |
| Not present | Highlights, notes, chat with the Paper, Collections and Tags (the glossary defines them, but the library has no table for them), a library citation export, a URL scheme, a phone app. |
| Privacy | No account. The library and Keychain keys stay on the Mac. The code has no analytics library. It contacts arXiv, Semantic Scholar, doi.org, the update feed, and the reader's AI provider. |

## 3. alphaXiv overview

**Company.** alphaXiv started in May 2023 as a Stanford class project by Rehaan Ahmad (CEO) and Raj Palleti. alphaXiv Inc. was founded in 2024 in San Francisco, with co-founders Daniel Kim and Lino Le Van (CTO) ([PR Newswire, 2025-11-19](https://www.prnewswire.com/news-releases/alphaxiv-raises-7m-seed-round-to-bridge-the-ai-research-to-practice-divide-302619615.html)).

**Funding.** $7M seed on 2025-11-19, co-led by Menlo Ventures and Haystack, with Shakti, Conviction Embed, Upfront, and angels that include Eric Schmidt and Sebastian Thrun (same source). No later round was found.

**Team and hiring.** "Our team is small". Third-party head counts go from 8 to 31. Open roles: ML Researcher, LLM Inference Engineer, Mobile Developer, Web Engineer, Designer ([about](https://www.alphaxiv.org/about)). There are no sales or enterprise roles. The roles point to own models, cheaper inference, and mobile.

**Traction.** alphaXiv says it had 500,000 monthly visitors in May 2025 ([AIM, 2025-05-31](https://analyticsindiamag.com/ai-features/arxiv-is-great-but-what-if-you-deserve-better)), and "millions of users" in total by November 2025. Chrome extension: 60,000 users. iOS: 17 ratings, 4.7. Android: 1,000+ downloads.

**Distribution.** Every arxiv.org abstract page has an alphaXiv toggle through arXivLabs ([arXiv page](https://arxiv.org/abs/1706.03762)). A reader can also change "arxiv" to "alphaxiv" in any paper URL. Users repeat this tip often. No other competitor found has this access.

**Positioning over time.**

| Year | Claim | Source |
| --- | --- | --- |
| 2024 | "Stack Overflow for papers", for students and researchers | [IEEE Spectrum, 2025-03-25](https://spectrum.ieee.org/alphaxiv) |
| 2025 | "GitHub of AI research", for applied AI teams, "research to production" | [SiliconANGLE, 2025-11-19](https://siliconangle.com/2025/11/19/alphaxiv-raises-7m-funding-become-github-ai-research/) |
| 2026 | "Follow the latest research", plus research agents (autoarxiv, OpenResearch, MCP) | [alphaxiv.org](https://www.alphaxiv.org/) |

The founders said that the paper as an artifact will be "less and less useful" in 5 to 10 years ([Latent Space, 2025-12-31](https://www.youtube.com/watch?v=T0mZJjl_dsA)). Their direction goes away from the reading of papers.

**Recent moves.** iOS app (2026-07-08) and Android app (2026-10-06). Paid plans (2026-06). OpenResearch, a signed desktop app for macOS, Windows, and Linux that turns coding agents into research agents (2026-07-21, [GitHub](https://github.com/alphaXiv/OpenResearch), 7,300 stars). Claude Opus 5.5 writes the Overviews, alphaXiv says ([X, 2026-09-22](https://x.com/askalphaxiv/status/2102464761141346483)).

## 4. Feature comparison

Scale: **Strong** (leads), **Adequate** (works, no edge), **Weak** (exists with large gaps), **Absent**.

| Reader job and capability | alphaXiv | LocalXiv | Evidence |
| --- | --- | --- | --- |
| **Find a paper** | | | |
| Trending and personal feeds | Strong | Absent | Hot, For You, and custom feeds; follow researchers. Users praise this most (about 14 people). |
| Search by title, author, or topic | Strong | Adequate | alphaXiv: keyword, embedding, and social ranking. LocalXiv: Paper search through Semantic Scholar, then arXiv. |
| Open a paper from arxiv.org | Strong | Weak | alphaXiv: arXivLabs toggle, URL swap, extension. LocalXiv: paste a link or ID only. |
| Papers outside arXiv | Adequate | Absent | alphaXiv: private upload, extension on any PDF. |
| **Read it comfortably** | | | |
| Reading preferences on reflowed text | Absent | Strong | alphaXiv shows the PDF with a theme only ([paper page](https://www.alphaxiv.org/abs/1706.03762)). LocalXiv: font, size, margins, spacing, three themes. |
| Share of papers that reflow | Absent | Adequate | alphaXiv reflows no paper. LocalXiv: 83 of 100 corpus papers reflow; the other 17 open as the original PDF. |
| Reference previews and Back | Adequate | Strong | alphaXiv added citation hover on 2026-09-15; users still report no way back after a citation ([#51](https://github.com/alphaXiv/feedback/issues/51), [#416](https://github.com/alphaXiv/feedback/issues/416)). LocalXiv: citation, figure, table, equation, and section previews; Back returns to the paragraph. |
| Highlights and notes | Strong | Absent | alphaXiv: PDF-anchored, synced, download with annotations. |
| Phone and tablet | Adequate | Absent | alphaXiv apps show the PDF; a user says the text is too small on a phone ([#8](https://github.com/alphaXiv/feedback/issues/8)). |
| **Understand it** | | | |
| Explanation of one paper | Strong | Adequate | alphaXiv: Overview for every paper, free, instant, page-cited, translated, with audio. LocalXiv: Blog with passage citations, length, tone, and language; costs the reader's key; takes minutes; can fail. |
| Visual explanation | Weak | Adequate | alphaXiv: in the Overview we inspected, only the paper's own figures. It also makes one-off pieces (Illustrated NeurIPS, a 3D Transformer), and its iOS listing says "AI Visual Blogs", which we did not inspect. LocalXiv: the Overview is a Figure render drawn from a Scene; no other product found draws one per paper. Live reliability is not proven. |
| Chat with the paper (select text, ask) | Strong | Absent | The second most praised alphaXiv feature (about 8 people). |
| Questions across papers | Strong | Absent | Homepage assistant, literature review, MCP server with 21 tools. |
| Model choice | Adequate | Strong | alphaXiv: presets; any model on the $20 plan; no own key. LocalXiv: five provider presets and a Custom endpoint. |
| **Keep and cite** | | | |
| Organize a library | Strong | Weak | alphaXiv: folders, shared folders, history, likes. LocalXiv: Library search and Reading state; no Collections or Tags. |
| Citation export | Weak | Weak | Both: BibTeX for one paper. alphaXiv promised Zotero on 2025-06-25; [#86](https://github.com/alphaXiv/feedback/issues/86) and [#267](https://github.com/alphaXiv/feedback/issues/267) are still open. |
| **Take it elsewhere** | | | |
| EPUB and Kindle | Absent | Strong | LocalXiv: Paper export of the Paper or an explanation; Send to Kindle through Apple Mail. Actual Kindle delivery is not in the automated checks. |
| Offline reading | Absent | Strong | alphaXiv caches PDFs in the browser for speed only. |
| Text export | Adequate | Absent | alphaXiv: Markdown at `/abs/<id>.md` and `/overview/<id>.md`. |
| **Community** | | | |
| Comments and author replies | Adequate | Absent | Strong on LLM papers; most other papers have no comments ([HN, 2026-05-11](https://news.ycombinator.com/item?id=48098462)). |
| **Trust and data** | | | |
| Account | Adequate | Strong | alphaXiv: reading needs no account; chat, notes, and bookmarks do. LocalXiv: no account. |
| Where data goes | Weak | Strong | alphaXiv: its cloud; its policy names 13 AI providers; PostHog analytics ([privacy](https://www.alphaxiv.org/privacy)). LocalXiv: local; content goes only to the reader's provider. |
| Model and date on each explanation | Weak | Strong | An author asked alphaXiv to say which model wrote the Overview of their paper ([#392](https://github.com/alphaXiv/feedback/issues/392), 2026-09-07). On 2026-09-22 alphaXiv named one model for all Overviews, but not for each paper. |
| **Platform and cost** | | | |
| Platforms | Strong | Weak | alphaXiv: web, Chrome, Firefox, iOS, Android. LocalXiv: one Mac configuration, not notarized. |
| AI cost | Adequate | Adequate | alphaXiv: Free with strict limits, Go $8 ($5 for students, open models only), Pro $20, Extended $100 a month. LocalXiv: the app is free; the reader pays the provider for each request. |

Pricing source: alphaXiv's subscription code on 2026-10-17 (`/assets/subscription-*.js`; the file name changes with each deploy), confirmed by [ToolGPA on 2026-10-05](https://toolgpa.com/tools/alphaxiv/pricing). `alphaxiv.org/pricing` returns 404.

## 5. Competitive set for LocalXiv

| Level | Products | Why |
| --- | --- | --- |
| Direct (read a paper comfortably, on a Mac or an e-reader) | k2pdfopt, arXiv HTML and ar5iv, KOReader, Calibre, indie converters (Any2Ebook, PDFling, md2kindle), Readwise Reader | Users of e-readers name these. k2pdfopt is the most named, but its output is still a PDF ([r/Calibre, 2026-05-23](https://www.reddit.com/r/Calibre/comments/1tlu4y1/)). No source connects alphaXiv to e-readers. |
| Indirect (understand a paper) | alphaXiv, NotebookLM, Moonlight, ChatGPT, Claude, Gemini | The same job, from a web page or a chat. |
| Adjacent (could add reading) | alphaXiv, Hugging Face Papers, Zotero | alphaXiv has the users, the money, and a Mobile Developer opening. |
| Substitute | The PDF on an iPad, or print | Several users say: read papers on an iPad, not a Kindle. |

## 6. Positioning

**alphaXiv.** For AI researchers and applied AI teams who must keep up with a high volume of papers, alphaXiv is a research platform that connects papers, researchers, and organizations and grounds its AI answers in the work. Unlike Hugging Face Papers, it has comments on passages, author replies, and an assistant on every paper.

**LocalXiv.** The README says "Read arXiv papers comfortably. On your Mac or Kindle." In the same template: for readers who read a paper in depth, LocalXiv is a local reader that converts arXiv papers to reflowed text and EPUB, with optional explanations on the reader's own key. Unlike alphaXiv, it reflows the paper, works offline, exports to Kindle, and keeps data and keys on the Mac.

| Position | Status | Evidence |
| --- | --- | --- |
| "AI summary of any paper" | Crowded | alphaXiv, NotebookLM, Moonlight, general chat models. One PhD user left alphaXiv for frontier models ([r/PhdProductivity, 2026-07-04](https://www.reddit.com/r/PhdProductivity/comments/1ulxxi0/what_paid_research_aillm_are_you_using/ovi4l6l/)). |
| "Comfortable reading of the paper itself" | Unclaimed | alphaXiv went back to PDF after about 25% of papers rendered badly in HTML ([HN, 2024-09-08](https://news.ycombinator.com/item?id=41481783)). This is a render-quality measure, not the same as LocalXiv's 17% PDF-fallback rate. |
| "Your own model, no second subscription" | Unclaimed by a funded product | alphaXiv refused ([#232](https://github.com/alphaXiv/feedback/issues/232), [#317](https://github.com/alphaXiv/feedback/issues/317)). Indie tools only. |
| "Papers on e-ink" | Fragmented | Many single-purpose converters from 2025 and 2026; no clear winner. |
| alphaXiv's "grounded" claim | Vulnerable | Authors found wrong facts and figures in the Overviews of their own papers ([#388](https://github.com/alphaXiv/feedback/issues/388), [#389](https://github.com/alphaXiv/feedback/issues/389), [#392](https://github.com/alphaXiv/feedback/issues/392)). |
| "Local-first" | Contested | alphaXiv uses this word for OpenResearch. A Reddit post on 2026-10-14 found that an OpenResearch skill said "Do not mention the report to the user" ([commit 58eaa16](https://github.com/alphaXiv/OpenResearch/blob/58eaa168380b95f2cca36907d8f627ae27280dd5/agent-skills/orx-feedback/SKILL.md)). alphaXiv fixed it from 2026-10-14 to 2026-10-16. |

## 7. alphaXiv: strengths and weaknesses

**Strengths.**

- Distribution that no one else has: the arXivLabs toggle and the URL swap.
- Discovery: users praise the feeds most.
- AI on every paper at no cost to the reader: the Overview is ready before the reader arrives.
- Speed of delivery: about 60 dated launches in 22 months, and a team that replies to issues within hours.
- Funding and a technical team that trains models and runs inference.
- Every platform except desktop reading.

**Weaknesses.**

- A PDF-only reader. Users report inverted figures in dark mode, no table of contents, no way back after a citation, and 1.5 GB to 10 GB of memory for one paper ([#360](https://github.com/alphaXiv/feedback/issues/360)). About 68 of 423 issues are about the reader view.
- AI limits and billing. alphaXiv removed the strong models from the free tier on 2026-03-27 ([#244](https://github.com/alphaXiv/feedback/issues/244), 12 reactions). One Pro reply used a whole allowance ([#263](https://github.com/alphaXiv/feedback/issues/263)). Quotas have no published numbers.
- AI accuracy. Authors report errors, and the assistant read only some pages until May 2026 ([#168](https://github.com/alphaXiv/feedback/issues/168)).
- Accounts. Random logouts and failed sign-ins until June 2026 ([#249](https://github.com/alphaXiv/feedback/issues/249)).
- No export path. No EPUB, no Kindle, no Zotero, no library export.
- Narrow audience. Mathematicians and physicists say the site is not for them ([#81](https://github.com/alphaXiv/feedback/issues/81), [#396](https://github.com/alphaXiv/feedback/issues/396)).

## 8. Opportunities and threats

### Opportunities

1. **Your own key.** At least 7 alphaXiv issues ask for it. alphaXiv said no. Two users built their own readers to avoid a second subscription ([BetaXiv](https://www.reddit.com/r/learnmachinelearning/comments/1tyy9lq/), [Little Alpha](https://www.reddit.com/r/selfhosted/comments/1ulvzjo/new_project_megathread_week_of_02_jul_2026/ov8bamu/)). LocalXiv already uses the reader's key; it lacks the chat that these users want.
2. **Reflowed reading and e-ink.** Phone users ask alphaXiv for reflowed text ([#8](https://github.com/alphaXiv/feedback/issues/8), [#100](https://github.com/alphaXiv/feedback/issues/100)). E-reader users have many single-purpose converters and no established one. The most named tool, k2pdfopt, still gives a PDF.
3. **Citation export.** alphaXiv promised Zotero 16 months ago. Users still ask.
4. **Trust.** LocalXiv names the model and date on each explanation and links each Blog citation to its passage. It sends no analytics.
5. **Downstream of alphaXiv.** Direct import already accepts alphaXiv links. A reader can find a paper on alphaXiv and read it in LocalXiv.

### Threats

1. **alphaXiv adds a reflowed reader.** It has a Mobile Developer opening and user requests for it. Its 2024 attempt failed, but the team is now larger.
2. **alphaXiv allows an own key for students.** The team said it "may consider" this ([#317](https://github.com/alphaXiv/feedback/issues/317), 2026-06-29).
3. **alphaXiv adds EPUB or Kindle export.** `/overview/<id>.md` already exists, so an EPUB of the Overview is small work.
4. **alphaXiv ships desktop apps quickly.** OpenResearch is signed and notarized for macOS, Linux, and Windows (beta). LocalXiv supports one Mac configuration and is not notarized.
5. **General chat models take the "understand" job.** They are already paid for and read PDFs.
6. **No users.** Any of the above can happen before LocalXiv has an audience.

**Worst case.** alphaXiv adds a reflowed TeX reader to its apps and a "Send to Kindle" for the paper and its free Overview. LocalXiv then keeps only four edges: the reader's own key, local data, the drawn Overview, and the Mac app.

## 9. Strategic implications

### 9.1 Build first: where LocalXiv leads

1. **Conversion coverage and quality.** This is the one thing alphaXiv tried and reverted. Reduce the 17 PDF-only papers and fix the open defects in [the parser audit](parser-audit-2026-10-15.md). Bundle the Pandoc and EPUBCheck versions that the corpus uses, so the corpus result is the app result.
2. **Chat with the Paper on the reader's own key.** Select a passage and ask. Each answer cites passages with the Blog's citation and Reference preview. This turns the most repeated alphaXiv request into a LocalXiv feature.
3. **Kindle reading quality.** Check math and figures on a real Kindle, because the automated checks do not cover delivery. E-ink is the job with no clear winner.

### 9.2 Make equal: small and expected

4. **Highlights and notes** on the reflowed Paper. Put them in the EPUB export, so that notes go to the Kindle. alphaXiv cannot do this.
5. **Collections and Tags.** The glossary already defines them.
6. **Library citation export** (BibTeX for a Collection, then Zotero). alphaXiv promised Zotero on 2025-06-25 and has not shipped it.
7. **Open in LocalXiv.** A `localxiv://` URL scheme and a bookmarklet for arxiv.org and alphaxiv.org pages. alphaXiv grew through the URL swap. The Chrome extension was removed on 2026-09-17 (`22c3e87`); a URL scheme needs no extension.

### 9.3 Do not build

Feeds, comments, author claims, people search, preprint publishing, audio, research agents, an MCP server, and a phone app. alphaXiv leads each one with a network and funding. LocalXiv gets discovery from alphaXiv and arXiv through Direct import.

### 9.4 Decide: the weight of the Blog

alphaXiv's Overview has these properties: free, ready for every paper, instant, page-cited, translated, with audio. `/overview/<id>.md` lets any converter put it on a Kindle.

The LocalXiv Blog costs the reader's key, takes minutes, and can fail. Its remaining edges:

- Blog figures that the application draws from a Scene.
- Length, Tone, and language that the reader controls.
- A Reference preview and a Split view into the retained Paper.
- No account, and offline reading after import.
- The model and date on each Blog.

Two options:

- **Keep the investment.** Make figures and control the reason to generate a Blog.
- **Hold the Blog at its current level.** Put AI effort into the Overview drawing and chat, where alphaXiv is Weak or where users ask most.

### 9.5 Monitor

| Signal | Trigger to act |
| --- | --- |
| [#8](https://github.com/alphaXiv/feedback/issues/8) (reflowed text on phone) and [#100](https://github.com/alphaXiv/feedback/issues/100) (Kindle-like reading) | A reflowed or HTML view ships in the alphaXiv apps. Then make Kindle and the own key the lead message. |
| [#317](https://github.com/alphaXiv/feedback/issues/317) (own key) | alphaXiv allows an own key for any group. Then chat with the Paper loses part of its edge. |
| [#86](https://github.com/alphaXiv/feedback/issues/86) (Zotero) | Zotero ships. Then item 6 becomes parity only. |
| EPUB or Kindle in alphaXiv code or posts | Any export to e-ink. Then threat 3 is real. |
| OpenResearch | It gets paper-reading features. Then alphaXiv competes on the desktop. |
| arXiv HTML quality | arXiv renders most papers well. Then LocalXiv's conversion edge gets smaller. |
| alphaXiv overview accuracy issues | New author complaints. Use them as evidence for model and date on each explanation. |
