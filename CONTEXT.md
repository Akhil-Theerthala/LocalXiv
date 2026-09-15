# LocalXiv

LocalXiv provides comfortable research-paper reading and a personal local library.

## Language

**Paper**: A research work in the library. Its source, EPUB, and PDF are representations of that paper, not separate collection entries.

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

**Overview**: One image with 1–7 numbered panels that orients a reader to a Paper's contribution, essential idea, and main finding with its key qualification. Image dimensions follow content; there is no fixed page size, aspect ratio, or whole-image word budget. The current design is [the 2026-09-13 Overview workflow rebuild](docs/superpowers/specs/2026-09-13-overview-workflow-rebuild-design.md).

**Blog**: An accessible explanation that builds relevant context and explains prior approaches so a reader can follow a Paper's ideas and gain a working understanding of its central contributions, supporting evidence, and limitations. At the reader's chosen length, it opens with an honest account of what the paper contributes and why that contribution matters, without assuming the reader's personal needs, then progresses through practical questions using concrete terminology and purposeful images.

**Blog reader**: An impatient reader who has glanced through the Overview and remembers some of it, knows the basics of the paper's field, and is unfamiliar with its particular method. They value articles that are easy to read and help them answer practical questions.

**Blog figure**: A focused visual explanation that makes an idea understandable through depicted relationships, operations, or comparisons. Text supports the drawing where needed; surrounding Blog prose carries the context and detailed explanation.

**Blog drawing brief**: The detailed assignment for one Blog figure, including its explanatory purpose, required content and labels, and a broad layout idea. Together with relevant SVG examples and construction guidance, it gives the drawing author what is needed to produce the SVG alone.

**Blog background**: General knowledge used to explain concepts or prior approaches that a Paper assumes its reader understands, permitted under the current Blog policy. It supplies explanatory context, not evidence for claims about the paper's novelty, results, or comparisons.

**Blog length**: The reader's choice of explanatory depth, with the contribution's importance, central idea, main evidence, and qualification preserved at every length. Longer Blogs develop examples, difficult steps, and relevant comparisons; shorter Blogs explain fewer details clearly, and figures follow the explanation's needs.

**Omitted Blog figure**: A planned illustration that remains unusable after four drawing attempts, counting initial creation and up to three repairs; the target is a usable figure within two or three attempts. The delivered article excludes the illustration and its caption, marker, and dependent discussion; essential scientific explanation remains understandable in prose.

**Overview panel**: One numbered drawing in an Overview, the smallest unit a reader can follow on its own. Each panel is drawn from a complete drawing assignment by an independent request, then checked and repaired locally before composition.

**Panel brief**: The planner's assignment for one panel: its purpose, the narrative claims it owns, the earlier panels it builds on, the state it leaves the reader in, the canonical shared facts it uses, ordered content items with their evidence, and a construction family.

**Shared fact**: A canonical name, equation, or value used by more than one panel, with its exact display text and a kind of `source` or `illustrative`. Panels use the display text unchanged; illustrative values are never reported as paper results.

**Drawing assignment**: The author-facing projection of a panel brief: inherited context, resolved shared facts, and content without evidence IDs or source text. A panel author receives this and nothing else from the paper.

**Panel arrangement**: Composing checked panels in planned order, left to right then top to bottom, by measured reality: body text is normalised to one shared size, rows use actual panel heights and gaps, and the canvas grows to hold the drawing.

**Overview composition**: The assembled Overview the reader sees: numbered panels in one free-sized SVG document, from which the PNG, PDF, editable SVG, and compatibility SVG are rendered.

**Planner refinement**: The bounded review passes inside panel planning. The first clarification checks ownership, handoffs, support, and shared values; the second simplification makes affected panels self-contained instead of removing the dependency by description.

**Paper orientation**: A deterministic local map of the retained abstract, sections, passages, figures, tables, appendices, and source sizes. Building it makes no provider call and does not open image files.

**Evidence selection**: The smallest source subset a generation stage requests from the Paper orientation. The application validates every ID, resolves sections and descendants in source order, excludes bibliography content from the AI view, and loads only explicitly selected safe local images.

**Accepted narrative**: The evidence-linked reader journey approved structurally before authoring: question, contribution, finding, limitation, ordered visual focus, and essential relationships. Its digest binds later figure submissions and repairs.

**Repair decision**: A bounded correction record naming the current issue IDs, proposed change, reason, preserved accepted-narrative paths, and supporting passage IDs. Local validation and review—not the author’s summary—decide whether the repair worked.
