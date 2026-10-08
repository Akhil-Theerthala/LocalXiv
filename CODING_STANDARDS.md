# Coding standards

Rules for code in LocalXiv. Each rule gives its reason.

## Write the simplest change that works

Invoke the `ponytail` skill before you write, change, review, or design code, and before you choose a dependency. The skill holds the full rule set, so this file does not repeat it.

## Run ruff before you commit Python

`ruff.toml` sets the lint style. No CI step or hook runs ruff, so run `uvx ruff check .` before you commit Python and fix what it reports. This file does not restate the rules, because a copy goes stale when `ruff.toml` changes.

## Write tests as "Check changes" tells you

Follow "Check changes" in `docs/development.md`. It says what kind of test to write, where to put it, and how to run it. Git ignores `tests/` by the user's choice, so `git ls-files` and ripgrep do not show the tests that exist.

## Merge with `--no-ff`

Merge a branch into `main` with `git merge --no-ff <branch>`. Then each branch leaves one merge commit on `main`, which you can read, revert, or bisect past as one unit. Always type the flag. The `merge.ff = false` setting is in this clone's local git config. Worktrees share it, but a fresh clone fast-forwards without it.

## Record removals in `docs/cleanup.md`

If a review, an audit, or another task finds a set of items to remove, create `docs/cleanup.md` and list every item there. Start the file with this header:

```markdown
# Cleanup

Temporary checklist of things to remove. Delete this file when every item below is done.
```

The delete rule lives in that header because only a session that has opened the file acts on it. Git ignores `docs/cleanup.md`, so the checklist stays local.
