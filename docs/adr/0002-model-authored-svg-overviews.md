---
superseded-by: ../../superpowers/specs/2026-09-13-overview-workflow-rebuild-design.md
status: superseded
date: 2026-09-13
---

# Model-authored SVG Overviews

## Decision

Overview generation accepts one complete, model-authored SVG teaching scene. The model owns
composition, coordinates, grouping, hierarchy and connectors. LocalXiv owns a bounded static-SVG
profile, deterministic normalization, page rendering, structured WebKit measurements, repair
state and evidence review.

The accepted source is stored verbatim after normalization as `.source.svg`. PNG, PDF and the
raster-backed compatibility SVG remain complete-page exports. The source download exposes the
genuine SVG rather than the compatibility wrapper.

There is no Overview target word count. Six hundred visible SVG words is an extreme rejection
ceiling. Page height, readable type, overlap and bounds checks remain hard acceptance gates.

## Why

The former scene compiler constrained composition without making representative live generation
reliably fast or acceptable. The reference pages show that architecture, method and comparison
papers need materially different compositions. A fixed panel grammar made those differences hard
to express and introduced a second visual language between the model and the reviewed artifact.

Static SVG provides the required freedom without executing model code. The allowlist excludes
scripts, foreign objects, external resources, embedded images and active links. WebKit measures
the actual transformed result instead of predicting layout in a separate Python compiler.

## Consequences

- `papers/overview_scene.py`, its production examples and its structured prototype are removed.
- New Overview tool schemas use fixed figure ID `fig1` and an `svg` field; HTML and scene fields
  are rejected for new candidates.
- Existing HTML-based and scene-era saved generations remain readable. Scene metadata is inert.
- Blog authoring remains HTML/SVG and may adapt a valid saved Overview source.
- Native layout defects and semantic review issues stay active together until resolved.
- Architecture, worked-method and comparison fixtures are regression evidence, not production
  templates or paper-type routing rules.

This decision supersedes [ADR 0001](0001-structured-visual-authoring.md) for Overview authoring.
