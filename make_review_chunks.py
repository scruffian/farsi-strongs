'''Split NMV_strongs.json and the original language text into chunk files for review in a chat.

Each chunk holds a run of verses (whole chapters where they fit) with, for every verse:
the Hebrew/Greek words with their Strong's numbers, morphology and a short English gloss,
and the numbered Persian entries with their current tags. Verses already reviewed by hand
(retag/locked_verses.txt) and verses with no original text are left out.

    python make_review_chunks.py --sync-bible ../sync.bible

See review_chunks/README.md for how to use the chunks.'''
import argparse
import math
import os
import re
import shutil

from retag import data, manual, original, persian, variants

OUT_DIR = os.path.join(data.REPO, 'review_chunks')

BOOKS = [
    'Genesis', 'Exodus', 'Leviticus', 'Numbers', 'Deuteronomy', 'Joshua', 'Judges', 'Ruth',
    'I Samuel', 'II Samuel', 'I Kings', 'II Kings', 'I Chronicles', 'II Chronicles', 'Ezra',
    'Nehemiah', 'Esther', 'Job', 'Psalms', 'Proverbs', 'Ecclesiastes', 'Song of Solomon',
    'Isaiah', 'Jeremiah', 'Lamentations', 'Ezekiel', 'Daniel', 'Hosea', 'Joel', 'Amos',
    'Obadiah', 'Jonah', 'Micah', 'Nahum', 'Habakkuk', 'Zephaniah', 'Haggai', 'Zechariah',
    'Malachi',
    'Matthew', 'Mark', 'Luke', 'John', 'Acts', 'Romans', 'I Corinthians', 'II Corinthians',
    'Galatians', 'Ephesians', 'Philippians', 'Colossians', 'I Thessalonians',
    'II Thessalonians', 'I Timothy', 'II Timothy', 'Titus', 'Philemon', 'Hebrews', 'James',
    'I Peter', 'II Peter', 'I John', 'II John', 'III John', 'Jude', 'Revelation of John',
]
NEW_TESTAMENT = set(BOOKS[BOOKS.index('Matthew'):])

# Hand-reviewed verses shown at the top of each chunk as worked examples.
EXAMPLES = {
    'OT': ['Genesis 1:1', 'Deuteronomy 26:7'],
    'NT': ['Philemon 1:1'],
}


CANTILLATION = re.compile('[\u0591-\u05AF\u05BD\u05BF\u05C0\u05C3-\u05C6]')


def plain(text):
    '''Hebrew without cantillation marks (vowel points are kept).'''
    return CANTILLATION.sub('', text)


def gloss(lemma, dictionary, limit=50):
    '''Dictionary form and short English meaning of a Strong's number.'''
    entry = dictionary.get(lemma) or {}
    definition = (entry.get('strongs_def') or '').strip()
    renderings = (entry.get('kjv_def') or '').strip()
    # Greek definitions in the dictionary are often truncated; the renderings read better there.
    text = renderings if lemma.startswith('G') and renderings else definition or renderings
    text = re.sub(r'\[idiom\]|\[phrase\]|\bX\b|[{}]', '', text)
    text = re.sub(r'\s+', ' ', text).strip(' ,.;')
    if len(text) > limit:
        cut = text[:limit]
        cut = cut.rsplit(';', 1)[0] if ';' in cut else cut.rsplit(',', 1)[0] if ',' in cut else cut.rsplit(' ', 1)[0]
        text = cut.strip(' ,;(') + '…'
    form = plain(entry.get('lemma') or '')
    return f'{form} "{text}"' if form and lemma not in original.HEBREW_PREFIXES | {original.HEBREW_ARTICLE} else f'"{text}"'


def original_lines(verse, dictionary):
    lines = []
    for n, word in enumerate(verse, 1):
        if len(word) < 2 or not word[1]:
            lines.append(f'- o{n}: {plain(word[0])} (no Strong\'s number)')
            continue
        lemmas = word[1].split('/')
        parts = [f'{l} {gloss(l, dictionary)}' for l in lemmas]
        morph = f' [{word[2]}]' if len(word) > 2 and word[2] else ''
        source = f' (variant reading, {word[3]})' if variants.is_variant(word) else ''
        lines.append(f'- o{n}: {plain(word[0])} = ' + ' + '.join(parts) + morph + source)
    return lines


def original_text(verse):
    '''The original as running text, with words from variant readings in ⟨ ⟩.'''
    return ' '.join(f'⟨{plain(w[0])}⟩' if variants.is_variant(w) else plain(w[0]) for w in verse)


