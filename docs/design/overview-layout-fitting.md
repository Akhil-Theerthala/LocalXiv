# Fit generated panels by their gaps

The user approved implementing this geometry stage after discussing it on 2026-09-13. Text reflow is a later task. Each panel remains a uniformly scaled SVG with unchanged internal coordinates and content.

## Inputs and constraints

- Accepted SVGs and their tight native content bounds.
- An initial combined layout. Its positions establish the spatial relationships to preserve. The saved layouts are inputs to replay, not hand-tuned templates.
- Fixed `pad_length` between panels and an outer margin. Keep inner padding and the number band fixed in final drawing units.
- The initial layout's canvas supplies a finite fitting envelope. This does not impose a preferred aspect ratio. Without a finite envelope, enlarging every panel and the canvas has no stopping point.
- Each panel's starting scale is the minimum allowed scale for this pass. Do not shrink readable content to make a candidate feasible.

Centres establish direction. Overlapping perpendicular spans identify facing neighbours. Retain all such neighbours, including multiple panels along one side. A signed gap below `pad_length` is a violated constraint. The smallest gap is the first limiting constraint, not a reason to discard the others.

## Pseudocode

```text
FIT_LAYOUT(panels, initial_layout, pad_length, outer_margin):
    boxes = tight_content_boxes(panels, initial_layout)
    frames = add_fixed_padding_and_number_band(boxes)
    envelope = initial_layout.canvas
    original = copy(initial_layout)

    neighbours = find_facing_neighbours(frames)
        # left/right require overlapping vertical spans
        # top/bottom require overlapping horizontal spans
        # preserve every relevant neighbour, not only the nearest one

    horizontal_edges, vertical_edges = separation_constraints(frames)
        # i -> j horizontally means x[j] >= x[i] + width[i] + pad_length
        # i -> j vertically means y[j] >= y[i] + height[i] + pad_length
        # use facing relationships first
        # every pair must retain at least one separating direction
        # for diagonal pairs, choose a direction consistent with their original positions
        # keep the chosen directions during fitting to preserve spatial order

    verify_each_axis_graph_is_acyclic_with_a_deterministic_topological_sort()
    start_scale = exact_saved_scale_for_each_panel_in_source_units()
    growth = 1 for every panel
    active = all panels

    PLACE(growth):
        sizes = content_sizes * start_scale * growth + fixed_frame_padding
        x = earliest_positions(horizontal_edges, sizes.width, pad_length, outer_margin)
        y = earliest_positions(vertical_edges, sizes.height, pad_length, outer_margin)
            # process each directed graph in coordinate order
            # each coordinate is max(margin, every predecessor's far edge + pad_length)
            # this propagates movement through neighbours instead of growing panels independently
        return frames(x, y, sizes)

    if PLACE(growth) does not fit envelope:
        return original with an explicit diagnostic

    while active is not empty and iteration_budget remains:
        increment = largest common relative growth increment for active panels
                    whose PLACE(growth + increment_for_active) fits envelope
            # bounded binary search; one candidate contains ALL panels
            # fixed separation constraints protect shared gaps and prevent diagonal collisions
        growth[active] += increment

        blocked = active panels that cannot grow individually by tolerance
                  while PLACE still fits envelope
        remove blocked from active
        if no numerical progress and no newly blocked panels:
            stop

    fitted = PLACE(growth)
    latest = latest_allowed_positions_by_reverse_topological_pass(envelope, sizes)
    choose positions in topological order:
        preferred = original_content_centre - scaled_content_half_size - frame_inset
        lower = max(outer_margin, placed_predecessor_far_edges + pad_length)
        coordinate = clamp(preferred, lower, latest[panel])
        # retain original centre positions wherever constraints permit
        # earliest placement alone would needlessly left-align a panel centred below two others
    gaps = recompute_directional_neighbours_and_signed_gaps(fitted)
    assert every pair is separated by at least pad_length on one axis
    assert every frame stays within the envelope and outer margin
    assert scale never falls below start_scale
    assert panel order, source content, and uniform proportions are preserved

    remove unused outer canvas beyond the required margin
        # right/bottom-only trimming needs no translation
        # left/top trimming must translate ALL frames, SVG origins, and click bounds together
    recheck final containment and separation after any trim/translation
    build SVG transforms from fitted content positions and final scales
    draw backgrounds around fitted frames
    return fitted layout, scales, gaps, binding constraints, remaining whitespace
```

`earliest_positions` is a longest-path calculation on a directed acyclic graph. The reverse pass finds each node's latest feasible position. Final placement prefers the original centres within those limits. With at most seven panels, the geometry search can stay small and deterministic without a general optimization dependency. Derive directional edges consistently from the initial coordinates, break ties deterministically, and verify acyclicity. Return the initial layout with an explicit `not_fitted` diagnostic if the input cannot be fitted; that fallback is not evidence that the new padding constraints passed.

The common growth increment gives panels equal opportunity to enlarge until a constraint binds; unconstrained panels can continue growing. This is a bounded fitting heuristic, not a claim of globally optimal packing. Exact `pad_length` on every side can be impossible while preserving arbitrary panel proportions and spatial relationships. Report residual gaps instead of stretching content or claiming they disappeared.

## Validation

Use synthetic cases to verify shared-gap consumption, several neighbours on one side, diagonal panels, propagation through a chain, no available growth, and deterministic results. At least one fixture must show different resulting scales and a strict reduction in unused canvas space. Check frame containment, pair separation, minimum text size, content preservation, and click-to-focus metadata.

Apply the fitter to every completed saved layout under `.scratch/overview-rebuild/live/runs`, using that layout's existing coordinates as the seed. Also wire the same fitter into production after initial arrangement. Save outputs separately, with before/after scales, canvas occupancy, remaining gaps, and native render checks. No model-provider requests are needed.
