# Blog sections plan (2026-10-08)

Build [the Blog sections design](../specs/2026-10-08-blog-sections-design.md) on the branch `blog-sections`. Commit only the files a task names: the working tree holds the user's own changes.

## Tasks

1. **Thread-safe coordinator.** Take the request ordinal and record each event under one `threading.Lock` in `Coordinator`. Add `outline`, `section`, and `join` to `PROGRESS_STAGES`. Done when two threads that call `call_with_event` at once write two numbered responses.
2. **Length as a target.** Remove `Article.shorten` and its callers, `BLOG_WORD_LIMITS`, the word check in `_blog_validate_text`, and the ceiling sentence in `BlogRules`. The prompt states the requested length. Done when no code reads a word ceiling.
3. **Outline.** Add `BLOG_OUTLINE_SCHEMA`, `validate_blog_outline`, and `OUTLINE_PROMPT`. The outline stage replaces `BlogWorkflow.author` and keeps the narrative revision. Done when an outline with a figure no section names, or a term owned by an unknown section, gets a correction that names it.
4. **Parallel sections and figures.** Add `SECTION_PROMPT` and `BlogWorkflow.write_sections`: one pool of `BLOG_WORKERS` workers takes every section request, then every figure. The application writes each heading and checks each body: known citations, and the section's marker exactly when it has a figure. A failed section gets one more request. State changes happen in the main thread. A `Cancelled` in a worker cancels the pending futures and propagates. Done when a test with `BLOG_WORKERS = 1` produces the article in outline order.
5. **Join.** Add the join task to `Article` and call it after assembly. Done when a test sees the join request and its edit in the article.
6. **Review scope.** Pass the outline in the review request and redefine `missing_explanation` in `REVIEW_PROMPT`. Done when the review request carries the outline.
7. **Tests, docs, live run.** Update `tests/test_blog_workflow.py` for the new stages. Update `CONTEXT.md` (Outline, Blog figure brief). Run `uvx ruff check .` and compare it with the 21 errors on `main`. Run AI Control with haiku-5.5 and report the join edits and the `missing_explanation` count in verdict 0.

Merge with `git merge --no-ff blog-sections`.
