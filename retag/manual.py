'''Finding and remembering the verses whose tags were corrected by hand in sync.bible.

A verse is "locked" (copied verbatim from sync.bible, never re-tagged) when:
  * it differs from the last machine output this tool produced (or, before the first run,
    from the original aligner output in outputs/NMV_ESV_strongs.json), or
  * it is listed in retag/locked_verses.txt, which records every verse locked by previous
    runs and can also be edited by hand to protect passages reviewed without changes.'''
import datetime
import os

from . import data

LOCKED_VERSES_FILE = os.path.join(data.REPO, 'retag', 'locked_verses.txt')


def machine_baseline_path():
    return data.MACHINE_OUTPUT if os.path.exists(data.MACHINE_OUTPUT) else data.ORIGINAL_ALIGNER_OUTPUT


MAX_PLAUSIBLE_EDITS = 3000


def detect_edits(current, grid):
    '''Keys of verses in the current sync.bible file that differ from the last machine output.'''
    baseline_path = machine_baseline_path()
    baseline = data.align_to_grid(data.load_bible(baseline_path), grid)
    edited = sorted(k for k, verse in current.items() if k in baseline and baseline[k] != verse)
    if len(edited) > MAX_PLAUSIBLE_EDITS:
        raise SystemExit(
            f'{len(edited)} verses differ between sync.bible and {baseline_path}, which is far more '
            'than hand editing would produce. The last output of this tool was probably not copied '
            'into sync.bible. Copy it there (or restore the matching machine output) and rerun.')
    return edited


def read_locked(grid, path=LOCKED_VERSES_FILE):
    keys = set()
    if not os.path.exists(path):
        return keys
    with open(path, encoding='utf8') as f:
        for n, line in enumerate(f, 1):
            ref = line.split('#', 1)[0].strip()
            if ref:
                try:
                    keys.update(data.parse_references(ref, grid))
                except ValueError as error:
                    raise SystemExit(f'{path}, line {n}: {error}')
    return keys


def record_locked(new_keys, path=LOCKED_VERSES_FILE):
    if not new_keys:
        return
    today = datetime.date.today().isoformat()
    with open(path, 'a', encoding='utf8') as f:
        for key in sorted(new_keys):
            f.write(f'{data.reference(key)}  # manual edit detected {today}\n')


def locked_verses(current, grid, record=False):
    '''All locked keys, optionally appending newly detected edits to locked_verses.txt.'''
    listed = read_locked(grid)
    edited = set(detect_edits(current, grid))
    if record:
        record_locked(edited - listed)
    return listed | edited, edited - listed
