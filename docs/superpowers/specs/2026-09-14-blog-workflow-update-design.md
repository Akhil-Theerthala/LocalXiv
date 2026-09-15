# Blog workflow update

Status: agreed product direction, with implementation choices specified below for the requested plan. Documentation only; implementation and live provider evaluation have not started.

## Purpose and reader

The Blog gives an impatient reader a working understanding of the paper's central contributions. The reader knows the basics of the field, has glanced at the Overview and remembers some of it, but does not know the particular method.

Open with what the paper contributes and why that contribution matters. Make an honest case from the paper's problem, contribution, evidence, and scope. Do not infer the reader's personal needs or manufacture importance. Then progress through questions the reader can answer and use to reason about the idea. Explain relevant context and prior approaches before their differences become necessary to understand the contribution. Introduce technical terms through concrete meaning, examples, and operations.

General background knowledge is permitted for now. It may explain a standard concept the paper assumes; it is not evidence for novelty, measured results, or claims about competing methods. Illustrative examples must be identified as illustrative. This change adds no external literature search.

Length controls depth. Every setting retains the contribution's importance, central idea, main evidence, and qualification. Longer articles develop examples, difficult steps, and relevant comparisons. Shorter articles explain fewer details clearly. Preserve the existing language and length preferences, including the internal `large` setting and current maximum word counts.

## Source reading

Use the same local reading mechanism as Overview: `build_orientation`, `orientation_page`, `evidence_document`, and `retrieve_evidence` in `papers/reading.py`. Blog already calls these functions. Preserve and verify that reuse rather than introduce a second reader.

1. Build the source map locally, identifying the abstract and available sections, passages, figures, and tables.
2. Use the abstract to direct selection toward context, mechanism, evidence, and qualifications. The abstract is a navigation aid, not sufficient support for details it does not establish.
3. Retrieve the smallest sufficient source set, preserving paper order. Include relevant discussion of prior work and appendices. A selected parent includes its descendants.
4. Permit batched supplemental reading when the author or reviewer identifies missing support. All such requests use the same filtered retrieval boundary.
5. Filter bibliography entries from source maps, evidence, and provider messages, including supplemental reading and old Overview reference admission. Preserve in-text citations, relevant related-work prose, and material after the bibliography. Never mutate the retained paper.
6. Preserve explicit absent/ambiguous-abstract status and index pagination. If no abstract is identified, select from available headings and passages; do not silently label another passage as the abstract or send the whole paper.

An existing Overview is optional reference material. Blog must work without one. Its claims are grounded in the retained paper, and an old Overview is not a substitute for fresh source identity and reading-revision checks.

## Article and drawing responsibilities

Preserve the current prose author, citation handling, length preferences, and evidence review. Change its output from prose plus authored HTML/SVG to prose plus focused drawing briefs. Do not redesign text generation merely because figures failed.

A brief identifies one idea best explained visually: an operation, relationship, comparison, or change. It carries the question the picture answers, what the preceding prose establishes, the intended reader takeaway, supporting passage IDs, exact necessary labels or values, one existing construction family, and a broad layout idea. For example: input on the left, frozen and trainable paths stacked in the middle, addition and output on the right. This describes reading order and relationships without prescribing every coordinate. A figure is not a miniature Overview. Preserve the current allowance of zero to three figures; this is a ceiling, not a quota.

Reuse Overview's individual drawing machinery: complete assignments, concise guides and relevant SVG examples, direct structured responses, safe SVG validation, native measurement, and exact-value checks. Do not invoke Overview's whole-paper panel planner, arrangement, numbered frames, mixed scaling, or text-panel recovery.

Use the same request structure as Overview panel generation: detailed drawing assignment including layout intent, one or two relevant complete SVG examples, applicable construction notes, common drawing guidance, and the SVG output contract. The drawing model primarily writes the `<svg>...</svg>` content; retain the existing small JSON envelope with the stable ID for reliable parsing. The application owns article HTML, figure placement, caption rendering, and asset generation.

The drawing model receives one assignment and its drawing references. It does not receive the complete article, paper, sibling figures, or planning history. Text in a figure is limited to what helps interpret the visual: labels, values, or necessary equations. Context and detailed explanation belong in the article.

Reliable figure completion is the objective. Before drawing, validate that the brief gives a coherent visual operation and sufficient context, that labels and values are defined, and that its layout can be attempted at the reading width. Keep required content focused instead of feeding a paragraph-heavy assignment to the SVG model. Each repair receives the same assignment/examples, its previous drawing, all current measured defects with locations and required sizes, and a rendered image when vision is enabled. Preserve correct relationships and change the geometry that failed. Do not spend the budget repeating vague advice to make the figure readable.