def persian_lines(verse, strip_markers=False):
    lines = []
    for n, entry in enumerate(verse, 1):
        tags = data.entry_tags(entry) or ''
        if strip_markers:
            tags = ' '.join(t for t in tags.split() if data.STRONGS_TAG.match(t))
        lines.append(f'- p{n}: {data.display(entry[0])}' + (f'  → {tags}' if tags else ''))
    return lines


def persian_text(verse):
    text = ''
    for token in data.verse_words(verse):
        text += ('' if not text or persian.is_punctuation(token) else ' ') + token
    return text


def verse_block(key, verse, original_verse, dictionary, heading='###', example=False):
    out = [f'{heading} {data.reference(key)}', '']
    out.append('Original: ' + original_text(original_verse))
    out.append('Persian: ' + persian_text(verse))
    out.append('')
    out.append('Original words:')
    out += original_lines(original_verse, dictionary)
    out.append('')
    out.append('Correct Persian tags (reviewed by hand):' if example else 'Persian entries and current tags:')
    out += persian_lines(verse, strip_markers=example)
    out.append('')
    return out


def split_evenly(keys, sizes, max_verses, max_chars):
    '''Split one chapter's verses into the fewest, roughly equal parts that fit.'''
    parts = max(math.ceil(len(keys) / max_verses), math.ceil(sum(sizes) / max_chars), 1)
    while True:
        bounds = [round(i * len(keys) / parts) for i in range(parts + 1)]
        groups = [keys[a:b] for a, b in zip(bounds, bounds[1:])]
        if all(sum(sizes[keys.index(k)] for k in g) <= max_chars for g in groups) or parts >= len(keys):
            return groups
        parts += 1


def plan_chunks(keys_by_chapter, sizes, max_verses, max_chars):
    '''Pack whole chapters of one book into chunks; split chapters that are too big.'''
    chunks, current, current_chars = [], [], 0
    for chapter_keys in keys_by_chapter:
        chapter_sizes = [sizes[k] for k in chapter_keys]
        if len(chapter_keys) > max_verses or sum(chapter_sizes) > max_chars:
            if current:
                chunks.append(current)
                current, current_chars = [], 0
            chunks += split_evenly(chapter_keys, chapter_sizes, max_verses, max_chars)
            continue
        if current and (len(current) + len(chapter_keys) > max_verses
                        or current_chars + sum(chapter_sizes) > max_chars):
            chunks.append(current)
            current, current_chars = [], 0
        current += chapter_keys
        current_chars += sum(chapter_sizes)
    if current:
        chunks.append(current)
    return chunks


def chunk_name(book_number, keys):
    (book, c1, v1), (_, c2, v2) = keys[0], keys[-1]
    return f'{book_number:02d}_{book.replace(" ", "_")}_{c1 + 1:03d}.{v1 + 1:03d}-{c2 + 1:03d}.{v2 + 1:03d}.md'


