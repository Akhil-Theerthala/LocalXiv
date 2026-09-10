# Compact Overview implementation plan

Reduce oversized Overview images and make the paper's contribution clear before the detailed mechanism. Use the existing renderer, figure viewer, and evidence review. No new dependencies or live provider calls.

- [x] Bound Overview previews to 70% of viewport height, capped at 720px, with proportional scaling and existing enlargement controls. Leave Blog and Paper sizing intact.
- [x] Give newly generated Overviews a compact header and a 960px total height budget at 960px width. Measure labels at a 640px square reading size. Return excess height as a repairable review issue.
- [x] Replace mandatory vertical architecture panels with a focused example and compact integration context. Lead with the contribution, retain supported findings and limitations, and limit Overview content to 180 visible words. Keep Blog's existing 260-word figure budget.
- [x] Exercise oversized rejection, smaller-label rejection, successful agent repair, exports and existing UI behavior with offline tests. Render a local example and inspect desktop and 320px layouts. Record what was actually verified.

Files: `app/static/reader-layout.css`, `papers/agent_overviews.py`, `papers/html_figures.py`, `papers/HTMLSnapshot.swift`, `papers/diagram-style.md`, and their existing tests. Saved generations remain readable; regeneration is needed for new composition rules. Installation and publication are separate actions.

Verification: 30 offline agent, markup, Overview and export tests passed. After adding preservation of older 260-word Blog references, the full agent test module passed again. Both native-renderer tests passed using a fresh Swift build, covering compact acceptance, total height across multiple SVGs, label scaling and unchanged Blog bounds. The Node UI suite passed. An isolated browser using the real app HTML/CSS/JS and synthetic paper data passed at widths 1440, 1024, 640 and 320: no horizontal overflow, bounded preview, working enlarge/actual-size/Escape controls, unchanged Blog image sizing and functioning Paper tab. Desktop and 320px screenshots were inspected; the final frame now fits the displayed image. Native WebKit and Chromium required execution outside the sandbox. No live model generation, installed-app update or publication was performed, so the revised storytelling prompt still needs evaluation on real generated papers.
