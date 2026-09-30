'''Persian text helpers: punctuation detection, normalisation/stemming for alignment,
and detection of the "light verbs" used to build Persian compound verbs.'''
import collections
import re

PUNCTUATION = re.compile(r'^[\s«»:،؛.؟!()\[\]\-‌"\'…,;?”“’‘]+$')
DIACRITICS = re.compile(r'[ً-ْٰٔ]')
SEPARATORS = '[_~‌ ]'

# Auxiliaries and particles that are split off when a token is a multi-part compound
# (e.g. "خواهند_کُشت", "رفته_است", "می‌بخشد") so the content part is used for alignment.
AUXILIARIES = set(
    'است بود بودند بودم بودی بودیم بودید شد شده شدند خواهد خواهند خواهم خواهی خواهیم خواهید '
    'باشد باشند باشم باشی باشیم باشید اند ام ای ایم اید می نمی ها های هایی را'.split()
)

# Suffixes (plural markers and pronominal suffixes) stripped when the remainder is itself
# a common word in the corpus.
SUFFIXES = ['هایشان', 'هایتان', 'هایمان', 'هایش', 'هایت', 'هایم', 'هایی', 'های', 'ها',
            'یشان', 'یتان', 'یمان', 'شان', 'تان', 'مان', 'یش', 'ش', 'ت', 'م', 'ی']

LIGHT_VERB_STEMS = [
    'کرد', 'کن', 'نمود', 'نما', 'فرمود', 'فرما', 'شد', 'شو', 'گشت', 'گرد', 'گردید', 'داد', 'ده',
    'داشت', 'دار', 'آورد', 'آور', 'ساخت', 'ساز', 'یافت', 'یاب', 'گرفت', 'گیر', 'زد', 'زن', 'خورد',
    'خور', 'است', 'بود', 'باش', 'هست', 'نیست', 'آمد', 'آی', 'برآورد', 'برآور', 'افکند', 'افکن',
    'کشید', 'کش', 'بست', 'بند', 'نهاد', 'نه', 'خواه', 'خواست',
]
_LIGHT_VERB = re.compile(
    r'^(ن|نمی|می|ب|)(' + '|'.join(sorted(LIGHT_VERB_STEMS, key=len, reverse=True)) + r')'
    r'(ه|ن|ند|ید|یم|م|ی|د|ده|یده|ست|ستند|اند|ام|ای|ایم|اید|یت)?$'
)
_VERB_AFFIX_SEGMENTS = {'می', 'نمی', 'ام', 'ای', 'ایم', 'اید', 'اند'}


def is_punctuation(token):
    return bool(PUNCTUATION.match(token))


def normalise(token):
    return (
        DIACRITICS.sub('', token)
        .replace('ك', 'ک').replace('ي', 'ی').replace('ۀ', 'ه').replace('ة', 'ه')
        .replace('أ', 'ا').replace('إ', 'ا')
    )


def content_part(token):
    '''Normalised token, reduced to its main content part if it is a compound.'''
    parts = [p for p in re.split(SEPARATORS, normalise(token)) if p]
    if not parts:
        return token
    if len(parts) > 1:
        parts = [p for p in parts if p not in AUXILIARIES] or parts
    return max(parts, key=len)


def make_stemmer(tokens, min_count=5):
    '''Build a stemmer from the corpus: a suffix is removed only when what remains is
    itself a frequent word (so "پدرانمان" -> "پدران" but "آسمان" stays "آسمان").'''
    counts = collections.Counter(content_part(t) for t in tokens if not is_punctuation(t))
    cache = {}

    def stem(token):
        base = content_part(token)
        if base not in cache:
            cache[base] = base
            for suffix in SUFFIXES:
                if base.endswith(suffix) and len(base) - len(suffix) >= 3:
                    root = base[:-len(suffix)]
                    if counts[root] >= min_count and counts[root] >= counts[base]:
                        cache[base] = root
                        break
        return cache[base]

    return stem


def is_light_verb(token):
    '''True for tokens like "کنید", "می‌دهد", "داده_است" that complete a compound verb.'''
    segments = [s for s in re.split(SEPARATORS, DIACRITICS.sub('', token))
                if s and s not in _VERB_AFFIX_SEGMENTS]
    return bool(segments) and all(_LIGHT_VERB.match(s) for s in segments)


def is_object_marker(token):
    return DIACRITICS.sub('', token) == 'را'
