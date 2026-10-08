# Blog sections design (2026-10-08)

The Blog stops writing the article in one request. An outline plans the whole story, then one request writes each section, and the figures draw at the same time. This design follows [the Blog readability design](2026-10-08-blog-readability-design.md) and keeps its figure ranges, Tone levels, and review severity.

## Why the one-request article failed

Two live haiku-5.5 runs on AI Control (2312.06942) shipped with 10 and 12 open "missing explanation" findings. Three causes:

- **The length cut undid the repairs.** A repair added 239 words. The article passed its 1,400-word ceiling, and the cut that followed removed 140 words, among them the sentences the repair had added. The next verdict reported those gaps again.
- **The reviewer had no fixed scope.** It checked whether "a reader follows the mechanism", read the whole article again each round, and found new gaps in almost every verdict.
- **One request wrote everything.** The author planned and wrote about 1,300 words in one answer, so no request could look at one section's explanation alone.

## Length is a target

The prompt states the requested length and each section's share of it. No check enforces it: the word ceiling, the length validation, and the length cuts are removed.

## Stages

1. **Selection** and **narrative** stay as they are.
2. **Outline** replaces the author request. One request returns:
   - `title` and `rationale`: the through-line in two or three sentences, from why the work was needed to what it achieved.
   - `example`: the running example the sections carry.
   - `terms`: each technical term, its plain explanation, and the section that first explains it.
   - `sections`: three to eight, in order. Each has an `id`, a question `heading`, the `answer` that opens it, ordered `points` with passage citations, `leaves_with` (what the reader knows at its end), an optional `figure`, and a target `words`.
   - `figures`: the briefs, each named by exactly one section.

   The outline may ask for a narrative revision, as the author could.
3. **Sections and figures** run in parallel, in one pool of `BLOG_WORKERS` workers. Each section request gets the whole outline, its own section, the previous section's `leaves_with` as its entry, and the retrieved evidence. It returns the section body; the application writes the heading. Each figure draws from its brief as before.
4. **Join**: one exact-edit request reads the assembled article and fixes the joins: a transition where a section's opening does not follow from the previous section's end, and a second explanation of a term.
5. **Review** as in the readability design, with a fixed scope (below).

## Continuity

- One copy of each contract: the outline gives each section only `leaves_with`. The application passes section *n−1*'s `leaves_with` to section *n* as its entry.
- Term ownership: a section explains the terms it owns. It may use a term that it or an earlier section owns. For a term a later section owns, it uses the plain words.
- The join request fixes what the contracts miss.

## Review scope

The review request carries the outline. `missing_explanation` means an outline point the article does not make, or a term used before the section that owns it explains it. An explanation outside the outline is advice only when a reader needs it to follow the outline.

## Costs and failure

- Every section request carries the full retrieved evidence, so input tokens grow with the section count. A per-section subset is the follow-up if the cost matters.
- A section request that fails its three attempts gets one more request of its own; if that fails too, the run fails. A figure still falls back to omission.
- A cancelled job stops the pool: pending requests are cancelled, and the run records the cancellation.
