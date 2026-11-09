'''Unchecked chat-review replies used as provisional tags.

Every verse line in review_replies/pending/ and review_replies/approved/ that passes
`review_replies.py check` is used for that verse in the output, in place of the machine
tagging, and as extra training data at reduced weight. Hand-corrected (locked) verses always
win: a reply is never used for a locked verse. Because the reply's tags also go into the
machine baseline (outputs/NMV_strongs_machine.json), a later edit to such a verse in
sync.bible differs from the baseline, is detected as a hand edit and locked as usual.'''
import sys

from . import data


def load(sync_bible, locked, window=1, log=print):
    '''{key: entries} for the valid reply verses that are not locked.'''
    if data.REPO not in sys.path:
        sys.path.insert(0, data.REPO)
    import review_replies  # at the repository root; it imports this package too

    ctx = review_replies.Context(sync_bible, window)
    files = review_replies.reply_files(review_replies.PENDING) + review_replies.reply_files(review_replies.APPROVED)
    proposals, problems = review_replies.load_and_validate(files, ctx)
    out, rejected = {}, []
    for p in proposals:
        if p.key in locked:
            continue
        if p.errors:
            rejected.append(p)
        else:
            out[p.key] = p.entries
    log(f'{len(out)} verses from {len(files)} chat-review replies'
        + (f'; {len(rejected) + len(problems)} reply lines skipped (run python review_replies.py check)'
           if rejected or problems else ''))
    return out
