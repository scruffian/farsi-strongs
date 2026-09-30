'''Deciding which candidate links become tags.

Candidates are the union of every eflomal link (both directions, all runs) plus the tags
from the original ESV-pivot aligner. Each candidate gets a few features (how many runs and
directions produced it, whether the pivot agreed, how strongly the Persian stem and the
Strong's number are associated across the whole Bible, relative position, kind of
morpheme...) and a small gradient boosted classifier, trained on the hand-corrected verses
from sync.bible, estimates the probability that it is a correct tag.'''
import collections
import math

import numpy as np
from sklearn.ensemble import GradientBoostingClassifier

from . import data, original


class Candidates:
    def __init__(self, verses, alignments, pivot):
        self.by_key = {}
        links = [set().union(*(f[n] | r[n] for f, r in alignments)) for n in range(len(verses))]
        stem_n, lemma_n, pair_n = collections.Counter(), collections.Counter(), collections.Counter()
        for v, verse_links in zip(verses, links):
            stem_n.update(v.stems)
            lemma_n.update(l for _, l in v.morphemes)
            pair_n.update((v.stems[i], v.morphemes[j][1]) for i, j in verse_links)

        for n, v in enumerate(verses):
            pivot_tags = pivot.get(v.key)
            candidates = set(links[n])
            for i, ti in enumerate(v.token_idx):
                if pivot_tags:
                    candidates.update((i, j) for j, (_, l) in enumerate(v.morphemes) if l in pivot_tags[ti])
            fert_fa = collections.Counter(i for i, _ in links[n])
            fert_orig = collections.Counter(j for _, j in links[n])
            n_fa, n_orig = max(1, len(v.stems)), max(1, len(v.morphemes))
            rows = []
            for i, j in sorted(candidates):
                stem, lemma = v.stems[i], v.morphemes[j][1]
                fwd = sum((i, j) in f[n] for f, _ in alignments) / len(alignments)
                rev = sum((i, j) in r[n] for _, r in alignments) / len(alignments)
                pair = pair_n[(stem, lemma)]
                features = [
                    fwd, rev, fwd * rev,
                    float(bool(pivot_tags) and lemma in pivot_tags[v.token_idx[i]]),
                    2 * pair / (stem_n[stem] + lemma_n[lemma]),
                    pair / stem_n[stem],
                    pair / lemma_n[lemma],
                    abs(i / n_fa - j / n_orig),
                    float(lemma == original.HEBREW_ARTICLE),
                    float(lemma in original.HEBREW_PREFIXES),
                    float(lemma == original.GREEK_ARTICLE),
                    math.log(stem_n[stem]),
                    fert_fa[i], fert_orig[j],
                    float(lemma.startswith('G')),
                ]
                rows.append((v.token_idx[i], j, lemma, features))
            self.by_key[v.key] = rows


def gold_labels(verse):
    '''Per-token gold tag sets from a hand-corrected sync.bible verse.'''
    return [{original.GREEK_PRONOUN_FORMS.get(t, t) for t in data.clean_tags(tags)}
            for tags in data.token_tags(verse)]


def train(candidates, gold):
    '''gold: {key: per-token tag sets}.'''
    X, y = [], []
    for key, labels in gold.items():
        for ti, _, lemma, features in candidates.by_key.get(key, []):
            X.append(features)
            y.append(lemma in labels[ti])
    if not X or len(set(y)) < 2:
        raise SystemExit('Not enough hand-corrected verses to train the tagger.')
    model = GradientBoostingClassifier(n_estimators=100, max_depth=3, random_state=0)
    return model.fit(np.array(X), np.array(y))


def predict(model, candidates, keys, threshold):
    '''{key: {token_index: {lemma: (probability, morpheme_index)}}} for links above threshold.'''
    out = {}
    for key in keys:
        rows = candidates.by_key.get(key, [])
        chosen = collections.defaultdict(dict)
        if rows:
            probs = model.predict_proba(np.array([r[3] for r in rows]))[:, 1]
            for (ti, j, lemma, _), p in zip(rows, probs):
                if p >= threshold and p > chosen[ti].get(lemma, (0, None))[0]:
                    chosen[ti][lemma] = (p, j)
        out[key] = dict(chosen)
    return out
