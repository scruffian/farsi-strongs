import sys

def FindSimilarWords():
    from nltk.corpus import wordnet
    import json
    import pandas as pd
    from copy import deepcopy
    
    book_name = sys.argv[1]

    with open(f"NMV_translations_{book_name}.json", encoding="utf8") as f:
        nmv_translations = json.load(f)

    with open("ESV.json") as f:
        esv = json.load(f)

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
                            for translated_word in word[1]:
                                translated_word_synsets = wordnet.synsets(translated_word)

                                for esv_word in esv["books"][book][n_chapter][n_verse]:
                                    esv_word_synsets = wordnet.synsets(esv_word[0])
                                    # TODO - look at options for speeding up... there's a function for getting every possible list pair I think
                                    # Can more generators be worked in? or Recursion? Vectorise? Need less nested iteration.
                                    similarities = []
                                    if translated_word_synsets and esv_word_synsets:
                                        for t_synset in translated_word_synsets:
                                            for e_synset in esv_word_synsets:
                                                s = t_synset.wup_similarity(e_synset)
                                                similarities.append(
                                                    s
                                                )
                                                # print(f"farsi: {word[0]}, translation: {translated_word}, esv: {esv_word}, similarity: {s}")
                                                # print(translated_word_synsets)
                                                # print(esv_word)
                                                # print(esv_word_synsets)
                                        esv_word_links = pd.DataFrame(
                                            {
                                                "book":[book],
                                                "chapter":[n_chapter],
                                                "verse":[n_verse],
                                                "word_order":[n_word],
                                                "farsi_word":[word[0]],
                                                "possible_translation":[translated_word],
                                                "esv_word": [esv_word[0]], 
                                                "esv_strongs": [
                                                    esv_word[1] if len(esv_word) > 1 else None
                                                ],
                                                "esv_morphology": [
                                                    esv_word[2] if len(esv_word) > 2 else None
                                                ],
                                                "max_similarity":[max(similarities)]
                                            }
                                        )
                                        yield esv_word_links
                                    else:
                                        esv_word_links = pd.DataFrame(
                                            {
                                                "book":[book],
                                                "chapter":[n_chapter],
                                                "verse":[n_verse],
                                                "word_order":[n_word],
                                                "farsi_word":[word[0]],
                                                "possible_translation":[None],
                                                "esv_word": [None], 
                                                "esv_strongs": [None],
                                                "esv_morphology": [None],
                                                "max_similarity":[0]
                                            }
                                        )
                                        yield esv_word_links
                        else:
                            esv_word_links = pd.DataFrame(
                                {
                                    "book":[book],
                                    "chapter":[n_chapter],
                                    "verse":[n_verse],
                                    "word_order":[n_word],
                                    "farsi_word":[word[0]],
                                    "possible_translation":[None],
                                    "esv_word": [None], 
                                    "esv_strongs": [None],
                                    "esv_morphology": [None],
                                    "max_similarity":[0]
                                }
                            )
                            yield esv_word_links
                            
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
        if row["max_similarity"] == 1:
            # data = [row["esv_word"], row["esv_strongs"]]
            out_json["books"][row["book"]][row["chapter"]][row["verse"]][row["word_order"]].append(row["esv_strongs"])

    with open(f"NMV_strongs_{book_name}.json","w",encoding="utf8") as out_f:
        json.dump(out_json, out_f, ensure_ascii=False)

if __name__ == "__main__":
    if len(sys.argv) <= 1:
        print('Please specify a book')
        sys.exit()
    else: 
        FindSimilarWords()
        print("Done")