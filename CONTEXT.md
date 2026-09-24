# LocalXiv

LocalXiv provides comfortable research-paper reading and a personal local library.

## Language

**Paper**: A research work in the library. Its source, EPUB, and PDF are representations of that paper, not separate collection entries.

**Paper queue**: Ordered jobs for one arXiv paper, including its versions and reimports. Different papers run concurrently. A cancelled job holds its place until its running operation stops, so a retry cannot overwrite files still in use.

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

**Overview**: The first pass over a Paper: one information-dense image of its core content at one small text size. For an architecture, every component and how they nest with the operation each computes; for a method, the mechanism as a worked example; for a survey, the taxonomy of families and representative methods. One 1000-unit column of 1–4 panels, stacked or side by side, with a header, title, subtitle, and footer. The current design is [the 2026-09-18 Overview scene layout](docs/superpowers/specs/2026-09-18-overview-scene-layout-design.md). Reference figures are in `docs/reference_images/`.

**Blog**: An accessible explanation that builds relevant context and explains prior approaches so a reader can follow a Paper's ideas and gain a working understanding of its central contributions, supporting evidence, and limitations. At the reader's chosen length, it opens with an honest account of what the paper contributes and why that contribution matters, without assuming the reader's personal needs, then progresses through practical questions using concrete terminology and purposeful images.

**Blog reader**: An impatient reader who has glanced through the Overview and remembers some of it, knows the basics of the paper's field, and is unfamiliar with its particular method. They value articles that are easy to read and help them answer practical questions.

**Blog figure**: A focused visual explanation that makes an idea understandable through depicted relationships, operations, or comparisons. Text supports the drawing where needed; surrounding Blog prose carries the context and detailed explanation.

**Blog figure brief**: The article author's assignment for one Blog figure: purpose, entry context, exit state, ordered content items, exact text, and illustrative values. The model authors one Scene panel from it, and every exact text and illustrative value must appear in that panel.

**Blog background**: General knowledge used to explain concepts or prior approaches that a Paper assumes its reader understands, permitted under the current Blog policy. It supplies explanatory context, not evidence for claims about the paper's novelty, results, or comparisons.

**Blog length**: The reader's choice of explanatory depth, with the contribution's importance, central idea, main evidence, and qualification preserved at every length. Longer Blogs develop examples, difficult steps, and relevant comparisons; shorter Blogs explain fewer details clearly, and figures follow the explanation's needs.

**Omitted Blog figure**: A planned figure whose Scene panel still fails validation, coverage, layout, or the native checks after one request and three corrections. The delivered article excludes its caption, marker, and dependent discussion; essential scientific explanation remains understandable in prose.

**Overview panel**: One framed region of an Overview with a numbered heading chip and one node tree of cards, groups, notes, sequences, grids, steps, bars, and dividers, joined by arrows the application routes.

**Digest**: The model's one-call extraction of a Paper's core: contribution, result, qualification, a running example, hyperparameters, and 4–24 components with containment, data flow, and the operation each computes, all evidence-linked. Its required fields are what makes "the core is present" checkable.

**Scene**: The model's tree of what the reader sees: title, subtitle, footer, and 1–4 panels of nodes and arrows. It names content and structure only; the validator rejects any gap, size, or coordinate. Coverage requires every digest component name and operation to appear, and a component with two or more parts of its own to be a group heading.

**Scene layout**: The application's deterministic layout of a Scene: measured text at 14 units, cards sized to their words, rows that share width, then wrap into even lines, before they become columns, narrow columns reflowed into two, justified top-level rows, panels flowing into the shortest column, and arrows routed around every other card.

**Figure library**: `papers/figures/`, the one path from a Scene to SVG, PNG, PDF, checks, and issues, used by the Overview and every Blog figure. It makes no provider call and knows nothing about papers or prompts.

**Figure render**: The laid-out Scene rendered by the Figure library as one SVG document, with the page frame for an Overview or as a bare panel for a Blog figure, from which the PNG, PDF, and editable SVG are rendered. It must pass the native checks, and an Overview must reach 40 text runs per million square units.

**Reading preferences**: The reader's theme, text size, font, and margin choice. One module maps them to values. The page and the Paper's reader iframe apply those values and hold no colour of their own.

**Figure palette**: The named colours a Figure render draws with. The light palette is the export palette for PNG, PDF, and Kindle. The dark palette follows the reader's theme on screen.

**Component hover**: The Digest fields for one drawn card or group heading, shown when the reader hovers or focuses it in the inline Figure render: name, `computes`, role, and values. A click opens the Paper at the component's first passage. The figure's drawn text does not change, so the on-screen figure and every export are the same figure.

**Scene correction**: The bounded requests that fix a Scene: up to two for validation and coverage, one more when an arrow cannot be routed or a panel spans under 40% of its width. There is no drawing repair; geometry defects cannot occur.

**Paper orientation**: A deterministic local map of the retained abstract, sections, passages, figures, tables, appendices, and source sizes. Building it makes no provider call and does not open image files.

**Evidence selection**: The smallest source subset a generation stage requests from the Paper orientation. The application validates every ID, resolves sections and descendants in source order, excludes bibliography content from the AI view, and loads only explicitly selected safe local images.

**Accepted narrative**: The evidence-linked reader journey approved structurally before authoring: question, contribution, finding, limitation, ordered visual focus, and essential relationships. Its digest binds later figure submissions and repairs.

**Repair decision**: A bounded correction record naming the current issue IDs, proposed change, reason, preserved accepted-narrative paths, and supporting passage IDs. Local validation and review—not the author’s summary—decide whether the repair worked.
