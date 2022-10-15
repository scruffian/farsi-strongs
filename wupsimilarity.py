import sys

def FindSimilarWords():
    from nltk.corpus import wordnet
    import json
    import pandas as pd
    from copy import deepcopy

    book_name = sys.argv[1]
    eng_version = sys.argv[2]

    with open(f"transformations/NMV_translations_{book_name}.json", encoding="utf8") as f:
        nmv_translations = json.load(f)

    with open(f"inputs/{eng_version}.json") as f:
        eng = json.load(f)

    with open(f"transformations/keyed_words_translations.json") as f:
        keyed_words_translations = json.load(f)

    def flatten(List):
        newList = []
        for obj in List:
            newList.extend(List[obj])
        return newList

    def SemanticSimilarity():
        for book in nmv_translations["books"]:
            for chapter, n_chapter in zip(
                nmv_translations["books"][book],
                range(0,len(nmv_translations["books"][book]))
            ):
                for verse, n_verse in zip(
                    chapter,
                    range(0,len(chapter))
                ):
                    print(f"{book} Chapter {n_chapter +1}:{n_verse +1}")
                    for word, n_word in zip(
                        verse,
                        range(0, len(verse))
                    ):
                        if len(word[1]) > 0:
                            # Get the google translations for this word
                            if word[0] in keyed_words_translations:
                                google_translation_data = keyed_words_translations[ word[0] ]

                                # if there's a transations array then Google has lots of similar words.
                                if len(google_translation_data['translations']) > 0:
                                    # the similar words are keyed by word type, so we need to flatten them.
                                    google_translations = flatten( google_translation_data['translations'] )
                                else :
                                    # if there's no translations we might still have a "translation" key
                                    google_translations = []
                                    google_translations = google_translations.extend( google_translation_data['translation'] )

                                for translated_word in google_translation_data:
                                    translated_word_synsets = wordnet.synsets(translated_word)

                                    for eng_word in eng["books"][book][n_chapter][n_verse]:
                                        eng_word_synsets = wordnet.synsets(eng_word[0])
                                        # TODO - look at options for speeding up... there's a function for getting every possible list pair I think
                                        # Can more generators be worked in? or Recursion? Vectorise? Need less nested iteration.
                                        similarities = []
                                        if translated_word_synsets and eng_word_synsets:
                                            for t_synset in translated_word_synsets:
                                                for e_synset in eng_word_synsets:
                                                    s = t_synset.wup_similarity(e_synset)

                                                    similarities.append(
                                                        s
                                                    )
                                                    # print(f"farsi: {word[0]}, translation: {translated_word}, eng: {eng_word}, similarity: {s}")
                                                    # print(translated_word_synsets)
                                                    # print(eng_word)
                                                    # print(eng_word_synsets)
                                            eng_word_links = pd.DataFrame(
                                                {
                                                    "book":[book],
                                                    "chapter":[n_chapter],
                                                    "verse":[n_verse],
                                                    "word_order":[n_word],
                                                    "farsi_word":[word[0]],
                                                    "possible_translation":[translated_word],
                                                    "eng_word": [eng_word[0]],
                                                    "eng_strongs": [
                                                        eng_word[1] if len(eng_word) > 1 else None
                                                    ],
                                                    "eng_morphology": [
                                                        eng_word[2] if len(eng_word) > 2 else None
                                                    ],
                                                    "max_similarity":[max([s if s else 0 for s in similarities]) if len(similarities) > 0 else 0]
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
                                                    "farsi_word":[word[0]],
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
                                        "farsi_word":[word[0]],
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

    out_json = deepcopy(nmv_translations)
    for book in out_json["books"]:
        for chapter in range(0, len(out_json["books"][book])):
            for verse in range(0, len(out_json["books"][book][chapter])):
                for word in range(0, len(out_json["books"][book][chapter][verse])):
                    if len(out_json["books"][book][chapter][verse][word]) > 1:
                        out_json["books"][book][chapter][verse][word].pop(1)
    for i, row in similarity_max_df.iterrows():
        if row["max_similarity"] == 1 and type(row["eng_strongs"]==str):
            # data = [row["eng_word"], row["eng_strongs"]]
            out_json["books"][row["book"]][row["chapter"]][row["verse"]][row["word_order"]].append(row["eng_strongs"])

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
