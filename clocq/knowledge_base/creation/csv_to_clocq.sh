#!/bin/bash 
# create directory for temporary data
mkdir tmp_data
# extract a dictionary: unique-predicate-ID -> qualifiers
python csv_to_clocq/extract_qualifiers.py
# extract a list of unique wikidata IDs/literals
python csv_to_clocq/extract_distinct_nodes.py
# extract dictionaries: Wikidata ID/literal -> INT (and inverse)
python csv_to_clocq/create_int_dicts.py
# extract the KB list expected by the CLOCQ framework
python csv_to_clocq/create_KB_list.py
# convert the json-dicts to pkl files
python csv_to_clocq/transform_json_to_pickle.py