def compress_refs(keys):
    '''"Genesis 1:1-3, 1:5" style list of references.'''
    out, run = [], []
    for key in sorted(keys):
        if run and key[:2] == run[-1][:2] and key[2] == run[-1][2] + 1:
            run.append(key)
            continue
        if run:
            out.append(run)
        run = [key]
    if run:
        out.append(run)
    text = []
    for r in out:
        ref = data.reference(r[0])
        text.append(ref if len(r) == 1 else f'{ref}-{r[-1][2] + 1}')
    return ', '.join(text)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--sync-bible', default=os.path.join(data.REPO, '..', 'sync.bible'),
                        help='Path to a sync.bible checkout (default: ../sync.bible)')
    parser.add_argument('--max-verses', type=int, default=25, help='Most verses in one chunk')
    parser.add_argument('--max-chars', type=int, default=50000,
                        help='Most characters of verse data in one chunk (excluding the examples)')
    parser.add_argument('--window', type=int, default=1,
                        help='Neighbouring verses either side whose Strong\'s numbers may be used (default 1)')
    parser.add_argument('--no-variants', action='store_true',
                        help='Show accented.json alone, without the Greek variant readings from WHNU.json and TR.json')
    args = parser.parse_args()

    paths = data.sync_bible_paths(args.sync_bible)
    dictionary = data.load_json(os.path.join(args.sync_bible, 'public', 'data', 'strongsDictionary.json'))
    grid = data.load_token_grid()
    accented = variants.load_original(args.sync_bible, grid, variants=not args.no_variants)
    current = data.align_to_grid(data.load_bible(paths['nmv_strongs']), grid)
    missing = sorted(set(grid) - set(current))
    if missing:
        raise SystemExit(f'{len(missing)} verses of the NMV are missing from NMV_strongs.json '
                         f'(e.g. {data.reference(missing[0])}). Run python -m retag run first.')
    locked = manual.read_locked(grid)
    order = original.verse_order(accented)

    def original_verse(key):
        book, ci, vi = key
        try:
            return accented[book][ci][vi]
        except (KeyError, IndexError):
            return []

    examples = {}
    for testament, refs in EXAMPLES.items():
        lines = ['## Worked examples (already reviewed by hand; follow these conventions)', '']
        for ref in refs:
            key = data.parse_references(ref, grid)[0]
            lines += verse_block(key, current[key], original_verse(key), dictionary, example=True)
        examples[testament] = lines

    if os.path.isdir(OUT_DIR):
        for name in os.listdir(OUT_DIR):
            path = os.path.join(OUT_DIR, name)
            if os.path.isdir(path):
                shutil.rmtree(path)
    os.makedirs(OUT_DIR, exist_ok=True)

    index = ['# Review chunks', '',
             'Generated by `make_review_chunks.py`. See README.md for how to use them.', '',
             '| Chunk | Verses |', '| --- | --- |']
    total_chunks = total_verses = 0
    for book_number, book in enumerate(BOOKS, 1):
        book_keys = sorted(k for k in grid if k[0] == book)
        skipped_locked = [k for k in book_keys if k in locked]
        skipped_empty = [k for k in book_keys if k not in locked and not original.morphemes(original_verse(k))]
        review = [k for k in book_keys if k not in locked and k not in skipped_empty]
        blocks = {k: verse_block(k, current[k], original_verse(k), dictionary) for k in review}
        sizes = {k: len('\n'.join(b)) for k, b in blocks.items()}
        chapters = sorted({k[1] for k in review})
        keys_by_chapter = [[k for k in review if k[1] == c] for c in chapters]

        book_dir = os.path.join(OUT_DIR, f'{book_number:02d}_{book.replace(" ", "_")}')
        os.makedirs(book_dir, exist_ok=True)
        for keys in plan_chunks(keys_by_chapter, sizes, args.max_verses, args.max_chars):
            first, last = keys[0], keys[-1]
            span = (first[1], first[2]), (last[1], last[2])
            in_span = [k for k in book_keys if span[0] <= (k[1], k[2]) <= span[1]]
            name = chunk_name(book_number, keys)
            title = data.reference(first) + '–' + (
                f'{last[2] + 1}' if first[1] == last[1] else f'{last[1] + 1}:{last[2] + 1}')
            lines = [f'# NMV Strong\'s review: {title}', '',
                     f'Chunk file: {name}. {len(keys)} verses to review.']
            left_out = [k for k in in_span if k in locked]
            if left_out:
                lines.append(f'Already reviewed by hand, not included: {compress_refs(left_out)}.')
            no_original = [k for k in in_span if k in skipped_empty]
            if no_original:
                lines.append(f'No original text, not included: {compress_refs(no_original)}.')
            lines.append('')
            lines += examples['NT' if book in NEW_TESTAMENT else 'OT']
            lines += ['## Verses to review', '']
            for key in keys:
                lines += blocks[key]
            in_chunk = set(keys)
            context = sorted({k for key in keys for k in original.nearby_keys(order, key, args.window)
                              if k not in in_chunk and original.morphemes(original_verse(k))})
            if context:
                lines += ['## Neighbouring verses (context only, not for review)', '',
                          'Original words of verses next to the ones above. Where the Persian verse division '
                          'differs, their Strong\'s numbers may be used for the verses above.', '']
                for key in context:
                    lines += [f'### {data.reference(key)} (context)', '']
                    lines += original_lines(original_verse(key), dictionary) + ['']
            with open(os.path.join(book_dir, name), 'w', encoding='utf8') as f:
                f.write('\n'.join(lines))
            index.append(f'| [{title}]({os.path.basename(book_dir)}/{name}) | {len(keys)} |')
            total_chunks += 1
            total_verses += len(keys)

    index += ['', f'{total_chunks} chunks, {total_verses} verses. '
              f'{len(locked)} hand-reviewed verses are not included.']
    with open(os.path.join(OUT_DIR, 'INDEX.md'), 'w', encoding='utf8') as f:
        f.write('\n'.join(index) + '\n')
    print(f'Wrote {total_chunks} chunks ({total_verses} verses) to {OUT_DIR}')


if __name__ == '__main__':
    main()
