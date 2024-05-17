"""Statistics file aggregation

@author Christoph Broschinski (https://github.com/cbroschinski)

This script aggregates the statistics files in STATS_DIR and
creates a number of CSV files in ANALYZE_DIR, summarizing
different aspects of the analyzed BASE dump.
"""
import csv
import json
import os
import sys

from copy import deepcopy
from process_reduced_records import Stats

STATS_DIR = "../data/stats"
ANALYZE_DIR = "../analyze"

def _get_nested_dict(top_dict, path):
    current_dict = top_dict
    for path_element in path:
        current_dict = current_dict[path_element]
    return current_dict

def create_summarized_stats():
    summarized_stats = deepcopy(Stats.STATS_TEMPLATE)
    stat_files = sorted(os.listdir(STATS_DIR))
    for stat_file in stat_files:
        with open(os.path.join(STATS_DIR, stat_file), encoding="utf-8") as f:
            try:
                content = json.load(f)
                path_list = []
                for category in content.keys():
                    path_list.append([category])
                while len(path_list) > 0:
                    path = path_list.pop()
                    bottom_level = _get_nested_dict(content, path)
                    if type(bottom_level) == type({}):
                        for next_level in bottom_level.keys():
                            path_list.append(list(path) + [next_level])
                    else:
                        key = path.pop()
                        parent_dict = _get_nested_dict(summarized_stats, path)
                        if key not in parent_dict:
                            parent_dict[key] = bottom_level
                        else:
                            parent_dict[key] += bottom_level

            except json.decoder.JSONDecodeError as de:
                print(str(de))
                sys.exit()
    with open(os.path.join(ANALYZE_DIR, "summarized_stats.json"), "w", encoding="utf-8") as sum_file:
        sum_file.write(json.dumps(summarized_stats, indent=2, sort_keys=True, ensure_ascii=False))
    return summarized_stats

def extract_corpus_stats(summarized_stats):
    with open(os.path.join(ANALYZE_DIR, "corpus_stats.csv"), "w", encoding="utf-8") as corpus_file:
        writer = csv.writer(corpus_file)
        writer.writerow(["lang", "ddc_class", "desc_length"])
        for lang in summarized_stats["corpus"].keys():
            classcode_dict = summarized_stats["corpus"][lang]["classcodes"]
            for classcode, desc_length_list in classcode_dict.items():
                for desc_length in desc_length_list:
                    writer.writerow([lang, classcode, desc_length])
    with open(os.path.join(ANALYZE_DIR, "corpus_single_class_stats.csv"), "w", encoding="utf-8") as s_file:
        writer = csv.writer(s_file)
        writer.writerow(["lang", "ddc_class", "count"])
        collected_classes = {
            "de": {},
            "en": {}
        }
        for lang in summarized_stats["corpus"].keys():
            classcode_dict = summarized_stats["corpus"][lang]["classcodes"]
            for class_names, desc_length_list in classcode_dict.items():
                classes = class_names.split(":")
                count = len(desc_length_list)
                for class_name in classes:
                    if class_name not in collected_classes[lang]:
                        collected_classes[lang][class_name] = count
                    else:
                        collected_classes[lang][class_name] += count
        for lang, class_dict in collected_classes.items():
            for single_class, collected_count in class_dict.items():
                writer.writerow([lang, single_class, collected_count])

def extract_classcode_stats(summarized_stats):
    for category in summarized_stats["ddc_data"].keys():
        file_path = os.path.join(ANALYZE_DIR, category + "_stats.csv")
        with open(file_path, "w", encoding="utf-8") as out_file:
            writer = csv.writer(out_file)
            writer.writerow([category, "count"])
            for code, count in summarized_stats["ddc_data"][category]["codes"].items():
                writer.writerow([code, count])
        s_file_path = os.path.join(ANALYZE_DIR, category + "_single_class_stats.csv")
        with open(s_file_path, "w", encoding="utf-8") as out_file:
            writer = csv.writer(out_file)
            writer.writerow([category, "count"])
            collected_classes = {}
            for code, count in summarized_stats["ddc_data"][category]["codes"].items():
                classes = code.split(":")
                for class_name in classes:
                    if class_name not in collected_classes:
                        collected_classes[class_name] = count
                    else:
                        collected_classes[class_name] += count
            for single_class, collected_count in collected_classes.items():
                writer.writerow([single_class, collected_count])

def extract_language_stats(summarized_stats):
    with open(os.path.join(ANALYZE_DIR, "language_stats.csv"), "w", encoding="utf-8") as out_file:
        writer = csv.writer(out_file)
        writer.writerow(["min_length", "detection", "lang", "count"])
        for min_length in ["desc_min_length", "not_desc_min_length"]:
            for detection in ["all", "reliable"]:
                for lang, count in summarized_stats["languages"][min_length][detection].items():
                    writer.writerow([min_length, detection, lang, count])

def extract_processing_stats(summarized_stats):
    with open(os.path.join(ANALYZE_DIR, "processing_stats.csv"), "w", encoding="utf-8") as out_file:
        writer = csv.writer(out_file)
        writer.writerow(["processing_result", "count"])
        # Write events in order of processing pipeline
        for event in ["min_length", "no_classcodes", "lang_detection_failure", "lang_detection_unreliable", "lang_min_confidence", "other_lang", "eligible"]:
            writer.writerow([event, summarized_stats["processing_stats"][event]])

def extract_description_stats(summarized_stats):
    with open(os.path.join(ANALYZE_DIR, "description_num_per_record_stats.csv"), "w", encoding="utf-8") as out_file:
        writer = csv.writer(out_file)
        writer.writerow(["num_per_record", "count"])
        for num_per_record, count in summarized_stats["descriptions"]["num_descs_per_record"].items():
            writer.writerow([num_per_record, count])
    with open(os.path.join(ANALYZE_DIR, "description_length_stats.csv"), "w", encoding="utf-8") as out_file:
        writer = csv.writer(out_file)
        writer.writerow(["length_bin", "length_bin_center", "count"])
        for length_bin, count in summarized_stats["descriptions"]["combined_desc_lengths"].items():
            bin_center = 0
            if length_bin != "0":
                bounds = length_bin.split("-")
                bin_center = (float(bounds[0]) + float(bounds[1])) / 2
            writer.writerow([length_bin, bin_center, count])

if __name__ == '__main__':
    if not os.path.isdir(ANALYZE_DIR):
        os.mkdir(ANALYZE_DIR)
    sum_stats = create_summarized_stats()
    extract_corpus_stats(sum_stats)
    extract_description_stats(sum_stats)
    extract_classcode_stats(sum_stats)
    extract_language_stats(sum_stats)
    extract_processing_stats(sum_stats)
