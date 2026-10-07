# Overview story plan (2026-10-08)

Build the design in [the Overview story spec](../specs/2026-10-08-overview-story-design.md) on the branch `overview-story`. The throwaway branch `overview-prototype` holds the variants the user compared; read it for reference and port nothing from it unchanged.

Every Figure library task ends with the 43-scene check:

```sh
python3 tests/relayout_saved_scenes.py > after.txt
diff before.txt after.txt
```

`before.txt` is the output on `main` at `d8fc7b1`. A change in height is expected for layout tasks. A new `ERROR` line or a new issue is a regression.

## Tasks

1. **Inline details.** In `papers/figures/nodes.py`, a card puts its detail on the label's line when both fit, and a card with a detail of at most 280 units asks for the one-line width, up to `canvas.stretch_max`. A group puts its detail on the heading's line when both fit. Done when the 43-scene check shows no new issue, and the Blog tests pass.
2. **Spacing.** Set `NOTES_GAP` to 16 and the gap between panel rows to 14. Done when the 43-scene check shows no new issue.
3. **Stat node.** Add the `stat` kind: `value` of at most 12 characters, `label`, optional `tone` and `id`. It draws the value at 34 units, bold, in its tone's text colour, with the label under it. Done when a scene with a stat validates, renders, and shows the stat text in `Figure.text`.
4. **Chips.** Add the card field `minor`. A minor card draws its label only, in the muted colour, on the sunk fill, with no border, at its natural width. In a column group, a run of two or more minor cards lays out as one wrapped row inside `Group.size`, with no new group in the scene. Done when a scene with five minor cards in a column renders them in rows, and validation depth stays at 4.
5. **Chart width and ticks.** A chart widens like a card in `justify`, up to `canvas.stretch_max`. The x axis gets round ticks from the same rule as the y axis. Done when the corrected AI Control chart shows at least three x ticks.
6. **Auto layout.** Add `auto` to the scene `layout` values. `auto_slots` in `papers/figures/render.py` pairs two neighbouring panels when the pair is under 85% of their stacked height and their heights are within 1.3×. It tries the splits 50/50, 40/60, and 60/40 and keeps the shortest. It caches each panel height by width. Scene-level edges are valid in `auto`. Done when the AI Control F scene pairs Setup with One run, and the Attention F scene stacks every panel.
7. **Arrow detours.** In `_draw_edge`, compare the routed length with the Manhattan distance between the arrow's ends. Above a threshold set from the 43 scenes, add a warning that names both cards. `FigureResult.warnings` carries warnings apart from `issues`. Done when the gpt-6-luna Attention scene warns about its arrow under the result panel, and fewer than one scene in five of the 43 warns.
8. **Digest why.** Add `why: {problem, obstacle, idea, passages}` to `DIGEST_INSTRUCTION` and `validate_digest`, each text at most 160 characters. Update the Attention, AI Control, and gpt-6-luna digest fixtures. Done when the digest tests pass with the new field.
9. **Scene rules.** Rewrite `SCENE_WRAPPER`: a `why` panel first, claim headings, complete statements, one fact per detail, arrows for flow only, and one to three stats in the last panel. Delete "Join every card to the path with an edge". Add validator issues for: no first panel `why` with three cards and two edges, no `stat`, and a card detail with more than one `; `. Update `ATTENTION_EXAMPLE` and `VARIETY_EXAMPLE` to show all of it. Bump `PROMPT_REVISION`. Done when both examples validate and each new rule has a test that checks its correction message.
10. **Workflow pass.** After coverage passes, mark untoned cards that no edge touches as `minor`, drop their details, and set `layout` to `auto`. A warning from task 7 asks for one Scene correction, then the figure ships. Done when the AI Control test run renders chips, and `component_hooks` still returns the chips' components.
11. **Docs and memory.** Rewrite the Overview entry in `CONTEXT.md` and point it at this design. Update the memory file `project-overview-focus-prototype.md` with the pick and the merge.

Merge with `git merge --no-ff overview-story` when every task is done and the Overview and Blog tests pass.
