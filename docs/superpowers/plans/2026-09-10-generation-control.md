# Generation control implementation plan

Implement the approved generation-process improvements with the existing smolagents author and local renderer. Keep saved generations and native provider reasoning compatible. Do not make live provider calls or install/publish the app.

- [x] Give the application ownership of plan submission, candidate validation/rendering, evidence review, repair, and completion. Provider failures leave the author loop and retain the latest draft. Bind reviews to candidate digests; stop repeated identical failures without a global request cap.
- [x] Introduce an evidence-linked explanation plan using the existing question, contribution, finding and limitation concepts. Carry relationships and the visual focus into authoring and review. Keep one local parallel-architecture layout as a separate prototype; generation continues using the existing SVG renderer.
- [x] Start a fresh author context for each repair. Keep native reasoning intact within each context. Return short validation errors rather than rejected candidate dumps. Append per-call timing, status, input size and usage, including failed calls; omit repeated request bodies.
- [x] Preserve bounded, redacted provider error details and cache/reasoning usage. Use explicit low DeepSeek effort for authoring; leave evidence review at provider default. Replace contradictory layout snippets with supported guidance.
- [x] Exercise terminal HTTP failures, automatic completion, stale approval, cancellation, duplicate repairs, independent contexts, native reasoning, old reference/export compatibility, safe diagnostics, and the architecture renderer offline. Record native-render and integration results.
