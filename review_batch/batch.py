'''Resumable batch review of the chunks in review_chunks/ by helper agents.

    python review_batch/batch.py status        # how far the batch has got
    python review_batch/batch.py next 8        # the next chunks to hand to helpers
    python review_batch/batch.py progress NAME # where a helper (re)starts in its chunk
    python review_batch/batch.py assemble NAME # draft -> reply, check it, mark it complete if OK
    python review_batch/batch.py commit        # verify, commit and push finished replies
    python review_batch/batch.py salvage       # after a cut-off (no helpers running!): keep what is usable

A chunk is done when a reply named after it is committed in review_replies/pending, approved
or applied. Helpers don't write the reply directly: they append their verdict on each verse to a
draft in review_batch/drafts/ as they go, and `assemble` turns the draft into the reply, runs the
check and appends COMPLETE_MARKER when it passes. A helper cut off by a usage limit leaves its
draft behind; the next helper for that chunk continues after the last verse in the draft instead
of starting again. See review_batch/README.md.'''
import argparse
import json
import os
import re
import subprocess
import sys
import time
import unicodedata

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHUNKS = os.path.join(REPO, 'review_chunks')
REPLIES = os.path.join(REPO, 'review_replies')
DRAFTS = os.path.join(REPO, 'review_batch', 'drafts')
FOLDERS = ['pending', 'approved', 'applied']
COMPLETE_MARKER = '<!-- review complete -->'
CHUNK_NAME = re.compile(r'^\d+_(.+)_(\d{3})\.(\d{3})-(\d{3})\.(\d{3})\.md$')


def git(*args, check=True):
    return subprocess.run(['git', '-C', REPO, *args], check=check, capture_output=True, text=True).stdout


def all_chunks():
    '''Chunk paths relative to review_chunks/, in Bible order (as in INDEX.md).'''
    with open(os.path.join(CHUNKS, 'INDEX.md'), encoding='utf8') as f:
        return re.findall(r'^\| \[[^\]]*\]\(([^)]+)\)', f.read(), re.M)


def chunk_path(name):
    '''review_chunks/<book folder>/NAME for a chunk file name.'''
    for c in all_chunks():
        if os.path.basename(c) == name:
            return os.path.join(CHUNKS, c)
    raise SystemExit(f'No chunk named {name}')


def chunk_verses(name):
    '''The refs under "Verses to review" in a chunk, in order.'''
    with open(chunk_path(name), encoding='utf8') as f:
        text = f.read()
    part = text.split('## Verses to review', 1)[1].split('\n## ', 1)[0]
    return re.findall(r'^### (.+?)\s*$', part, re.M)


def draft_paths(name):
    return os.path.join(DRAFTS, name[:-3] + '.jsonl'), os.path.join(DRAFTS, name[:-3] + '.notes.md')


def read_draft(name):
    '''([(line number, text, obj or None)], notes text) of a chunk's draft.'''
    jpath, npath = draft_paths(name)
    rows, notes = [], ''
    if os.path.exists(jpath):
        with open(jpath, encoding='utf8') as f:
            for n, line in enumerate(f, 1):
                text = line.strip()
                if not text:
                    continue
                try:
                    obj = json.loads(text)
                except json.JSONDecodeError:
                    obj = None
                rows.append((n, text, obj))
    if os.path.exists(npath):
        with open(npath, encoding='utf8') as f:
            notes = f.read().strip()
    return rows, notes


def drafted_refs(rows):
    return {obj['ref'] for _, _, obj in rows if isinstance(obj, dict) and 'ref' in obj}


def draft_names():
    if not os.path.isdir(DRAFTS):
        return set()
    return {n[:-len('.jsonl')] + '.md' for n in os.listdir(DRAFTS) if n.endswith('.jsonl')}


def tracked_replies():
    names = set()
    for line in git('ls-files', 'review_replies').splitlines():
        folder, name = line.split('/')[-2:]
        if folder in FOLDERS and not name.endswith('.check.md'):
            names.add(name)
    return names


def untracked_replies():
    '''{name: complete?} for reply files in pending/ that are not committed yet.'''
    out = {}
    # No --exclude-standard: in-progress replies may be listed in .git/info/exclude (see README).
    for line in git('ls-files', '--others', 'review_replies/pending').splitlines():
        name = os.path.basename(line)
        if name.endswith('.md') and not name.endswith('.check.md'):
            with open(os.path.join(REPO, line), encoding='utf8') as f:
                out[name] = COMPLETE_MARKER in f.read()
    return out


