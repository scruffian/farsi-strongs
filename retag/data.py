'''Loading and writing the Bible files involved in re-tagging.

Verses are identified by a key (book, chapter_index, verse_index), 0-indexed, following the
versification of transformations/NMV_hazm.parquet (which matches NMV.json and the KJV
versification used by accented.json in sync.bible).'''
import json
import os
import re

import pandas as pd

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HAZM_TOKENS = os.path.join(REPO, 'transformations', 'NMV_hazm.parquet')
ORIGINAL_ALIGNER_OUTPUT = os.path.join(REPO, 'outputs', 'NMV_ESV_strongs.json')
MACHINE_OUTPUT = os.path.join(REPO, 'outputs', 'NMV_strongs_machine.json')

STRONGS_TAG = re.compile(r'^[HG](\d+[a-z]?|[a-z])$')


def sync_bible_paths(sync_bible):
    return {
        'nmv_strongs': os.path.join(sync_bible, 'public', 'bibles', 'NMV_strongs.json'),
        'accented': os.path.join(sync_bible, 'public', 'bibles', 'accented.json'),
    }


def load_json(path):
    with open(path, encoding='utf8') as f:
        return json.load(f)


def load_bible(path):
    data = load_json(path)
    return data['books'] if 'books' in data and isinstance(data['books'], dict) else data


def write_sync_bible_json(bible, path):
    '''Write in the same tab-indented format as sync.bible's NMV_strongs.json.'''
    with open(path, 'w', encoding='utf8') as f:
        f.write(json.dumps(bible, indent='\t', ensure_ascii=False))


def write_compact_json(bible, path):
    with open(path, 'w', encoding='utf8') as f:
        json.dump(bible, f, ensure_ascii=False, separators=(',', ':'))


def load_token_grid():
    '''{(book, chapter_idx, verse_idx): [persian tokens]} for every verse of the NMV.'''
    df = pd.read_parquet(HAZM_TOKENS).sort_values(['book', 'idx_chapter', 'idx_verse', 'idx_word'])
    return {k: list(v) for k, v in df.groupby(['book', 'idx_chapter', 'idx_verse'])['word']}


def entry_tokens(entry):
    '''Tokens of one tagged entry (grouped entries hold several space-separated tokens).'''
    return entry[0].split(' ')


def verse_tokens(verse):
    return [t for entry in verse for t in entry_tokens(entry)]


def entry_tags(entry):
    return entry[1] if len(entry) > 1 and entry[1] else None


def clean_tags(tags):
    '''Set of Strong's tags in a tag string, dropping markers like "dvnNm" and "added".'''
    return {t for t in (tags or '').split() if STRONGS_TAG.match(t)}


def token_tags(verse):
    '''Per-token tag strings for a (possibly grouped) verse.'''
    out = []
    for entry in verse:
        out += [entry_tags(entry)] * len(entry_tokens(entry))
    return out


def align_to_grid(bible, grid):
    '''Map a file-shaped bible onto grid keys by matching tokens.

    Needed because the original aligner output (and so sync.bible's NMV_strongs.json until
    this re-tagging) silently dropped the verses missing from the ESV (e.g. Matthew 17:21),
    shifting every following verse in those chapters.'''
    out = {}
    for book, chapters in bible.items():
        for ci, chapter in enumerate(chapters):
            vi = 0
            for verse in chapter:
                tokens = verse_tokens(verse)
                while (book, ci, vi) in grid and grid[(book, ci, vi)] != tokens:
                    vi += 1
                if (book, ci, vi) in grid:
                    out[(book, ci, vi)] = verse
                    vi += 1
    return out


def reference(key):
    book, ci, vi = key
    return f'{book} {ci + 1}:{vi + 1}'


_REF = re.compile(r'^(.+?) (\d+)(?::(\d+)(?:-(\d+))?)?$')


def parse_references(text, grid):
    '''Parse "Book 3", "Book 3:4" or "Book 3:4-9" (1-indexed) into grid keys.'''
    m = _REF.match(text.strip())
    if not m:
        raise ValueError(f'Cannot parse reference: {text!r}')
    book, chapter, start, end = m.group(1), int(m.group(2)) - 1, m.group(3), m.group(4)
    keys = sorted(k for k in grid if k[0] == book and k[1] == chapter)
    if not keys:
        raise ValueError(f'Unknown reference: {text!r}')
    if start:
        lo, hi = int(start) - 1, int(end or start) - 1
        keys = [k for k in keys if lo <= k[2] <= hi]
    return keys
