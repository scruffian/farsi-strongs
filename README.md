# farsi-strongs

Tools for tagging the NMV Persian (Farsi) Bible with Strong's numbers for
[sync.bible](https://github.com/borealsole/sync.bible). Each Persian word gets the Strong's
numbers of the Hebrew or Greek words it translates. The result is sync.bible's
`public/bibles/NMV_strongs.json`.

The current approach is the `retag` tool described below. It aligns the Persian directly
to the original languages in sync.bible's `accented.json`. It keeps every verse corrected
by hand, and it learns from those corrections. The original 2022 approach (`word_aligner.py`)
aligned the Persian to the ESV with simalign and took the ESV's Strong's numbers. Its output
is kept in `outputs/NMV_ESV_strongs.json` and is used as a starting point by `retag`.

Technical details of the method are in [retag/README.md](retag/README.md).

## Running the alignment

You need Python 3.10+ and a checkout of sync.bible next to this repository:

```
parent/
├── farsi-strongs/   (this repository)
└── sync.bible/
```

1. **Install the dependencies** (numpy, pandas, pyarrow, scikit-learn, eflomal):

   ```sh
   cd farsi-strongs
   pip install -r retag/requirements.txt
   ```

2. **Update both repositories** so the latest hand corrections are included:

   ```sh
   git -C ../sync.bible pull
   git pull
   ```

3. **Optionally, check the accuracy** against the hand-corrected verses (about 3 minutes):

   ```sh
   python -m retag evaluate --sync-bible ../sync.bible
   ```

4. **Re-tag** (about 3 minutes). This rewrites `../sync.bible/public/bibles/NMV_strongs.json`:

   ```sh
   python -m retag run --sync-bible ../sync.bible
   ```

   Use `--dry-run` to see what would happen without writing anything, or `--output PATH`
   to write somewhere else. Use `--threshold 0.6` (default `0.45`) for fewer, safer tags.

5. **Commit in both repositories.** Future runs need both to find new hand edits:
   - in sync.bible: `public/bibles/NMV_strongs.json`
   - here: `outputs/NMV_strongs_machine.json` (a copy of what was written) and
     `retag/locked_verses.txt` (new hand-corrected verses are added to it automatically).

   If only one side is committed, the next run stops with an error instead of treating
   thousands of verses as hand-edited. Fix it by copying the file across, or by restoring
   the matching `outputs/NMV_strongs_machine.json`.

To run the unit tests: `python -m unittest retag.test_tagger`.

## What the tagging produces

| Case | Entry in NMV_strongs.json |
| --- | --- |
| Persian word not in the original (added in translation) | `["خود"]` (untagged) |
| One Persian word for one original word | `["زمین", "H776"]` |
| One Persian word for several original words | `["خداوندمان", "G2962 G2249"]` |
| Adjacent Persian words for one original word | `["ساکن گشتید", "H3427"]` (one grouped entry) |
| Non-adjacent Persian words for one original word | each word tagged with the same number |

Hebrew prefixes are tagged too: `Hc` for و, `Hl` for به/برای, `Hb` for در, `Hm` for از,
`Hk` for همچون. را is tagged as the object marker את (`H853`).

## Accuracy

The results come from 5-fold cross-validation on the 44 hand-corrected verses. The model
is trained on four fifths of the verses and scored on the fifth it hasn't seen, five times
over. Scores are per (Persian word, Strong's number) pair:

- **Precision** is the share of tags given that are correct.
- **Recall** is the share of correct tags that were given.
- **F1** combines the two.

| | Precision | Recall | F1 |
| --- | --- | --- | --- |
| Tags before hand correction (2022 simalign via ESV) | 0.874 | 0.631 | 0.733 |
| `retag` | 0.791 | 0.796 | 0.793 |

By testament:

| | Old tagging F1 | `retag` F1 |
| --- | --- | --- |
| Hebrew (Deuteronomy 26) | 0.66 | ~0.82 |
| Greek (Philemon 1:1–13) | ~0.77 | ~0.77 |

Things to bear in mind:

- 44 verses is a small test set, mostly from Deuteronomy 26 and Philemon.
- The test set favours the old tags, because editors kept the old tags they accepted.
- `retag` finds many more of the right tags (Hebrew prefixes, את, both halves of compound
  verbs). It also adds some wrong ones; a higher `--threshold` trades recall for precision.
- In Greek it only matches the old tagging so far. More corrected New Testament verses are
  the best way to improve it (see below).
- Scores vary by about ±0.01 between runs, because eflomal is a random sampler.

Run `python -m retag evaluate` after adding corrections to see the current figures.

## Growing the gold standard: `retag/locked_verses.txt`

Every verse in `retag/locked_verses.txt` is treated as correct:

- it is **copied unchanged** from sync.bible on every run (never re-tagged), and
- it is **training data**. The model that decides which tags to keep is retrained on these
  verses each run, and they are the test set for `evaluate`.

The more verses are carefully checked and listed, the better the rest of the Bible is tagged.

### Verses you corrected in sync.bible

Nothing to do. Retag words in the sync.bible app (alt/ctrl/cmd-click a Persian word, then
click the Hebrew/Greek word it translates) and commit `NMV_strongs.json`. On the next run
every verse that differs from the last machine output is detected. It is added to
`locked_verses.txt` with a `# manual edit detected <date>` note.

### Verses you checked that were already right

These are **not** detected automatically, because nothing changed in them. Add them to
`retag/locked_verses.txt` by hand, one reference per line:

```
Philemon 1:14            # a single verse
Philemon 1:15-25         # a range within a chapter
Deuteronomy 27           # a whole chapter
John 3:16  # reviewed by <name> 2026-10
```

- Use the book names as they appear in NMV_strongs.json, e.g. `Song of Solomon`,
  `Revelation of John`, `I Corinthians`.
- Chapter and verse numbers start at 1.
- Anything after `#` is a comment.
- A misspelt reference makes the run stop and report the line, so nothing is silently lost.

### Guidelines for checking a verse

A locked verse teaches the model exactly what it contains, so only lock a verse once
*every* word in it has been checked:

- each word that translates an original word has that word's Strong's number, or numbers;
- words added in translation have no tag;
- words that together translate one original word all carry its number. Adjacent ones
  are grouped automatically on the next run.

A verse only partly checked (one word fixed, the rest left as the machine tagged it) still
gets locked when it is edited in the app. If you know a verse is only partly checked, finish
checking it before the next run, or remove its line from `locked_verses.txt`. It will then be
re-tagged, and your fix is lost unless you redo it.

To un-lock a verse, delete its line from `locked_verses.txt`. It must also match the last
machine output, otherwise it is detected as edited again; revert its hand edit in sync.bible
if needed.

### Suggested routine

1. Check a chapter or passage in sync.bible, correcting tags in the app.
2. Commit `NMV_strongs.json` in sync.bible.
3. Add any checked verses that needed no change to `locked_verses.txt`.
4. `python -m retag evaluate --sync-bible ../sync.bible` to see the new accuracy.
5. `python -m retag run --sync-bible ../sync.bible`, then commit in both repositories.

A mix of books helps most, especially New Testament passages and Old Testament poetry,
which the current 44 verses barely cover.
