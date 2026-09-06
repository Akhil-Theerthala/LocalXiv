# Structured and illustrated overviews

Verified on 2026-09-06. Test responses are deterministic fixtures, not live provider output or measured research findings. The user's existing library and API key were not used to generate test articles.

The pipeline reads every retained section, plans an article, drafts it with explicit figure briefs, checks its prose against evidence notes, then designs and reviews each figure against its original supporting passages. Excalidrawer 0.5.12 renders local PNG, SVG and editable scenes. Figure review is a text-model evidence check, not an independent vision-model inspection. Current layouts are short sequences and paired conceptual comparisons.

- Python: `python3 -m unittest tests.test_ai tests.test_overview tests.test_app tests.test_desktop_launcher -q`, 26 tests, 25 passed and one opt-in Keychain smoke test skipped.
- Browser logic: `node tests/test_app_ui.js`, passed. Includes grouped citation cleanup, chat citation preservation, figure display, editable download links and rejection of external or traversing image paths.
- Real renderer: both sequence and comparison fixtures produced PNG/SVG/Excalidraw artifacts with no renderer warnings. Separate generations use different asset directories.
- Real export integration: overview and combined paper/overview exports passed validation in Kindle and semantic profiles. Figure PNGs are embedded; passage IDs and unresolved figure placeholders are absent. Original paper EPUB bytes remain unchanged.
- Failure and cancellation: an unsuccessful figure render or cancelled overview job retains the previously saved generation.
- Visual inspection: comparison PNG inspected at full size; rendered browser article inspected at 1265 px viewport width. Headings, image, caption and editable link are visible. Codes are absent from the article. The diagram's panels, focal color, takeaway and simplification note are readable at article width.
- Icon: existing rust bookmark and cream P enclosed in a cream squircle. Generated all macOS icon resolutions with librsvg and Apple's iconutil. Rebuild with `app/macos/build-icon.sh`.
- Dependency audit: npm install reported zero known vulnerabilities.

Artifacts: [comparison PNG](overview-workflow/comparison.png), [editable comparison](overview-workflow/comparison.excalidraw), [app icon](overview-workflow/app-icon.png).

Existing saved overviews receive presentation/export citation cleanup without regeneration. The new article outline and figures require explicit regeneration. Runtime model quality across providers and physical Kindle display have not been tested for this revision.

Installation: updated `~/Applications/Papers to Kindle.app`, verified installed runtime files and AppIcon.icns byte-for-byte, checked there were no active jobs, then restarted the idle service. Opened the native application and observed both saved papers and the existing Gemini overview with passage codes removed. No regeneration was triggered in the real library.
