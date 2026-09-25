# Skills

Invoke with the Skill tool before acting. The skill's instructions govern from there.

- `ponytail` — every coding task: writing, changing, reviewing, or designing code, and choosing a dependency.
- `pstack:unslop` — every response and every text you produce, including comments and commit messages.
- `pstack:technical-writing` and `writing-for-agents` — every writing task: README, docs, plans, specs, ADRs, this file, skills.
- `pstack:how` — asked how a subsystem works or where code belongs; before changing code you have not read this session.
- `pstack:why` — asked why something is built this way; before removing or changing a behavior whose reason is not in the code.

# Response Considerations: 
- Talk in ASD-STE100 Simplified Technical English and use ubiquitous language from CONTEXT.md

# Git

Merge a branch with `git merge --no-ff` so every branch leaves one merge commit on `main`. Never fast-forward.

# Tests

Write every test under `tests/`.

# Cleanup

`docs/cleanup.md` is a temporary checklist of things to remove. Create it when an audit or another task finds a set of items to remove, and list every item there.
If `docs/cleanup.md` exists, stop before any other work and ask the user whether to run that cleanup first.
Delete `docs/cleanup.md` as soon as its items are done.
