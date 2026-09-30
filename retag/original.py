'''Helpers for the original language text (accented.json in sync.bible).

Each accented word is [text, lemmas, morphology] where Hebrew words may hold several
morphemes separated by "/", e.g. ["וּ/מוּסָ֑ר", "Hc/H4148", "HC/Ncmsa"]. Every morpheme
with a Strong's number (including the prefixes Hc, Hl, Hb, Hm, Hk, Hd...) is an alignment
unit. Pronominal suffixes have no Strong's number and so are never tagged.'''

HEBREW_PREFIXES = {'Hc', 'Hl', 'Hb', 'Hm', 'Hk', 'Hi', 'Hs'}
HEBREW_ARTICLE = 'Hd'
GREEK_ARTICLE = 'G3588'

# The traditional Strong's numbers for inflected Greek pronoun forms, mapped to the lemma
# numbers used in accented.json. Only used when comparing against existing tags.
GREEK_PRONOUN_FORMS = {
    **{g: 'G1473' for g in ['G3427', 'G3165', 'G3450', 'G1698', 'G1700', 'G1691']},
    **{g: 'G2249' for g in ['G2248', 'G2254', 'G2257']},
    **{g: 'G4771' for g in ['G4671', 'G4571', 'G4675']},
    **{g: 'G5210' for g in ['G5209', 'G5213', 'G5216']},
}


def morphemes(verse):
    '''[(word_index, lemma)] for every Strong's-numbered morpheme in an original verse.'''
    out = []
    for wi, word in enumerate(verse):
        if len(word) > 1 and word[1]:
            out += [(wi, lemma) for lemma in word[1].split('/') if lemma]
    return out


def verb_lemmas(verse):
    '''Lemmas of the morphemes in a verse that are verbs.'''
    out = set()
    for word in verse:
        if len(word) < 3 or not word[1] or not word[2]:
            continue
        lemmas, morph = word[1].split('/'), word[2]
        if morph[0] in 'HA' and not morph.startswith('A-'):
            parts = morph[1:].split('/')
            out.update(l for l, m in zip(lemmas, parts) if m.startswith('V'))
        elif morph.startswith('V-'):
            out.update(lemmas)
    return out


def has_lemma(verse, lemma):
    return any(l == lemma for _, l in morphemes(verse))
