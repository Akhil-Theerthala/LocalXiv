# LocalXiv

LocalXiv provides comfortable research-paper reading and a personal local library.

## Language

**Paper**: A research work in the library. Its source, EPUB, and PDF are representations of that paper, not separate collection entries.

**Paper queue**: Ordered jobs for one arXiv paper, including its versions and reimports. Different papers run concurrently. A cancelled job holds its place until its running operation stops, so a retry cannot overwrite files still in use.

**Direct import**: Adding a Paper from input that names exactly one arXiv paper: an arXiv ID, an arXiv link, or an alphaXiv link. It needs no Paper search.
_Avoid_: fetch, L1 fetch

**Paper search**: Finding a Paper from ambiguous input, such as a title, an author, or a topic, among arXiv papers and the papers already in the library, so the reader can open it or import it without its link.
_Avoid_: fetch, L2 fetch

**Suggestions**: The Paper search results that show under a search field while the reader types.

**Library search**: Filtering the saved papers on the Library page by title, author, or arXiv ID. It finds only papers already in the library.

**Paper retention**: Keeping a Paper and its available representations in the library. A failed conversion can still leave a retained Paper with useful original files.

**Conversion recovery**: Trying another readable representation when an earlier conversion attempt fails.

**Paper export**: A file prepared for downloading or sending, containing the original Paper, a generated explanation, or both.

**Collection**: A named group of papers. A paper may belong to multiple collections.

**Tag**: A user-created label for describing and finding papers.

**Element repair**: Preservation of a difficult equation, table, figure, or diagram through a different readable representation, including a locally rendered image.

**Reflowed PDF fallback**: An alternative reading document whose layout and pagination regenerate at the reader's chosen text size when EPUB repairs are insufficient.

**Content retention**: Preservation assessed separately for text, equations, tables, figures, and references in each paper. Faithful representation changes do not constitute loss.

**Independent conversion**: Conversion performed on the reader's current device without requiring another device or a LocalXiv server.

**Visual explanation**: An illustrated account of a Paper's ideas and findings, with relationships and examples that help the reader understand them. Its composition can vary with what the Paper needs to explain.

**Overview**: The first pass over a Paper: one image that tells why the work was needed, how it works, and what it achieved, which the reader follows panel by panel along its arrows. A Why panel comes first; every panel heading states a claim, so the headings alone tell the story; the Result panel opens with headline numbers drawn large. Every component appears, but only the cards on the mechanism's path carry details; the other cards are chips, and the Component hover shows their Digest fields. For an architecture, the How panel shows the core operation on the running example and a Model panel shows how the parts nest; for a method, the mechanism as a worked example; for a survey, the families of methods. One 1000-unit column of 3–4 panels with a header, title, subtitle, and footer. The current design is [the 2026-10-08 Overview story](docs/superpowers/specs/2026-10-08-overview-story-design.md), on the pipeline of [the 2026-09-18 Overview scene layout](docs/superpowers/specs/2026-09-18-overview-scene-layout-design.md). Reference figures are in `docs/reference_images/`.

**Blog**: An accessible explanation that builds relevant context and explains prior approaches so a reader can follow a Paper's ideas and gain a working understanding of its central contributions, supporting evidence, and limitations. At the reader's chosen length, it opens with an honest account of what the paper contributes and why that contribution matters, without assuming the reader's personal needs, then follows the Overview's order: why the work was needed, how it works, what it achieved, and where the result holds. Each section heading is the question it answers, and the section opens with the answer. One running example carries through the mechanism. The design is [the 2026-10-08 Blog readability design](docs/superpowers/specs/2026-10-08-blog-readability-design.md).

**Blog reader**: An impatient reader who has glanced through the Overview and remembers some of it, knows the basics of the paper's field, and is unfamiliar with its particular method. They value articles that are easy to read and help them answer practical questions.

**Blog figure**: A focused visual explanation that makes an idea understandable through depicted relationships, operations, or comparisons. Text supports the drawing where needed; surrounding Blog prose carries the context and detailed explanation.

**Blog outline**: The plan the Blog's sections are written from: a title, the through-line from why the work was needed to what it achieved, the running example, each technical term with the section that explains it first, three to eight sections, and the figure briefs. Each section has a question heading, the answer that opens it, cited points, what the reader knows at its end, its figure, and a target word count. Sections and figures are then written in parallel, each section passes its Section check, and one join pass smooths the seams the application lists. The design is [the 2026-10-08 Blog checks design](docs/superpowers/specs/2026-10-08-blog-checks-design.md), on the stages of [the 2026-10-08 Blog sections design](docs/superpowers/specs/2026-10-08-blog-sections-design.md).

**Blog figure brief**: The Blog outline's assignment for one Blog figure: purpose, entry context, exit state, ordered content items, exact text, and illustrative values. The model authors one Scene panel from it, and every exact text and illustrative value must appear in that panel.

**Blog background**: General knowledge used to explain concepts or prior approaches that a Paper assumes its reader understands, permitted under the current Blog policy. It supplies explanatory context, not evidence for claims about the paper's novelty, results, or comparisons.

**Blog length**: The reader's choice of explanatory depth, with the contribution's importance, central idea, main evidence, and qualification preserved at every length. Longer Blogs develop examples, difficult steps, and relevant comparisons; shorter Blogs explain fewer details clearly. The length also sets the figure count: short 1–2, medium 2–4, large 3–6, one for each section where a picture explains an operation, a relationship, a comparison, or a change.