def state():
    done, untracked = tracked_replies(), untracked_replies()
    chunks = all_chunks()
    drafts = draft_names()
    # An unfinished reply with a draft failed assemble's check: the chunk is handed out again.
    busy = {n for n, ok in untracked.items() if ok or n not in drafts}
    remaining = [c for c in chunks if os.path.basename(c) not in done and os.path.basename(c) not in busy]
    return chunks, done, untracked, remaining


def cmd_status(args):
    chunks, done, untracked, remaining = state()
    n_done = sum(os.path.basename(c) in done for c in chunks)
    finished = [n for n, ok in untracked.items() if ok]
    drafts = sorted(draft_names() - done - set(finished))
    print(f'{n_done} of {len(chunks)} chunks reviewed and committed, {len(remaining)} not finished.')
    if finished:
        print(f'{len(finished)} finished but not committed yet (run commit): {", ".join(sorted(finished))}')
    partial = [n for n, ok in untracked.items() if not ok]
    if partial:
        print(f'{len(partial)} replies without the completion line (run salvage once no helpers are running): '
              f'{", ".join(sorted(partial))}')
    if drafts:
        print(f'{len(drafts)} partly reviewed (next helper continues the draft): {", ".join(drafts)}')
    if remaining:
        print(f'Next: {remaining[0]}')


def cmd_next(args):
    '''The next chunks not started, after --after (the last chunk handed out, whose helpers
    may not have written anything yet).'''
    remaining = state()[3]
    if args.after:
        order = all_chunks()
        start = order.index(args.after) + 1 if args.after in order else 0
        later = set(order[start:])
        remaining = [c for c in remaining if c in later]
    for chunk in remaining[:args.n]:
        print(chunk)


def run_check(path, sync_bible):
    """(ok, status line, [problems]) from review_replies.py check for one reply."""
    out = subprocess.run([sys.executable, os.path.join(REPO, 'review_replies.py'), 'check',
                          '--sync-bible', sync_bible, path], capture_output=True, text=True, cwd=REPO).stdout
    line = next((l for l in out.splitlines() if f'/{os.path.basename(path)}:' in l), '')
    problems = []
    report = path + '.check.md'
    if os.path.exists(report):
        with open(report, encoding='utf8') as f:
            text = f.read()
        if '## Problems' in text:
            section = text.split('## Problems', 1)[1].split('\n## ', 1)[0]
            problems = [l[2:] for l in section.splitlines() if l.startswith('- ')]
    # A chunk where no verse needs a change gives a reply without verse lines: that's fine.
    problems = [x for x in problems if not x.endswith(': no verse lines found')]
    return (', OK.' in line or ' 0 verses with changes, 1 problem(s)' in line) and not problems, line, problems


def cmd_salvage(args):
    """After a cut-off, with no helpers running: keep every bit of finished work."""
    completed, removed = [], []
    for name, complete in untracked_replies().items():
        if complete:
            continue
        path = os.path.join(REPLIES, 'pending', name)
        if name in draft_names():
            # Written by assemble; the helper was fixing problems when it stopped. The draft
            # is kept and the next helper re-assembles it.
            ok = False
        else:
            # A whole reply written in one go (older helpers): often only the check was cut off.
            with open(path, encoding='utf8') as f:
                text = f.read()
            ok = text.lstrip().startswith('```jsonl') and text.count('```') >= 2 \
                and not refs_outside(name, text) and run_check(path, args.sync_bible)[0]
        if ok:
            with open(path, 'a', encoding='utf8') as f:
                f.write(('' if text.endswith('\n') else '\n') + '\n' + COMPLETE_MARKER + '\n')
            completed.append(name)
        else:
            for p in (path, path + '.check.md'):
                if os.path.exists(p):
                    os.remove(p)
            removed.append(name)
    print(f'Completed {len(completed)} replies whose check passes: {", ".join(completed) or "-"}')
    print(f'Removed {len(removed)} unusable replies (their drafts, if any, are kept): {", ".join(removed) or "-"}')
    drafts = sorted(draft_names() - tracked_replies())
    if drafts:
        print(f'{len(drafts)} drafts will be continued: {", ".join(drafts)}')


