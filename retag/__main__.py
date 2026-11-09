'''Re-tag sync.bible's NMV_strongs.json while keeping every hand-corrected verse.

    python -m retag run --sync-bible ../sync.bible
    python -m retag evaluate --sync-bible ../sync.bible

See retag/README.md.'''
import argparse
import collections
import sys

from . import align, data, evaluate, manual, replies, tagger, variants
from . import model as tag_model


def log(message):
    print(message, file=sys.stderr, flush=True)


def prepare(args):
    paths = data.sync_bible_paths(args.sync_bible)
    log('Loading NMV tokens, accented.json' + ('' if args.no_variants else ' (+ WHNU.json and TR.json variants)')
        + ' and NMV_strongs.json')
    grid = data.load_token_grid()
    accented = variants.load_original(args.sync_bible, grid, variants=not args.no_variants)
    current_file = data.load_bible(paths['nmv_strongs'])
    current = data.align_to_grid(current_file, grid)
    unmapped = sum(len(v) for ch in current_file.values() for v in ch) - len(current)
    if unmapped:
        log(f'Warning: {unmapped} verses in NMV_strongs.json do not match the NMV token grid '
            f'and are ignored (their words differ from transformations/NMV_hazm.parquet)')
    return paths, grid, accented, current_file, current


def build_candidates(grid, accented, runs):
    log('Aligning Persian tokens to original language morphemes')
    verses = align.build_corpus(grid, accented)
    pivot = align.pivot_tags(grid)
    alignments = align.align(verses, pivot, runs=runs, log=log)
    log('Scoring candidate links')
    return verses, tag_model.Candidates(verses, alignments, pivot)


def run(args):
    paths, grid, accented, current_file, current = prepare(args)
    locked, newly_locked = manual.locked_verses(current, grid, record=not args.dry_run)
    log(f'{len(locked)} locked (hand-corrected) verses, {len(newly_locked)} newly detected')

    provisional = {} if args.no_replies else replies.load(args.sync_bible, locked, log=log)
    verses, candidates = build_candidates(grid, accented, args.runs)
    gold = {k: tag_model.gold_labels(current[k], grid[k]) for k in locked if k in current}
    extra = {k: tag_model.gold_labels(v, grid[k]) for k, v in provisional.items()}
    model = tag_model.train(candidates, gold, extra, args.reply_weight)
    to_tag = [v.key for v in verses if v.key not in locked]
    predicted = tag_model.predict(model, candidates, to_tag, args.threshold)
    by_key = {v.key: v for v in verses}

    chapters = collections.defaultdict(lambda: collections.defaultdict(list))
    stats = collections.Counter()
    alternatives = {}
    for key in sorted(grid):
        book, ci, vi = key
        v = by_key[key]
        if key in locked and key in current:
            verse = current[key]
            if not args.no_group_locked:
                verse = tagger.group_locked_verse(verse, v.original)
        elif key in provisional:
            verse = provisional[key]
            stats['verses from chat-review replies'] += 1
            alternatives[data.reference(key)] = data.display_verse(
                tagger.tag_verse(v.tokens, predicted[key], v.original))
        else:
            verse = tagger.tag_verse(v.tokens, predicted[key], v.original)
        chapters[book][ci].append(data.display_verse(verse))

    books = list(current_file) + sorted(set(chapters) - set(current_file))
    output = {b: [chapters[b][ci] for ci in sorted(chapters[b])] for b in books if b in chapters}

    for chapter in (c for b in output.values() for c in b):
        for verse in chapter:
            for entry in verse:
                stats['tagged entries' if len(entry) > 1 else 'untagged entries'] += 1
                stats['multi-word entries'] += ' ' in entry[0]
    log(', '.join(f'{n} {name}' for name, n in stats.items()))

    if args.dry_run:
        log('Dry run: nothing written')
        return
    out_path = args.output or paths['nmv_strongs']
    data.write_sync_bible_json(output, out_path)
    data.write_compact_json(output, data.MACHINE_OUTPUT)
    data.write_compact_json(alternatives, data.REPLY_ALTERNATIVES)
    log(f'Wrote {out_path}\nWrote {data.MACHINE_OUTPUT} (baseline for detecting future hand edits)')


def run_evaluate(args):
    _, grid, accented, _, current = prepare(args)
    locked, _ = manual.locked_verses(current, grid)
    gold = {k: tag_model.gold_labels(current[k], grid[k]) for k in locked if k in current}
    provisional = {} if args.no_replies else replies.load(args.sync_bible, locked, log=log)
    extra = {k: tag_model.gold_labels(v, grid[k]) for k, v in provisional.items()}

    baseline = data.align_to_grid(data.load_bible(manual.machine_baseline_path()), grid)
    before = {k: evaluate.token_sets(baseline[k], grid[k]) for k in gold if k in baseline}
    log(evaluate.format_score('Saved machine output', evaluate.score(before, {k: gold[k] for k in before})))

    verses, candidates = build_candidates(grid, accented, args.runs)
    by_key = {v.key: v for v in verses}
    result = evaluate.cross_validate(candidates, by_key, gold, args.threshold, args.folds, extra, args.reply_weight)
    log(evaluate.format_score(f'Re-tagger ({args.folds}-fold CV)', result))


def main():
    parser = argparse.ArgumentParser(prog='python -m retag', description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)
    for name, help_text in [('run', 'Re-tag NMV_strongs.json'),
                            ('evaluate', 'Cross-validate against the hand-corrected verses')]:
        p = sub.add_parser(name, help=help_text)
        p.add_argument('--sync-bible', required=True, help='Path to a sync.bible checkout')
        p.add_argument('--threshold', type=float, default=0.45,
                       help='Minimum link probability for a tag (higher = fewer, safer tags)')
        p.add_argument('--runs', type=int, default=3, help='Number of eflomal runs to combine')
        p.add_argument('--no-replies', action='store_true',
                       help='Ignore the unchecked chat-review replies in review_replies/pending and approved')
        p.add_argument('--reply-weight', type=float, default=0.5,
                       help='Training weight of a chat-review reply verse relative to a hand-corrected one (default 0.5)')
        p.add_argument('--no-variants', action='store_true',
                       help='Use accented.json alone, without the Greek variant readings from WHNU.json and TR.json')
        if name == 'run':
            p.add_argument('--output', help='Where to write (default: overwrite NMV_strongs.json in sync.bible)')
            p.add_argument('--no-group-locked', action='store_true',
                           help='Copy hand-corrected verses exactly, without grouping adjacent words with identical tags')
            p.add_argument('--dry-run', action='store_true', help='Report only; write nothing')
        else:
            p.add_argument('--folds', type=int, default=5)
    args = parser.parse_args()
    {'run': run, 'evaluate': run_evaluate}[args.command](args)


if __name__ == '__main__':
    main()
