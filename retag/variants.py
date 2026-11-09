'''Greek variant readings that the NMV follows but accented.json (Tischendorf 8th) lacks.

The NMV New Testament follows a modern critical text close to NA27/UBS4, adding verses found
only in the Textus Receptus in square brackets (e.g. Matthew 17:21). Tischendorf, the Greek
in accented.json, differs from it in places such as Jude 22 (ἐλέγχετε, where the Persian
follows ἐλεᾶτε), Acts 20:28 (κυρίου / θεοῦ) and Luke 24:12 (missing). So the original text
used here is accented.json with extra words merged in from other Greek texts in sync.bible:

  * WHNU.json (Westcott-Hort with NA27/UBS4 variants) for every New Testament verse;
  * TR.json (Textus Receptus) for verses where the Persian has square brackets, or where
    neither accented.json nor WHNU.json has the verse.

Only words whose Strong's number is not already in the verse are added, placed where they
stand in the other text. Each added word carries a fourth field naming its source, e.g.
["ελεατε", "G1653", "V-PAM-2P", "WHNU"]. The Hebrew Old Testament is unchanged.'''
import difflib
import os
import re
import unicodedata

from . import data, original

SOURCES = {
    'WHNU': 'Westcott-Hort with NA27/UBS4 variants (WHNU.json)',
    'TR': 'Textus Receptus (TR.json)',
}

_NUMBER = re.compile(r'^G0*(\d+[a-z]?)$')

# Numbers TR.json gives to inflected forms, mapped to the numbers accented.json uses.
FORM_NUMBERS = {
    **{g: 'G1510' for g in ['G1488', 'G1498', 'G1526', 'G2070', 'G2071', 'G2075', 'G2076',
                            'G2077', 'G2252', 'G2258', 'G2468', 'G5600', 'G5607']},
    'G2400': 'G3708',
    **original.GREEK_PRONOUN_FORMS,
}


def normalise_word(word):
    '''[text, lemma, morph] using accented.json's numbering, or None for a word without a number.

    WHNU.json numbers every first/second person pronoun G1473/G4771 and TR.json uses the
    inflected-form numbers (G3450, G5213...); accented.json uses G1473/G4771 for singular and
    G2249/G5210 for plural.'''
    if len(word) < 2 or not word[1]:
        return None
    numbers = [_NUMBER.match(n) for n in word[1].split()]
    if not numbers or not all(numbers):
        return None
    morph = (word[2] if len(word) > 2 and word[2] else '').split(' ')[0]
    lemmas = [FORM_NUMBERS.get('G' + m.group(1), 'G' + m.group(1)) for m in numbers]
    pronoun = re.match(r'^P-([12])[NGDAV]?([SP])', morph)
    if pronoun and len(lemmas) == 1 and lemmas[0] in ('G1473', 'G2249', 'G4771', 'G5210'):
        lemmas = [{('1', 'S'): 'G1473', ('1', 'P'): 'G2249', ('2', 'S'): 'G4771', ('2', 'P'): 'G5210'}[pronoun.groups()]]
    return [word[0], '/'.join(lemmas), morph]


def plain_greek(text):
    '''Lower case Greek letters only, without accents or breathings.'''
    text = unicodedata.normalize('NFD', text.lower())
    return ''.join(c for c in text if 'α' <= c <= 'ω' or c == 'ς').replace('ς', 'σ')


def merge(base, other, source):
    '''base with the words of `other` whose numbers are not in base inserted where they stand.'''
    extra = [w for w in (normalise_word(w) for w in other or []) if w]
    if not base:
        return [w + [source] for w in extra]
    known = {l for _, l in original.morphemes(base)}
    texts = [plain_greek(w[0]) for w in base]
    inserts = {}
    matcher = difflib.SequenceMatcher(None, [w[1] if len(w) > 1 else None for w in base],
                                      [w[1] for w in extra], autojunk=False)
    for op, i1, i2, j1, j2 in matcher.get_opcodes():
        if op not in ('insert', 'replace'):
            continue
        # The same word under another number (πλεῖον G4183 / G4119) or part of a compound
        # written as one word (διατί, εἴπως) is not a different reading.
        around = texts[max(0, i1 - 2):i2 + 2]
        for w in extra[j1:j2]:
            text = plain_greek(w[0])
            if any(l in known for l in w[1].split('/')) or any(text and text in t for t in around):
                continue
            known.update(w[1].split('/'))
            inserts.setdefault(i2, []).append(w + [source])
    out = []
    for i in range(len(base) + 1):
        out += inserts.get(i, [])
        if i < len(base):
            out.append(base[i])
    return out


def bracketed_keys(grid):
    '''Verses whose Persian has square brackets, which mark Textus Receptus additions.'''
    return {k for k, tokens in grid.items() if any('[' in t or ']' in t for t in tokens)}


def is_variant(word):
    return len(word) > 3 and word[3] in SOURCES


def load_original(sync_bible, grid, variants=True):
    '''accented.json, with the New Testament supplemented as described above.'''
    accented = data.load_bible(data.sync_bible_paths(sync_bible)['accented'])
    if not variants:
        return accented
    bibles = os.path.join(sync_bible, 'public', 'bibles')
    whnu = data.load_bible(os.path.join(bibles, 'WHNU.json'))
    tr = data.load_bible(os.path.join(bibles, 'TR.json'))
    bracketed = bracketed_keys(grid)

    def verse(bible, book, ci, vi):
        try:
            return bible[book][ci][vi]
        except (KeyError, IndexError):
            return []

    out = dict(accented)
    for book in whnu:
        keys = sorted(k for k in grid if k[0] == book)
        chapters = [list(c) for c in accented.get(book, [])]
        for _, ci, vi in keys:
            while len(chapters) <= ci:
                chapters.append([])
            while len(chapters[ci]) <= vi:
                chapters[ci].append([])
            merged = merge(chapters[ci][vi], verse(whnu, book, ci, vi), 'WHNU')
            if (book, ci, vi) in bracketed or not merged:
                merged = merge(merged, verse(tr, book, ci, vi), 'TR')
            chapters[ci][vi] = merged
        out[book] = chapters
    return out
