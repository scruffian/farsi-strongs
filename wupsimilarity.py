import sys

def FindSimilarWords():
    from nltk.corpus import wordnet
    import json
    import pandas as pd
    from copy import deepcopy
    from spacy.lang.fa import Persian
    import numpy as np

    book_name = sys.argv[1]
    eng_version = sys.argv[2]

    # initiate spacy persian language class
    fa_nlp = Persian()

    with open(f"inputs/NMV.json", encoding="utf8") as f:
        nmv = json.load(f)

    with open(f"inputs/{eng_version}.json") as f:
        eng = json.load(f)

    with open(f"transformations/keyed_words_translations.json", encoding="utf8") as f:
        keyed_words_translations = json.load(f)

    def SemanticSimilarity():
        # allow whole bible to be run
        if book_name == "Whole Bible":
            target_books = list(nmv["books"].keys())
        else:
            target_books = [book_name]
            
        for book in target_books:
            for chapter, n_chapter in zip(
                nmv["books"][book],
                range(0,len(nmv["books"][book]))
            ):
                for verse, n_verse in zip(
                    chapter,
                    range(0,len(chapter))
                ):
                    print(f"{book} Chapter {n_chapter +1}:{n_verse +1}")
                    # nmv verses need to be tokenised as they are strings not lists of words
                    # tokens should be words
                    verse_tokens = fa_nlp.tokenizer(verse)
                    for token, n_word in zip(
                        verse_tokens.__iter__(), # syntax to access spacy tokens as iterator
                        range(0, verse_tokens.__len__()) # syntax for length of spacy Doc class that contains tokens
                    ):
                        word = token.__str__()
                        # Get the google translations for this word
                        if word in keyed_words_translations:
                            google_translation_data = keyed_words_translations[word]

                            # if there's no translations we might still have a "translation" key
                            google_translations = [google_translation_data['translation']]

                            # if there's a transations list then Google has lots of similar words.
                            if len(google_translation_data['translations']) > 0:
                                # the similar words are keyed by word type, so we need to flatten them.
                                (
                                    google_translations
                                    .extend(
                                        [
                                            value for (key, values) 
                                            in google_translation_data['translations'].items() 
                                            for value in values
                                        ]
                                    )
                                )

                            for translated_word in google_translations:
                                translated_word_synsets = wordnet.synsets(translated_word)

                                for eng_word in eng["books"][book][n_chapter][n_verse]:
                                    eng_word_synsets = wordnet.synsets(eng_word[0])
                                    # TODO - look at options for speeding up. Vectorise? Need less nested iteration.
                                    if translated_word_synsets and eng_word_synsets:
                                        similarities = (
                                            t_synset.wup_similarity(e_synset) for e_synset 
                                            in eng_word_synsets 
                                            for t_synset in translated_word_synsets
                                        )

                                        eng_word_links = pd.DataFrame(
                                            {
                                                "book":[book],
                                                "chapter":[n_chapter],
                                                "verse":[n_verse],
                                                "word_order":[n_word],
                                                "farsi_word":[word],
                                                "possible_translation":[translated_word],
                                                "eng_word": [eng_word[0]],
                                                "eng_strongs": [
                                                    eng_word[1] if len(eng_word) > 1 else None
                                                ],
                                                "eng_morphology": [
                                                    eng_word[2] if len(eng_word) > 2 else None
                                                ],
                                                "max_similarity":[max(similarities)]
                                            }
                                        )
                                        yield eng_word_links
                                    else:
                                        eng_word_links = pd.DataFrame(
                                            {
                                                "book":[book],
                                                "chapter":[n_chapter],
                                                "verse":[n_verse],
                                                "word_order":[n_word],
                                                "farsi_word":[word],
                                                "possible_translation":[None],
                                                "eng_word": [None],
                                                "eng_strongs": [None],
                                                "eng_morphology": [None],
                                                "max_similarity":[0]
                                            }
                                        )
                                        yield eng_word_links
                        else:
                            eng_word_links = pd.DataFrame(
                                {
                                    "book":[book],
                                    "chapter":[n_chapter],
                                    "verse":[n_verse],
                                    "word_order":[n_word],
                                    "farsi_word":[word],
                                    "possible_translation":[None],
                                    "eng_word": [None],
                                    "eng_strongs": [None],
                                    "eng_morphology": [None],
                                    "max_similarity":[0]
                                }
                            )
                            yield eng_word_links

    similarity_df = pd.concat(SemanticSimilarity()).set_index(["book","chapter","verse","farsi_word"])
    similarity_max_df = (
        similarity_df
        .sort_values(
            by="max_similarity"
        )
        .reset_index()
        .drop_duplicates(
            subset=["book","chapter","verse","farsi_word"],
            keep="last"
        )
    )

    similarity_max_df["word"] = (
        np.where(
            similarity_max_df.max_similarity==1,
            similarity_max_df
            [["farsi_word","eng_strongs","max_similarity"]]
            .apply(list,axis=1),
            similarity_max_df.farsi_word
        )
    )

    similarity_max_df = (
        similarity_max_df
        .groupby(["book", "chapter", "verse"])
        [["word"]]
        .agg(list)
        .reset_index()
        .groupby(["book", "chapter"])
        [["word"]]
        .agg(list)
        .reset_index()
        .groupby("book")
        [["word"]]
        .agg(list)
        .reset_index()
    )

    out_json = {"books":{}}
    for i, row in similarity_max_df.iterrows():
        out_json["books"][row["book"]]=row["word"]

    with open(f"transformations/NMV_{eng_version}_strongs_{book_name}.json","w",encoding="utf8") as out_f:
        json.dump(out_json, out_f, ensure_ascii=False)

if __name__ == "__main__":
    if len(sys.argv) <= 1:
        print('Please specify a book')
        sys.exit()
    elif len(sys.argv) <= 2:
        print('Please specify an english version')
        sys.exit()
    else:
        FindSimilarWords()
        print("Done")
