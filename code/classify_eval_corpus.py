"""Evaluation corpus classification by Annif

@author Christoph Broschinski (https://github.com/cbroschinski)

This script performs a classification of a language-specific
eval corpus by sending it to Annif.

The eval corpus is selected automatically by setting the
language parameter (-c). 
Before running this script, make sure that Annif is running
on localhost (standard port 5000) and the selected backend
has been trained.

Classification results will be written to a CSV file in the
PREP_CORPORA_DIR (see command line message after finishing).
"""
import argparse
import csv
import json
from os.path import join

import requests

PREP_CORPORA_DIR = "../data/prepared_corpora"
DDC_VOCAB_PATH = "en_ddc.tsv"

ANNIF_URL = "http://localhost:5000"

def _load_ddc_vocab():
    vocab = {}
    with open(DDC_VOCAB_PATH, encoding="utf-8") as f:
        for line in f:
            components = line.split("\t")
            classname = components[1].replace("\n", "")
            vocab[classname] = components[0]
    return vocab

def _print_stats(results, args):
    print("Processing finished, results:\n")
    msg = "Annif Settings:\n - Backend: {}\n - Corpus Language: {}\n - Limit: {}\n - Threshold: {}"
    print(msg.format(args.backend, args.corpus_language, args.limit, args.threshold))
    msg = "Documents sent to Annif for classification: {}"
    print(msg.format(len(results)))
    baseclf_docs = [x["auto_keys"] for x in results if len(x["auto_keys"]) > 0]
    msg = "Number of documents with a baseclf classification: {} ({}%)"
    print(msg.format(len(baseclf_docs), round(len(baseclf_docs)*100/len(results), 2)))
    annif_docs = [x["annif_keys"] for x in results if len(x["annif_keys"]) > 0]
    msg = "Number of documents which could be classified by Annif: {} ({}%)"
    print(msg.format(len(annif_docs), round(len(annif_docs)*100/len(results), 2)))
    both_docs =  [(x["annif_keys"], x["auto_keys"]) for x in results if len(x["annif_keys"]) > 0 and len(x["auto_keys"]) > 0]
    msg = "Number of documents with both an Annif and a baseclf classification: {} ({}%)"
    print(msg.format(len(both_docs), round(len(both_docs)*100/len(results), 2)))
    baseclf_correct = [x["auto_keys"] for x in results if sorted(x["auto_keys"]) == sorted(x["document_keys"])]
    msg = "Number of documents classified correctly by baseclf (full match of all classes): {} ({}%)"
    print(msg.format(len(baseclf_correct), round(len(baseclf_correct)*100/len(results), 2)))
    annif_correct = [x["annif_keys"] for x in results if sorted(x["annif_keys"]) == sorted(x["document_keys"])]
    msg = "Number of documents classified correctly by Annif (full match of all classes): {} ({}%)"
    print(msg.format(len(annif_correct), round(len(annif_correct)*100/len(results), 2)))
    msg = "baseclf success rate: {}/{} ({}%)"
    print(msg.format(len(baseclf_correct), len(baseclf_docs), round(len(baseclf_correct)*100/len(baseclf_docs), 2)))
    msg = "Annif success rate: {}/{} ({}%)"
    print(msg.format(len(annif_correct), len(annif_docs), round(len(annif_correct)*100/len(annif_docs), 2)))

def _eval_corpus(args):
    json_path = join(PREP_CORPORA_DIR, args.corpus_language, "eval_corpus.json")
    results = []
    suggest_url = ANNIF_URL + "/v1/projects/" + args.backend + "/suggest"
    with open(json_path, "r", encoding="utf-8") as json_file:
        json_content = json.load(json_file)
        docs_to_process = int(len(json_content) * args.percentage)
        msg = "Starting classification of eval corpus '{}'. Corpus consists of {} documents, {} ({}%) will be processed."
        msg = msg.format(args.corpus_language, len(json_content), docs_to_process, args.percentage * 100)
        print(msg)
        for doc_data in json_content:
            doc_name = doc_data["document"]
            doc_path = join(PREP_CORPORA_DIR, args.corpus_language, "eval", doc_name + ".txt")
            text = None
            with open(doc_path, "r", encoding="utf-8") as doc:
                text = doc.read()
            post_data = {
                "limit": args.limit,
                "threshold": args.threshold
            }
            post_data["text"] = text
            #print(post_data)
            res = requests.post(suggest_url, data=post_data)
            content = json.loads(res.text)
            #print(content)
            doc_data["annif_keys"] = []
            for result in content["results"]:
                doc_data["annif_keys"].append(result["label"])
            #print(res.text)
            results.append(doc_data)
            if len(results) % 100 == 0:
                msg = "{} documents processed ({}%)"
                msg = msg.format(len(results), round(len(results)*100/docs_to_process, 2))
                print(msg)
            if len(results) >= docs_to_process:
                break
    _print_stats(results, args)
    out_file_name = "eval_corpus_classified_{}_{}_{}.csv"
    out_file_name = out_file_name.format(args.backend, args.limit, args.threshold)
    out_csv_path = join(PREP_CORPORA_DIR, args.corpus_language, out_file_name)
    with open(out_csv_path, "w", encoding="utf-8") as csv_file:
        vocab = _load_ddc_vocab()
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow(["document", "document_classes", "baseclf_classes", "annif_classes"])
        for doc in results:
            line = [doc["document"]]
            for keys in ["document_keys", "auto_keys", "annif_keys"]:
                res = "NA"
                if doc[keys]:
                    class_keys = [vocab[classname] for classname in doc[keys]]
                    res = ":".join(class_keys)
                line.append(res)
            csv_writer.writerow(line)
    print("Full classification results of this run were written to " + out_csv_path)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("backend", help="The annif backend to use. The backend language should correspond to the language of the evaluation corpus (f.e. 'de-omikuji' should be used with '-c de')")
    parser.add_argument("-c", "--corpus_language", choices=["de", "en"], help="select which language version of the evaluation corpora to use")
    parser.add_argument("-l", "--limit", type=int, default=2, help="The upper limit of suggested classes when querying annif, see the Annif Rest API for more details. Default: 2")
    parser.add_argument("-t", "--threshold", type=float, default=0.5, help="The lower limit of the confidence score required to suggest a class when querying annif, see the Annif Rest API for more details. Default: 0.5")
    parser.add_argument("-p", "--percentage", type=float, default=1.0, help="Percentage of the corpus to classify (default: full corpus (1.0))")
    args = parser.parse_args()
    _eval_corpus(args)

if __name__ == '__main__':
    main()
