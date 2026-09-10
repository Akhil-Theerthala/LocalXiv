# Bento generation v4

The content prompt now asks for short headings, answer-first bodies, a clear focal
contribution, and distinct evidence, mechanism and limitation cards. The existing
second model call reviews both grounding and readability. No additional calls are
introduced. Hard text limits remain compatible with saved v3 designs.

The layout puts focus first, uses aligned pairs in landscape and a single column
in portrait. Odd card counts give the lead a full row. Card count no longer forces
three narrow columns. Heights are measured from content.

Up to two cards may contain a cited visual: a two- or three-step process, or two
or three labeled reported values. Captions explain arrow meaning or evaluation
conditions. The prompt prohibits turning branching networks into serial flows.
Validation checks schemas and passage IDs, not scientific entailment; the model's
evidence review remains responsible for that. The renderer measures all labels,
stacks flows when needed, and preserves editable Excalidraw elements. The app text
transcript includes visual content in rendered reading order.

## Library decision

Inspected the public [Excalidraw library directory](https://libraries.excalidraw.com/)
and [Deep learning library source](https://raw.githubusercontent.com/excalidraw/excalidraw-libraries/main/libraries/yuelfei/deep-learning.excalidrawlib).
Its network and attention assets are reusable full diagrams, but shrinking them
does not establish readability or factual agreement with an arbitrary paper.
This implementation uses the installed excalidrawer rectangle, text and arrow
helpers for bounded diagrams instead. It does not import third-party library
assets, fetch libraries at runtime, or add dependencies. General library import,
branching network diagrams and equation typesetting are outside this change.

## Verification

- `python3 -m unittest tests.test_bento`: 9 tests passed, including all card counts
  in both orientations, evidence/schema rejection, visual containment, editable
  scene IDs, generated portrait PNGs, PDF and EPUB export paths.
- `node tests/test_app_ui.js`: passed.
- `node --check papers/overview_render.mjs`: passed.
- Landscape and portrait previews rendered without warnings and visually inspected
  using manually curated content from the saved Attention Is All You Need paper.
- No live provider calls, installed-app rebuild, or saved-generation replacement.
  Prompt quality across model-generated papers has not been measured.
