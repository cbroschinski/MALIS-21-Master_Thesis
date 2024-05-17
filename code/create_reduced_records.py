"""BASE dump record reduction and reformatting.

@author Christoph Broschinski (https://github.com/cbroschinski)

This script operates on a directory containing an untar-ed
BASE dump (a collection of ListRecord files, compressed with bzip2).
Its purpose is to decompress the files on-the-fly, extract the DC fields
which are relevant for the purpose of the master thesis project
and write them to output files in JSON format ("reduced records").
"""

import argparse
import bz2
import json
import os
import re

from copy import deepcopy
from math import inf
import multiprocessing as mp
from time import sleep

ddc_regex = re.compile(r">\s*(info:eu-repo/classification/ddc/|ddc:\s*)?\d\d\d\s*<")
record_regex = re.compile(r"<record>.*?</record>", re.DOTALL)

target_regexes = {
    "title": re.compile(r"<dc:title>(.*?)</dc:title>"),
    "description": re.compile(r"<dc:description>(.*?)</dc:description>"),
    "subject": re.compile(r"<dc:subject>(.*?)</dc:subject>"),
    "classcode": re.compile(r"<base_dc:classcode type=\"ddc\">(.*?)</base_dc:classcode>"),
    "autoclasscode": re.compile(r"<base_dc:autoclasscode type=\"ddc\">(.*?)</base_dc:autoclasscode>"),
    "identifier": re.compile(r"<identifier>(.*?)</identifier>")
}

output_template = {
    "title": [],
    "description": [],
    "subject": [],
    "classcode": [],
    "autoclasscode": [],
    "identifier": []
}

PROCESS_POOL = []
CONTENT_WAITING_QUEUE = []
MAX_PROCESSES = 8

BASE_DUMP_DIR = "../data/base_dump"
TARGET_DIR = "../data/reducedListRecords"

def process_content(content, filename):
    records = record_regex.findall(content)
    out_content = []
    for record in records:
        output = deepcopy(output_template)
        for target, regex in target_regexes.items():
            match = regex.findall(record)
            output[target] = list(match)
        out_content.append(output)
    path = os.path.join(TARGET_DIR, "Reduced" + filename)
    out_string = json.dumps(out_content, indent=2, ensure_ascii=False)
    with open(path, "w", encoding="utf-8") as o:
        o.write(out_string)

def _cleanup_process_pool():
    global PROCESS_POOL
    still_running = []
    for process in PROCESS_POOL:
        if process.is_alive():
            still_running.append(process)
    PROCESS_POOL = still_running

def _start_new_process():
    global CONTENT_WAITING_QUEUE, PROCESS_POOL, MAX_PROCESSES
    if len(PROCESS_POOL) < MAX_PROCESSES:
        data = CONTENT_WAITING_QUEUE.pop()
        p = mp.Process(target=process_content, args=(data[0], data[1],), name="Process_" + data[1])
        PROCESS_POOL.append(p)
        p.start()
        number = int(data[1].split(".")[1])
        if number % 10 == 0:
            print("started process " + str(p))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--processes", type=int, help="Max number of concurrent processes (Default: " + str(MAX_PROCESSES) + ")")
    parser.add_argument("-s", "--start", type=int, default=0, help="ListRecords start number")
    parser.add_argument("-e", "--end", type=int, default=inf, help="ListRecords end number")
    parser.add_argument("-o", "--overwrite", action="store_true", help="Overwrite existing result files")
    args = parser.parse_args()
    if not os.path.isdir(TARGET_DIR):
        os.mkdir(TARGET_DIR)
    if args.processes:
        MAX_PROCESSES = args.processes

    mp.set_start_method('fork')
    files = sorted(os.listdir(BASE_DUMP_DIR))
    start_msg = "Processing ListRecords with {} concurrent processes, start index {}, end index {}"
    print(start_msg.format(MAX_PROCESSES, args.start, args.end))
    for full_name in files:
        components = full_name.split(".")
        if components[0] != "ListRecords":
            continue
        file_number = int(components[1])
        file_name = components[0] + "." + components[1]
        if args.start > file_number or args.end < file_number:
            continue
        if not args.overwrite and os.path.isfile(os.path.join(TARGET_DIR, "Reduced" + file_name)):
            continue
        with bz2.open(os.path.join(BASE_DUMP_DIR, full_name), mode="rt", encoding="utf-8") as f:
            content = f.read()
            CONTENT_WAITING_QUEUE.append((content, file_name))
            _cleanup_process_pool()
            _start_new_process()
    print("All Files read, processing remaining content...")
    while len(CONTENT_WAITING_QUEUE) > 0:
        _cleanup_process_pool()
        _start_new_process()
        sleep(0.1)
    print("Waiting for all processes to finish...")
    while len(PROCESS_POOL) > 0:
        _cleanup_process_pool()
        sleep(0.1)
    print("Done!")
