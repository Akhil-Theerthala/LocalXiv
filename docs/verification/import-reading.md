# Prepare paper understanding after import

Implemented in the source checkout on 2026-09-10. No installed app rebuild or
live provider call was performed for this scheduling change.

After conversion and saving the paper, import queues a `reading` job when the
paper has retained passages and the user has configured a model and stored API
key. This is independent of `auto_summary`. If automatic overview generation is
enabled, its bento job follows the reading job on the existing single worker.

Import finishes before the optional AI work. Reading failure cannot invalidate
the saved paper or change its completed import status. Reading has its own job
progress and usage accounting. Queued reading rechecks authentication before
calling the provider.

`prepare_reading` is shared by this import follow-up and overview generation.
An overview reuses a matching saved reading, including figure notes. If the paper
was imported without AI, or the reading failed or became stale, the requested
overview prepares it first. Saving credentials does not queue a library-wide
backfill. Existing cache invalidation rules remain in effect.

21 reading/bento tests and the UI checks passed. New checks cover credentials
present/absent, model absent, automatic overview on/off, queue order, reuse at
overview time, late authentication, removed credentials and failure preservation.
