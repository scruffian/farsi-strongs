'''Statistical word alignment of Persian tokens to original language morphemes.

The whole Bible is aligned at once with eflomal (a Bayesian IBM/HMM/fertility aligner),
Persian stems on one side and Strong's numbers on the other. Using Strong's numbers rather
than inflected Hebrew/Greek forms means every occurrence of a lemma contributes to the same
statistics. The tags from the original simalign/ESV-pivot run are fed in as lexical priors.'''
import collections
import os
import shutil
import subprocess
import tempfile

from . import data, original, persian


class Verse:
    '''One verse prepared for alignment.'''

    def __init__(self, key, tokens, original_verse, stem):
        self.key = key
        self.tokens = tokens
        self.original = original_verse
        self.token_idx = [i for i, t in enumerate(tokens) if not persian.is_punctuation(t)]
        self.stems = [stem(tokens[i]) for i in self.token_idx]
        self.morphemes = original.morphemes(original_verse)


def build_corpus(grid, accented):
    stem = persian.make_stemmer(t for tokens in grid.values() for t in tokens)
    verses = []
    for key in sorted(grid):
        book, ci, vi = key
        try:
            original_verse = accented[book][ci][vi]
        except (KeyError, IndexError):
            original_verse = []
        verses.append(Verse(key, grid[key], original_verse, stem))
    return verses


def pivot_tags(grid):
    '''Per-verse token tag sets from the original ESV-pivot aligner output.'''
    pivot = data.align_to_grid(data.load_bible(data.ORIGINAL_ALIGNER_OUTPUT), grid)
    return {k: [data.clean_tags(t) for t in data.token_tags(v)] for k, v in pivot.items()}


def write_priors(verses, pivot, path, weight=2.0):
    counts = collections.Counter()
    for v in verses:
        tags = pivot.get(v.key)
        if not tags:
            continue
        lemmas = {l for _, l in v.morphemes}
        for stem, ti in zip(v.stems, v.token_idx):
            for tag in tags[ti] & lemmas:
                counts[(stem, tag)] += 1
    with open(path, 'w', encoding='utf8') as f:
        for (stem, tag), n in sorted(counts.items()):
            f.write(f'LEX\t{stem}\t{tag}\t{n * weight:g}\n')


def _read_links(path):
    with open(path) as f:
        return [{tuple(map(int, p.split('-'))) for p in line.split()} for line in f]


def run_eflomal(verses, priors_path, workdir, name, samplers=4):
    src, trg = os.path.join(workdir, f'{name}.fa'), os.path.join(workdir, f'{name}.orig')
    fwd, rev = os.path.join(workdir, f'{name}.fwd'), os.path.join(workdir, f'{name}.rev')
    with open(src, 'w', encoding='utf8') as f:
        f.writelines(' '.join(v.stems) + '\n' for v in verses)
    with open(trg, 'w', encoding='utf8') as f:
        f.writelines(' '.join(l for _, l in v.morphemes) + '\n' for v in verses)
    subprocess.run(
        ['eflomal-align', '-s', src, '-t', trg, '-f', fwd, '-r', rev, '-p', priors_path,
         '--overwrite', '--n-samplers', str(samplers)],
        check=True, capture_output=True,
    )
    return _read_links(fwd), _read_links(rev)


def align(verses, pivot, runs=3, log=print):
    '''Run eflomal several times (it is a sampler, so runs differ) and return
    [(forward_links, reverse_links)] per run, links being {(persian_idx, morpheme_idx)}.'''
    if not shutil.which('eflomal-align'):
        raise SystemExit('eflomal-align not found: pip install -r retag/requirements.txt')
    workdir = tempfile.mkdtemp(prefix='retag-')
    try:
        priors = os.path.join(workdir, 'priors.txt')
        write_priors(verses, pivot, priors)
        results = []
        for i in range(runs):
            log(f'  eflomal run {i + 1}/{runs}')
            results.append(run_eflomal(verses, priors, workdir, f'run{i}'))
        return results
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
