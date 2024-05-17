"""Final corpora generation.

@author Christoph Broschinski (https://github.com/cbroschinski)

This script generates the final form of the corpora used by Annif for
machine learning and testing. It is meant to work on the results of
process_reduced_records.py with the -C option (corpus generation). The
script fulfils the following tasks:

1) Extract a random subset of documents which form the evaluation corpus.
This corpus may be randomly sampled OR can be specifically constructed to
contain only BASE documents which have already been classified by the
legacy baseclf classifier.
Its purpose is to enable a comparison between the results of baseclf and
the new annif-based system. Note that this corpus has no other usage,
so when doing a re-training of Annif later, generation of the evaluation
corpus can safely be omitted (eval_corpus_ratio: 0.0)

2) Extract a random subset of documents which form the test corpus. This
corpus is used by Annif to test the performance of its trained classifier
backends.

3) Use the remaining documents to create the Annif training corpus.

4) Create CSV/JSON files to store document metadata for all 3 corpora.

Per default, the final corpora will be created in language-specific
directories inside RAW_CORPUS_PATH, so f. e. the English training
corpus can be found in:

data/prepared_corpora/en/train

To minimize disk usage, soft links to the raw corpus directory will
be used instead of copying files.
"""

import argparse
import csv
import json
import sys
import os

from os.path import join
from random import sample

RAW_CORPUS_PATH = "../data/corpus"
TARGET_PATH = "../data/prepared_corpora"

HELP_STRINGS = {
    "test_corpus_ratio": "Ratio of the documents which go into the test corpus. Default: 0.1",
    "eval_corpus_ratio": "Ratio of the documents which go into the evaluation corpus. Note that if the evaluation corpus is not randomized, the final size may be lower than this. Default: 0.1",
    "clear": "Delete an existing corpus before preparation",
    "german": "Prepare the german corpora",
    "english": "Prepare the english corpora",
    "non-random": "Do not create an random evaluation corpus, use only documents classfied by baseclf instead"
}

# We take up to 5 DDC classes contained in the Document for comparison.
EVAL_CSV_FIELDNAMES = ["document", "doc_class_1", "doc_class_2", "doc_class_3", "doc_class_4", "doc_class_5","annif_class_1", "annif_class_2", "baseclf_class_1", "baseclf_class_2"]

def _extrakt_keys(key_file_path):
    res = []
    with open(key_file_path, "r", encoding="utf-8") as key_file:
        for line in key_file:
            res.append(line.replace("\n", ""))
    return res

def _clear_directory(dir_path):
    current_dir = os.getcwd()
    os.chdir(dir_path)
    for file_name in os.listdir("."):
        os.remove(file_name)
    os.chdir(current_dir)

def _create_eval_corpus(lang, documents, clear=False):
    eval_docs = []
    target_dir = join(TARGET_PATH, lang, "eval")
    if os.path.isdir(target_dir):
        if clear:
            print("Deleting old eval corpus...")
            _clear_directory(target_dir)
    else:
        os.makedirs(target_dir)
    current_dir = os.getcwd()
    os.chdir(target_dir)
    relative_target_path = join("../../../corpus/", lang)
    for doc in documents:
        doc_data = {"document": doc}
        autokey_path = join(relative_target_path, doc + ".autokey")
        autokeys = []
        if os.path.isfile(autokey_path):
            autokeys = _extrakt_keys(autokey_path)
        doc_data["auto_keys"] = autokeys
        doc_key_path = join(relative_target_path, doc + ".key")
        doc_keys = _extrakt_keys(doc_key_path)
        doc_data["document_keys"] = doc_keys
        for file_ext in [".txt", ".key"]:
            file_name = doc + file_ext
            try:
                os.symlink(join(relative_target_path, file_name), file_name)
            except FileExistsError as fee:
                print("Error: " + str(fee) + "\nHint:use -c option to clear old corpora beforehand.")
                sys.exit()
        eval_docs.append(doc_data)
    os.chdir(current_dir)
    json_path = join(TARGET_PATH, lang, "eval_corpus.json")
    with open(json_path, "w", encoding="utf-8") as json_file:
        json_file.write(json.dumps(eval_docs, indent=2, sort_keys=True, ensure_ascii=False))

def _create_annif_corpus(corpus_type, lang, documents, clear=False):
    if corpus_type not in ["train", "test"]:
        print('Error: Corpus type must be either "train" or "test"')
        sys.exit()
    target_dir = join(TARGET_PATH, lang, corpus_type)
    if os.path.isdir(target_dir):
        if clear:
            print("Deleting old " + corpus_type + " corpus...")
            _clear_directory(target_dir)
    else:
        os.makedirs(target_dir)
    csv_path = join(TARGET_PATH, lang, corpus_type + "_corpus.csv")
    csv_file = open(csv_path, "w", encoding="utf-8")
    csv_writer = csv.writer(csv_file)
    csv_writer.writerow(["document", "annif_class_1", "annif_class_2"])
    current_dir = os.getcwd()
    os.chdir(target_dir)
    relative_target_path = join("../../../corpus/", lang)
    for doc in documents:
        csv_writer.writerow([doc, "", ""])
        for file_ext in [".txt", ".key"]:
            file_name = doc + file_ext
            try:
                os.symlink(join(relative_target_path, file_name), file_name)
            except FileExistsError as fee:
                print("Error: " + str(fee) + "\nHint:use -c option to clear old corpora beforehand.")
                sys.exit()
    os.chdir(current_dir)
    csv_file.close()

