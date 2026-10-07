# Overview story design (2026-10-08)

This design replaces the dense Overview of [the 2026-09-18 scene layout](2026-09-18-overview-scene-layout-design.md). The 2026-09-18 pipeline stays: selection, digest, scene, and app layout. What changes is what the scene shows and how the app draws it.

## Why the dense Overview failed

On 2026-10-08 the user read sonnet-5.5 and gpt-6-luna Overviews of AI Control (2312.06942) and Attention (1706.03762). The figures had "too much going on" and no "oomph". Three rules caused it:

- Coverage asked for every component and every `computes` string, so the model drew 14 to 24 components as about 30 equal boxes.
- The prompt said "join every card to the path with an edge", so models chained cards that have no data flow, such as "Untrusted model U → Trusted model T → Trusted labor H".
- Every value had one small text size, so the headline result had no more weight than a hyperparameter.

The user compared six variants on the branch `overview-prototype` and picked F, the story variant. The user's goal: a reader follows what the paper did and why, at a high level.

## What the Overview shows

The Overview reads as a story in 2 to 4 panels:

1. **Why.** The first panel has the id `why` and three cards in a row joined by two arrows: the problem, what blocks the usual approach, and the paper's idea. The Digest's `why` field supplies them.
2. **How.** The mechanism with the running example as values, as today.
3. **Result.** The last panel opens with one to three `stat` nodes: headline numbers drawn large. A chart or bars show the comparison behind them, with no value repeated from a stat.

Every panel heading states a claim, such as "One run: GPT-3.5 flags code, experts catch 6 of 19 working backdoors". The headings alone tell the story.

Every card is a complete statement. It names who acts, on what, and what any comparison is against. "GPT-3.5 is weaker; humans check 2%" fails this rule. "GPT-3.5 is safe but codes worse than GPT-4; experts can review only 2% of solutions" passes it. A card detail holds one fact.

Arrows show data or control flow only: the output of one card goes into the next. Containment, lists, and comparisons take no arrows.

## What the app does

The app owns these decisions. The model names none of them.

- **Chips.** After coverage passes, the workflow marks each untoned card that no arrow touches as `minor`, and drops its detail. The Figure library draws a minor card as a small label chip. A run of chips in a column wraps as one row. The Component hover still shows the Digest fields, so the detail moves to the hover.
- **Inline details.** A card puts its detail on the label's line when both fit. A group puts its detail on the heading's line when both fit. A card with a short detail asks for the width that keeps it on one line.
- **Auto layout.** The workflow sets `layout` to `auto`. Two neighbouring panels share a row when that row is shorter than stacking them and their heights are within 1.3×. The row tries the widths 50/50, 40/60, and 60/40 and keeps the shortest. Every other panel takes the full width.
- **Arrow detours.** An arrow that is much longer than the distance between its ends is a warning. A warning asks for one Scene correction and does not fail the figure.

## What stays

Coverage still requires every component name. A `computes` string still has to appear in the scene, but it can sit on a chip's dropped detail, because the hover shows it. The Figure library makes no provider call. The density floor stays at 40 text runs per million square units; the prototype F figures measure above it.
