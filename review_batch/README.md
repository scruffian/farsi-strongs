# Batch review by helper agents

This folder drives the review of every chunk in [review_chunks/](../review_chunks/) by Claude
helper agents, working through them in Bible order. The batch is long and is regularly cut
off by usage limits, so all of its state is in the repository: it can be resumed at any time,
from any session.

- [HELPER.md](HELPER.md): the instructions each helper follows (the review prompt from
  `review_chunks/README.md`, plus where to save the reply and how to check it).
- `batch.py`: finds the next chunks, removes unfinished replies, and commits finished ones.

Replies go to `review_replies/pending/` as usual. They are used by `python -m retag run`
straight away (see [review_replies/README.md](../review_replies/README.md)), and can be
checked by a person at any time.

## Running or resuming the batch

Paste this into a Claude Code session that has farsi-strongs and sync.bible checked out next
to each other, on farsi-strongs' `review-chunks` branch:

> Continue the batch review: follow review_batch/README.md in farsi-strongs.

The session then does this:

1. **Update:** `git pull origin review-chunks` in farsi-strongs, and pull sync.bible's main.
   Install pyarrow if `python -c "import pyarrow"` fails (the check needs it).
2. **Salvage after an interruption** (with no helpers running):
   `python review_batch/batch.py commit` commits replies that were finished, then
   `python review_batch/batch.py salvage` keeps everything else that is usable: a reply that
   was fully written but whose helper was cut off before marking it complete is checked and
   marked complete if it passes; drafts of partly reviewed chunks are kept, so the next helper
   for that chunk continues after the last saved verse. Only replies that fail the check
   without a draft are deleted. Run commit again afterwards.
3. **Status:** `python review_batch/batch.py status`.
4. **Work in waves:** `python review_batch/batch.py next 8` lists the next chunks, partly
   reviewed ones first (add `--after <last chunk handed out>` while helpers are still running,
   so chunks they have not written anything for yet are not listed again). Start one helper
   agent per chunk (in the background), each with the task message
   `Follow /home/user/farsi-strongs/review_batch/HELPER.md exactly. CHUNK=<chunk>`.
   When helpers finish, run `python review_batch/batch.py commit` (it checks each finished
   reply again, makes sure it only contains verses of its own chunk, commits it and pushes),
   then start helpers for the next chunks, keeping about 8 running.
5. **Usage limit:** helpers that are cut off leave their draft (and sometimes a reply without
   the completion line). Nothing that was saved is lost. After the limit resets, start again
   from step 1.

How it tracks progress: a chunk is done when a reply file with the chunk's name is committed
in `review_replies/pending/`, `approved/` or `applied/`. Helpers don't write replies directly.
They append their verdict on each verse (changed: the corrected verse; unchanged:
`{"ref": ..., "unchanged": true}`) to `review_batch/drafts/<chunk>.jsonl` as they go, and notes
to `<chunk>.notes.md`. `batch.py progress <chunk>` tells a helper where to (re)start, and
`batch.py assemble <chunk>` turns a complete draft into the reply, runs the check and appends
`<!-- review complete -->` only if it passes. So a cut-off costs at most the verse being
worked on, and `commit` only takes finished replies. Drafts are not committed (they are
ignored by git and deleted once their reply is committed), so they only survive within the
same checkout.

Why not stop before the limit instead: a session can't see how much of its usage limit is
left, so it can't tell whether a helper will finish. Saving verse by verse makes that
unnecessary.

To keep `git status` (and session stop hooks) quiet while helpers are writing, you can add
`review_replies/pending/*` to `.git/info/exclude`. That only hides uncommitted replies;
`batch.py` still finds them, and committed replies are tracked as usual.

**Don't regenerate the chunks during the batch** (`make_review_chunks.py`, which also follows
`python -m retag run` in the usual routine). Chunk names include their verse ranges, and new
hand-locked verses can change them, so already reviewed chunks could be handed out again.
Retagging itself is fine at any time; regenerate the chunks once the batch is finished.
