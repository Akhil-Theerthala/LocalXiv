# Blog checks design (2026-10-08)

The Blog drops its model reviewer. The application checks each section before it accepts it, the way the Overview checks a Scene, and one bounded join request smooths the seams. This design follows [the Blog sections design](2026-10-08-blog-sections-design.md) and keeps its stages, its figure ranges, and its Tone rules.

## Why the review loop never ends

The Overview ends because the application decides: a Scene passes fixed checks with exact messages, or its correction budget runs out. No model reads the result. The Blog kept a model reviewer that reads the whole article against the paper and reports what it finds. Each verdict finds new problems, so the loop ends only on the budget.

Five live runs on AI Control (2312.06942), 2026-10-08:

| Run | Verdicts | Findings per verdict | Result |
| --- | --- | --- | --- |
| 00:54 | 9 | 10, 12, 14, 15, 14, 17, 14, 4, 2 | failed |
| 04:26 | 3 | 14, 15, 12 | shipped with 12 open |
| 04:56 | 6 | 15, 20, 18, 16, 7, 11 | shipped with 11 open |
| 05:41 | 4 | 17, 16, 16, 18 | failed |
| 06:04 | 5 | 10, 6, 9, 9, 14 | shipped with 14 open |

The three section-branch drafts (05:41, 06:04, 06:13) show what the reviewer did not report and what needs no check at all:

| Measured in the three drafts | Result |
| --- | --- |
| Section words against the outline target | every section over, 1.3 to 3.2 times; outlines of about 1,100 words became drafts of 1,815 to 2,239 |
| Sentences of 25 words or fewer | 99 to 100 percent |
| Outline points whose passages the section cites | all 129 |
| Terms used before the section that owns them | one or two per draft, always in the first section |
| Terms explained in more than one section | one to four per draft |

So the length and the term order need a check, the STE rules and the citations do not, and the seams need one pass that knows where they are.

## Stages

1. **Selection** and **narrative** stay as they are.
2. **Outline** stays, with one more check. A term's owner section is the first section whose heading, answer, or points use the term. The validator rejects an outline where an earlier section's heading, answer, or point uses a term a later section owns, with the message naming the term, the section, and the owner. Without this check a section writer cannot both open with the outline's answer and avoid the term.
3. **Sections and figures** run in parallel as before. Each section request keeps its three attempts plus one more request, and the application rejects a section body with an exact message when:
   - its word count, without citations and the figure marker, is above 1.5 times the section's `words`. The message gives the count, the target, and the ceiling.
   - it uses a term a later section owns, as a whole word, singular or plural. The message names the term and the owner section and asks for plain words.
   - a point's passages are all absent from the body's citations. The message quotes the point and its passages.
   - the figure marker is not exactly the section's, or a citation names an unknown passage, as before.
   - a figure marker shares a line with other text. The HTML export replaces a marker only when it is a paragraph of its own.
4. **Join** stays one exact-edit request with one correction, and the application now hands it the seam list instead of asking it to search:
   - for each pair of adjacent sections, the first section's `leaves_with` and the second section's first sentence;
   - each term the article explains more than once: the sentence that explains it first in reading order, which stays, and each later explaining sentence. A sentence explains a term when it opens with the term, after an optional article, followed by "is", "are", "means", or "refers to", or when "called", "named", or "known as" precedes the term. The term as a subject elsewhere in a sentence is a measurement ("at a 2% budget, safety is 15%"), not an explanation. A term explained once is not listed, whatever section the outline names as its owner, so the join can never cut an article's only explanation.

   The join may edit only the listed sentences: the seam openings and the later explanations. The application rejects an edit whose old text lies outside them, with that text in the message, and the one correction follows. The first live run after this design cut the only explanation of "Pareto dominance", a sentence the list never named.

   The article ships when the join request and its correction both fail, and the provenance records the reason. The checks after the join are the article's own: known citations and the surviving figure markers.
5. The run ends. There is no review stage.

## Why a per-section ceiling is not the cut this branch removed

The readability design removed a 1,400-word ceiling on the whole article because the cut that enforced it deleted the sentences a repair had just added. This ceiling applies to one section, before assembly, inside the request loop. A section over the ceiling is rejected and rewritten; nothing is deleted from an accepted text. The ceiling is loose, 1.5 times the target, because a model counts words poorly and a tight band would spend all three attempts on counting.

## What this drops

- The reviewer, its prompt, its response schema, its severity categories, and the findings model: `blog_review.py`, `REVIEW_PROMPT`, `REVIEW_RESPONSE_SCHEMA`, `ERROR_CATEGORIES`, `FIGURE_SCIENCE_CATEGORIES`.
- The correction rounds that answered verdicts: `review_loop`, `correct_round`, `redrawn`, the brief correction, `Article.repair`, `Article.delete_errors`, and the `issues` argument of `BlogFigures.draw`.
- The one-request author's draft schema and validator, dead since the sections design: `BLOG_DRAFT_SCHEMA`, `BLOG_AUTHOR_RESPONSE_SCHEMA`, `validate_blog_draft`.
- The provenance fields `reviews`, `vision_review`, `verdict_count`, `open_advice`, and `deleted_errors`, and the session context keys `reviews`, `open_findings`, and `draft_issues`. No front-end code reads them.
- The CONTEXT.md entry for Review finding.

Fidelity after this change rests on the citation requirement, as it does for the Overview: every paper claim cites a retrieved passage the application knows. The reviewer was the only semantic check for an unsupported claim, and it found one to five per verdict. If that proves too weak, the bounded form is one claim check per section with one correction, in the same pool; it is not part of this design.

## Costs and failure

- The section checks and the seam list make no provider call.
- A section that fails its checks costs the same corrections as a section that fails its marker today.
- An omitted figure still removes its marker and rewrites the prose that depended on it, as before.
- A cancelled job stops the pool, as before.
