import json
import pickle
import re

HIGHEST_ID = 92114576
ENT_PATTERN = re.compile('^Q[0-9]+$')
PRE_PATTERN = re.compile('^P[0-9]+$')

with open("dicts/entity_nodes.pickle", "rb") as infile:
	entities_dict = pickle.load(infile)

with open("dicts/pred_nodes.pickle", "rb") as infile:
	predicates_dict = pickle.load(infile)

def item_to_integer(item):
	try:
		if item[0] == "Q" and re.match(ENT_PATTERN, item):
			return int(entities_dict[item])
		elif item[0] == "P" and re.match(PRE_PATTERN, item):
			return int(predicates_dict[item])
		elif len(item) < 40:
			return int(-literals_dict[item])
	except:
		return None

def json_to_encoded_pickle(json_path, pickle_path):
	pickle_dict = list()
	with open(json_path, "r") as fp:
		json_dict = json.load(fp)

	for i in range(HIGHEST_ID):
		pickle_dict.append(None)

	for item in json_dict:
		entry = json_dict[item]
		integer_encoded_item = item_to_integer(item)
		if not integer_encoded_item:
			continue
		try:
			pickle_dict[integer_encoded_item] = entry
		except:
			print(integer_encoded_item)

	with open(pickle_path, 'wb') as output:
		pickle.dump(pickle_dict, output, protocol=pickle.HIGHEST_PROTOCOL)


"""
MAIN
"""
if __name__ == "__main__":
	json_to_encoded_pickle("dicts/aliases_dict.json", "dicts/aliases.pickle")
	json_to_encoded_pickle("dicts/labels_dict.json", "dicts/labels.pickle")
	json_to_encoded_pickle("dicts/descriptions_dict.json", "dicts/descriptions.pickle")