# Review chunks

These files split the whole NMV Strong's tagging into pieces small enough to review one at a
time in a chat with Claude (or another assistant that reads Persian, Hebrew and Greek). Each
chunk covers about 25 verses, usually whole chapters, and is very roughly 15,000–25,000 tokens.

They are generated from:

- `public/bibles/NMV_strongs.json` in sync.bible (the current tags)
- `public/bibles/accented.json` in sync.bible (the Hebrew and Greek)
- `public/data/strongsDictionary.json` in sync.bible (dictionary forms and English meanings)
- `retag/locked_verses.txt` here (verses already reviewed by hand are left out)

[INDEX.md](INDEX.md) lists every chunk in Bible order.

## What a chunk contains

1. A header naming the passage, plus any verses in it that were left out because they are
   already reviewed by hand or have no original text.
2. **Worked examples:** two Old Testament or one New Testament verse already reviewed by hand,
   showing the tagging conventions.
3. **Verses to review.** For each verse:
   - the original and the Persian as running text;
   - the original words `o1, o2, …`, each with its Strong's number(s), dictionary form,
     a short English meaning and morphology code. Hebrew words split into parts, e.g.
     `וַ/יְהִי = Hc "and" + H1961 הָיָה "to exist, i.e. be or become…"`;
   - the Persian entries `p1, p2, …` exactly as in NMV_strongs.json, with their current tags.
4. **Neighbouring verses (context only):** the original words of verses just before or after
   the reviewed ones that aren't in the chunk themselves, e.g. at the chunk's edges or next to
   a hand-reviewed verse. Persian and Hebrew/Greek verse divisions sometimes differ: the
   Greek of Revelation 12:18 is at the start of Persian Revelation 13:1. So a Persian word
   may take its number from the verse immediately before or after. `--window` sets how many
   verses either side count (default 1); use the same value for `review_replies.py`.

Hebrew is shown with vowel points but without cantillation marks, to keep chunks smaller.

In the New Testament, the NMV follows a text close to NA27/UBS4 (plus bracketed Textus
Receptus verses) where `accented.json` has Tischendorf. Greek words from those readings are
merged into the verse, shown in ⟨ ⟩ in the running text and marked `(variant reading, WHNU)` or
`(variant reading, TR)` in the word list. Their numbers can be used like any other in the
verse. `--no-variants` leaves them out.

## Reviewing a chunk

1. Start a **new chat** for each chunk, so earlier chunks don't crowd the conversation.
2. Attach the chunk's `.md` file (or paste its contents), then paste the prompt below.
3. Save the whole reply as a file in `review_replies/pending/`, named after the chunk.
4. Run `python review_replies.py check`, read the report it writes, fix or delete any lines
   you disagree with, then move the reply into `review_replies/approved/`. The model makes
   mistakes too, so check every change against the original, especially anything it
   listed as "unsure".
5. Run `python review_replies.py apply` to write the approved verses into sync.bible and lock
   them. Then commit both repositories.

The full steps are in [review_replies/README.md](../review_replies/README.md). Changes can also
be made directly in the sync.bible app (alt/ctrl/cmd-click a Persian word, then click the
original word); those verses are locked automatically on the next `python -m retag run`.

## Regenerating

After `python -m retag run`, or after adding verses to `locked_verses.txt`, regenerate the
chunks so they show the latest tags and leave out newly reviewed verses:

```sh
python make_review_chunks.py --sync-bible ../sync.bible
```

`--max-verses` (default 25) and `--max-chars` (default 50000) control the chunk size. Use smaller
values if replies get cut off or the model starts skipping verses.

Regenerating replaces every chunk file. Chunk names include their verse range
(`01_Genesis_002.001-002.025.md`), so names change when reviewed verses drop out.

## Prompt

Copy everything inside the box and paste it with the chunk.

````text
I'm reviewing the Strong's number tags on the NMV Persian Bible for sync.bible. The attached file has, for each verse, the Hebrew or Greek words (o1, o2, …) with their Strong's numbers, dictionary form, English meaning and morphology, and the Persian entries (p1, p2, …) with their current tags. The worked examples at the top were reviewed by hand: follow their conventions.

For every verse under "Verses to review", check each Persian entry and correct its tags using these rules:

1. A Persian word that translates an original word gets that word's Strong's number. Use the numbers listed for that verse's original words, including words marked "variant reading": these come from other Greek texts, which the Persian often follows where the main Greek text differs. Only where the Persian verse division differs from the original (the Persian includes words that belong to the original verse just before or after) may you use a number from that neighbouring verse, i.e. the verse before or after in the file, or under "Neighbouring verses". List every such case in your notes.
2. A Persian word added in translation, with no original word behind it, has no tag. Punctuation is never tagged.
3. If one Persian word translates several original words, or several parts of one Hebrew word, give it all their numbers separated by spaces, in original word order (e.g. "Hc H3068").
4. If adjacent Persian words together translate one original word (e.g. a compound verb such as تسلی می‌دهد), group them into one entry: join their text with a single space and give the group one tag. Never group across punctuation.
5. If non-adjacent Persian words translate the same original word, tag each of them with the same number.
6. Hebrew prefixes have their own numbers: Hc (ו "and"), Hl (ל "to, for"), Hb (ב "in"), Hm (מ "from"), Hk (כ "like"), Hs (ש "which"). Tag the Persian word that translates them (و، به، برای، در، از، مانند …). Hd (the article ה) is usually not translated in Persian; tag it only if a Persian word really renders it.
7. Tag را as H853 only when it marks the object where the verse has אֵת (H853); otherwise leave it untagged. Persian pronouns or suffixes that translate a Hebrew or Greek pronoun suffix (which has no number) stay untagged.
8. Tag the Greek article G3588 only where a Persian word renders it (e.g. به for a dative article).
9. Don't change, reorder or respell the Persian text. The only allowed text changes are joining adjacent entries into a group (rule 4) or splitting a wrongly grouped entry back into its separate words.

Check every verse, however long, and every entry in it.

Reply with:

1. One ```jsonl code block containing a line for each verse you changed, giving the whole corrected verse:
{"ref": "Genesis 1:8", "entries": [["خدا", "H430"], ["فَلَک", "H7549"], ["را"], ["’آسمان‘", "H8064"], ["نامید", "H7121"], ["."]]}
An untagged entry is ["word"] and a tagged one is ["word", "numbers"]. Leave out verses that need no change.
2. After the code block, a short list of verses where you were unsure, each with the entry numbers and the reason, and of every number you took from a neighbouring verse.
````
