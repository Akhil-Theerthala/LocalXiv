# Reader design prototypes

Three competing layouts for desktop reading. This directory is a throwaway visual study, separate from the running application. The production server does not route to these files.

Run from the repository root:

```sh
python3 -m http.server 8878 --bind 127.0.0.1 --directory app/prototypes
```

Open http://127.0.0.1:8878/ for the comparison or `reader.html?variant=A`, `B`, or `C` for a full prototype. The bottom bar switches layouts. Arrow keys also switch when focus is outside an interactive control.

| Prototype | Layout | Trade-off |
| --- | --- | --- |
| A, Outline | Library, document, and contents in a stable grid | Fast navigation; more controls remain visible |
| B, Focus | Document page, floating toolbar, library grid in a dialog | Most uninterrupted reading space; navigation takes an extra action |
| C, Study | Original paper beside an example overview | Easier source checking; less spare width for figures |

The default body type is Georgia at 20 px, 1.8 line height, with a 680 px text column. Georgia is used for sustained academic reading; app controls use the existing Avenir/system stack. At phone widths, initial article text is 18 px. Text size, sans-serif text, narrower/wider columns, and light/dark modes can be tested through Aa. System theme is respected. Preferences are kept only for the current page session.

The references suggest rounded, gridded controls with short eased transitions and panel expansion. These prototypes use 20 px panel corners, 10 px controls, pill-shaped floating controls, frosted borders, and opacity/transform transitions. No ambient animation runs over the article. Reduced motion and reduced transparency fallbacks are included. This is web glassmorphism, not native Apple Liquid Glass.

## Current app audit

The app uses Avenir controls, Georgia headings, a rust accent, cream backgrounds, small corner radii, a persistent 280 px library rail, and an import form above the paper. Overview, Paper, and Chat are the existing view names. Original content appears in a bordered iframe below the header and section selector. The inset reader and persistent import form spend vertical space before the text begins.

The prototypes retain the name, bookmark motif, view names, paper metadata, library access, settings, and export choices. They explore a new cool neutral palette and reading layout. No existing app file, route, API, conversion, or delivery behavior is changed by the prototype.

## Content and interaction boundary

- `paper.html`, `paper.json`, and `assets/reader/` derive from the local retained conversion at `.verification/converted/2406.15927v1`. All chapter bodies remain in order. Cross-chapter links become anchors in the combined reading document. Figures and MathML are retained. Source punctuation and wording are preserved even where they differ from the writing style used for new UI copy.
- The original title is *Semantic Entropy Probes: Robust and Cheap Hallucination Detection in LLMs*, arXiv:2406.15927v1. These are the authors' original claims, not new research findings from the prototype.
- The overview and one chat answer were written as labeled design examples. They are not output from the app's overview pipeline. Other library entries are sample titles.
- Imports validate a link and simulate progress. Export and delivery buttons show preview feedback. No API provider, database, Mail, or real library is connected.
- `assets/outline.png`, `focus.png`, and `study.png` are screenshots of the actual prototypes, captured at 1440 by 1000 CSS pixels.

These prototypes answer which layout the user prefers. A chosen direction still needs integration with the real app, including the sandboxed document reader and its source-link contracts.

## Observed verification

Checked the rendered prototypes at 1440 by 1000, 1024 by 768, and 390 by 844 CSS pixels. Inspected light and dark themes, the library grid and empty search state, appearance controls, original-paper section navigation, the prepared chat answer and its source jump, invalid import input and simulated completion, and simulated delivery feedback. The inspected layouts had no page-level horizontal overflow. Reduced-motion emulation reported zero active animations.

Browser inspection found 93 MathML elements and no unresolved internal paper anchors. JavaScript syntax and whitespace checks passed. The local browser reported LCP 72 ms and CLS 0 for one load; this is a local preview observation, not a production performance guarantee or a Lighthouse audit. Full application tests and live-provider or Kindle delivery checks are outside this read-only design study.