**Tone**: The reader's level of ASD-STE100 Simplified Technical English for the Blog: one list of twelve STE rules, kept in about 7 of 10 sentences for Casual, about 85 of 100 for Semi-formal, and every sentence for Formal. The model reads the level; the application does not score sentences.

**Section check**: The application's checks on one Blog section body before it is accepted, inside the section request's correction loop: at most 1.5 times the section's target words, no term that a later section owns, one of each point's passages cited, the section's figure marker exactly once, and known citations only. Each failed check sends an exact message back. No model reviews the article after the sections pass.

**Omitted Blog figure**: A planned figure whose Scene panel still fails validation, coverage, layout, or the native checks after one request and three corrections. The delivered article excludes its caption, marker, and dependent discussion; essential scientific explanation remains understandable in prose.

**Overview panel**: One framed region of an Overview with a numbered heading chip and one node tree of cards, groups, notes, sequences, grids, steps, bars, charts, stats, and dividers, joined by arrows the application routes. An arrow means the output of one card goes into the next.

**Chip**: A card that no arrow touches and that has no tone, drawn as its label only on a sunk fill, or on the page fill when it sits on a sunk surface, with no detail. The Overview workflow makes chips after coverage passes; a run of chips in a column lays out as one wrapping row.

**Stat**: A Scene node that draws one headline number at 34 units with a label under it that says what it measures and for what. One to three open an Overview's Result panel.

**Digest**: The model's one-call extraction of a Paper's core: why (the problem, what blocks the usual approach, and the paper's idea), contribution, result, qualification, a running example, hyperparameters, and 4–24 components with containment, data flow, and the operation each computes, all evidence-linked. Its required fields are what makes "the core is present" checkable.

**Scene**: The model's tree of what the reader sees: title, subtitle, footer, and 1–4 panels of nodes and arrows. It names content and structure only; the validator rejects any gap, size, or coordinate. Coverage requires every digest component name and operation to appear, a component with two or more parts of its own to be a group heading, a first panel with the id `why`, and a stat in the last panel.

**Scene math**: The plain-text equation notation of a Digest and a Scene: an underscore starts a subscript and a caret a superscript, for one word (`d_k`, `W^Q`) or a bracketed group (`10000^{2i/d_model}`), with Unicode for symbols. Unicode script characters mean the same. The Figure library draws scripts as raised or lowered text at three quarters of the line size; the native checks give them a 10-unit floor and count one math line as one text run. A Scene wraps each equation in backticks: the Figure library draws it in the math font inside a faint box and never splits it across lines, and a panel too narrow for it is a layout error. Digest coverage ignores the backticks.

**Scene layout**: The application's deterministic layout of a Scene: measured text at 14 units, cards sized to their words, rows that share width, then wrap into even lines that no arrow crosses, before they become columns, narrow columns reflowed into two, justified top-level rows, a detail on its label's line when both fit, panels split into rows of one to three by the `auto` layout so the page is shortest and no frame stands mostly empty, and arrows routed around every other card: an arrow between two stacked cards enters its target across their shared span, or ends on the frame of the group that holds the target when the group heading spans the whole card; a label is dropped when an arrow crosses it. An arrow that runs far around other cards is a warning that asks for one Scene correction. A headed group inside a headed group draws as a surface with no border, sunk and page by turns.

**Figure library**: `papers/figures/`, the one path from a Scene to SVG, PNG, PDF, checks, and issues, used by the Overview and every Blog figure. It makes no provider call and knows nothing about papers or prompts.

**Figure render**: The laid-out Scene rendered by the Figure library as one SVG document, with the page frame for an Overview or as a bare panel for a Blog figure, from which the PNG, PDF, and editable SVG are rendered. It must pass the native checks, and an Overview must reach 40 text runs per million square units.

**Reading preferences**: The reader's theme, text size, font, and margin choice. One module maps them to values. The page and the Paper's reader iframe apply those values and hold no colour of their own.

**Figure palette**: The named colours a Figure render draws with. The light palette is the export palette for PNG, PDF, and Kindle. The dark palette follows the reader's theme on screen.

**Component hover**: The Digest fields for one drawn card or group heading, shown when the reader hovers or focuses it in the inline Figure render: name, `computes`, role, and values. A click opens the Paper at the component's first passage. The figure's drawn text does not change, so the on-screen figure and every export are the same figure.

**Scene correction**: The bounded requests that fix a Scene: up to two for validation and coverage, one more when an arrow cannot be routed, an arrow detours far around other cards, or a panel spans under 40% of its width. A figure whose only defect is a detour ships after that one correction. There is no drawing repair; geometry defects cannot occur.

**Stage retry**: One more run of a failed Overview or Blog stage, from the results of the stages before it. The Overview retries selection, digest, and Scene. The Blog retries selection, narrative, and outline; its figures already fall back to an Omitted Blog figure, and a failed join ships the sections as written. A cancelled job or a rejected key does not retry. The reader sees an error only when the retry also fails.

**Paper orientation**: A deterministic local map of the retained abstract, sections, passages, figures, tables, appendices, and source sizes. Building it makes no provider call and does not open image files.

**Evidence selection**: The smallest source subset a generation stage requests from the Paper orientation. The application validates every ID, resolves sections and descendants in source order, excludes bibliography content from the AI view, and loads only explicitly selected safe local images.

**Accepted narrative**: The evidence-linked reader journey approved structurally before authoring: question, contribution, finding, limitation, ordered visual focus, and essential relationships. Its digest binds later figure submissions and repairs.
