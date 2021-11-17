Fact-based approach

Run: bash csv_to_clocq.sh
	=> nohup bash csv_to_clocq.sh &

Input: wikidata_dump csv
1. csv_to_clocq/extract_qualifiers.py
2. csv_to_clocq/extract_distinct_nodes.py
3. csv_to_clocq/create_int_dicts.py
4. csv_to_clocq/create_KG_list.py
5. csv_to_clocq/create_ngb_fact_index.py
Output: KG list that can be loaded with KnowledgeGraph.py class


