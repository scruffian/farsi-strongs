'''Tests for the output rules. Run with: python -m unittest retag.test_tagger'''
import unittest

from retag import persian, tagger

# Deuteronomy 26:1 (end): וִֽ/ירִשְׁתָּ֖/הּ וְ/יָשַׁ֥בְתָּ בָּֽ/הּ
ORIGINAL = [['וִֽ/ירִשְׁתָּ֖/הּ', 'Hc/H3423', 'HC/Vqq2ms/Sp3fs'],
            ['וְ/יָשַׁ֥בְתָּ', 'Hc/H3427', 'HC/Vqq2ms'],
            ['בָּֽ/הּ', 'Hb', 'HR/Sp3fs']]
# morpheme indexes: 0 Hc, 1 H3423, 2 Hc, 3 H3427, 4 Hb


def predicted(links):
    return {ti: {l: (0.9, j) for l, j in lemmas.items()} for ti, lemmas in links.items()}


class TaggerTest(unittest.TestCase):
    def test_adjacent_words_for_one_original_word_are_grouped(self):
        tokens = ['در', 'آن', 'ساکن', 'گشتید', '،']
        out = tagger.tag_verse(tokens, predicted({0: {'Hb': 4}, 2: {'H3427': 3}, 3: {'H3427': 3}}), ORIGINAL)
        self.assertEqual(out, [['در', 'Hb'], ['آن'], ['ساکن گشتید', 'H3427'], ['،']])

    def test_light_verb_joins_its_verb(self):
        tokens = ['آن', 'را', 'تصرف', 'کرده', '،']
        out = tagger.tag_verse(tokens, predicted({2: {'H3423': 1}}), ORIGINAL)
        self.assertEqual(out, [['آن'], ['را'], ['تصرف کرده', 'H3423'], ['،']])

    def test_non_adjacent_words_are_tagged_separately(self):
        tokens = ['ساکن', 'آنجا', 'گشتید']
        out = tagger.tag_verse(tokens, predicted({0: {'H3427': 3}, 2: {'H3427': 3}}), ORIGINAL)
        self.assertEqual(out, [['ساکن', 'H3427'], ['آنجا'], ['گشتید', 'H3427']])

    def test_one_word_for_several_original_words_gets_all_numbers_in_original_order(self):
        out = tagger.tag_verse(['ساکنش'], predicted({0: {'Hb': 4, 'H3427': 3}}), ORIGINAL)
        self.assertEqual(out, [['ساکنش', 'H3427 Hb']])

    def test_same_number_for_different_original_words_is_not_grouped(self):
        out = tagger.tag_verse(['و', 'و'], predicted({0: {'Hc': 0}, 1: {'Hc': 2}}), ORIGINAL)
        self.assertEqual(out, [['و', 'Hc'], ['و', 'Hc']])

    def test_punctuation_breaks_groups(self):
        out = tagger.tag_verse(['ساکن', '،', 'گشتید'], predicted({0: {'H3427': 3}, 2: {'H3427': 3}}), ORIGINAL)
        self.assertEqual(out, [['ساکن', 'H3427'], ['،'], ['گشتید', 'H3427']])

    def test_object_marker_only_tagged_with_et(self):
        original = [['אֶת', 'H853', 'HTo'], ['הָ/אָ֔רֶץ', 'Hd/H776', 'HTd/Ncbsa'], ['נָתַ֖ן', 'H5414', 'HVqp3ms']]
        out = tagger.tag_verse(['زمین', 'را', 'داد'], predicted({0: {'H776': 2}, 1: {'H5414': 3}, 2: {'H5414': 3}}), original)
        self.assertEqual(out, [['زمین', 'H776'], ['را', 'H853'], ['داد', 'H5414']])
        out = tagger.tag_verse(['زمین', 'را', 'داد'], predicted({1: {'H5414': 2}}), ORIGINAL)
        self.assertEqual(out[1], ['را'])

    def test_locked_verse_grouping_keeps_every_tag(self):
        verse = [['ساکن', 'H3427'], ['گشتید', 'H3427'], ['و', 'Hc'], ['و', 'Hc'], ['،'], ['یهوه', 'dvnNm H3068']]
        out = tagger.group_locked_verse(verse, ORIGINAL)
        # Hc occurs twice in the original verse, so the two "و" may be different words.
        self.assertEqual(out, [['ساکن گشتید', 'H3427'], ['و', 'Hc'], ['و', 'Hc'], ['،'], ['یهوه', 'dvnNm H3068']])


