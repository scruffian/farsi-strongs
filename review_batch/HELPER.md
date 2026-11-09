# Instructions for a review helper

You are reviewing the Strong's number tags of the Persian (NMV) Bible for one chunk, acting
exactly as a chat assistant would when a user pastes the review prompt plus the chunk file.
Your task message gives CHUNK (a path inside `review_chunks/`, e.g.
`01_Genesis/01_Genesis_002.001-002.025.md`). Below, NAME is its file name
(`01_Genesis_002.001-002.025.md`), BASE is NAME without `.md`, and REPO is
`/home/user/farsi-strongs`. Run all commands from REPO.

Usage limits can cut you off at any moment, so you save your work verse by verse in a draft.
The next helper for this chunk then continues where you stopped instead of starting again.

1. Read the review prompt in full. It is the text inside the ```` ```text ```` block under
   "## Prompt" at the end of REPO/review_chunks/README.md. Follow it exactly; it is your
   instruction set.
2. Run `python3 review_batch/batch.py progress NAME`. It says which verses are already in the
   draft (from an earlier helper that was cut off) and where to start. Don't redo those verses.
3. Read the chunk file REPO/review_chunks/CHUNK (the "attached file" the prompt refers to):
   the worked examples, then the verses you still have to do (you may skip the entries of
   verses already in the draft), and the neighbouring verses if you need them.
4. Work through your verses in order, entry by entry, using your knowledge of Biblical Hebrew
   or Koine Greek and Persian. In the New Testament, original words marked "variant reading"
   come from other Greek texts that the Persian often follows. Be careful and conservative:
   only change a tag where you are confident the current one is wrong or missing.
5. Save as you go: after every verse (or every two or three short ones), append one line per
   verse to REPO/review_batch/drafts/BASE.jsonl, e.g. with
   `cat >> review_batch/drafts/BASE.jsonl <<'EOF'` … `EOF`:
   - a changed verse: the whole corrected verse, exactly as in the prompt's reply format,
     `{"ref": "Genesis 1:8", "entries": [["خدا", "H430"], ...]}`;
   - a verse that needs no change: `{"ref": "Genesis 1:9", "unchanged": true}`.

   Each line is valid JSON on one line, with the Persian copied exactly from the chunk file
   (don't retype or normalise it). Append your notes (doubtful cases, numbers taken from a
   neighbouring verse) the same way, as `- ` list items, to
   REPO/review_batch/drafts/BASE.notes.md. Never rewrite lines another helper saved.
6. When every verse is in the draft, run `python3 review_batch/batch.py assemble NAME`. It
   writes the reply to review_replies/pending/NAME, checks it and, if the check passes, marks it
   complete. If it lists problems (invalid JSON, Persian words not matching, numbers not in the
   verse or its neighbours, tagged punctuation, ...), fix those lines in the draft and run
   assemble again until it reports "complete". Only fix the problems; don't change your
   judgements just to make it pass. Don't read the long .check.md report; assemble prints what
   matters.
7. For temporary files use only `/tmp/review_batch/BASE/`. Other helpers are working at the
   same time: never edit, move or delete any file in the repository except your own draft
   files. Don't write the reply or its completion line yourself; assemble does that. Don't
   read anything in review_replies/superseded/. Don't commit, push or change anything else in
   either repository.

Finish with one line only: the line assemble printed, e.g.
`NAME: changed X of Y verses, check OK, complete.`
