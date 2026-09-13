# Shrink-first refinement after gap fitting

This is the next stage after `overview-layout-fitting.md`, authorized by the user after reviewing the fitted images. Keep the existing gap fitter as the checkpoint. Refine its result through modest uniform reductions, position compaction, and canvas trimming. Do not reflow text, stretch one axis independently, or add a preferred aspect ratio.

## Rules

- A panel may shrink below its checkpoint scale. Its limits are readability and a small maximum cumulative reduction, both measured against the checkpoint rather than reset each iteration.
- Reuse the existing 14-unit rendered-text minimum. Derive each panel's source-unit text minimum from its native `text_runs` measurements, including transforms, rather than assuming the authored font-size attribute is its displayed size. Leave a numerical margin above the minimum when rounding output scales. Default to at most 20% reduction from the checkpoint; keep the unchanged candidate available.
- Inner padding, number bands, and outer padding stay fixed in drawing units.
- Preserve reading order and the checkpoint's pair-separation directions. Move panels as needed to restore padding. The new canvas encloses the result and may shrink; it must not exceed the checkpoint envelope.
- Shrinking a narrow panel simply to make it smaller is not an improvement. Evaluate the resulting gaps after repositioning and canvas trimming.
- No further growth in this refinement. The checkpoint has already applied enlargement. Leave residual whitespace where useful reductions are exhausted.

## Measure gaps without assuming centred panels

Sweep horizontal bands between consecutive panel top/bottom edges, including canvas edges as breakpoints. In each occupied band, sort the intersecting panels by x and measure gaps from the left canvas edge, between consecutive panels, and to the right canvas edge. Weight each gap by the band's height. Repeat vertically, weighting by band width. Skip bands with no panels in that direction: gaps between rows are measured by the perpendicular sweep. Charging an empty band's entire width would also penalize intentional row gutters and outer margins.

This measures actual visible gaps and exposed boundary segments. It handles staggered rows, multiple neighbours along a side, and off-centre panels without inventing row membership or counting a distant panel through an intervening one. Compare internal gaps with `pad_length` and outer gaps with `outer_margin`.

Reject padding and margin deficits before scoring. Sum horizontal `excess_gap² * band_height` and divide by `canvas_width² * canvas_height`; sum vertical `excess_gap² * band_width` and divide by `canvas_height² * canvas_width`. The sum of these dimensionless terms is the gap-discrepancy score. Add a small, explicit resizing penalty relative to the checkpoint. Record both terms independently. An unchanged layout wins ties. Frame occupancy is total frame area divided by the candidate's trimmed canvas area; reject candidates that reduce it. Do not use a fixed checkpoint denominator for this guard, since every shrink would reduce its numerator. The occupancy guard works together with the resizing penalty and cumulative cap to discourage gratuitous shrinking.

## Pseudocode

```text
SHRINK_FIRST(panels, checkpoint, pad_length, outer_margin):
    if checkpoint already contains a shrink-first result:
        return checkpoint unchanged
    if checkpoint is not a validated fitted layout:
        return checkpoint with a skipped-refinement diagnostic

    reference = copy(checkpoint)
    best = reference
    separation_graph = checkpoint's fixed horizontal and vertical constraints
    minimum_scale[i] = max(
        0.80 * reference.scale[i],
        safe_readability_minimum / panel_source_minimum_text_size[i]
    )
    for a verified text-free panel, use only the cumulative-reduction limit
    if text measurement is missing or unusable, retain that panel's checkpoint scale
    keep already-readable panels at their checkpoint scale if they have no safe shrink allowance
    skip refinement of a checkpoint whose measured text already violates the 14-unit minimum
    step = 0.02

    COMPACT(scales):
        sizes = tight_source_content_sizes * scales + fixed_frame_padding
        minimum_width, minimum_height = longest_path_extents(separation_graph, sizes, padding)
        if either extent exceeds the checkpoint envelope:
            reject
        place panels within these compact extents using existing constraint-aware placement
        prefer checkpoint centres where feasible; do not retain empty outer canvas to preserve them
        translate all frames, SVG origins, and click bounds consistently when trimming
        validate rounded frame containment, required separation padding, uniform transforms, and readable scales
        recheck actual final canvas dimensions do not exceed checkpoint envelope
        return layout

    consider COMPACT(reference.scales) first, with zero resizing cost

    repeat within a finite iteration budget:
        winner = best

        for each nonempty subset of panels still above their minimum scale:
            # at most 127 subsets for seven panels
            # joint reductions allow a wide row to shrink when changing one panel alone would not help
            scales = best.scales
            for i in subset:
                scales[i] = max(minimum_scale[i], scales[i] - step * reference.scale[i])

            candidate = COMPACT(scales)
            if invalid or candidate occupancy is below best occupancy:
                continue

            gaps = swept_directional_gap_discrepancy(candidate)
            resize_cost = mean(square(log(scales[i] / reference.scale[i])))
            score = gaps + small_resize_penalty * resize_cost
            if score improves winner's score by more than an explicit numerical tolerance:
                winner = candidate
            break ties by less resizing, then stable panel order

        if winner is best:
            stop
        best = winner

    validate final output and retain reference unchanged if validation fails
    return best with checkpoint/final scales, canvas, gap scores, occupancy,
           accepted reductions, stopping reason, and any residual gaps
```

This is a bounded local search, not a claim of optimal packing. The maximum reduction and small step are initial implementation defaults. They must remain visible in diagnostics; the example replay establishes whether they help. Reuse the existing graph, placement, transform, and validation helpers rather than creating a second layout engine.

## Acceptance

Tests must demonstrate that a width-setting panel shrinks and permits a narrower canvas, an already narrow panel is not reduced gratuitously, two panels can shrink together to compact a row, off-centre/staggered arrangements produce meaningful gap measurements, and the readability/cumulative-reduction limits hold. Preserve exact source text, all panel IDs, and safe final click rectangles. Keep the unchanged checkpoint when refinement cannot improve it.

Run the checkpoint and this refinement on all 13 saved runs / 59 panels. Preserve the original runs and `.scratch/overview-gap-fit` outputs. Save new comparisons under `.scratch/overview-shrink-fit`, with before/after gap scores and final native checks. Wire the same refinement after the checkpoint in production. No provider calls or internal SVG content edits are needed.