def cmd_progress(args):
    name = os.path.basename(args.name)
    verses = chunk_verses(name)
    rows, _ = read_draft(name)
    seen = drafted_refs(rows)
    todo = [v for v in verses if v not in seen]
    if not rows:
        print(f'{name}: no draft yet; start with {verses[0]} ({len(verses)} verses).')
    elif not todo:
        print(f'{name}: all {len(verses)} verses are in the draft; run assemble.')
    else:
        print(f'{name}: {len(verses) - len(todo)} of {len(verses)} verses done; continue with {todo[0]}'
              f' (still to do: {", ".join(todo)}).')


MISMATCH = re.compile(r'\((?P<ref>[^)]*)\): Persian words differ from the verse at word \d+: '
                      r'got "(?P<got>[^"]*)", expected "(?P<want>[^"]*)"')


def fix_spelling(name, problems):
    '''Fix draft words that equal the verse's word up to Unicode normalisation (diacritic order).'''
    fixes = []
    for p in problems:
        m = MISMATCH.search(p)
        if m and m['got'] != m['want'] and \
                unicodedata.normalize('NFC', m['got']) == unicodedata.normalize('NFC', m['want']):
            fixes.append((m['ref'], m['got'], m['want']))
    if not fixes:
        return False
    with open(chunk_path(name), encoding='utf8') as f:
        chunk = f.read()
    jpath = draft_paths(name)[0]
    with open(jpath, encoding='utf8') as f:
        lines = f.readlines()
    changed = False
    for ref, got, _ in fixes:
        # The verse's own spellings of this word, in order (a verse may spell it differently
        # in different places), are copied onto the draft line's occurrences in order.
        section = chunk.split(f'### {ref}\n', 1)[-1].split('\n### ', 1)[0]
        key = unicodedata.normalize('NFC', got)
        source = [w for w in re.findall(r'[^\s"\[\],:|`]+', section)
                  if unicodedata.normalize('NFC', w) == key]
        for i, line in enumerate(lines):
            if f'"ref": "{ref}"' not in line:
                continue
            spots = [m for m in re.finditer(r'"([^"]+)"', line)
                     if unicodedata.normalize('NFC', m.group(1)) == key]
            if source and len(source) >= len(spots):
                new_line, last = '', 0
                for m, w in zip(spots, source):
                    new_line += line[last:m.start(1)] + w
                    last = m.end(1)
                new_line += line[last:]
                if new_line != line:
                    lines[i] = new_line
                    changed = True
            break
    if changed:
        with open(jpath, 'w', encoding='utf8') as f:
            f.writelines(lines)
    return changed


def cmd_assemble(args):
    name = os.path.basename(args.name)
    verses = chunk_verses(name)
    rows, notes = read_draft(name)
    jpath = draft_paths(name)[0]
    problems = []
    lines = []
    for n, text, obj in rows:
        where = f'{os.path.relpath(jpath, REPO)}, line {n}'
        if not isinstance(obj, dict) or 'ref' not in obj:
            problems.append(f'{where}: not a JSON object with "ref"')
        elif obj['ref'] not in verses:
            problems.append(f'{where}: {obj["ref"]} is not one of this chunk\'s verses')
        elif obj.get('unchanged'):
            continue
        elif 'entries' not in obj:
            problems.append(f'{where} ({obj["ref"]}): needs "entries" (or "unchanged": true)')
        else:
            lines.append(json.dumps({'ref': obj['ref'], 'entries': obj['entries']}, ensure_ascii=False))
    missing = [v for v in verses if v not in drafted_refs(rows)]
    if missing:
        problems.append(f'not in the draft yet: {", ".join(missing)}')
    if problems:
        print(f'{name}: NOT assembled.')
        for p in problems:
            print(f'- {p}')
        return
    path = os.path.join(REPLIES, 'pending', name)
    with open(path, 'w', encoding='utf8') as f:
        f.write('```jsonl\n' + ''.join(l + '\n' for l in lines) + '```\n\n' + (notes or '- No doubtful cases.') + '\n')
    ok, status, problems = run_check(path, args.sync_bible)
    if not ok and getattr(args, 'fixes', 0) < 3 and fix_spelling(name, problems):
        args.fixes = getattr(args, 'fixes', 0) + 1
        # Words that only differ from the verse in the order of their diacritics were
        # replaced with the verse's own spelling; assemble again.
        return cmd_assemble(args)
    if not ok:
        print(f'{name}: assembled, but the check found problems. Fix the verse lines in the draft '
              f'({os.path.relpath(jpath, REPO)}) and run assemble again:')
        for p in problems or [status or 'check did not run']:
            print(f'- {p}')
        return
    with open(path, 'a', encoding='utf8') as f:
        f.write('\n' + COMPLETE_MARKER + '\n')
    print(f'{name}: changed {len(lines)} of {len(verses)} verses, check OK, complete.')


