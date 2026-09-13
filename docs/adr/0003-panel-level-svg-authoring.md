---
status: superseded
date: 2026-09-13
superseded-by: ../../superpowers/specs/2026-09-13-overview-workflow-rebuild-design.md
---

# Panel-level SVG authoring for Overviews

> **Superseded for new Overviews.** The [Overview workflow rebuild]
> (../../superpowers/specs/2026-09-13-overview-workflow-rebuild-design.md) keeps the panel boundary
> but replaces the draft/group/bridge contract, the page-fit arrangement, and the review-and-repair
> agent with a flat panel plan, ordered free-sized composition, and one local repair per panel.

## Decision

Overview figures are authored as a **draft plus independently generated panels**, then arranged and
composed by the application into one SVG document before rendering, review and persistence.

1. **Draft planning.** The accepted narrative becomes a draft: which panels exist, what each must
   say, how they group, the order they read in, and the bridges between them. It carries a rough
   shape hint per panel (`wide`, `square`, `tall`) and no coordinates. The application validates it
   deterministically — coverage of the narrative's steps and the claim passages, unique ids,
   bounded depth, declared bridges — before anything is drawn.
2. **Draft review.** One model review checks the draft against the accepted narrative and the
   retrieved evidence for missing explanations, missing transitions, unsupported claims and false
   relationships. A rejected draft gets one bounded revision.
3. **Panel generation.** Each leaf panel is authored as its own standalone SVG document whose size
   and shape follow its content, not a fixed rectangle. Leaves may reference only the markers the
   composer provides, so no cross-panel id collision is possible. A leaf is validated and measured
   on its own, and a failing leaf is repaired on its own.
4. **Panel arrangement.** The application measures each panel's real aspect and label sizes,
   scales each panel uniformly so every panel displays the same type size, and packs them using the
   draft's grouping, order and shape hints. Coordinates are computed, never authored.
5. **Composition.** The application draws the chrome — cards, grid gaps, headings — places each
   panel as a translated group, and draws the declared bridges with their labels. The result is one
   ordinary SVG document.

The complete figure remains the unit of validation, review, approval and digest identity.

## Why

Live runs showed the single-document pipeline failing on mechanics rather than explanation quality.
Every repair rewrote the whole SVG, so fixing one overflowing label routinely introduced another;
one run spent nine of its twenty diagnostic requests on one to three container overflows, and a
semantic correction could only be applied by relaying out the entire figure.

Authoring panels independently breaks that coupling. A panel's labels cannot collide with another
panel's content, a repair payload shrinks from a whole figure to one panel, and fixing a panel
cannot perturb the rest of the figure. Arranging *after* generation is what makes this practical:
because each panel is scaled uniformly, its internal layout is preserved exactly, so the
application can normalise every panel to one display size and pack measured reality instead of
guessing coordinates before the content exists.

Bridges became explicit artifacts of the draft instead of something the authoring model might
forget; missing bridges were among the most frequent review findings. The chrome lives in the
application, so independently authored panels still come out looking like one figure.

## Consequences

- The response contract for Overview authoring is draft + panels; the persisted `source_svg`
  remains the composed document, so reading, export, source download, Blog reference reuse and the
  word ceiling are unchanged.
- `figures[0].svg` remains a complete SVG document. The draft/panel protocol is internal to
  generation and is recorded in provenance for audit; it does not create a second production
  authoring system.
- Draft and panel schemas are additions to `papers/explanation.py`; draft validation is local and
  deterministic.
- Repair may replace one leaf panel or revise the draft. A draft revision re-authors only the
  affected panels.
- Native issue records carry the measured element centre so a defect maps to its panel by geometry,
  including after renames.
- The readability floor is never lowered to make an arrangement fit: when nothing fits, the
  arrangement names the panels whose content must be reduced and those panels are re-authored.
- The frozen live ceilings for this architecture are 30 model requests and 600 seconds per
  generation, recorded in the run manifest; the earlier 20-request ceiling belonged to the
  single-document pipeline.
- The SVG profile, native measurements, page fit, evidence rules and review gates are unchanged in
  strength.

This decision refines [ADR 0002](0002-model-authored-svg-overviews.md): the artifact remains
model-authored static SVG, reviewed as one document. Authoring, arrangement and repair granularity
change.
