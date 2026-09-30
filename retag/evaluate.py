'''Scoring tags against the hand-corrected verses.

Tags are compared per Persian token as (token, Strong's number) pairs, after expanding
grouped entries to their tokens, so grouping itself neither gains nor loses points.'''
from . import model as tag_model
from . import tagger


def score(predicted, gold):
    '''predicted, gold: {key: per-token tag sets}.'''
    tp = fp = fn = 0
    for key, labels in gold.items():
        for p, g in zip(predicted[key], labels):
            tp += len(p & g)
            fp += len(p - g)
            fn += len(g - p)
    precision = tp / max(1, tp + fp)
    recall = tp / max(1, tp + fn)
    f1 = 2 * precision * recall / max(1e-9, precision + recall)
    return {'precision': precision, 'recall': recall, 'f1': f1, 'verses': len(gold)}


def token_sets(entries):
    return tag_model.gold_labels(entries)


def cross_validate(candidates, verses_by_key, gold, threshold, folds=5):
    '''Train on all but one fold of the hand-corrected verses, tag the held-out fold.'''
    keys = sorted(gold)
    folds = min(folds, len(keys))
    predicted = {}
    for f in range(folds):
        test = keys[f::folds]
        train = {k: gold[k] for k in keys if k not in test}
        model = tag_model.train(candidates, train)
        for key, links in tag_model.predict(model, candidates, test, threshold).items():
            v = verses_by_key[key]
            predicted[key] = token_sets(tagger.tag_verse(v.tokens, links, v.original))
    return score(predicted, gold)


def format_score(name, s):
    return (f'{name:<28} precision {s["precision"]:.3f}  recall {s["recall"]:.3f}  '
            f'F1 {s["f1"]:.3f}  ({s["verses"]} verses)')