## Geometry at article width

New Blog figures use the panel SVG profile and a Blog rendering mode that displays the drawing at 640px wide, with proportional height. The application supplies the surrounding article, title/caption metadata, and placement. The drawing has no legacy 960px page wrapper or hidden 40px padding.

Author toward a 640-unit-wide viewBox with 18px body labels and a 14px minimum displayed label size. Height follows content within existing rendering resource limits. Different viewBox widths remain legal, but the native checker measures the actual result at 640px, including transforms. Increasing viewBox width must not bypass readability checks. Keep clipping, overlap, marker, and exact-content checks.

This is acceptance at the current 640px reading target, not a claim that every smaller phone viewport is equally readable. Verify actual reader and export output, including captions and enlargement. Do not weaken Overview or legacy saved-figure behavior.

## Four drawing attempts, with omission as recovery

The target is a usable figure within two or three attempts, preferably on the first. The hard limit is four provider drawing requests for a stable figure ID over the entire Blog run: initial creation plus up to three repairs. Stop when the figure passes; do not make extra calls to fill the budget. A later semantic review may consume remaining repair attempts, but cannot reset the counter. Malformed drawing responses consume an attempt. A transport retry must fit inside the same four-request ceiling. Authentication failure, cancellation, or a broken local renderer is a run error, not an excuse to report a successful figure omission.

If a figure is still unusable after its fourth attempt:

- Mark it omitted permanently for that run; keep failed sources, issues, and attempt counts in diagnostics.
- Exclude its asset entry, marker, caption, alt text, and generated-figure references from the delivered article.
- Remove or rewrite figure-dependent discussion throughout the article, including phrases such as “the blue branch above” and “as the diagram shows.” Marker deletion alone is insufficient.
- Preserve the scientific idea where it is essential. Remove discussion of the missing illustration, not the central contribution. Explain the necessary operation directly in prose and discard purely visual walkthroughs.
- Preserve successful figures and their stable IDs. Do not regenerate or renumber them to close gaps.
- Never replace the failed drawing with a text-filled SVG or a copied Overview.

Batch omissions already known into one focused text-edit request. Send the article for context, the omitted briefs, surviving figure IDs, and relevant filtered evidence. Request exact text replacements, not a new article or new figures. Apply replacements only to a matching article digest; preserve all text outside the replaced spans.

Example:

Before: “Follow the blue branch in the diagram below to see the update added to the frozen output. {{figure:fig2}}”

After: “The frozen weights produce one output, and the small trainable matrices produce an update. Adding them gives the layer's output.”

The replacement keeps any necessary source citations. It says nothing about an absent picture. Explicit references to figures in the original paper are distinct and must not be indiscriminately deleted.

After cleanup, check citations, length, surviving markers and assets, scientific meaning, and continuity. The final review sees exactly the cleaned article and surviving rendered figures. A Blog with no surviving figures can be delivered if it passes these checks. If cleanup or semantic review cannot produce a sound article within the bounded correction policy, retain the draft and prior saved generation rather than publish broken prose.

## Persistence, scope, and acceptance

Keep the existing generation fields and save boundary. Store the original draft, brief assignments, per-figure attempts, omitted IDs, cleanup edits, and final review alongside current run artifacts. Published `figures` contains accepted figures only. Omission diagnostics belong in provenance, not as broken-image placeholders in reader content.

Use new Blog prompt/schema revisions so previous HTML candidates and contexts cannot be mistaken for new drawing briefs. Continue displaying and exporting old saved Blogs without regeneration. Keep Overview behavior unchanged except for shared code changes covered by regression tests.

Local completion requires evidence for abstract-directed selection, bibliography exclusion at every new provider boundary, focused assignments with layout intent and examples, actual-width SVG checking, successful second/third/fourth-attempt recovery, no fifth drawing request, coherent removal of one/several/all failed figures, stable surviving assets, cancellation, and reader/export compatibility. Mocked success does not establish live reliability. A later explicitly authorized pilot must report delivered Blogs separately from figure retention and omission rates, and compare cost/time per accepted article. Report the fractions of planned figures accepted on attempt one, by attempt two, by attempt three, and by attempt four. Article delivery after omission is successful recovery, not successful figure generation.

Implementation plan: [Blog workflow update](../plans/2026-09-14-blog-workflow-update.md).
