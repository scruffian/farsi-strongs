# Review replies

Chat replies to the [review chunks](../review_chunks/README.md) are saved here. Nothing in a
reply reaches sync.bible until a person has checked it and moved it into `approved/`.

```
review_replies/
├── pending/    replies saved from the chat, waiting to be checked
├── approved/   replies a person has checked and accepted
├── applied/    replies already written into sync.bible (kept as a record)
└── superseded/ old replies replaced by a newer review of the same chunk (kept as a record)
```

`superseded/` holds the replies made before the Greek variant readings were added (see
[retag/README.md](../retag/README.md#greek-variant-readings-variantspy)). Those chunks were
reviewed again, and the new replies are in `pending/`. Nothing reads `superseded/`.

## Workflow

1. **Save the reply.** Copy the whole chat reply into a new text file in `pending/`. Name it
   after the chunk, e.g. `pending/01_Genesis_002.001-002.025.md`. Any extra text in the reply,
   such as the "unsure" notes, can stay: only lines that are verse JSON
   (`{"ref": …, "entries": …}`) are read.

2. **Check it:**

   ```sh
   python review_replies.py check --sync-bible ../sync.bible
   ```

   For each reply this writes a report beside it (`<reply>.check.md`) and prints a summary.
   Add reply file names at the end to check only those.
   The report lists:
   - **Problems** that would stop it being applied, such as:
     - invalid JSON;
     - Persian words that don't match the verse;
     - a Strong's number that is neither in that verse's original (including the Greek
       variant readings from `WHNU.json` and `TR.json`; see
       [retag/README.md](../retag/README.md#greek-variant-readings-variantspy)) nor in the
       verse immediately before or after it (`--window` widens this);
     - tagged punctuation, or a group that includes punctuation;
     - a verse already hand-reviewed;
     - the same verse proposed twice.
   - **Verses the reply doesn't actually change**, which are skipped.
   - **Each changed verse:** the original words with meanings, and a table of every Persian
     word with its current and proposed tags. Rows marked ✱ change, and changed tags show
     their meanings.
   - **Numbers from Greek variant readings,** labelled e.g. `(variant reading, WHNU)`.
   - **Numbers taken from a neighbouring verse,** for places where the Persian and original
     verse divisions differ. Each is labelled with its source verse (e.g. `(from Revelation
     of John 12:18)`), and that verse's original words are shown so you can check it.

3. **Do the human check.** Read each changed verse in the report against the original. In
   the reply file, delete any verse line you reject and edit any tags you want different.
   Then run `check` again until the report shows no problems and every change is one you agree
   with. A verse you approve here becomes part of the training set (the gold standard) for
   the retag model, so only approve verses whose every word you're happy with.

4. **Approve it.** Move the reply file (and its report, if you like) from `pending/` into
   `approved/`.

5. **Apply:**

   ```sh
   python review_replies.py apply --sync-bible ../sync.bible --dry-run   # optional preview
   python review_replies.py apply --sync-bible ../sync.bible
   ```

   This checks every approved reply again against the current sync.bible file. If anything is
   wrong, nothing is written. Otherwise it:
   - writes each changed verse into `../sync.bible/public/bibles/NMV_strongs.json`;
   - adds those verses to `retag/locked_verses.txt` (`# reviewed via chat reply, applied`);
   - moves the replies and their reports into `applied/`.

6. **Commit both repositories:**
   - sync.bible: `public/bibles/NMV_strongs.json`
   - here: `review_replies/`, `retag/locked_verses.txt`

   Then regenerate the review chunks (`python make_review_chunks.py`) so the applied verses
   drop out of them. Rerunning `python -m retag run` will also use the new gold verses to
   improve the rest of the tagging.

## Notes

- **Pending replies are used before they are checked.** `python -m retag run` puts every
  pending or approved reply line that passes `check` into NMV_strongs.json, in place of the
  machine tagging. They also train the model at reduced weight. They are not locked, so
  editing such a verse in the app still overrides the reply. Applying a checked reply locks
  it. Delete a reply you reject, and the next run goes back to machine tagging for its
  verses. See [retag/README.md](../retag/README.md#unchecked-chat-review-replies-repliespy).

- **Only changed verses are applied and locked.** Verses the chat left alone are not treated
  as checked. If you also checked those verses and they're right, add them to
  `retag/locked_verses.txt` by hand (see the main README).
- **A reply proposes whole verses,** so applying one replaces that verse's tags entirely,
  including any edits made in the app since the chunk was generated. The report always
  compares against the current sync.bible file, so check it after any such edits.
- **Already-locked verses can't be changed** through a reply. Edit those in the app instead.