def _create_corpora(lang, args):
    print("Analyzing raw corpus '{}'...".format(lang))
    raw_corpus_path = join(RAW_CORPUS_PATH, lang)
    files = os.listdir(raw_corpus_path)
    basenames_no_autokey = []
    basenames_autokey = []
    for count, filename in enumerate(files):
        if count % 10000 == 0:
            print("{} files".format(count))
        basename = os.path.splitext(filename)[0]
        autokey_file_path = join(raw_corpus_path, (basename + ".autokey"))
        if os.path.isfile(autokey_file_path):
            if basename not in basenames_autokey:
                basenames_autokey.append(basename)
        else:
            if basename not in basenames_no_autokey:
                basenames_no_autokey.append(basename)
    corpus_size = len(basenames_no_autokey) + len(basenames_autokey)
    msg = "Raw corpus '{}' consists of {} documents, {} have been classified by baseclf"
    print(msg.format(lang, corpus_size, len(basenames_autokey)))
    eval_corpus_size = min(round(corpus_size * args.eval_corpus_ratio), len(basenames_autokey))
    if eval_corpus_size > 0:
        len_autokey_before = len(basenames_autokey)
        msg = "Creating evaluation corpus, target size is {} documents ({} %)"
        print(msg.format(eval_corpus_size, round(eval_corpus_size / corpus_size * 100, 2)))
        if args.non_random:
            eval_docs = sample(basenames_autokey, eval_corpus_size)
        else:
            full_sample = basenames_no_autokey + basenames_autokey
            eval_docs = sample(full_sample, eval_corpus_size)
        _create_eval_corpus(lang, eval_docs, args.clear)
        basenames_autokey = [filename for filename in basenames_autokey if filename not in eval_docs]
        basenames_no_autokey = [filename for filename in basenames_no_autokey if filename not in eval_docs]
        msg = "{} out of {} documents in the evaluation corpus have been classified by baseclf"
        print(msg.format(len_autokey_before - len(basenames_autokey), len(eval_docs)))
    remaining_basenames = basenames_no_autokey + basenames_autokey
    test_corpus_size = round(corpus_size * args.test_corpus_ratio)
    if test_corpus_size > 0:
        msg = "Creating test corpus, target size is {} documents ({} %)"
        print(msg.format(test_corpus_size, round(test_corpus_size / corpus_size * 100, 2)))
        test_docs = sample(remaining_basenames, test_corpus_size)
        _create_annif_corpus("test", lang, test_docs, args.clear)
        remaining_basenames = [filename for filename in remaining_basenames if filename not in test_docs]
    msg = "Creating training corpus, target size is {} documents"
    print(msg.format(len(remaining_basenames)))
    _create_annif_corpus("train", lang, remaining_basenames, args.clear)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-t", "--test_corpus_ratio", type=float, default=0.1, help=HELP_STRINGS["test_corpus_ratio"])
    parser.add_argument("-e", "--eval_corpus_ratio", type=float, default=0.1, help=HELP_STRINGS["eval_corpus_ratio"])
    parser.add_argument("-c", "--clear", action="store_true", help=HELP_STRINGS["clear"])
    parser.add_argument("-n", "--non-random", action="store_true", help=HELP_STRINGS["non-random"])
    parser.add_argument("-D", "--german", action="store_true", help=HELP_STRINGS["german"])
    parser.add_argument("-E", "--english", action="store_true", help=HELP_STRINGS["english"])
    args = parser.parse_args()

    if args.test_corpus_ratio < 0.0 or args.test_corpus_ratio > 1.0:
        print("Error: test_corpus_ratio must be a float from 0.0 to 1.0")
        sys.exit()
    if args.eval_corpus_ratio < 0.0 or args.eval_corpus_ratio > 1.0:
        print("Error: eval_corpus_ratio must be a float from 0.0 to 1.0")
        sys.exit()
    if args.eval_corpus_ratio + args.test_corpus_ratio > 1.0:
        print("Error: The sum of eval_corpus_ratio and test_corpus_ratio may not exceed 1.0")
        sys.exit()
    langs = []
    if args.german:
        langs.append("de")
    if args.english:
        langs.append("en")
    if not langs:
        print("Error: Either a German (-D) or English (-E) corpus must be created (or both)")
        sys.exit()

    for lang in langs:
        _create_corpora(lang, args)
