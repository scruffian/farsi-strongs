'''Turning per-token links into sync.bible verse entries.

Output rules:
  * a Persian word that translates no original word is left untagged: ["word"]
  * a Persian word translating one or more original words is tagged with all of their
    Strong's numbers, in original word order: ["word", "H3068 H430"]
  * adjacent Persian words translating the same original word are grouped into one entry:
    ["ساکن گشتید", "H3427"]
  * non-adjacent Persian words translating the same original word are each tagged with it.'''
from . import original, persian


def apply_rules(tokens, links, original_verse):
    '''links: {token_index: {lemma: morpheme_index}}, updated in place and returned.

    Compound verbs: an untagged light verb ("کرد", "می‌دهد", "داده_است"...) following a word
    tagged only with original verbs belongs to the same translation.
    Object marker: "را" translates the Hebrew object marker את (H853) when the verse has one,
    and nothing else.'''
    for i, token in enumerate(tokens):
        if persian.is_object_marker(token) and i in links:
            links[i] = {l: j for l, j in links[i].items() if l == 'H853'}
    verbs = original.verb_lemmas(original_verse)
    for a in range(len(tokens) - 1):
        b = a + 1
        if any(persian.is_punctuation(t) or persian.is_object_marker(t) for t in (tokens[a], tokens[b])):
            continue
        if persian.is_light_verb(tokens[b]) and not persian.is_light_verb(tokens[a]):
            la = links.get(a)
            if la and not links.get(b) and set(la) <= verbs:
                links[b] = dict(la)
    object_markers = [j for j, (_, l) in enumerate(original.morphemes(original_verse)) if l == 'H853']
    if object_markers:
        for i, token in enumerate(tokens):
            if persian.is_object_marker(token) and not links.get(i):
                links[i] = {'H853': object_markers[0]}
    return links


def group(tokens, links):
    '''Build verse entries, merging runs of adjacent tokens linked to the same original words.'''
    entries, previous = [], None
    for i, token in enumerate(tokens):
        current = links.get(i) or None
        if current and current == previous:
            entries[-1][0] += ' ' + token
        else:
            if current:
                tags = ' '.join(l for l, _ in sorted(current.items(), key=lambda x: (x[1], x[0])))
                entries.append([token, tags])
            else:
                entries.append([token])
        previous = current
    return entries


def tag_verse(tokens, predicted, original_verse):
    '''predicted: {token_index: {lemma: (probability, morpheme_index)}}.'''
    links = {ti: {l: j for l, (_, j) in lemmas.items()} for ti, lemmas in predicted.items() if lemmas}
    return group(tokens, apply_rules(tokens, links, original_verse))


def group_locked_verse(verse, original_verse):
    '''Group adjacent hand-tagged entries with identical tags, without changing any tag.

    Only done when every Strong's number involved occurs once in the original verse, so the
    words must translate the same original word.'''
    counts = {}
    for _, lemma in original.morphemes(original_verse):
        counts[lemma] = counts.get(lemma, 0) + 1
    out = []
    for entry in verse:
        tags = entry[1] if len(entry) > 1 else None
        if (out and tags and len(out[-1]) > 1 and out[-1][1] == tags
                and not persian.is_punctuation(entry[0]) and not persian.is_punctuation(out[-1][0])
                and all(counts.get(t) == 1 for t in tags.split())):
            out[-1] = [out[-1][0] + ' ' + entry[0], tags]
        else:
            out.append(list(entry))
    return out