def refs_outside(name, text):
    m = CHUNK_NAME.match(name)
    book = m.group(1).replace('_', ' ')
    lo, hi = (int(m.group(2)), int(m.group(3))), (int(m.group(4)), int(m.group(5)))
    bad = []
    for ref in re.findall(r'"ref":\s*"([^"]*)"', text):
        rb, _, cv = ref.rpartition(' ')
        try:
            c, v = map(int, cv.split(':'))
        except ValueError:
            bad.append(ref)
            continue
        if rb != book or not lo <= (c, v) <= hi:
            bad.append(ref)
    return bad


def cmd_commit(args):
    finished = sorted(n for n, ok in untracked_replies().items() if ok)
    if not finished:
        print('Nothing finished to commit.')
        return
    paths = [os.path.join(REPLIES, 'pending', n) for n in finished]
    out = subprocess.run([sys.executable, os.path.join(REPO, 'review_replies.py'), 'check',
                          '--sync-bible', args.sync_bible, *paths], capture_output=True, text=True, cwd=REPO).stdout
    good, bad = [], []
    for name, path in zip(finished, paths):
        line = next((l for l in out.splitlines() if f'/{name}:' in l), '')
        with open(path, encoding='utf8') as f:
            outside = refs_outside(name, f.read())
        if (', OK.' in line or run_check(path, args.sync_bible)[0]) and not outside:
            good.append(name)
        else:
            bad.append(f'{name}: {"refs outside the chunk: " + ", ".join(outside) if outside else line or "not checked"}')
    for b in bad:
        print('NOT COMMITTED', b)
    if not good:
        return
    files = [f'review_replies/pending/{n}{s}' for n in good for s in ('', '.check.md')]
    git('add', '-f', *files)
    label = ', '.join(n[:-3] for n in good) if len(good) <= 3 else f'{len(good)} chunks ({good[0][:-3]} … {good[-1][:-3]})'
    git('commit', '-q', '-m', f'Chat review replies for {label} (pending human check)\n\n'
        'Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>'
        + (f'\nClaude-Session: {args.session}' if args.session else ''))
    for attempt in range(5):
        if subprocess.run(['git', '-C', REPO, 'pull', '-q', '--rebase', 'origin', args.branch]).returncode == 0:
            break
        time.sleep(2 ** attempt)
    for attempt in range(5):
        if subprocess.run(['git', '-C', REPO, 'push', '-q', 'origin', f'HEAD:{args.branch}']).returncode == 0:
            break
        time.sleep(2 ** attempt)
    for n in good:
        for p in draft_paths(n):
            if os.path.exists(p):
                os.remove(p)
    print(f'Committed and pushed {len(good)}: {", ".join(good)}')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)
    sync_bible = os.path.join(REPO, '..', 'sync.bible')
    sub.add_parser('status')
    p = sub.add_parser('next')
    p.add_argument('n', type=int, nargs='?', default=8)
    p.add_argument('--after', help='Only chunks after this one (e.g. the last one handed out)')
    p = sub.add_parser('progress')
    p.add_argument('name', help='Chunk file name or path')
    p = sub.add_parser('assemble')
    p.add_argument('name', help='Chunk file name or path')
    p.add_argument('--sync-bible', default=sync_bible)
    for cmd in ('salvage', 'clean'):  # clean: old name
        p = sub.add_parser(cmd)
        p.add_argument('--sync-bible', default=sync_bible)
    p = sub.add_parser('commit')
    p.add_argument('--sync-bible', default=sync_bible)
    p.add_argument('--branch', default='review-chunks')
    p.add_argument('--session', default=os.environ.get('CLAUDE_SESSION_URL', ''),
                   help='Claude session link for the commit message (default: $CLAUDE_SESSION_URL)')
    args = parser.parse_args()
    {'status': cmd_status, 'next': cmd_next, 'progress': cmd_progress, 'assemble': cmd_assemble,
     'salvage': cmd_salvage, 'clean': cmd_salvage, 'commit': cmd_commit}[args.command](args)


if __name__ == '__main__':
    main()
