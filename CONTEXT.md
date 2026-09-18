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

**Overview**: One image that orients a reader to a Paper's contribution, essential idea, and main finding with its key qualification. It is one 1000-unit-wide column: a header, a title, a one-line subtitle, one to four stacked panels with numbered headings, and a one-line footer. Three panels is the default. The current design is [the 2026-09-18 Overview simplification](docs/superpowers/specs/2026-09-18-overview-simplification-design.md).

**Blog**: An accessible explanation that builds relevant context and explains prior approaches so a reader can follow a Paper's ideas and gain a working understanding of its central contributions, supporting evidence, and limitations. At the reader's chosen length, it opens with an honest account of what the paper contributes and why that contribution matters, without assuming the reader's personal needs, then progresses through practical questions using concrete terminology and purposeful images.

**Blog reader**: An impatient reader who has glanced through the Overview and remembers some of it, knows the basics of the paper's field, and is unfamiliar with its particular method. They value articles that are easy to read and help them answer practical questions.

**Blog figure**: A focused visual explanation that makes an idea understandable through depicted relationships, operations, or comparisons. Text supports the drawing where needed; surrounding Blog prose carries the context and detailed explanation.

**Blog drawing brief**: The detailed assignment for one Blog figure, including its explanatory purpose, required content and labels, and a broad layout idea. Together with relevant SVG examples and construction guidance, it gives the drawing author what is needed to produce the SVG alone.

**Blog background**: General knowledge used to explain concepts or prior approaches that a Paper assumes its reader understands, permitted under the current Blog policy. It supplies explanatory context, not evidence for claims about the paper's novelty, results, or comparisons.

**Blog length**: The reader's choice of explanatory depth, with the contribution's importance, central idea, main evidence, and qualification preserved at every length. Longer Blogs develop examples, difficult steps, and relevant comparisons; shorter Blogs explain fewer details clearly, and figures follow the explanation's needs.

**Omitted Blog figure**: A planned illustration that remains unusable after four drawing attempts, counting initial creation and up to three repairs; the target is a usable figure within two or three attempts. The delivered article excludes the illustration and its caption, marker, and dependent discussion; essential scientific explanation remains understandable in prose.

**Overview panel**: One drawing in an Overview, shown at the column width under its numbered heading. Each panel is drawn from a Drawing assignment by an independent request, then checked and repaired locally before composition.

**Panel plan**: The planner's one-call assignment of the Accepted narrative to the Overview: title, subtitle, footer, and one to four panels, each with a heading, a purpose, a construction family, two to twelve short labels, up to eight relations between labels, an optional note, and its passages. The plan's limits are the content budget; the validator rejects excess and a plan that fails twice fails the run.

**Label**: One short string in a Panel plan that the drawing must show exactly as written. Labels are the whole text of a panel; relations and the note are the only other text.

**Drawing assignment**: The author-facing projection of one planned panel: heading, purpose, labels, relations, note, and the one-line figure story. A panel author receives this and nothing else from the paper. A Blog drawing brief projects to the same shape.

**Panel arrangement**: Scaling each checked panel to the 920-unit column, both axes alike, and stacking the panels in plan order with a fixed gap.

**Overview composition**: The assembled Overview the reader sees: the application-drawn header, title, subtitle, framed panels with numbered heading chips, and footer in one SVG document, from which the PNG, PDF, editable SVG, and compatibility SVG are rendered.

**Subtracting repair**: The local repair of one panel. The checks reject a missing label, text beyond the assignment's word budget, a panel taller than 1.25 times its width, and the measured geometry defects. The repair instruction orders removal before wrapping and enlargement. A panel gets at most two repairs; one that still has defects fails the run.

**Paper orientation**: A deterministic local map of the retained abstract, sections, passages, figures, tables, appendices, and source sizes. Building it makes no provider call and does not open image files.

**Evidence selection**: The smallest source subset a generation stage requests from the Paper orientation. The application validates every ID, resolves sections and descendants in source order, excludes bibliography content from the AI view, and loads only explicitly selected safe local images.

**Accepted narrative**: The evidence-linked reader journey approved structurally before authoring: question, contribution, finding, limitation, ordered visual focus, and essential relationships. Its digest binds later figure submissions and repairs.

**Repair decision**: A bounded correction record naming the current issue IDs, proposed change, reason, preserved accepted-narrative paths, and supporting passage IDs. Local validation and review—not the author’s summary—decide whether the repair worked.
