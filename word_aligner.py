from tqdm import tqdm
from simalign import SentenceAligner
import pandas as pd
import json

def main():
    def LoadBible(parquet_filename):
        '''Function to read pre-processed farsi bible as pandas dataframe'''
        return pd.read_parquet(f"transformations/{parquet_filename}.parquet")

    def cat(x):
        '''Helper function to concatenate strongs numbers linked to same input word in dataframe'''
        return " ".join(list(filter(lambda item: item is not None, x.astype(str))))

    def Align(row):
        '''Function to use sentence aligner to match input words to strongs words.
        Returns nested list format suitable for json array'''
        trg = row.eng_word
        src = row.word
        alignments = aligner.get_word_aligns(src, trg)
        method_alignments = [(srci, row.strongs[trgi]) for srci,trgi in alignments["itermax"]]
        lookup = {key:value for key, value in pd.DataFrame.from_records(method_alignments).dropna().groupby(0).agg(cat).to_records().tolist()}
        return [list(filter(lambda item: item is not None, [word, lookup[src.index(word)]])) if src.index(word) in lookup  else [word] for word in src]

    # Initiate aligner model
    aligner = SentenceAligner()

    # Load and format english strongs tagged Bible
    kjv = LoadBible("KJV")
    kjv = (
        kjv
        .groupby(["book", "idx_chapter", "idx_verse"])
        [["eng_word", "strongs", "morphology"]]
        .agg(list)
    )

    # Load and format target Farsi Bible
    nmv = LoadBible("nmv_pos_tagged")
    nmv = (
        nmv
        .groupby(["book", "idx_chapter", "idx_verse"])
        [["word"]]
        .agg(list)
    )

    # Combine dataframes for verse by verse iteration using apply
    combined_df = kjv.join(nmv)

    # Match strongs words to farsi words
    tqdm.pandas(desc="Aligning words for each verse in the Bible")
    combined_df["books"] = combined_df.progress_apply(Align, axis=1)

    # Format dataframe for export as json for sync.bible
    out_json = (
        combined_df
        .groupby(["book", "idx_chapter", "idx_verse"])
        [["books"]]
        .agg(list)
        .groupby(["book", "idx_chapter"])
        [["books"]]
        .agg(list)
        .groupby("book")
        [["books"]]
        .agg(list)
        .to_dict()
    )

    # Write output json file
    with open("outputs/NMV_KJV_strongs.json","w",encoding="utf8") as out_f:
        json.dump(out_json, out_f, ensure_ascii=False)
    
    print("Completed. Output written to: outputs/NMV_KJV_strongs.json")

if __name__ == "__main__":
    main()