class PersianTest(unittest.TestCase):
    def test_light_verbs(self):
        for token in ['کنید', 'می‌دهد', 'داده_است', 'گشتید', 'شده‌ام', 'نمی‌کنند']:
            self.assertTrue(persian.is_light_verb(token), token)
        for token in ['می‌بخشد', 'دید', 'رفته', 'می‌گویم', 'زمین']:
            self.assertFalse(persian.is_light_verb(token), token)

    def test_stemmer_keeps_words_that_only_look_suffixed(self):
        stem = persian.make_stemmer(['پدران'] * 10 + ['پدرانمان', 'آسمان', 'ایمان'] + ['ای'] * 50)
        self.assertEqual(stem('پدرانمان'), 'پدران')
        self.assertEqual(stem('آسمان'), 'آسمان')
        self.assertEqual(stem('ایمان'), 'ایمان')


if __name__ == '__main__':
    unittest.main()


class VariantsTest(unittest.TestCase):
    def test_variant_words_are_merged_in_place(self):
        from retag import variants
        # Jude 22: Tischendorf ἐλέγχετε, NA27/UBS4 ἐλεᾶτε
        base = [['καὶ', 'G2532', 'CONJ'], ['οὓς', 'G3739', 'R-APM'], ['μὲν', 'G3303', 'PRT'],
                ['ἐλέγχετε', 'G1651', 'V-PAM-2P'], ['διακρινομένους', 'G1252', 'V-PMP-APM']]
        whnu = [['και', 'G2532', 'CONJ'], ['ους', 'G3739', 'R-APM'], ['μεν', 'G3303', 'PRT'],
                ['ελεατε', 'G1653', 'V-PAM-2P strongsMorph:G5720'], ['διακρινομενους', 'G1252', 'V-PMP-APM']]
        out = variants.merge(base, whnu, 'WHNU')
        self.assertEqual([w[1] for w in out], ['G2532', 'G3739', 'G3303', 'G1651', 'G1653', 'G1252'])
        self.assertEqual(out[4], ['ελεατε', 'G1653', 'V-PAM-2P', 'WHNU'])

    def test_same_word_under_another_number_is_not_a_variant(self):
        from retag import variants
        base = [['πλεῖον', 'G4183', 'A-ASN-C'], ['ὑμῖν', 'G5210', 'P-2DP']]
        other = [['πλειον', 'G4119', 'A-ASN-C'], ['υμιν', 'G4771', 'P-2DP']]
        self.assertEqual(variants.merge(base, other, 'WHNU'), base)

    def test_numbering_follows_accented(self):
        from retag import variants
        self.assertEqual(variants.normalise_word(['εστιν', 'G2076', 'V-PXI-3S'])[1], 'G1510')
        self.assertEqual(variants.normalise_word(['υμας', 'G5209', 'P-2AP'])[1], 'G5210')
        self.assertEqual(variants.normalise_word(['ημιν', 'G1473', 'P-1DP'])[1], 'G2249')
        self.assertEqual(variants.normalise_word(['αδελφω', 'G0080', 'N-DSM'])[1], 'G80')

    def test_whole_verse_from_variant_text(self):
        from retag import variants
        out = variants.merge([], [['τουτο', 'G3778', 'D-NSN'], [',']], 'TR')
        self.assertEqual(out, [['τουτο', 'G3778', 'D-NSN', 'TR']])


class DisplayTest(unittest.TestCase):
    def test_compounds_are_shown_with_spaces(self):
        from retag import data
        verse = [['او', 'H1931'], ['فرو~گرفت', 'H7363'], ['خواهد_شد', 'H1961'], ['.']]
        self.assertEqual(data.display_verse(verse),
                         [['او', 'H1931'], ['فرو گرفت', 'H7363'], ['خواهد شد', 'H1961'], ['.']])

    def test_token_tags_match_either_form(self):
        from retag import data
        tokens = ['او', 'فرو~گرفت', 'خواهد_شد', '.']
        spaced = [['او', 'H1931'], ['فرو گرفت', 'H7363'], ['خواهد', 'H1961'], ['شد', 'Hc'], ['.']]
        self.assertEqual(data.token_tags(spaced, tokens), ['H1931', 'H7363', 'H1961 Hc', None])
        joined = [['او', 'H1931'], ['فرو~گرفت', 'H7363'], ['خواهد_شد', 'H1961'], ['.']]
        self.assertEqual(data.token_tags(joined, tokens), ['H1931', 'H7363', 'H1961', None])
