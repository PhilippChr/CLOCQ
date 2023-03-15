import json
import pickle
import random
import re
import time
import requests


class CLOCQInterfaceClient:
	def __init__(self, host="http://localhost", port="7777"):
		self.host = host
		self.port = port
		self.req = requests.Session()
		self.ENTITY_PATTERN = re.compile("^Q[0-9]+$")
		self.PRED_PATTERN = re.compile("^P[0-9]+$")

	def get_label(self, kb_item):
		"""
		Retrieves a single label for the given KB item.
		E.g. "France national association football team" for "Q47774".

		Note: The n-triples Wikidata dump stores multiple labels (not aliases) for the same item.
		Here, we return the first KB label which is not exactly the KB item id (i.e. "Q47774").
		Shown as "Label" in Wikidata.
		"""
		params = {"item": kb_item}
		res = self._req("/item_to_label", params)
		json_string = res.content.decode("utf-8")
		label = json.loads(json_string)
		return label

	def get_labels(self, kb_item):
		"""
		Retrieves the list of label for the given KB item.
		E.g. ["France national association football team", "France national team"] for "Q47774".

		Note: The n-triples Wikidata dump stores multiple labels (not aliases) for the same item.
		Here, we return the full list of KB labels stored in the n-triples dump.
		Shown as "Label" in Wikidata.
		"""
		params = {"item": kb_item}
		res = self._req("/item_to_labels", params)
		json_string = res.content.decode("utf-8")
		label = json.loads(json_string)
		return label

	def get_aliases(self, kb_item):
		"""
		Retrieves the aliases for the given KB item.
		E.g. "France" for "Q47774".
		Shown as "Also known as" in Wikidata.
		"""
		params = {"item": kb_item}
		res = self._req("/item_to_aliases", params)
		json_string = res.content.decode("utf-8")
		aliases = json.loads(json_string)
		return aliases

	def get_description(self, kb_item):
		"""
		Retrieves the description for the given KB item.
		The descriptions can be seen on top of Wikidata pages.
		E.g. "men's national association football team representing France" for "Q47774".
		Shown as "Description" in Wikidata.
		"""
		params = {"item": kb_item}
		res = self._req("/item_to_description", params)
		json_string = res.content.decode("utf-8")
		aliases = json.loads(json_string)
		return aliases

	def get_types(self, kb_item):
		"""
		Retrieves the types for the given KB item.
		Returns list of items with keys: {"id", "label"}.
		E.g. [{"id": "Q6979593", "label": "national association football team"}] for "Q47774".
		"""
		params = {"item": kb_item}
		res = self._req("/item_to_types", params)
		json_string = res.content.decode("utf-8")
		types = json.loads(json_string)
		return types

	def get_type(self, kb_item):
		"""
		Retrieves the  most frequent type for the given KB item.
		Returns one item with keys: {"id", "label"}.
		E.g. {"id": "Q6979593", "label": "national association football team"} for "Q47774".
		"""
		params = {"item": kb_item}
		res = self._req("/item_to_type", params)
		json_string = res.content.decode("utf-8")
		types = json.loads(json_string)
		return types

	def get_frequency(self, kb_item):
		"""
		A list of two frequency numbers for the given KB item:
		- number of facts with the item occuring as subject
		- number of facts with the item occuring as object/qualifier-object.
		"""
		params = {"item": kb_item}
		res = self._req("/frequency", params)
		json_string = res.content.decode("utf-8")
		frequencies = json.loads(json_string)
		return frequencies

	def get_neighborhood(self, kb_item, p=1000, include_labels=True, include_type=False):
		"""
		Returns a list of facts including the item (the 1-hop neighborhood)
		each fact is a n-tuple, with subject, predicate, object and qualifier information.
		"""
		params = {"item": kb_item, "p": p, "include_labels": include_labels, "include_type": include_type}
		res = self._req("/neighborhood", params)
		json_string = res.content.decode("utf-8")
		neighbors = json.loads(json_string)
		return neighbors

	def get_neighborhood_two_hop(self, kb_item, p=1000, include_labels=True, include_type=False):
		"""
		Returns a list of facts in the 2-hop neighborhood of the item
		each fact is a n-tuple, with subject, predicate, object and qualifier information.
		"""
		params = {"item": kb_item, "p": p, "include_labels": include_labels, "include_type": include_type}
		res = self._req("/two_hop_neighborhood", params)
		json_string = res.content.decode("utf-8")
		neighbors = json.loads(json_string)
		return neighbors

	def connect(self, kb_item1, kb_item2):
		"""
		Returns a list of paths between item1 and item2. Each path is given by either 1 fact
		(1-hop connection) or 2 facts (2-hop connections).
		"""
		params = {"item1": kb_item1, "item2": kb_item2}
		res = self._req("/connect", params)
		json_string = res.content.decode("utf-8")
		paths = json.loads(json_string)
		return paths

	def connectivity_check(self, kb_item1, kb_item2):
		"""
		Returns the distance of the two items in the graph, given a fact-based definition.
		Returns 1 if the items are within 1 hop of each other,
		Returns 0.5 if the items are within 2 hops of each other,
		and returns 0 otherwise.
		"""
		params = {"item1": kb_item1, "item2": kb_item2}
		res = self._req("/connectivity_check", params)
		connectivity = float(res.content)
		return connectivity

	def relation_linking(self, question, parameters=dict(), top_ranked=True):
		"""
		Run relation linking on the given question.
		This method follows the approach submitted to the SMART 2022 task.
		For implementing the linking method, the standard CLOCQ algorithm is used.
		The output is a set of linkings: a list of dicts, with the mention and relation.
		"""
		params = {"question": question, "parameters": parameters, "top_ranked": top_ranked}
		res = self._req("/relation_linking", params, linking_path=True)
		json_string = res.content.decode("utf-8")
		result = json.loads(json_string)
		return result

	def entity_linking(self, question, parameters=dict(), k="AUTO"):
		"""
		Run entity linking on the given question.
		This method follows the approach submitted to the SMART 2022 task.
		For implementing the linking method, the standard CLOCQ algorithm is used.
		k can be given as part of the parameters dict, or separately.
		If both are given, the value in the parameters dict is used.
		The output is a set of linkings: a list of dicts, with the mention and entity.
		"""
		params = {"question": question, "parameters": parameters, "k": k}
		res = self._req("/entity_linking", params, linking_path=True)
		json_string = res.content.decode("utf-8")
		result = json.loads(json_string)
		return result

	def get_search_space(self, question, parameters=dict(), include_labels=True, include_type=False):
		"""
		Extract a question-specific context for the given question using the CLOCQ algorithm.
		Returns k (context tuple, context graph)-pairs for the given questions,
		i.e. a mapping of question words to KB items and a question-relevant KG subset.
		In case the dict is empty, the default CLOCQ parameters are used
		"""
		params = {"question": question, "parameters": parameters, "include_labels": include_labels, "include_type": include_type}
		res = self._req("/search_space", params)
		json_string = res.content.decode("utf-8")
		result = json.loads(json_string)
		return result

	def is_wikidata_entity(self, string):
		"""
		Check whether the given string can be a wikidata entity.
		"""
		return self.ENTITY_PATTERN.match(string) is not None

	def is_wikidata_predicate(self, string):
		"""
		Check whether the given string can be a wikidata predicate.
		"""
		return self.PRED_PATTERN.match(string) is not None

	def _req(self, action, json, linking_path=False):
		# linking has a different backend (wrapper around native CLOCQ API)
		if linking_path:
			return self.req.post(self.host.replace("api", "linking_api") + action, json=json)
		if self.port == "443":
			return self.req.post(self.host + action, json=json)
		else:
			return self.req.post(self.host + ":" + self.port + action, json=json)
		


"""
MAIN
"""
if __name__ == "__main__":
	clocq = CLOCQInterfaceClient(host="https://clocq.mpi-inf.mpg.de/api", port="443")

	kb_item = "Q5"
	res = clocq.get_label(kb_item)
	print(res)
