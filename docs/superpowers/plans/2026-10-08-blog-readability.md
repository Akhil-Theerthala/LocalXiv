# Blog readability plan (2026-10-08)

Build [the Blog readability design](../specs/2026-10-08-blog-readability-design.md) on the branch `blog-readability`. Live checks use the app's provider and model, `anthropic/claude-haiku-5.5` on OpenRouter.

## Tasks

1. **Figure counts.** Put the range for each length in one table in `papers/explanation.py`. `validate_blog_draft` rejects a figure count outside the range, with a message that names the range. `BLOG_DRAFT_SCHEMA` and `AUTHOR_RESPONSE_SCHEMA` allow up to six briefs. Done when a medium draft with one brief gets a correction that asks for two to four, and the Blog tests pass.
2. **Review severity.** Add the error and advice sets to `papers/blog_prompts.py`. `BlogWorkflow.review_loop` answers every finding in the first correction and errors only after it, ships when no error is open, and records open advice in the provenance as `open_advice`. After two prose corrections with errors open, one `CleanupRequest` deletes the sentences those errors quote, and the Blog ships. Done when a test with a reviewer that never approves ships a Blog, and a test with an error that survives two corrections ships the Blog without the quoted sentence.
3. **Tone levels.** Replace `LANGUAGES` in `papers/overview.py` with the STE rule list and the three levels of the design. Done when each level's text names its share of sentences and what the other sentences may do.
4. **Blog prompts.** Rewrite `SHARED_RULES`, `SELECTION_PROMPT`, `NARRATIVE_PROMPT`, `AUTHORING`, `REVIEW_PROMPT`, `CLEANUP_PROMPT`, `BRIEF_CORRECTION_PROMPT`, `PANEL_WRAPPER`, `NARRATIVE_TIPS`, and `WRITING_TIPS` with the `writing-for-agents` rules. The author prompt carries the figure range for the length, the question headings, the running example, and figure placement. The review prompt asks for a severity through the category. Bump `PROMPT_REVISION`. Done when no rule appears in two prompts and every prompt states its target behaviour positively.
5. **Overview prompts.** Rewrite `DIGEST_INSTRUCTION` and `SCENE_WRAPPER` the same way. Bump the Overview `PROMPT_REVISION`. Done when both examples still validate and the Overview tests pass.
6. **Live check.** Generate the AI Control Overview and Blog with haiku-5.5 through the workflows, outside the app server. Done when both finish, and the report states the number of figures, the correction rounds, the open advice, and the run directories.
7. **Docs and memory.** Update the Blog entries in `CONTEXT.md` and the memory index.

Merge with `git merge --no-ff blog-readability` when the tests pass and the live check is reported.
